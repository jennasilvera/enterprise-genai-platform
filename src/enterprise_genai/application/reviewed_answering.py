from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import model_validator
from sqlalchemy.orm import Session

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
)
from enterprise_genai.answering.evidence import (
    evidence_bundle_from_snapshot,
    unsupported_request_bundle,
)
from enterprise_genai.answering.instruction_integrity import (
    evaluate_instruction_integrity,
)
from enterprise_genai.answering.outcomes import (
    GroundedAnswer,
)
from enterprise_genai.answering.sufficiency import (
    evaluate_sufficiency,
)
from enterprise_genai.answering.synthesis import (
    SynthesisInstruction,
    synthesize_answer,
)
from enterprise_genai.application.answering import (
    AbstainedServiceResult,
    AnsweredServiceResult,
    AnswerRequest,
)
from enterprise_genai.application.service import (
    AnswerExecutionRuntimeProtocol,
    _deterministic_abstention,
    _guarded_answer_result,
    _instruction_integrity_abstention,
)
from enterprise_genai.application.specification import (
    AnswerSpecificationProviderProtocol,
    ExecutableAnswerSpecification,
    UnsupportedAnswerSpecification,
)
from enterprise_genai.generation.contracts import (
    GenerationAuthority,
    GenerationEvidence,
    GenerationProvider,
    GroundedGenerationRequest,
    generation_request_from_outcome,
)
from enterprise_genai.generation.guarded import (
    resolve_safe_generation,
)
from enterprise_genai.generation.validation import (
    assess_generation_fidelity,
)
from enterprise_genai.human_review.contracts import (
    HUMAN_REVIEW_CONTRACT_VERSION,
    HumanReviewDecision,
    HumanReviewEvidence,
    HumanReviewRequest,
)
from enterprise_genai.human_review.repository import (
    HumanReviewRepository,
)

HUMAN_REVIEW_WORKFLOW_VERSION = "northstar-human-review-workflow-v1"


class AwaitingHumanReviewResult(FrozenAnsweringModel):
    """Control returned after a prepared answer is durably paused."""

    status: Literal["awaiting_review"] = "awaiting_review"

    review_id: NonEmptyStr

    revision: Literal[1] = 1

    contract_version: NonEmptyStr = HUMAN_REVIEW_CONTRACT_VERSION

    @model_validator(mode="after")
    def validate_result(
        self,
    ) -> AwaitingHumanReviewResult:
        if self.contract_version != HUMAN_REVIEW_CONTRACT_VERSION:
            raise ValueError("Awaiting review result requires the frozen review contract version.")

        return self


class HumanReviewRejectedResult(FrozenAnsweringModel):
    """Terminal human rejection with no answer presentation."""

    status: Literal["human_rejected"] = "human_rejected"

    review_id: NonEmptyStr

    reviewer_identity: NonEmptyStr

    reason: Literal["human_rejected"] = "human_rejected"

    revision: Literal[2] = 2

    contract_version: NonEmptyStr = HUMAN_REVIEW_CONTRACT_VERSION

    @model_validator(mode="after")
    def validate_result(
        self,
    ) -> HumanReviewRejectedResult:
        if self.contract_version != HUMAN_REVIEW_CONTRACT_VERSION:
            raise ValueError("Human-rejected result requires the frozen review contract version.")

        return self


ReviewedAnswerStartResult = AwaitingHumanReviewResult | AbstainedServiceResult

ReviewedAnswerResumeResult = (
    AwaitingHumanReviewResult | HumanReviewRejectedResult | AnsweredServiceResult
)


def _human_review_from_grounded_answer(
    *,
    review_id: str,
    question: str,
    outcome: GroundedAnswer,
) -> HumanReviewRequest:
    if question != outcome.assessment.bundle.question:
        raise ValueError(
            "Human-review question must exactly match the deterministic outcome question."
        )

    records_by_id = {record.record_id: record for record in outcome.assessment.bundle.records}

    selected_records = tuple(
        records_by_id[record_id] for record_id in outcome.supporting_record_ids
    )

    evidence = tuple(
        HumanReviewEvidence(
            record_id=record.record_id,
            tool=record.tool,
            kind=record.kind,
            content=record.summary,
            source_fact_ids=record.source_fact_ids,
            document_id=record.document_id,
        )
        for record in selected_records
    )

    return HumanReviewRequest(
        review_id=review_id,
        question=question,
        answer_type=outcome.answer_type,
        answer_value=outcome.value,
        unit=outcome.unit,
        supporting_record_ids=outcome.supporting_record_ids,
        citation_ids=outcome.supporting_record_ids,
        source_fact_ids=outcome.source_fact_ids,
        evidence=evidence,
        synthesis_version=outcome.synthesis_version,
        sufficiency_policy_version=(outcome.assessment.policy_version),
    )


def generation_request_from_human_review(
    review: HumanReviewRequest,
) -> GroundedGenerationRequest:
    """Reconstruct approved generation authority from persisted review state."""

    if review.status != "approved":
        raise ValueError("Only an approved human review may construct generation authority.")

    if review.decision != "approve":
        raise ValueError("Approved human review must contain an approve decision.")

    evidence = tuple(
        GenerationEvidence(
            record_id=item.record_id,
            tool=item.tool,
            kind=item.kind,
            content=item.content,
            source_fact_ids=item.source_fact_ids,
            document_id=item.document_id,
        )
        for item in review.evidence
    )

    authority = GenerationAuthority(
        outcome="answer",
        answer_type=review.answer_type,
        value=review.answer_value,
        unit=review.unit,
        supporting_record_ids=(review.supporting_record_ids),
        source_fact_ids=review.source_fact_ids,
    )

    return GroundedGenerationRequest(
        question=review.question,
        authority=authority,
        evidence=evidence,
        allowed_citation_ids=review.citation_ids,
    )


