from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
)

from enterprise_genai.answering import (
    SUFFICIENCY_POLICY_VERSION,
    SYNTHESIS_VERSION,
)
from enterprise_genai.answering.sufficiency import (
    EvidenceRequirement,
)
from enterprise_genai.application import (
    HUMAN_REVIEW_WORKFLOW_VERSION,
    AnswerRequest,
    AnswerSynthesisSpecification,
    AwaitingHumanReviewResult,
    ExecutableAnswerSpecification,
    HumanReviewRejectedResult,
    ReviewedAnsweringService,
    UnsupportedAnswerSpecification,
)
from enterprise_genai.db.models import (
    HumanReviewRow,
)
from enterprise_genai.execution.contracts import (
    RetrievalHit,
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionPlan,
    ToolExecutionResult,
)
from enterprise_genai.generation.contracts import (
    GenerationProviderMetadata,
    GroundedGenerationRequest,
    RawGeneration,
)
from enterprise_genai.human_review import (
    HumanReviewDecision,
    HumanReviewNotFoundError,
    HumanReviewRepository,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    OrchestrationStateSnapshot,
)

QUESTION = "What defect affected ORBIS-IDX-7?"

AUTHORITY_TEXT = "ORBIS-IDX-7 suffered an indexing defect."


def _metadata() -> GenerationProviderMetadata:
    return GenerationProviderMetadata(
        provider_id="test-generation-provider",
        model_id="test-model",
        model_revision="test-revision",
        device="cpu",
        dtype="float32",
    )


def _plan() -> BoundedOrchestrationPlan:
    return BoundedOrchestrationPlan(
        question=QUESTION,
        execution_plan=ToolExecutionPlan(
            route_label="retrieval",
            retrieval=RetrievalQuery(question=QUESTION),
        ),
    )


def _requirement() -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="orbis-risk",
        description=("Evidence explicitly describing ORBIS-IDX-7."),
        allowed_tools=("retrieval",),
        allowed_kinds=("retrieval_hit",),
        all_terms=("ORBIS-IDX-7",),
    )


def _spec() -> ExecutableAnswerSpecification:
    return ExecutableAnswerSpecification(
        question=QUESTION,
        orchestration_plan=_plan(),
        requirements=(_requirement(),),
        synthesis=AnswerSynthesisSpecification(
            mode="retrieval_text",
            answer_type="text",
        ),
    )


def _snapshot() -> OrchestrationStateSnapshot:
    return OrchestrationStateSnapshot(
        plan=_plan(),
        results=(
            ToolExecutionResult(
                tool="retrieval",
                status="ok",
                duration_ms=0.0,
                payload=RetrievalPayload(
                    hits=(
                        RetrievalHit(
                            rank=1,
                            chunk_id="CHUNK-001",
                            evidence_id="EVID-001",
                            document_id="DOC-001",
                            text=AUTHORITY_TEXT,
                            source_fact_ids=("RISK-006",),
                            rrf_score=1.0,
                        ),
                    )
                ),
            ),
        ),
        status="completed",
    )


class StaticSpecificationProvider:
    def __init__(
        self,
        specification,
    ) -> None:
        self.specification = specification
        self.calls = 0

    def prepare(
        self,
        request: AnswerRequest,
    ):
        self.calls += 1

        return self.specification


class NoCallSpecificationProvider:
    def prepare(
        self,
        request: AnswerRequest,
    ):
        raise AssertionError("specification must not rerun during resume")


class FixedRuntime:
    def __init__(
        self,
        snapshot: OrchestrationStateSnapshot,
    ) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot:
        self.calls += 1

        return self.snapshot


class NoCallRuntime:
    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot:
        raise AssertionError("runtime must not rerun during resume")


class FakeGenerationProvider:
    def __init__(
        self,
        text: str = AUTHORITY_TEXT,
    ) -> None:
        self.text = text
        self.calls = 0
        self.last_request = None

    def generate(
        self,
        request: GroundedGenerationRequest,
    ) -> RawGeneration:
        self.calls += 1
        self.last_request = request

        return RawGeneration(
            text=self.text,
            metadata=_metadata(),
        )


class NoCallGenerationProvider:
    def generate(
        self,
        request: GroundedGenerationRequest,
    ) -> RawGeneration:
        raise AssertionError("generation must not be invoked")


def _session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    HumanReviewRow.__table__.create(engine)

    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


def _reviewed_service(
    *,
    session_factory,
    specification_provider=None,
    runtime=None,
    generation_provider=None,
) -> ReviewedAnsweringService:
    return ReviewedAnsweringService(
        specification_provider=(
            specification_provider
            if specification_provider is not None
            else StaticSpecificationProvider(_spec())
        ),
        runtime=(runtime if runtime is not None else FixedRuntime(_snapshot())),
        generation_provider=(
            generation_provider if generation_provider is not None else FakeGenerationProvider()
        ),
        session_factory=session_factory,
    )


def test_reviewed_workflow_version_is_frozen() -> None:
    assert HUMAN_REVIEW_WORKFLOW_VERSION == ("northstar-human-review-workflow-v1")


