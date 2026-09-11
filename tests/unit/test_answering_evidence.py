from __future__ import annotations

import pytest

from enterprise_genai.answering.evidence import (
    evidence_bundle_from_snapshot,
    unsupported_request_bundle,
)
from enterprise_genai.execution.contracts import (
    DatabaseRowReference,
    GraphEdge,
    GraphNode,
    GraphPayload,
    PortfolioGraphPredicate,
    PortfolioGraphQuery,
    RetrievalHit,
    RetrievalPayload,
    RetrievalQuery,
    StructuredEntity,
    StructuredPayload,
    StructuredQuery,
    ToolExecutionPlan,
    ToolExecutionResult,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    OrchestrationStateSnapshot,
)


def _retrieval_plan() -> BoundedOrchestrationPlan:
    question = "What evidence exists?"

    return BoundedOrchestrationPlan(
        question=question,
        execution_plan=(
            ToolExecutionPlan(
                route_label="retrieval",
                retrieval=(
                    RetrievalQuery(
                        question=question,
                        top_k=10,
                    )
                ),
            )
        ),
    )


def test_retrieval_snapshot_normalizes_grounded_hits() -> None:
    result = ToolExecutionResult(
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
                    text="Grounded evidence.",
                    source_fact_ids=(
                        "RISK-005",
                        "FIN-PC-005-2026Q2",
                    ),
                    rrf_score=0.03,
                    bm25_rank=1,
                    dense_rank=2,
                ),
            )
        ),
    )

    snapshot = OrchestrationStateSnapshot(
        plan=_retrieval_plan(),
        results=(result,),
        status="completed",
    )

    bundle = evidence_bundle_from_snapshot(snapshot)

    assert bundle.status == "completed"

    assert len(bundle.records) == 1

    record = bundle.records[0]

    assert record.record_id == "RET:001:EVID-001"

    assert record.source_fact_ids == (
        "FIN-PC-005-2026Q2",
        "RISK-005",
    )

    assert record.rank == 1

    assert record.document_id == "DOC-001"


def test_ungrounded_retrieval_hit_is_not_answer_evidence() -> None:
    result = ToolExecutionResult(
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
                    text=("Retrieved text without canonical provenance."),
                    source_fact_ids=(),
                    rrf_score=0.03,
                    bm25_rank=1,
                    dense_rank=1,
                ),
            )
        ),
    )

    snapshot = OrchestrationStateSnapshot(
        plan=_retrieval_plan(),
        results=(result,),
        status="completed",
    )

    bundle = evidence_bundle_from_snapshot(snapshot)

    assert bundle.records == ()


def test_structured_entity_preserves_operation_provenance() -> None:
    question = "Which company had lower revenue?"

    plan = BoundedOrchestrationPlan(
        question=question,
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql",
                sql=StructuredQuery(
                    period="2026Q2",
                    operation=("portfolio_metric_rank"),
                    metric="revenue_usd",
                    rank_order="lowest",
                    result_limit=1,
                ),
            )
        ),
    )

    payload = StructuredPayload(
        operation=("portfolio_metric_rank"),
        value=None,
        entities=(
            StructuredEntity(
                company_id="PC-008",
                name=("NovaBio Instruments"),
                score=83_000_000,
                canonical_fact_ids=("FIN-PC-008-2026Q2",),
            ),
        ),
        source_rows=(
            DatabaseRowReference(
                table=("financial_metrics"),
                primary_key={
                    "company_id": "PC-002",
                    "period": "2026Q2",
                },
                canonical_fact_ids=("FIN-PC-002-2026Q2",),
            ),
            DatabaseRowReference(
                table=("financial_metrics"),
                primary_key={
                    "company_id": "PC-008",
                    "period": "2026Q2",
                },
                canonical_fact_ids=("FIN-PC-008-2026Q2",),
            ),
        ),
    )

    snapshot = OrchestrationStateSnapshot(
        plan=plan,
        results=(
            ToolExecutionResult(
                tool="sql",
                status="ok",
                payload=payload,
                duration_ms=0.0,
            ),
        ),
        status="completed",
    )

    bundle = evidence_bundle_from_snapshot(snapshot)

    assert len(bundle.records) == 1

    record = bundle.records[0]

    assert record.record_id == "SQL:ENTITY:PC-008"

    assert record.source_fact_ids == (
        "FIN-PC-002-2026Q2",
        "FIN-PC-008-2026Q2",
    )


