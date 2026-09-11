from __future__ import annotations

import pytest

from enterprise_genai.answering.sufficiency import (
    EvidenceRequirement,
)
from enterprise_genai.application import (
    GROUNDED_ANSWERING_SERVICE_VERSION,
    AnswerExecutionRuntimeProtocol,
    AnsweringServiceProtocol,
    AnswerRequest,
    AnswerSynthesisSpecification,
    ExecutableAnswerSpecification,
    GroundedAnsweringService,
    UnsupportedAnswerSpecification,
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


def _plan(
    question: str = QUESTION,
) -> BoundedOrchestrationPlan:
    return BoundedOrchestrationPlan(
        question=question,
        execution_plan=(
            ToolExecutionPlan(
                route_label="retrieval",
                retrieval=RetrievalQuery(
                    question=question,
                ),
            )
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


def _spec(
    *,
    synthesis: bool = True,
) -> ExecutableAnswerSpecification:
    return ExecutableAnswerSpecification(
        question=QUESTION,
        orchestration_plan=_plan(),
        requirements=(_requirement(),),
        synthesis=(
            AnswerSynthesisSpecification(
                mode="retrieval_text",
                answer_type="text",
            )
            if synthesis
            else None
        ),
    )


def _snapshot(
    plan: BoundedOrchestrationPlan | None = None,
) -> OrchestrationStateSnapshot:
    effective_plan = plan if plan is not None else _plan()

    return OrchestrationStateSnapshot(
        plan=effective_plan,
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


class FakeGenerationProvider:
    def __init__(
        self,
        text: str,
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


class NoCallRuntime:
    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot:
        raise AssertionError("runtime must not be called")


class NoCallGenerationProvider:
    def generate(
        self,
        request: GroundedGenerationRequest,
    ) -> RawGeneration:
        raise AssertionError("generation provider must not be called")


def test_service_version_is_frozen() -> None:
    assert GROUNDED_ANSWERING_SERVICE_VERSION == "northstar-grounded-answering-service-v1"


def test_service_is_structural_answering_service() -> None:
    service = GroundedAnsweringService(
        specification_provider=(StaticSpecificationProvider(_spec())),
        runtime=FixedRuntime(_snapshot()),
        generation_provider=(FakeGenerationProvider(AUTHORITY_TEXT)),
    )

    assert isinstance(
        service,
        AnsweringServiceProtocol,
    )

    assert isinstance(
        service._runtime,
        AnswerExecutionRuntimeProtocol,
    )


def test_specification_question_must_match_request() -> None:
    specification = UnsupportedAnswerSpecification(
        question="Different question?",
        detail="unsupported",
    )

    service = GroundedAnsweringService(
        specification_provider=(StaticSpecificationProvider(specification)),
        runtime=NoCallRuntime(),
        generation_provider=(NoCallGenerationProvider()),
    )

    with pytest.raises(
        ValueError,
        match="incoming request question",
    ):
        service.answer(AnswerRequest(question=QUESTION))


def test_runtime_snapshot_must_match_requested_plan() -> None:
    different_plan = _plan("Different runtime question?")

    service = GroundedAnsweringService(
        specification_provider=(StaticSpecificationProvider(_spec())),
        runtime=FixedRuntime(_snapshot(different_plan)),
        generation_provider=(NoCallGenerationProvider()),
    )

    with pytest.raises(
        RuntimeError,
        match="different orchestration plan",
    ):
        service.answer(AnswerRequest(question=QUESTION))


def test_sufficient_evidence_requires_synthesis_specification() -> None:
    service = GroundedAnsweringService(
        specification_provider=(StaticSpecificationProvider(_spec(synthesis=False))),
        runtime=FixedRuntime(_snapshot()),
        generation_provider=(NoCallGenerationProvider()),
    )

    with pytest.raises(
        ValueError,
        match="explicit synthesis specification",
    ):
        service.answer(AnswerRequest(question=QUESTION))


def test_accepted_generation_crosses_presentation_boundary() -> None:
    provider = FakeGenerationProvider(AUTHORITY_TEXT)

    service = GroundedAnsweringService(
        specification_provider=(StaticSpecificationProvider(_spec())),
        runtime=FixedRuntime(_snapshot()),
        generation_provider=provider,
    )

    result = service.answer(AnswerRequest(question=QUESTION))

    assert result.status == "answered"

    assert result.presentation_source == "model_generation"

    assert result.generation_fidelity == "accepted"

    assert result.text == AUTHORITY_TEXT

    assert result.payload.answer_type == "text"

    assert result.payload.value == AUTHORITY_TEXT

    assert result.citation_ids == ("RET:001:EVID-001",)

    assert result.provenance_fact_ids == ("RISK-006",)

    assert provider.calls == 1


def test_rejected_generation_falls_back_to_authority() -> None:
    provider = FakeGenerationProvider("A different issue affected the system.")

    service = GroundedAnsweringService(
        specification_provider=(StaticSpecificationProvider(_spec())),
        runtime=FixedRuntime(_snapshot()),
        generation_provider=provider,
    )

    result = service.answer(AnswerRequest(question=QUESTION))

    assert result.status == "answered"

    assert result.presentation_source == "deterministic_fallback"

    assert result.generation_fidelity == "rejected"

    assert result.text == AUTHORITY_TEXT

    assert result.payload.value == AUTHORITY_TEXT


def test_unsupported_abstention_skips_runtime_and_generation() -> None:
    question = "What was Alder Manufacturing's exact customer churn rate?"

    service = GroundedAnsweringService(
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

    result = service.answer(AnswerRequest(question=question))

    assert result.status == "abstained"

    assert result.presentation_source == "deterministic"

    assert result.generation_fidelity == "not_applicable"

    assert result.reason == "unsupported_request"

    assert "customer_churn_rate" in (result.detail or "")

    assert result.citation_ids == ()

    assert result.provenance_fact_ids == ()


def test_generation_provider_failure_propagates() -> None:
    class RaisingProvider:
        def generate(
            self,
            request: GroundedGenerationRequest,
        ) -> RawGeneration:
            raise RuntimeError("simulated provider outage")

    service = GroundedAnsweringService(
        specification_provider=(StaticSpecificationProvider(_spec())),
        runtime=FixedRuntime(_snapshot()),
        generation_provider=(RaisingProvider()),
    )

    with pytest.raises(
        RuntimeError,
        match="simulated provider outage",
    ):
        service.answer(AnswerRequest(question=QUESTION))
