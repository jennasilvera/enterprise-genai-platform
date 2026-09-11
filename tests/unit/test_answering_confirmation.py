from __future__ import annotations

import json

from enterprise_genai.answering.evaluation import (
    build_phase9c4_protocol,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.evaluation.answering_confirmation import (
    ANSWERING_CONFIRMATION_VERSION,
    PHASE9C4A_CANONICAL_SHA256,
    phase9c4a_canonical_sha256,
    run_phase9c4_confirmation,
    verify_q0024_contract_rejection,
)
from enterprise_genai.execution.contracts import (
    DatabaseRowReference,
    RetrievalHit,
    RetrievalPayload,
    StructuredEntity,
    StructuredPayload,
    ToolExecutionResult,
)
from enterprise_genai.orchestration.contracts import (
    OrchestrationStateSnapshot,
)


class FakeRuntime:
    def execute(
        self,
        plan,
    ) -> OrchestrationStateSnapshot:
        execution = plan.execution_plan

        if execution.retrieval is not None:
            question = execution.retrieval.question

            if "ORBIS-IDX-7" in question:
                payload = RetrievalPayload(
                    hits=(
                        RetrievalHit(
                            rank=1,
                            chunk_id=("CHK-CORE-PC006-RISK-PRIMARY"),
                            evidence_id=("EVID-CORE-PC006-RISK-PRIMARY"),
                            document_id=("DOC-CORE-PC006-RISK-2026Q2"),
                            text=("ORBIS-IDX-7 experienced an authentication defect."),
                            source_fact_ids=("RISK-006",),
                            rrf_score=0.03,
                            bm25_rank=1,
                            dense_rank=1,
                        ),
                    )
                )

            else:
                payload = RetrievalPayload(
                    hits=(
                        RetrievalHit(
                            rank=1,
                            chunk_id=("CHK-CORE-PC001-RISK-PRIMARY"),
                            evidence_id=("EVID-CORE-PC001-RISK-PRIMARY"),
                            document_id=("DOC-CORE-PC001-RISK-2026Q2"),
                            text=("Meridian has material customer concentration."),
                            source_fact_ids=("RISK-001",),
                            rrf_score=0.03,
                            bm25_rank=1,
                            dense_rank=1,
                        ),
                    )
                )

            result = ToolExecutionResult(
                tool="retrieval",
                status="ok",
                payload=payload,
                duration_ms=123.456,
            )

        elif execution.sql is not None:
            query = execution.sql

            if query.operation == "portfolio_growth_rank":
                payload = StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    entities=(
                        StructuredEntity(
                            company_id="PC-004",
                            name=("HelioGrid Energy"),
                            score=(0.35294117647058826),
                            canonical_fact_ids=(
                                "FIN-PC-004-2025Q2",
                                "FIN-PC-004-2026Q2",
                            ),
                        ),
                    ),
                    unit="ratio",
                    source_rows=(),
                )

            else:
                rows = tuple(
                    DatabaseRowReference(
                        table=("financial_metric_observations"),
                        primary_key={
                            "company_id": (f"PC-{index:03d}"),
                            "period": "2026Q2",
                            "metric": ("revenue_usd"),
                        },
                        canonical_fact_ids=((f"FIN-PC-{index:03d}-2026Q2"),),
                    )
                    for index in range(
                        1,
                        9,
                    )
                )

                payload = StructuredPayload(
                    operation=(query.operation),
                    value=735_000_000,
                    entities=(),
                    unit="USD",
                    source_rows=rows,
                )

            result = ToolExecutionResult(
                tool="sql",
                status="ok",
                payload=payload,
                duration_ms=987.654,
            )

        else:
            raise AssertionError("Unexpected fake plan.")

        return OrchestrationStateSnapshot(
            plan=plan,
            results=(result,),
            status="completed",
        )


def _report():
    evaluation = build_seed_evaluation()

    protocols = build_phase9c4_protocol(evaluation)

    return run_phase9c4_confirmation(
        evaluation=evaluation,
        protocols=protocols,
        runtime=FakeRuntime(),
        q0024_contract_rejection_verified=True,
        retrieval_metadata={
            "retriever_version": ("hybrid:rrf-k60-v1"),
        },
    )


def test_confirmation_version_is_frozen() -> None:
    assert ANSWERING_CONFIRMATION_VERSION == "northstar-answering-confirmation-v1"


def test_confirmation_is_bound_to_frozen_9c4a_protocol() -> None:
    evaluation = build_seed_evaluation()

    protocols = build_phase9c4_protocol(evaluation)

    assert (
        phase9c4a_canonical_sha256(
            evaluation,
            protocols,
        )
        == PHASE9C4A_CANONICAL_SHA256
    )


def test_structured_contract_rejects_q0024_metric() -> None:
    assert verify_q0024_contract_rejection() is True


def test_confirmation_passes_all_five_stage_resolved_cases() -> None:
    report = _report()

    assert report["summary"] == {
        "cases": 5,
        "passed": 5,
        "failed": 0,
        "all_passed": True,
    }

    observations = {item["query_id"]: item for item in report["cases"]}

    assert observations["Q-0001"]["outcome"] == "answer"

    assert observations["Q-0010"]["observed_value"] == "HelioGrid Energy"

    assert observations["Q-0011"]["observed_value"] == 735_000_000

    assert observations["Q-0011"]["observed_unit"] == "USD"

    assert observations["Q-0023"]["sufficiency_reason"] == "missing_required_information"

    assert observations["Q-0024"]["sufficiency_reason"] == "unsupported_request"

    assert observations["Q-0024"]["contract_rejection_verified"] is True


def test_confirmation_report_omits_nondeterministic_durations() -> None:
    raw = json.dumps(
        _report(),
        sort_keys=True,
    )

    assert "duration_ms" not in raw


def test_confirmation_report_is_byte_reproducible_with_same_inputs() -> None:
    first = json.dumps(
        _report(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    second = json.dumps(
        _report(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    assert first == second