def test_start_persists_prepared_answer_and_returns_control() -> None:
    session_factory = _session_factory()

    specification_provider = StaticSpecificationProvider(_spec())

    runtime = FixedRuntime(_snapshot())

    generation_provider = FakeGenerationProvider()

    service = _reviewed_service(
        session_factory=session_factory,
        specification_provider=(specification_provider),
        runtime=runtime,
        generation_provider=(generation_provider),
    )

    result = service.start(
        AnswerRequest(question=QUESTION),
        review_id="review-1",
    )

    assert isinstance(
        result,
        AwaitingHumanReviewResult,
    )

    assert result.status == "awaiting_review"
    assert result.review_id == "review-1"
    assert result.revision == 1

    assert specification_provider.calls == 1
    assert runtime.calls == 1
    assert generation_provider.calls == 0

    review = service.inspect("review-1")

    assert review.status == "awaiting_review"
    assert review.answer_type == "text"
    assert review.answer_value == AUTHORITY_TEXT
    assert review.supporting_record_ids == ("RET:001:EVID-001",)
    assert review.citation_ids == ("RET:001:EVID-001",)
    assert review.source_fact_ids == ("RISK-006",)
    assert review.synthesis_version == (SYNTHESIS_VERSION)
    assert review.sufficiency_policy_version == (SUFFICIENCY_POLICY_VERSION)

    assert len(review.evidence) == 1

    evidence = review.evidence[0]

    assert evidence.record_id == ("RET:001:EVID-001")
    assert evidence.content == AUTHORITY_TEXT
    assert evidence.document_id == "DOC-001"
    assert evidence.source_fact_ids == ("RISK-006",)


def test_resume_awaiting_review_does_not_generate() -> None:
    session_factory = _session_factory()

    service = _reviewed_service(
        session_factory=session_factory,
    )

    service.start(
        AnswerRequest(question=QUESTION),
        review_id="review-1",
    )

    restarted = _reviewed_service(
        session_factory=session_factory,
        specification_provider=(NoCallSpecificationProvider()),
        runtime=NoCallRuntime(),
        generation_provider=(NoCallGenerationProvider()),
    )

    result = restarted.resume("review-1")

    assert isinstance(
        result,
        AwaitingHumanReviewResult,
    )
    assert result.status == "awaiting_review"
    assert result.revision == 1


def test_approval_resume_uses_only_persisted_authority() -> None:
    session_factory = _session_factory()

    service = _reviewed_service(
        session_factory=session_factory,
    )

    service.start(
        AnswerRequest(question=QUESTION),
        review_id="review-1",
    )

    decision = service.decide(
        HumanReviewDecision(
            review_id="review-1",
            disposition="approve",
            reviewer_identity="reviewer-1",
        )
    )

    assert decision.status == "approved"
    assert decision.revision == 2

    generation_provider = FakeGenerationProvider()

    restarted = _reviewed_service(
        session_factory=session_factory,
        specification_provider=(NoCallSpecificationProvider()),
        runtime=NoCallRuntime(),
        generation_provider=(generation_provider),
    )

    result = restarted.resume("review-1")

    assert result.status == "answered"
    assert result.text == AUTHORITY_TEXT
    assert result.payload.answer_type == "text"
    assert result.payload.value == AUTHORITY_TEXT
    assert result.citation_ids == ("RET:001:EVID-001",)
    assert result.provenance_fact_ids == ("RISK-006",)

    assert generation_provider.calls == 1

    request = generation_provider.last_request

    assert request is not None
    assert request.question == QUESTION

    assert request.authority.outcome == "answer"
    assert request.authority.answer_type == "text"
    assert request.authority.value == (AUTHORITY_TEXT)
    assert request.authority.supporting_record_ids == ("RET:001:EVID-001",)
    assert request.authority.source_fact_ids == ("RISK-006",)

    assert request.allowed_citation_ids == ("RET:001:EVID-001",)

    assert len(request.evidence) == 1
    assert request.evidence[0].content == (AUTHORITY_TEXT)


def test_rejection_is_terminal_and_never_generates() -> None:
    session_factory = _session_factory()

    service = _reviewed_service(
        session_factory=session_factory,
    )

    service.start(
        AnswerRequest(question=QUESTION),
        review_id="review-1",
    )

    rejected = service.decide(
        HumanReviewDecision(
            review_id="review-1",
            disposition="reject",
            reviewer_identity="reviewer-1",
        )
    )

    assert rejected.status == "rejected"
    assert rejected.revision == 2

    restarted = _reviewed_service(
        session_factory=session_factory,
        specification_provider=(NoCallSpecificationProvider()),
        runtime=NoCallRuntime(),
        generation_provider=(NoCallGenerationProvider()),
    )

    result = restarted.resume("review-1")

    assert isinstance(
        result,
        HumanReviewRejectedResult,
    )
    assert result.status == "human_rejected"
    assert result.review_id == "review-1"
    assert result.reviewer_identity == ("reviewer-1")
    assert result.revision == 2


def test_unsupported_request_never_creates_review() -> None:
    session_factory = _session_factory()

    question = "What was Alder Manufacturing's exact customer churn rate?"

    service = _reviewed_service(
        session_factory=session_factory,
        specification_provider=(
            StaticSpecificationProvider(
                UnsupportedAnswerSpecification(
                    question=question,
                    detail=("customer_churn_rate is outside the bounded structured metric set"),
                )
            )
        ),
        runtime=NoCallRuntime(),
        generation_provider=(NoCallGenerationProvider()),
    )

    result = service.start(
        AnswerRequest(question=question),
        review_id="review-unsupported",
    )

    assert result.status == "abstained"
    assert result.reason == ("unsupported_request")

    with session_factory() as session:
        repository = HumanReviewRepository(session)

        with pytest.raises(HumanReviewNotFoundError):
            repository.get("review-unsupported")


def test_exact_decision_replay_remains_idempotent() -> None:
    session_factory = _session_factory()

    service = _reviewed_service(
        session_factory=session_factory,
    )

    service.start(
        AnswerRequest(question=QUESTION),
        review_id="review-1",
    )

    decision = HumanReviewDecision(
        review_id="review-1",
        disposition="approve",
        reviewer_identity="reviewer-1",
    )

    first = service.decide(decision)

    replay = service.decide(decision)

    assert replay == first
    assert replay.status == "approved"
    assert replay.revision == 2
