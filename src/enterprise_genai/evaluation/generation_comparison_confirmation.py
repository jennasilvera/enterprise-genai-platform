from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from enterprise_genai.answering.evaluation import (
    build_phase9c4_protocol,
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
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.evaluation.answering_confirmation import (
    verify_q0024_contract_rejection,
)
from enterprise_genai.evaluation.generation_comparison import (
    GENERATION_COMPARISON_PROTOCOL_VERSION,
    GenerationSystemScore,
    build_generation_comparison_protocol,
    score_comparison_text,
)
from enterprise_genai.execution.frozen_retrieval import (
    FrozenHybridRetrievalExecutor,
)
from enterprise_genai.execution.structured_sql import (
    StructuredSqlExecutor,
)
from enterprise_genai.generation.contracts import (
    GenerationProvider,
    RawGeneration,
    generation_request_from_outcome,
)
from enterprise_genai.generation.guarded import (
    render_deterministic_authority,
    resolve_safe_generation,
)
from enterprise_genai.generation.validation import (
    assess_generation_fidelity,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
)
from enterprise_genai.orchestration.langgraph_runtime import (
    BoundedLangGraphRuntime,
)

GENERATION_COMPARISON_CONFIRMATION_VERSION = "northstar-generation-comparison-confirmation-v1"

FROZEN_COMPARISON_QUERY_IDS = (
    "Q-0001",
    "Q-0010",
    "Q-0011",
    "Q-0023",
    "Q-0024",
)


def canonical_comparison_report_bytes(
    report: dict[str, Any],
) -> bytes:
    return (
        json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _system_score_payload(
    score: GenerationSystemScore,
) -> dict[str, Any]:
    return {
        "system": score.system,
        "text": score.text,
        "passed": score.passed,
        "total": score.total,
        "metrics": [
            {
                "metric": item.metric,
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in score.metric_results
        ],
    }


def _unauthorized_flags(
    *,
    request,
    text: str,
    metadata,
) -> tuple[
    bool,
    bool,
]:
    audit = assess_generation_fidelity(
        request=request,
        raw_generation=RawGeneration(
            text=text,
            metadata=metadata,
        ),
    )

    codes = {violation.code for violation in audit.violations}

    return (
        "unauthorized_numeric_claim" in codes,
        "unauthorized_citation" in codes,
    )


def build_comparison_confirmation_report(
    *,
    dataset_version: str,
    evaluation_version: str,
    provider_metadata: dict[str, Any],
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    query_ids = tuple(case["query_id"] for case in cases)

    if query_ids != FROZEN_COMPARISON_QUERY_IDS:
        raise ValueError("Comparison confirmation requires the frozen five-case order.")

    systems = (
        "deterministic",
        "raw_llm",
        "guarded_llm",
    )

    summary = {
        system: {
            "passed": 0,
            "total": 0,
        }
        for system in systems
    }

    for case in cases:
        system_names = tuple(score["system"] for score in case["systems"])

        if system_names != systems:
            raise ValueError("Every comparison case must contain the frozen three-system order.")

        for score in case["systems"]:
            bucket = summary[score["system"]]

            bucket["passed"] += score["passed"]

            bucket["total"] += score["total"]

    for system in systems:
        result = summary[system]

        if result["total"] != 25:
            raise ValueError("Each system must receive exactly 25 frozen mechanical checks.")

        result["rate"] = result["passed"] / result["total"]

    return {
        "artifact_version": (GENERATION_COMPARISON_CONFIRMATION_VERSION),
        "comparison_protocol_version": (GENERATION_COMPARISON_PROTOCOL_VERSION),
        "dataset_version": (dataset_version),
        "evaluation_version": (evaluation_version),
        "provider_metadata": (provider_metadata),
        "query_ids": list(query_ids),
        "summary": summary,
        "cases": cases,
        "claim_boundary": [
            (
                "Scores are frozen deterministic "
                "mechanical fidelity checks, not "
                "general semantic accuracy."
            ),
            ("The five cases are an integration control set, not the complete 24-case benchmark."),
            (
                "The Phase 10D1 protocol was "
                "defined after Phase 10C model "
                "behavior had already been "
                "observed and was not blind or "
                "preregistered."
            ),
            (
                "The deterministic and guarded "
                "paths may receive architectural "
                "safety credit for preventing "
                "rejected raw model output from "
                "crossing presentation."
            ),
        ],
    }


def run_generation_comparison_confirmation(
    *,
    session: Session,
    provider: GenerationProvider,
) -> dict[str, Any]:
    evaluation = build_seed_evaluation()

    answering_protocols = {item.query_id: item for item in build_phase9c4_protocol(evaluation)}

    evaluation_cases = {item.query_id: item for item in evaluation.cases}

    comparison = build_generation_comparison_protocol()

    if tuple(item.query_id for item in comparison.cases) != FROZEN_COMPARISON_QUERY_IDS:
        raise AssertionError("Frozen comparison protocol query order changed.")

    retrieval = FrozenHybridRetrievalExecutor.from_persisted_corpus(
        session,
        evaluation.dataset_version,
    )

    sql = StructuredSqlExecutor(session)

    runtime = BoundedLangGraphRuntime(
        retrieval_executor=retrieval,
        sql_executor=sql,
    )

    observations: list[dict[str, Any]] = []

    for comparison_case in comparison.cases:
        query_id = comparison_case.query_id

        protocol = answering_protocols[query_id]

        case = evaluation_cases[query_id]

        if protocol.execution_kind == "unsupported_request":
            if query_id != "Q-0024":
                raise AssertionError("Unexpected unsupported comparison case.")

            if verify_q0024_contract_rejection() is not True:
                raise AssertionError("Q-0024 contract rejection was not verified.")

            bundle = unsupported_request_bundle(
                question=case.question,
                detail=(protocol.unsupported_detail),
            )

        else:
            if protocol.execution_plan is None:
                raise AssertionError("Executable comparison case requires an execution plan.")

            snapshot = runtime.execute(
                BoundedOrchestrationPlan(
                    question=case.question,
                    execution_plan=(protocol.execution_plan),
                )
            )

            if snapshot.status != "completed":
                raise AssertionError("Comparison execution did not complete.")

            bundle = evidence_bundle_from_snapshot(snapshot)

        sufficiency = evaluate_sufficiency(
            bundle=bundle,
            requirements=(protocol.requirements),
        )

        if sufficiency.status == "sufficient":
            if protocol.synthesis_mode is None or protocol.synthesis_answer_type is None:
                raise AssertionError("Sufficient comparison case requires synthesis metadata.")

            outcome = synthesize_answer(
                assessment=sufficiency,
                instruction=(
                    SynthesisInstruction(
                        mode=(protocol.synthesis_mode),
                        answer_type=(protocol.synthesis_answer_type),
                        answer_record_ids=(sufficiency.supporting_record_ids),
                    )
                ),
            )

        else:
            outcome = synthesize_answer(assessment=sufficiency)

        request = generation_request_from_outcome(
            question=case.question,
            outcome=outcome,
        )

        raw = provider.generate(request)

        raw_fidelity = assess_generation_fidelity(
            request=request,
            raw_generation=raw,
        )

        guarded = resolve_safe_generation(raw_fidelity)

        deterministic_text = render_deterministic_authority(request.authority)

        (
            deterministic_unauthorized_numeric,
            deterministic_unauthorized_citation,
        ) = _unauthorized_flags(
            request=request,
            text=deterministic_text,
            metadata=raw.metadata,
        )

        raw_codes = {violation.code for violation in raw_fidelity.violations}

        raw_unauthorized_numeric = "unauthorized_numeric_claim" in raw_codes

        raw_unauthorized_citation = "unauthorized_citation" in raw_codes

        (
            guarded_unauthorized_numeric,
            guarded_unauthorized_citation,
        ) = _unauthorized_flags(
            request=request,
            text=guarded.text,
            metadata=raw.metadata,
        )

        authority_outcome = request.authority.outcome

        authority_reason = request.authority.reason

        deterministic_score = score_comparison_text(
            case=comparison_case,
            system="deterministic",
            text=deterministic_text,
            authority_outcome=(authority_outcome),
            authority_answer_type=(request.authority.answer_type),
            authority_value=(request.authority.value),
            authority_unit=(request.authority.unit),
            authority_reason=(authority_reason),
            presented_outcome=(authority_outcome),
            presented_reason=(authority_reason),
            unauthorized_numeric_present=(deterministic_unauthorized_numeric),
            unauthorized_citation_present=(deterministic_unauthorized_citation),
            rejected_raw_exposed=False,
        )

        raw_score = score_comparison_text(
            case=comparison_case,
            system="raw_llm",
            text=raw.text,
            authority_outcome=(authority_outcome),
            authority_answer_type=(request.authority.answer_type),
            authority_value=(request.authority.value),
            authority_unit=(request.authority.unit),
            authority_reason=(authority_reason),
            presented_outcome=None,
            presented_reason=None,
            unauthorized_numeric_present=(raw_unauthorized_numeric),
            unauthorized_citation_present=(raw_unauthorized_citation),
            rejected_raw_exposed=(raw_fidelity.status == "rejected"),
        )

        guarded_score = score_comparison_text(
            case=comparison_case,
            system="guarded_llm",
            text=guarded.text,
            authority_outcome=(authority_outcome),
            authority_answer_type=(request.authority.answer_type),
            authority_value=(request.authority.value),
            authority_unit=(request.authority.unit),
            authority_reason=(authority_reason),
            presented_outcome=(authority_outcome),
            presented_reason=(authority_reason),
            unauthorized_numeric_present=(guarded_unauthorized_numeric),
            unauthorized_citation_present=(guarded_unauthorized_citation),
            rejected_raw_exposed=(raw_fidelity.status == "rejected" and guarded.text == raw.text),
        )

        observations.append(
            {
                "query_id": query_id,
                "question": case.question,
                "authority": {
                    "outcome": (authority_outcome),
                    "answer_type": (request.authority.answer_type),
                    "value": (request.authority.value),
                    "unit": (request.authority.unit),
                    "reason": (authority_reason),
                },
                "raw_fidelity_status": (raw_fidelity.status),
                "raw_violation_codes": [violation.code for violation in raw_fidelity.violations],
                "guarded_source": (guarded.source),
                "systems": [
                    _system_score_payload(score)
                    for score in (
                        deterministic_score,
                        raw_score,
                        guarded_score,
                    )
                ],
            }
        )

    return build_comparison_confirmation_report(
        dataset_version=(evaluation.dataset_version),
        evaluation_version=(evaluation.evaluation_version),
        provider_metadata=(provider.metadata.model_dump(mode="json")),
        cases=observations,
    )


def write_generation_comparison_confirmation(
    *,
    report: dict[str, Any],
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(canonical_comparison_report_bytes(report))
