from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import (
    Protocol,
    runtime_checkable,
)

import structlog

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
from enterprise_genai.observability.answering import (
    duration_ms,
    request_trace_fields,
)
from enterprise_genai.observability.metrics import (
    OperationalMetricsRegistry,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    OrchestrationStateSnapshot,
)

GROUNDED_ANSWERING_SERVICE_VERSION = "northstar-grounded-answering-service-v1"

logger = structlog.get_logger()


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

    Operational tracing is privacy-safe by construction: events use
    bounded taxonomy, status, and duration fields and never include
    question text, evidence contents, prompts, model output, or
    answer text.
    """

    def __init__(
        self,
        *,
        specification_provider: (AnswerSpecificationProviderProtocol),
        runtime: AnswerExecutionRuntimeProtocol,
        generation_provider: GenerationProvider,
        metrics_registry: (OperationalMetricsRegistry | None) = None,
        clock: Callable[
            [],
            float,
        ] = perf_counter,
    ) -> None:
        self._specification_provider = specification_provider

        self._runtime = runtime

        self._generation_provider = generation_provider

        self._metrics_registry = metrics_registry

        self._clock = clock

    def answer(
        self,
        request: AnswerRequest,
    ) -> AnswerServiceResult:
        service_started_at = self._clock()

        trace_fields = request_trace_fields()

        stage_durations_ms: dict[
            str,
            float,
        ] = {}

        tool_durations_ms: dict[
            str,
            float,
        ] = {}

        tool_statuses: dict[
            str,
            str,
        ] = {}

        specification_kind: str | None = None

        route_label: str | None = None

        tools: tuple[
            str,
            ...,
        ] = ()

        generation_invoked = False

        current_stage = "specification"

        logger.info(
            "answer_service_started",
            **trace_fields,
        )

        try:
            # -------------------------------------
            # Specification
            # -------------------------------------

            started_at = self._clock()

            specification = self._specification_provider.prepare(request)

            stage_durations_ms["specification"] = duration_ms(
                clock=self._clock,
                started_at=started_at,
            )

            if specification.question != request.question:
                raise ValueError(
                    "answer specification question must exactly match the incoming request question"
                )

            specification_kind = specification.kind

            if isinstance(
                specification,
                ExecutableAnswerSpecification,
            ):
                execution_plan = specification.orchestration_plan.execution_plan

                route_label = execution_plan.route_label

                tools = tuple(execution_plan.required_tools())

            logger.info(
                "answer_specification_prepared",
                **trace_fields,
                specification_kind=(specification_kind),
                route_label=route_label,
                tools=tools,
                duration_ms=(stage_durations_ms["specification"]),
            )

            # -------------------------------------
            # Execution / evidence
            # -------------------------------------

            if isinstance(
                specification,
                UnsupportedAnswerSpecification,
            ):
                current_stage = "evidence"

                started_at = self._clock()

                bundle = unsupported_request_bundle(
                    question=(request.question),
                    detail=(specification.detail),
                )

                stage_durations_ms["evidence"] = duration_ms(
                    clock=self._clock,
                    started_at=(started_at),
                )

                requirements = ()
                synthesis = None

            elif isinstance(
                specification,
                ExecutableAnswerSpecification,
            ):
                current_stage = "execution"

                started_at = self._clock()

                snapshot = self._runtime.execute(specification.orchestration_plan)

                stage_durations_ms["execution"] = duration_ms(
                    clock=self._clock,
                    started_at=(started_at),
                )

                if snapshot.plan != specification.orchestration_plan:
                    raise RuntimeError(
                        "answering runtime returned a snapshot for a different orchestration plan"
                    )

                tool_durations_ms = {result.tool: result.duration_ms for result in snapshot.results}

                tool_statuses = {result.tool: result.status for result in snapshot.results}

                logger.info(
                    "answer_execution_completed",
                    **trace_fields,
                    route_label=(route_label),
                    tools=tools,
                    orchestration_status=(snapshot.status),
                    tool_statuses=(tool_statuses),
                    tool_durations_ms=(tool_durations_ms),
                    duration_ms=(stage_durations_ms["execution"]),
                )

                current_stage = "evidence"

                started_at = self._clock()

                bundle = evidence_bundle_from_snapshot(snapshot)

                stage_durations_ms["evidence"] = duration_ms(
                    clock=self._clock,
                    started_at=(started_at),
                )

                requirements = specification.requirements

                synthesis = specification.synthesis

            else:
                raise TypeError("unsupported answer specification")

            # -------------------------------------
            # Sufficiency
            # -------------------------------------

            current_stage = "sufficiency"

            started_at = self._clock()

            assessment = evaluate_sufficiency(
                bundle=bundle,
                requirements=(requirements),
            )

            stage_durations_ms["sufficiency"] = duration_ms(
                clock=self._clock,
                started_at=started_at,
            )

            logger.info(
                "answer_sufficiency_evaluated",
                **trace_fields,
                sufficiency_status=(assessment.status),
                sufficiency_reason=(assessment.reason),
                duration_ms=(stage_durations_ms["sufficiency"]),
            )

            # -------------------------------------
            # Deterministic synthesis
            # -------------------------------------

            current_stage = "synthesis"

            started_at = self._clock()

            if assessment.status == "sufficient":
                if synthesis is None:
                    raise ValueError(
                        "sufficient evidence requires an explicit synthesis specification"
                    )

                outcome = synthesize_answer(
                    assessment=(assessment),
                    instruction=(
                        SynthesisInstruction(
                            mode=(synthesis.mode),
                            answer_type=(synthesis.answer_type),
                            answer_record_ids=(assessment.supporting_record_ids),
                        )
                    ),
                )

            else:
                outcome = synthesize_answer(assessment=(assessment))

            generation_request = generation_request_from_outcome(
                question=(request.question),
                outcome=outcome,
            )

            stage_durations_ms["synthesis"] = duration_ms(
                clock=self._clock,
                started_at=started_at,
            )

            # -------------------------------------
            # Deterministic abstention
            # -------------------------------------

            if generation_request.authority.outcome == "abstain":
                result = _deterministic_abstention(generation_request)

                logger.info(
                    "answer_generation_skipped",
                    **trace_fields,
                    authority_outcome=("abstain"),
                    abstention_reason=(result.reason),
                )

                logger.info(
                    "answer_service_completed",
                    **trace_fields,
                    specification_kind=(specification_kind),
                    route_label=(route_label),
                    tools=tools,
                    status=(result.status),
                    presentation_source=(result.presentation_source),
                    generation_fidelity=(result.generation_fidelity),
                    abstention_reason=(result.reason),
                    generation_invoked=(False),
                    stage_durations_ms=(stage_durations_ms),
                    tool_durations_ms=(tool_durations_ms),
                    total_duration_ms=(
                        duration_ms(
                            clock=(self._clock),
                            started_at=(service_started_at),
                        )
                    ),
                )

                if self._metrics_registry is not None:
                    self._metrics_registry.record_answer_completed(
                        status=result.status,
                        presentation_source=(result.presentation_source),
                        generation_fidelity=(result.generation_fidelity),
                        abstention_reason=(result.reason),
                        generation_invoked=False,
                        stage_durations_ms=(stage_durations_ms),
                        tool_durations_ms=(tool_durations_ms),
                        total_duration_ms=(
                            duration_ms(
                                clock=self._clock,
                                started_at=(service_started_at),
                            )
                        ),
                    )

                return result

            # -------------------------------------
            # Probabilistic generation
            # -------------------------------------

            current_stage = "generation"

            generation_invoked = True

            started_at = self._clock()

            raw = self._generation_provider.generate(generation_request)

            stage_durations_ms["generation"] = duration_ms(
                clock=self._clock,
                started_at=started_at,
            )

            # -------------------------------------
            # Fidelity / presentation guard
            # -------------------------------------

            current_stage = "fidelity"

            started_at = self._clock()

            fidelity = assess_generation_fidelity(
                request=(generation_request),
                raw_generation=raw,
            )

            safe = resolve_safe_generation(fidelity)

            stage_durations_ms["fidelity"] = duration_ms(
                clock=self._clock,
                started_at=started_at,
            )

            result = _guarded_answer_result(
                request=(generation_request),
                safe=safe,
            )

            logger.info(
                "answer_generation_completed",
                **trace_fields,
                generation_duration_ms=(stage_durations_ms["generation"]),
                fidelity_duration_ms=(stage_durations_ms["fidelity"]),
                fidelity_status=(fidelity.status),
                presentation_source=(safe.source),
            )

            logger.info(
                "answer_service_completed",
                **trace_fields,
                specification_kind=(specification_kind),
                route_label=(route_label),
                tools=tools,
                status=(result.status),
                presentation_source=(result.presentation_source),
                generation_fidelity=(result.generation_fidelity),
                abstention_reason=None,
                generation_invoked=(generation_invoked),
                stage_durations_ms=(stage_durations_ms),
                tool_durations_ms=(tool_durations_ms),
                total_duration_ms=(
                    duration_ms(
                        clock=(self._clock),
                        started_at=(service_started_at),
                    )
                ),
            )

            if self._metrics_registry is not None:
                self._metrics_registry.record_answer_completed(
                    status=result.status,
                    presentation_source=(result.presentation_source),
                    generation_fidelity=(result.generation_fidelity),
                    abstention_reason=None,
                    generation_invoked=(generation_invoked),
                    stage_durations_ms=(stage_durations_ms),
                    tool_durations_ms=(tool_durations_ms),
                    total_duration_ms=(
                        duration_ms(
                            clock=self._clock,
                            started_at=(service_started_at),
                        )
                    ),
                )

            return result

        except Exception as exc:
            logger.error(
                "answer_service_failed",
                **trace_fields,
                stage=current_stage,
                specification_kind=(specification_kind),
                route_label=(route_label),
                tools=tools,
                generation_invoked=(generation_invoked),
                error_type=(type(exc).__name__),
                stage_durations_ms=(stage_durations_ms),
                tool_durations_ms=(tool_durations_ms),
                total_duration_ms=(
                    duration_ms(
                        clock=self._clock,
                        started_at=(service_started_at),
                    )
                ),
            )

            if self._metrics_registry is not None:
                self._metrics_registry.record_answer_failed(
                    stage=current_stage,
                    generation_invoked=(generation_invoked),
                    total_duration_ms=(
                        duration_ms(
                            clock=self._clock,
                            started_at=(service_started_at),
                        )
                    ),
                )

            raise
