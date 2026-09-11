from __future__ import annotations

import json
from collections.abc import Sequence
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
from enterprise_genai.execution.frozen_retrieval import (
    FrozenHybridRetrievalExecutor,
)
from enterprise_genai.execution.structured_sql import (
    StructuredSqlExecutor,
)
from enterprise_genai.generation.contracts import (
    GenerationProvider,
    GenerationProviderMetadata,
    generation_request_from_outcome,
)
from enterprise_genai.generation.guarded import (
    SAFE_GENERATION_POLICY_VERSION,
    render_deterministic_authority,
    resolve_safe_generation,
)
from enterprise_genai.generation.validation import (
    GENERATION_FIDELITY_POLICY_VERSION,
    assess_generation_fidelity,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
)
from enterprise_genai.orchestration.langgraph_runtime import (
    BoundedLangGraphRuntime,
)

GUARDED_GENERATION_CONFIRMATION_VERSION = "northstar-guarded-generation-confirmation-v1"

GUARDED_GENERATION_QUERY_IDS = (
    "Q-0001",
    "Q-0010",
    "Q-0011",
    "Q-0023",
    "Q-0024",
)

EXPECTED_PRESENTATION_SOURCES = {
    "Q-0001": "deterministic_fallback",
    "Q-0010": "model_generation",
    "Q-0011": "deterministic_fallback",
    "Q-0023": "deterministic_fallback",
    "Q-0024": "deterministic_fallback",
}


