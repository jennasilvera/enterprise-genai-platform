from __future__ import annotations

import hashlib
import json
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy.orm import Session

from enterprise_genai.answering.evaluation import (
    ANSWERING_EVALUATION_PROTOCOL_VERSION,
    PHASE9C4_QUERY_IDS,
    AnsweringCaseProtocol,
    build_phase9c4_protocol,
    compare_answer_outcome,
)
from enterprise_genai.answering.evidence import (
    evidence_bundle_from_snapshot,
    unsupported_request_bundle,
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
from enterprise_genai.data.evaluation_models import (
    EvaluationSet,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.execution.contracts import (
    StructuredQuery,
)
from enterprise_genai.execution.frozen_retrieval import (
    FrozenHybridRetrievalExecutor,
)
from enterprise_genai.execution.structured_sql import (
    StructuredSqlExecutor,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    OrchestrationStateSnapshot,
)
from enterprise_genai.orchestration.langgraph_runtime import (
    BoundedLangGraphRuntime,
)

ANSWERING_CONFIRMATION_VERSION = "northstar-answering-confirmation-v1"

PHASE9C4A_CANONICAL_SHA256 = "31a2c3e2294e1b6954cf5955e8467fa012869e10d789055bdbc6b75ca6232ad6"


class RuntimeProtocol(Protocol):
    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot: ...


def _case_map(
    evaluation: EvaluationSet,
):
    return {case.query_id: case for case in evaluation.cases}


def _canonical_protocol_payload(
    evaluation: EvaluationSet,
    protocols: tuple[
        AnsweringCaseProtocol,
        ...,
    ],
) -> dict[str, object]:
    return {
        "protocol_version": (ANSWERING_EVALUATION_PROTOCOL_VERSION),
        "dataset_version": (evaluation.dataset_version),
        "evaluation_version": (evaluation.evaluation_version),
        "query_ids": list(PHASE9C4_QUERY_IDS),
        "cases": [protocol.model_dump(mode="json") for protocol in protocols],
    }


def phase9c4a_canonical_sha256(
    evaluation: EvaluationSet,
    protocols: tuple[
        AnsweringCaseProtocol,
        ...,
    ],
) -> str:
    canonical = json.dumps(
        _canonical_protocol_payload(
            evaluation,
            protocols,
        ),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_q0024_contract_rejection() -> bool:
    """Prove the requested churn metric is outside StructuredQuery."""

    payload = {
        "dataset_version": "northstar-v1",
        "company_id": "PC-002",
        "period": "2026Q2",
        "operation": "metric_value",
        "metric": "customer_churn_rate",
    }

    try:
        StructuredQuery.model_validate(payload)
    except ValidationError as exc:
        return any(
            tuple(error["loc"]) == ("metric",) and error.get("input") == "customer_churn_rate"
            for error in exc.errors()
        )

    return False


def _outcome_fields(
    outcome,
) -> dict[str, object]:
    if isinstance(
        outcome,
        GroundedAnswer,
    ):
        dumped = outcome.model_dump(mode="json")

        return {
            "outcome": "answer",
            "observed_answer_type": (outcome.answer_type),
            "observed_value": (dumped["value"]),
            "observed_unit": (outcome.unit),
            "source_fact_ids": list(outcome.source_fact_ids),
        }

    return {
        "outcome": "abstain",
        "observed_answer_type": "abstain",
        "observed_value": None,
        "observed_unit": None,
        "source_fact_ids": [],
    }


def run_phase9c4_confirmation(
    *,
    evaluation: EvaluationSet,
    protocols: tuple[
        AnsweringCaseProtocol,
        ...,
    ],
    runtime: RuntimeProtocol,
    q0024_contract_rejection_verified: bool,
    retrieval_metadata: dict[
        str,
        object,
    ]
    | None = None,
) -> dict[str, object]:
    """Execute the frozen answering protocol without timing fields."""

    protocol_sha = phase9c4a_canonical_sha256(
        evaluation,
        protocols,
    )

    if protocol_sha != PHASE9C4A_CANONICAL_SHA256:
        raise ValueError("Phase 9C4B requires the frozen Phase 9C4A protocol.")

    cases = _case_map(evaluation)

    observations: list[dict[str, object]] = []

    for protocol in protocols:
        case = cases[protocol.query_id]

        executed_tools: list[str] = []

        if protocol.execution_kind == "unsupported_request":
            bundle = unsupported_request_bundle(
                question=case.question,
                detail=(protocol.unsupported_detail),
            )

            execution_status = "unsupported_request"

            contract_rejection = q0024_contract_rejection_verified

        else:
            if protocol.execution_plan is None:
                raise RuntimeError("Orchestration protocol lost its execution plan.")

            snapshot = runtime.execute(
                BoundedOrchestrationPlan(
                    question=case.question,
                    execution_plan=(protocol.execution_plan),
                )
            )

            execution_status = snapshot.status

            executed_tools = [result.tool for result in snapshot.results]

            bundle = evidence_bundle_from_snapshot(snapshot)

            contract_rejection = None

        assessment = evaluate_sufficiency(
            bundle=bundle,
            requirements=(protocol.requirements),
        )

        if assessment.status == "sufficient":
            if protocol.synthesis_mode is None or protocol.synthesis_answer_type is None:
                raise RuntimeError("Sufficient protocol requires synthesis metadata.")

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

        comparison = compare_answer_outcome(
            case=case,
            protocol=protocol,
            outcome=outcome,
        )

        case_passed = comparison.case_passed

        if protocol.query_id == "Q-0024":
            case_passed = case_passed and bool(contract_rejection)

        outcome_fields = _outcome_fields(outcome)

        observations.append(
            {
                "query_id": (case.query_id),
                "split": case.split,
                "query_type": (case.query_type),
                "required_tools": list(case.required_tools),
                "execution_kind": (protocol.execution_kind),
                "execution_status": (execution_status),
                "executed_tools": (executed_tools),
                "evidence_status": (bundle.status),
                "evidence_record_ids": [record.record_id for record in bundle.records],
                "sufficiency_status": (assessment.status),
                "sufficiency_reason": (assessment.reason),
                "supporting_record_ids": list(assessment.supporting_record_ids),
                "missing_information": list(assessment.missing_information),
                **outcome_fields,
                "comparison": (comparison.model_dump(mode="json")),
                "contract_rejection_verified": (contract_rejection),
                "case_passed": (case_passed),
            }
        )

    passed = sum(bool(observation["case_passed"]) for observation in observations)

    total = len(observations)

    return {
        "confirmation_version": (ANSWERING_CONFIRMATION_VERSION),
        "protocol_version": (ANSWERING_EVALUATION_PROTOCOL_VERSION),
        "protocol_canonical_sha256": (protocol_sha),
        "dataset_version": (evaluation.dataset_version),
        "evaluation_version": (evaluation.evaluation_version),
        "query_ids": list(PHASE9C4_QUERY_IDS),
        "retrieval_metadata": (retrieval_metadata),
        "summary": {
            "cases": total,
            "passed": passed,
            "failed": (total - passed),
            "all_passed": (passed == total),
        },
        "cases": observations,
    }


def run_persisted_phase9c4_confirmation(
    session: Session,
) -> dict[str, object]:
    """Run the frozen protocol against persisted Northstar data."""

    evaluation = build_seed_evaluation()

    protocols = build_phase9c4_protocol(evaluation)

    retrieval = FrozenHybridRetrievalExecutor.from_persisted_corpus(
        session,
        evaluation.dataset_version,
    )

    sql = StructuredSqlExecutor(session)

    runtime = BoundedLangGraphRuntime(
        retrieval_executor=retrieval,
        sql_executor=sql,
    )

    return run_phase9c4_confirmation(
        evaluation=evaluation,
        protocols=protocols,
        runtime=runtime,
        q0024_contract_rejection_verified=(verify_q0024_contract_rejection()),
        retrieval_metadata=dict(retrieval.metadata),
    )
