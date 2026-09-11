from __future__ import annotations

from typing import (
    Protocol,
    runtime_checkable,
)

from enterprise_genai.answering.evidence import (
    evidence_bundle_from_snapshot,
    unsupported_request_bundle,
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
    AnswerPayload,
    AnswerRequest,
    AnswerServiceResult,
    BooleanAnswerPayload,
    EntitiesAnswerPayload,
    EntityAnswerPayload,
    NumberAnswerPayload,
    TextAnswerPayload,
)
from enterprise_genai.application.specification import (
    AnswerSpecificationProviderProtocol,
    ExecutableAnswerSpecification,
    UnsupportedAnswerSpecification,
)
from enterprise_genai.generation.contracts import (
    GenerationAuthority,
    GenerationProvider,
    GroundedGenerationRequest,
    generation_request_from_outcome,
)
from enterprise_genai.generation.guarded import (
    SafeGenerationResult,
    render_deterministic_authority,
    resolve_safe_generation,
)
from enterprise_genai.generation.validation import (
    assess_generation_fidelity,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    OrchestrationStateSnapshot,
)

GROUNDED_ANSWERING_SERVICE_VERSION = "northstar-grounded-answering-service-v1"


@runtime_checkable
class AnswerExecutionRuntimeProtocol(Protocol):
    """Bounded orchestration runtime consumed by the service."""

    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot: ...


def _answer_payload(
    authority: GenerationAuthority,
) -> AnswerPayload:
    if authority.outcome != "answer":
        raise ValueError("answer payload requires answer authority")

    answer_type = authority.answer_type
    value = authority.value

    assert answer_type is not None
    assert value is not None

    if answer_type == "text":
        assert isinstance(
            value,
            str,
        )

        return TextAnswerPayload(value=value)

    if answer_type == "entity":
        assert isinstance(
            value,
            str,
        )

        return EntityAnswerPayload(value=value)

    if answer_type == "entities":
        assert isinstance(
            value,
            tuple,
        )

        return EntitiesAnswerPayload(value=value)

    if answer_type == "number":
        if isinstance(
            value,
            bool,
        ) or not isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            raise AssertionError("invalid numeric generation authority")

        return NumberAnswerPayload(
            value=value,
            unit=authority.unit,
        )

    if answer_type == "boolean":
        assert isinstance(
            value,
            bool,
        )

        return BooleanAnswerPayload(value=value)

    raise AssertionError("unsupported generation authority answer type")


def _deterministic_abstention(
    request: GroundedGenerationRequest,
) -> AbstainedServiceResult:
    authority = request.authority

    if authority.outcome != "abstain":
        raise ValueError("deterministic abstention requires abstention authority")

    reason = authority.reason

    assert reason is not None

    detail = "; ".join(authority.missing_information) if authority.missing_information else None

    return AbstainedServiceResult(
        presentation_source="deterministic",
        generation_fidelity="not_applicable",
        text=render_deterministic_authority(authority),
        citation_ids=(request.allowed_citation_ids),
        provenance_fact_ids=(authority.source_fact_ids),
        reason=reason,
        detail=detail,
    )


def _guarded_answer_result(
    *,
    request: GroundedGenerationRequest,
    safe: SafeGenerationResult,
) -> AnsweredServiceResult:
    authority = request.authority

    if authority.outcome != "answer":
        raise ValueError("guarded answer result requires answer authority")

    return AnsweredServiceResult(
        presentation_source=safe.source,
        generation_fidelity=(safe.fidelity.status),
        text=safe.text,
        citation_ids=safe.citation_ids,
        provenance_fact_ids=(authority.source_fact_ids),
        payload=_answer_payload(authority),
    )


class GroundedAnsweringService:
    """Compose frozen grounded-answering boundaries.

    The service does not infer tool selection, execution plans,
    evidence requirements, or synthesis instructions.
    """

    def __init__(
        self,
        *,
        specification_provider: (AnswerSpecificationProviderProtocol),
        runtime: AnswerExecutionRuntimeProtocol,
        generation_provider: GenerationProvider,
    ) -> None:
        self._specification_provider = specification_provider
        self._runtime = runtime
        self._generation_provider = generation_provider

    def answer(
        self,
        request: AnswerRequest,
    ) -> AnswerServiceResult:
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
            if synthesis is None:
                raise ValueError("sufficient evidence requires an explicit synthesis specification")

            outcome = synthesize_answer(
                assessment=assessment,
                instruction=(
                    SynthesisInstruction(
                        mode=synthesis.mode,
                        answer_type=(synthesis.answer_type),
                        answer_record_ids=(assessment.supporting_record_ids),
                    )
                ),
            )

        else:
            outcome = synthesize_answer(assessment=assessment)

        generation_request = generation_request_from_outcome(
            question=request.question,
            outcome=outcome,
        )

        # Deterministic abstentions never cross the
        # probabilistic generation-provider boundary.
        if generation_request.authority.outcome == "abstain":
            return _deterministic_abstention(generation_request)

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