class ReviewedAnsweringService:
    """Persisted external human-review workflow.

    The reviewed path is additive. It does not alter the ordinary
    GroundedAnsweringService answer path.

    Start performs bounded deterministic preparation and persists the
    prepared grounded answer before any generation authority is built.

    Decide records a separately supplied human decision.

    Resume reloads persisted state. Approval constructs generation
    authority only from the persisted snapshot; rejection never invokes
    generation.
    """

    def __init__(
        self,
        *,
        specification_provider: AnswerSpecificationProviderProtocol,
        runtime: AnswerExecutionRuntimeProtocol,
        generation_provider: GenerationProvider,
        session_factory: Callable[[], Session],
    ) -> None:
        self._specification_provider = specification_provider
        self._runtime = runtime
        self._generation_provider = generation_provider
        self._session_factory = session_factory

    def _prepare(
        self,
        request: AnswerRequest,
    ) -> GroundedAnswer | AbstainedServiceResult:
        specification = self._specification_provider.prepare(request)

        if specification.question != request.question:
            raise ValueError(
                "answer specification question must exactly match the incoming request question"
            )

        if isinstance(
            specification,
            UnsupportedAnswerSpecification,
        ):
            bundle = unsupported_request_bundle(
                question=request.question,
                detail=specification.detail,
            )

            requirements = ()
            synthesis = None

        elif isinstance(
            specification,
            ExecutableAnswerSpecification,
        ):
            snapshot = self._runtime.execute(specification.orchestration_plan)

            if snapshot.plan != specification.orchestration_plan:
                raise RuntimeError(
                    "answering runtime returned a snapshot for a different orchestration plan"
                )

            bundle = evidence_bundle_from_snapshot(snapshot)

            requirements = specification.requirements
            synthesis = specification.synthesis

        else:
            raise TypeError("unsupported answer specification")

        assessment = evaluate_sufficiency(
            bundle=bundle,
            requirements=requirements,
        )

        if assessment.status == "sufficient":
            integrity_decision = evaluate_instruction_integrity(assessment=assessment)

            if integrity_decision.disposition == "block":
                return _instruction_integrity_abstention(
                    assessment=assessment,
                    decision=integrity_decision,
                )

            if synthesis is None:
                raise ValueError("sufficient evidence requires an explicit synthesis specification")

            outcome = synthesize_answer(
                assessment=assessment,
                instruction=SynthesisInstruction(
                    mode=synthesis.mode,
                    answer_type=(synthesis.answer_type),
                    answer_record_ids=(assessment.supporting_record_ids),
                ),
            )

        else:
            outcome = synthesize_answer(assessment=assessment)

        if isinstance(
            outcome,
            GroundedAnswer,
        ):
            return outcome

        generation_request = generation_request_from_outcome(
            question=request.question,
            outcome=outcome,
        )

        return _deterministic_abstention(generation_request)

    def start(
        self,
        request: AnswerRequest,
        *,
        review_id: str,
    ) -> ReviewedAnswerStartResult:
        prepared = self._prepare(request)

        if isinstance(
            prepared,
            AbstainedServiceResult,
        ):
            return prepared

        review = _human_review_from_grounded_answer(
            review_id=review_id,
            question=request.question,
            outcome=prepared,
        )

        with self._session_factory() as session:
            persisted = HumanReviewRepository(session).create(review)

            session.commit()

        return AwaitingHumanReviewResult(
            review_id=persisted.review_id,
            revision=persisted.revision,
            contract_version=(persisted.contract_version),
        )

    def inspect(
        self,
        review_id: str,
    ) -> HumanReviewRequest:
        with self._session_factory() as session:
            return HumanReviewRepository(session).get(review_id)

    def decide(
        self,
        decision: HumanReviewDecision,
    ) -> HumanReviewRequest:
        with self._session_factory() as session:
            persisted = HumanReviewRepository(session).decide(decision)

            session.commit()

        return persisted

    def resume(
        self,
        review_id: str,
    ) -> ReviewedAnswerResumeResult:
        review = self.inspect(review_id)

        if review.status == "awaiting_review":
            return AwaitingHumanReviewResult(
                review_id=review.review_id,
                revision=review.revision,
                contract_version=(review.contract_version),
            )

        if review.status == "rejected":
            reviewer_identity = review.reviewer_identity

            assert reviewer_identity is not None

            return HumanReviewRejectedResult(
                review_id=review.review_id,
                reviewer_identity=(reviewer_identity),
                revision=review.revision,
                contract_version=(review.contract_version),
            )

        if review.status != "approved":
            raise AssertionError("unreachable human-review lifecycle state")

        generation_request = generation_request_from_human_review(review)

        raw = self._generation_provider.generate(generation_request)

        fidelity = assess_generation_fidelity(
            request=generation_request,
            raw_generation=raw,
        )

        safe = resolve_safe_generation(fidelity)

        return _guarded_answer_result(
            request=generation_request,
            safe=safe,
        )
