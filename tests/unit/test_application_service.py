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


class _ObservabilityLogger:
    def __init__(
        self,
    ) -> None:
        self.events: list[
            tuple[
                str,
                str,
                dict[
                    str,
                    object,
                ],
            ]
        ] = []

    def info(
        self,
        event: str,
        **kwargs,
    ) -> None:
        self.events.append(
            (
                "info",
                event,
                kwargs,
            )
        )

    def error(
        self,
        event: str,
        **kwargs,
    ) -> None:
        self.events.append(
            (
                "error",
                event,
                kwargs,
            )
        )


class _IncrementingClock:
    def __init__(
        self,
    ) -> None:
        self.value = 0.0

    def __call__(
        self,
    ) -> float:
        self.value += 0.001

        return self.value


def test_answer_service_observability_trace_version() -> None:
    from enterprise_genai.observability.answering import (
        ANSWER_SERVICE_TRACE_VERSION,
    )

    assert ANSWER_SERVICE_TRACE_VERSION == "northstar-answer-service-trace-v1"


def test_answer_service_observability_is_privacy_safe_and_correlated(
    monkeypatch,
) -> None:
    from structlog.contextvars import (
        bind_contextvars,
        clear_contextvars,
    )

    import enterprise_genai.application.service as service_module

    fake = _ObservabilityLogger()

    monkeypatch.setattr(
        service_module,
        "logger",
        fake,
    )

    request_id = "request-observability-test"

    bind_contextvars(request_id=request_id)

    try:
        service = GroundedAnsweringService(
            specification_provider=(StaticSpecificationProvider(_spec())),
            runtime=(FixedRuntime(_snapshot())),
            generation_provider=(FakeGenerationProvider(AUTHORITY_TEXT)),
            clock=(_IncrementingClock()),
        )

        result = service.answer(AnswerRequest(question=QUESTION))

    finally:
        clear_contextvars()

    assert result.status == "answered"

    event_names = tuple(event for _level, event, _fields in fake.events)

    assert event_names == (
        "answer_service_started",
        "answer_specification_prepared",
        "answer_execution_completed",
        "answer_sufficiency_evaluated",
        "answer_generation_completed",
        "answer_service_completed",
    )

    for (
        _level,
        _event,
        fields,
    ) in fake.events:
        assert fields["request_id"] == request_id

        assert fields["answer_trace_version"] == ("northstar-answer-service-trace-v1")

    completed = fake.events[-1][2]

    assert completed["specification_kind"] == "executable"

    assert completed["route_label"] == "retrieval"

    assert completed["tools"] == ("retrieval",)

    assert completed["status"] == "answered"

    assert completed["presentation_source"] == "model_generation"

    assert completed["generation_fidelity"] == "accepted"

    assert completed["generation_invoked"] is True

    assert completed["tool_durations_ms"] == {
        "retrieval": 0.0,
    }

    assert set(completed["stage_durations_ms"]) == {
        "specification",
        "execution",
        "evidence",
        "sufficiency",
        "synthesis",
        "generation",
        "fidelity",
    }

    assert completed["total_duration_ms"] >= 0.0

    serialized = repr(fake.events)

    assert QUESTION not in serialized

    assert AUTHORITY_TEXT not in serialized

    assert "EVID-001" not in serialized

    assert "RISK-006" not in serialized


def test_unsupported_observability_skips_execution_and_generation(
    monkeypatch,
) -> None:
    import enterprise_genai.application.service as service_module

    question = "What was Alder Manufacturing's exact customer churn rate?"

    sensitive_detail = "PRIVATE-UNSUPPORTED-DETAIL"

    fake = _ObservabilityLogger()

    monkeypatch.setattr(
        service_module,
        "logger",
        fake,
    )

    service = GroundedAnsweringService(
        specification_provider=(
            StaticSpecificationProvider(
                UnsupportedAnswerSpecification(
                    question=question,
                    detail=(sensitive_detail),
                )
            )
        ),
        runtime=NoCallRuntime(),
        generation_provider=(NoCallGenerationProvider()),
        clock=(_IncrementingClock()),
    )

    result = service.answer(AnswerRequest(question=question))

    assert result.status == "abstained"

    event_names = tuple(event for _level, event, _fields in fake.events)

    assert event_names == (
        "answer_service_started",
        "answer_specification_prepared",
        "answer_sufficiency_evaluated",
        "answer_generation_skipped",
        "answer_service_completed",
    )

    completed = fake.events[-1][2]

    assert completed["specification_kind"] == "unsupported"

    assert completed["route_label"] is None

    assert completed["tools"] == ()

    assert completed["generation_invoked"] is False

    assert completed["presentation_source"] == "deterministic"

    assert completed["generation_fidelity"] == "not_applicable"

    assert completed["abstention_reason"] == "unsupported_request"

    serialized = repr(fake.events)

    assert question not in serialized

    assert sensitive_detail not in serialized


def test_answer_service_failure_observability_redacts_exception_message(
    monkeypatch,
) -> None:
    import enterprise_genai.application.service as service_module

    sensitive_error = "PRIVATE-PROVIDER-FAILURE"

    fake = _ObservabilityLogger()

    monkeypatch.setattr(
        service_module,
        "logger",
        fake,
    )

    class RaisingProvider:
        def generate(
            self,
            request: GroundedGenerationRequest,
        ) -> RawGeneration:
            raise RuntimeError(sensitive_error)

    service = GroundedAnsweringService(
        specification_provider=(StaticSpecificationProvider(_spec())),
        runtime=(FixedRuntime(_snapshot())),
        generation_provider=(RaisingProvider()),
        clock=(_IncrementingClock()),
    )

    with pytest.raises(
        RuntimeError,
        match=sensitive_error,
    ):
        service.answer(AnswerRequest(question=QUESTION))

    level, event, fields = fake.events[-1]

    assert level == "error"

    assert event == "answer_service_failed"

    assert fields["stage"] == "generation"

    assert fields["error_type"] == "RuntimeError"

    assert fields["generation_invoked"] is True

    assert sensitive_error not in repr(fake.events)

    assert QUESTION not in repr(fake.events)