def test_graph_snapshot_normalizes_node_and_edge_provenance() -> None:
    question = "Which company has the critical supplier?"

    # This test exercises the payload adapter
    # directly through a valid graph result.
    payload = GraphPayload(
        nodes=(
            GraphNode(
                entity_type="company",
                entity_id="PC-002",
                name=("Alder Manufacturing"),
                canonical_fact_ids=("PC-002",),
            ),
            GraphNode(
                entity_type="supplier",
                entity_id="SUP-005",
                name=("TitaniumWorks GmbH"),
                canonical_fact_ids=("SUP-005",),
            ),
        ),
        edges=(
            GraphEdge(
                relationship_type=("company_supplier"),
                relationship_id="CS-003",
                source_type="company",
                source_id="PC-002",
                target_type="supplier",
                target_id="SUP-005",
                canonical_fact_ids=("CS-003",),
            ),
        ),
        matched_company_ids=("PC-002",),
    )

    plan = BoundedOrchestrationPlan(
        question=question,
        execution_plan=(
            ToolExecutionPlan(
                route_label="graph",
                graph=PortfolioGraphQuery(
                    predicates=(
                        PortfolioGraphPredicate(
                            relationship_type="company_supplier",
                            target_country="Germany",
                            criticality="critical",
                        ),
                    )
                ),
            )
        ),
    )

    snapshot = OrchestrationStateSnapshot(
        plan=plan,
        results=(
            ToolExecutionResult(
                tool="graph",
                status="ok",
                payload=payload,
                duration_ms=0.0,
            ),
        ),
        status="completed",
    )

    bundle = evidence_bundle_from_snapshot(snapshot)

    record_ids = tuple(record.record_id for record in bundle.records)

    assert record_ids == (
        "GRAPH:NODE:company:PC-002",
        "GRAPH:NODE:supplier:SUP-005",
        ("GRAPH:EDGE:company_supplier:CS-003"),
    )


def test_completed_execution_may_have_no_answer_evidence() -> None:
    snapshot = OrchestrationStateSnapshot(
        plan=_retrieval_plan(),
        results=(
            ToolExecutionResult(
                tool="retrieval",
                status="ok",
                duration_ms=0.0,
                payload=(RetrievalPayload(hits=())),
            ),
        ),
        status="completed",
    )

    bundle = evidence_bundle_from_snapshot(snapshot)

    assert bundle.status == "completed"
    assert bundle.records == ()


def test_pending_snapshot_cannot_be_normalized() -> None:
    snapshot = OrchestrationStateSnapshot(
        plan=_retrieval_plan(),
        status="pending",
    )

    with pytest.raises(
        ValueError,
        match=("requires a terminal orchestration state"),
    ):
        evidence_bundle_from_snapshot(snapshot)


def test_failed_snapshot_becomes_failed_bundle() -> None:
    snapshot = OrchestrationStateSnapshot(
        plan=_retrieval_plan(),
        results=(
            ToolExecutionResult(
                tool="retrieval",
                status="error",
                duration_ms=0.0,
                error=("retrieval unavailable"),
            ),
        ),
        status="failed",
    )

    bundle = evidence_bundle_from_snapshot(snapshot)

    assert bundle.status == "failed"

    assert bundle.detail == ("retrieval: retrieval unavailable")

    assert bundle.records == ()


def test_unsupported_request_has_typed_bundle() -> None:
    bundle = unsupported_request_bundle(
        question=("What was Alder's customer churn rate?"),
        detail=("customer_churn_rate is outside the bounded structured metric set."),
    )

    assert bundle.status == "unsupported_request"

    assert bundle.records == ()

    assert "customer_churn_rate" in bundle.detail