def canonical_report_bytes(
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


def build_guarded_generation_report(
    *,
    dataset_version: str,
    evaluation_version: str,
    provider_metadata: GenerationProviderMetadata,
    observations: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    query_ids = tuple(item["query_id"] for item in observations)

    if query_ids != GUARDED_GENERATION_QUERY_IDS:
        raise ValueError(
            "Guarded generation confirmation requires the frozen five-case query order."
        )

    for item in observations:
        query_id = item["query_id"]

        if item["presentation_source"] != EXPECTED_PRESENTATION_SOURCES[query_id]:
            raise ValueError(f"Unexpected presentation source for {query_id}.")

        if item["fidelity_status"] == "rejected" and item["rejected_raw_exposed"]:
            raise ValueError("Rejected raw generation crossed the presentation boundary.")

    model_generation = sum(
        item["presentation_source"] == "model_generation" for item in observations
    )

    deterministic_fallback = sum(
        item["presentation_source"] == "deterministic_fallback" for item in observations
    )

    rejected = sum(item["fidelity_status"] == "rejected" for item in observations)

    accepted = sum(item["fidelity_status"] == "accepted" for item in observations)

    rejected_raw_exposed = sum(bool(item["rejected_raw_exposed"]) for item in observations)

    return {
        "artifact_version": (GUARDED_GENERATION_CONFIRMATION_VERSION),
        "dataset_version": (dataset_version),
        "evaluation_version": (evaluation_version),
        "fidelity_policy_version": (GENERATION_FIDELITY_POLICY_VERSION),
        "presentation_policy_version": (SAFE_GENERATION_POLICY_VERSION),
        "provider_metadata": (provider_metadata.model_dump(mode="json")),
        "query_ids": list(query_ids),
        "summary": {
            "cases": len(observations),
            "fidelity_accepted": accepted,
            "fidelity_rejected": rejected,
            "model_generation": (model_generation),
            "deterministic_fallback": (deterministic_fallback),
            "rejected_raw_exposed": (rejected_raw_exposed),
            "all_guarded": (rejected_raw_exposed == 0),
        },
        "cases": list(observations),
    }


def run_guarded_generation_confirmation(
    *,
    session: Session,
    provider: GenerationProvider,
) -> dict[str, Any]:
    evaluation = build_seed_evaluation()

    protocols = build_phase9c4_protocol(evaluation)

    cases = {case.query_id: case for case in evaluation.cases}

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

    for protocol in protocols:
        case = cases[protocol.query_id]

        if protocol.execution_kind == "unsupported_request":
            if protocol.query_id != "Q-0024":
                raise AssertionError("Unexpected unsupported confirmation case.")

            if verify_q0024_contract_rejection() is not True:
                raise AssertionError("Q-0024 contract rejection was not verified.")

            bundle = unsupported_request_bundle(
                question=case.question,
                detail=(protocol.unsupported_detail),
            )

        else:
            if protocol.execution_plan is None:
                raise AssertionError("Executable confirmation case requires an execution plan.")

            snapshot = runtime.execute(
                BoundedOrchestrationPlan(
                    question=case.question,
                    execution_plan=(protocol.execution_plan),
                )
            )

            if snapshot.status != "completed":
                raise AssertionError("Confirmation execution did not complete.")

            bundle = evidence_bundle_from_snapshot(snapshot)

        assessment = evaluate_sufficiency(
            bundle=bundle,
            requirements=(protocol.requirements),
        )

        if assessment.status == "sufficient":
            if protocol.synthesis_mode is None or protocol.synthesis_answer_type is None:
                raise AssertionError("Sufficient confirmation case requires synthesis metadata.")

            outcome = synthesize_answer(
                assessment=assessment,
                instruction=(
                    SynthesisInstruction(
                        mode=(protocol.synthesis_mode),
                        answer_type=(protocol.synthesis_answer_type),
                        answer_record_ids=(assessment.supporting_record_ids),
                    )
                ),
            )

        else:
            outcome = synthesize_answer(assessment=assessment)

        request = generation_request_from_outcome(
            question=case.question,
            outcome=outcome,
        )

        raw = provider.generate(request)

        fidelity = assess_generation_fidelity(
            request=request,
            raw_generation=raw,
        )

        safe = resolve_safe_generation(fidelity)

        if fidelity.status == "accepted":
            if (
                fidelity.safe_text is None
                or safe.text != raw.text
                or safe.source != "model_generation"
            ):
                raise AssertionError(
                    "Accepted model generation did not cross the guarded boundary exactly."
                )

        else:
            if fidelity.safe_text is not None:
                raise AssertionError("Rejected fidelity assessment exposed safe model text.")

            expected_fallback = render_deterministic_authority(request.authority)

            if safe.source != "deterministic_fallback" or safe.text != expected_fallback:
                raise AssertionError(
                    "Rejected generation did not resolve to exact deterministic authority."
                )

        rejected_raw_exposed = fidelity.status == "rejected" and safe.text == raw.text

        observations.append(
            {
                "query_id": (protocol.query_id),
                "authority_outcome": (request.authority.outcome),
                "authority_answer_type": (request.authority.answer_type),
                "authority_value": (request.authority.value),
                "authority_unit": (request.authority.unit),
                "authority_reason": (request.authority.reason),
                "generation_evidence_ids": [record.record_id for record in request.evidence],
                "allowed_citation_ids": list(request.allowed_citation_ids),
                "raw_generation": (raw.text),
                "fidelity_status": (fidelity.status),
                "violation_codes": [violation.code for violation in fidelity.violations],
                "presentation_source": (safe.source),
                "presentation_text": (safe.text),
                "citation_ids": list(safe.citation_ids),
                "rejected_raw_exposed": (rejected_raw_exposed),
            }
        )

    report = build_guarded_generation_report(
        dataset_version=(evaluation.dataset_version),
        evaluation_version=(evaluation.evaluation_version),
        provider_metadata=(provider.metadata),
        observations=observations,
    )

    by_id = {item["query_id"]: item for item in report["cases"]}

    if by_id["Q-0011"]["presentation_text"] != "735000000 USD":
        raise AssertionError("Q-0011 deterministic numeric fallback changed.")

    if "$735 million" in by_id["Q-0011"]["presentation_text"]:
        raise AssertionError("Q-0011 rejected raw numeric generation crossed presentation.")

    if "$15 billion" in by_id["Q-0023"]["presentation_text"]:
        raise AssertionError("Q-0023 hallucinated valuation crossed presentation.")

    if "no known customer churn rate" in by_id["Q-0024"]["presentation_text"]:
        raise AssertionError("Q-0024 unsupported substantive claim crossed presentation.")

    return report


def write_guarded_generation_confirmation(
    *,
    report: dict[str, Any],
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(canonical_report_bytes(report))
