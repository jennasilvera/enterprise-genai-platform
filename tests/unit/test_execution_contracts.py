from decimal import Decimal

import pytest
from pydantic import ValidationError

from enterprise_genai.execution.contracts import (
    DatabaseRowReference,
    GraphEdge,
    GraphNode,
    GraphPath,
    GraphPayload,
    GraphQuery,
    RetrievalPayload,
    RetrievalQuery,
    StructuredPayload,
    StructuredQuery,
    ToolExecutionBatch,
    ToolExecutionPlan,
    ToolExecutionResult,
)


def test_execution_plan_requires_exact_route_requests() -> None:
    retrieval = RetrievalQuery(
        question=("Why is management concerned about supplier concentration?"),
    )

    sql = StructuredQuery(
        company_id="PC-002",
        period="2026Q2",
        operation="metric_value",
        metric="revenue_usd",
    )

    plan = ToolExecutionPlan(
        route_label="retrieval+sql",
        retrieval=retrieval,
        sql=sql,
    )

    assert plan.required_tools() == (
        "retrieval",
        "sql",
    )

    with pytest.raises(
        ValidationError,
        match="does not match route_label",
    ):
        ToolExecutionPlan(
            route_label="retrieval+sql",
            retrieval=retrieval,
        )


def test_structured_query_enforces_operation_arguments() -> None:
    difference = StructuredQuery(
        company_id="PC-005",
        period="2026Q2",
        operation="metric_difference",
        metric="customer_count",
        comparison_period="2025Q2",
    )

    assert difference.comparison_period == "2025Q2"

    ratio = StructuredQuery(
        company_id="PC-004",
        period="2026Q2",
        operation="metric_ratio",
        metric="ebitda_usd",
        denominator_metric="revenue_usd",
    )

    assert ratio.denominator_metric == "revenue_usd"

    threshold = StructuredQuery(
        company_id="PC-005",
        period="2026Q2",
        operation="metric_threshold",
        metric="net_retention_pct",
        comparator="lt",
        threshold=Decimal("100"),
    )

    assert threshold.threshold == Decimal("100")

    with pytest.raises(
        ValidationError,
        match=("metric_difference requires comparison_period"),
    ):
        StructuredQuery(
            company_id="PC-005",
            period="2026Q2",
            operation="metric_difference",
            metric="revenue_usd",
        )

    with pytest.raises(
        ValidationError,
        match=("numerator and denominator must differ"),
    ):
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation="metric_ratio",
            metric="revenue_usd",
            denominator_metric=("revenue_usd"),
        )


def test_graph_query_validates_typed_transitions() -> None:
    query = GraphQuery(
        start_entity_type="customer",
        start_entity_id="CUST-001",
        paths=(
            GraphPath(
                hops=(
                    "customer_company",
                    "company_suppliers",
                ),
            ),
        ),
    )

    assert query.paths[0].hops == (
        "customer_company",
        "company_suppliers",
    )

    with pytest.raises(
        ValidationError,
        match="Invalid graph transition",
    ):
        GraphQuery(
            start_entity_type="company",
            start_entity_id="PC-001",
            paths=(
                GraphPath(
                    hops=("customer_company",),
                ),
            ),
        )


def test_graph_query_supports_branching_without_duplicate_paths() -> None:
    query = GraphQuery(
        start_entity_type="company",
        start_entity_id="PC-002",
        paths=(
            GraphPath(
                hops=("company_customers",),
            ),
            GraphPath(
                hops=("company_suppliers",),
            ),
        ),
    )

    assert len(query.paths) == 2

    with pytest.raises(
        ValidationError,
        match="duplicate traversal paths",
    ):
        GraphQuery(
            start_entity_type="company",
            start_entity_id="PC-002",
            paths=(
                GraphPath(
                    hops=("company_customers",),
                ),
                GraphPath(
                    hops=("company_customers",),
                ),
            ),
        )


def test_tool_result_requires_matching_payload_type() -> None:
    sql_payload = StructuredPayload(
        operation="metric_value",
        value=92_000_000,
        unit="USD",
        source_rows=(
            DatabaseRowReference(
                table="financial_metrics",
                primary_key={
                    "dataset_version": ("northstar-v1"),
                    "company_id": "PC-004",
                    "period": "2026Q2",
                },
            ),
        ),
    )

    result = ToolExecutionResult(
        tool="sql",
        status="ok",
        payload=sql_payload,
        duration_ms=1.25,
    )

    assert result.tool == "sql"

    with pytest.raises(
        ValidationError,
        match="payload type does not match",
    ):
        ToolExecutionResult(
            tool="retrieval",
            status="ok",
            payload=sql_payload,
            duration_ms=1.25,
        )

    with pytest.raises(
        ValidationError,
        match="requires an error message",
    ):
        ToolExecutionResult(
            tool="sql",
            status="error",
            duration_ms=1.25,
        )


def test_execution_batch_requires_complete_canonical_tool_order() -> None:
    plan = ToolExecutionPlan(
        route_label="sql+graph",
        sql=StructuredQuery(
            company_id="PC-002",
            period="2026Q2",
            operation="metric_value",
            metric="revenue_usd",
        ),
        graph=GraphQuery(
            start_entity_type="company",
            start_entity_id="PC-002",
            paths=(
                GraphPath(
                    hops=("company_suppliers",),
                ),
            ),
        ),
    )

    sql_result = ToolExecutionResult(
        tool="sql",
        status="ok",
        payload=StructuredPayload(
            operation="metric_value",
            value=155_000_000,
            unit="USD",
            source_rows=(),
        ),
        duration_ms=1.0,
    )

    graph_result = ToolExecutionResult(
        tool="graph",
        status="ok",
        payload=GraphPayload(
            nodes=(
                GraphNode(
                    entity_type="company",
                    entity_id="PC-002",
                    name="Alder Manufacturing",
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
                    attributes={
                        "criticality": ("critical"),
                    },
                ),
            ),
        ),
        duration_ms=1.0,
    )

    batch = ToolExecutionBatch(
        plan=plan,
        results=(
            sql_result,
            graph_result,
        ),
    )

    assert tuple(result.tool for result in batch.results) == (
        "sql",
        "graph",
    )

    with pytest.raises(
        ValidationError,
        match="canonical order",
    ):
        ToolExecutionBatch(
            plan=plan,
            results=(
                graph_result,
                sql_result,
            ),
        )


def test_empty_retrieval_result_is_typed() -> None:
    result = ToolExecutionResult(
        tool="retrieval",
        status="empty",
        payload=RetrievalPayload(
            hits=(),
        ),
        duration_ms=0.5,
    )

    assert result.status == "empty"
    assert result.payload is not None
