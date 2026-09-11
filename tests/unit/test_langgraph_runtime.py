from __future__ import annotations

from enterprise_genai.execution.contracts import (
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
    ExecutionDependency,
)
from enterprise_genai.orchestration.langgraph_runtime import (
    BoundedLangGraphRuntime,
)


class RecordingRetrievalExecutor:
    def __init__(
        self,
        calls: list[str],
    ) -> None:
        self.calls = calls

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        self.calls.append("retrieval")

        return ToolExecutionResult(
            tool="retrieval",
            status="ok",
            duration_ms=0.0,
            payload=RetrievalPayload(
                hits=(
                    RetrievalHit(
                        rank=1,
                        chunk_id="CHUNK-1",
                        evidence_id="EVID-1",
                        document_id="DOC-1",
                        text=("Synthetic supporting evidence."),
                        source_fact_ids=("RISK-005",),
                        rrf_score=0.03,
                        bm25_rank=1,
                        dense_rank=1,
                    ),
                )
            ),
        )


class RecordingSqlExecutor:
    def __init__(
        self,
        calls: list[str],
    ) -> None:
        self.calls = calls

        self.queries: list[StructuredQuery] = []

    def execute(
        self,
        query: StructuredQuery,
    ) -> ToolExecutionResult:
        self.calls.append("sql")

        self.queries.append(query)

        return ToolExecutionResult(
            tool="sql",
            status="ok",
            duration_ms=0.0,
            payload=StructuredPayload(
                operation=query.operation,
                value=None,
                entities=(
                    StructuredEntity(
                        company_id="PC-008",
                        name=("NovaBio Instruments"),
                        score=83_000_000,
                    ),
                ),
                source_rows=(),
            ),
        )


def _successful_graph_payload() -> GraphPayload:
    return GraphPayload(
        nodes=(
            GraphNode(
                entity_type="company",
                entity_id="PC-002",
                name=("Alder Manufacturing"),
            ),
            GraphNode(
                entity_type="company",
                entity_id="PC-008",
                name=("NovaBio Instruments"),
            ),
            GraphNode(
                entity_type="supplier",
                entity_id="SUP-005",
                name=("TitaniumWorks GmbH"),
            ),
            GraphNode(
                entity_type="supplier",
                entity_id="SUP-011",
                name="Helix Motion GmbH",
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
            ),
            GraphEdge(
                relationship_type=("company_supplier"),
                relationship_id="CS-011",
                source_type="company",
                source_id="PC-008",
                target_type="supplier",
                target_id="SUP-011",
            ),
        ),
        matched_company_ids=(
            "PC-002",
            "PC-008",
        ),
    )


class SuccessfulGraphExecutor:
    def __init__(
        self,
        calls: list[str],
    ) -> None:
        self.calls = calls

    def execute(
        self,
        query: PortfolioGraphQuery,
    ) -> ToolExecutionResult:
        self.calls.append("graph")

        return ToolExecutionResult(
            tool="graph",
            status="ok",
            duration_ms=0.0,
            payload=(_successful_graph_payload()),
        )


class EmptyGraphExecutor:
    def __init__(
        self,
        calls: list[str],
    ) -> None:
        self.calls = calls

    def execute(
        self,
        query: PortfolioGraphQuery,
    ) -> ToolExecutionResult:
        self.calls.append("graph")

        return ToolExecutionResult(
            tool="graph",
            status="empty",
            duration_ms=0.0,
            payload=GraphPayload(
                nodes=(),
                edges=(),
                matched_company_ids=(),
                empty_reason="no_matches",
            ),
        )


class ErrorGraphExecutor:
    def __init__(
        self,
        calls: list[str],
    ) -> None:
        self.calls = calls

    def execute(
        self,
        query: PortfolioGraphQuery,
    ) -> ToolExecutionResult:
        self.calls.append("graph")

        return ToolExecutionResult(
            tool="graph",
            status="error",
            duration_ms=0.0,
            error=("synthetic graph failure"),
        )


class MalformedGraphExecutor:
    def __init__(
        self,
        calls: list[str],
    ) -> None:
        self.calls = calls

    def execute(
        self,
        query: PortfolioGraphQuery,
    ) -> ToolExecutionResult:
        self.calls.append("graph")

        wrong_payload = StructuredPayload(
            operation=("portfolio_metric_rank"),
            value=1,
            source_rows=(),
        )

        return ToolExecutionResult.model_construct(
            tool="graph",
            status="ok",
            payload=wrong_payload,
            duration_ms=0.0,
            error=None,
        )


def _rank_query() -> StructuredQuery:
    return StructuredQuery(
        period="2026Q2",
        operation=("portfolio_metric_rank"),
        metric="revenue_usd",
        rank_order="lowest",
        result_limit=1,
    )


def _graph_query() -> PortfolioGraphQuery:
    return PortfolioGraphQuery(
        predicates=(
            PortfolioGraphPredicate(
                relationship_type=("company_supplier"),
                target_country="Germany",
                criticality="critical",
            ),
        )
    )


def _dependent_plan() -> BoundedOrchestrationPlan:
    return BoundedOrchestrationPlan(
        question=("Among companies with critical suppliers in Germany, which had lower revenue?"),
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql+graph",
                sql=_rank_query(),
                graph=_graph_query(),
            )
        ),
        dependencies=(ExecutionDependency(),),
    )


def test_sql_only_executes_once_and_completes() -> None:
    calls: list[str] = []

    sql = RecordingSqlExecutor(calls)

    runtime = BoundedLangGraphRuntime(sql_executor=sql)

    plan = BoundedOrchestrationPlan(
        question="Lowest revenue company",
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql",
                sql=_rank_query(),
            )
        ),
    )

    result = runtime.execute(plan)

    assert calls == [
        "sql",
    ]

    assert result.status == ("completed")

    assert tuple(item.tool for item in result.results) == ("sql",)

    assert result.handoffs == ()


def test_independent_retrieval_and_sql_execute_once() -> None:
    calls: list[str] = []

    retrieval = RecordingRetrievalExecutor(calls)

    sql = RecordingSqlExecutor(calls)

    runtime = BoundedLangGraphRuntime(
        retrieval_executor=retrieval,
        sql_executor=sql,
    )

    plan = BoundedOrchestrationPlan(
        question=("Which company had low retention and supporting document evidence?"),
        execution_plan=(
            ToolExecutionPlan(
                route_label=("retrieval+sql"),
                retrieval=(
                    RetrievalQuery(question=("newer customer cohorts failing to normalize"))
                ),
                sql=StructuredQuery(
                    period="2026Q2",
                    operation=("portfolio_metric_filter"),
                    metric=("net_retention_pct"),
                    comparator="lt",
                    threshold=100,
                ),
            )
        ),
    )

    result = runtime.execute(plan)

    assert calls == [
        "retrieval",
        "sql",
    ]

    assert result.status == ("completed")

    assert tuple(item.tool for item in result.results) == (
        "retrieval",
        "sql",
    )

    assert result.handoffs == ()


def test_graph_to_sql_materializes_candidate_handoff() -> None:
    calls: list[str] = []

    graph = SuccessfulGraphExecutor(calls)

    sql = RecordingSqlExecutor(calls)

    runtime = BoundedLangGraphRuntime(
        graph_executor=graph,
        sql_executor=sql,
    )

    plan = _dependent_plan()

    result = runtime.execute(plan)

    assert calls == [
        "graph",
        "sql",
    ]

    assert result.status == ("completed")

    assert len(result.handoffs) == 1

    handoff = result.handoffs[0]

    assert handoff.company_ids == (
        "PC-002",
        "PC-008",
    )

    assert len(sql.queries) == 1

    assert sql.queries[0].candidate_company_ids == (
        "PC-002",
        "PC-008",
    )

    assert plan.execution_plan.sql.candidate_company_ids == ()


def test_empty_graph_blocks_dependent_sql() -> None:
    calls: list[str] = []

    graph = EmptyGraphExecutor(calls)

    sql = RecordingSqlExecutor(calls)

    runtime = BoundedLangGraphRuntime(
        graph_executor=graph,
        sql_executor=sql,
    )

    result = runtime.execute(_dependent_plan())

    assert calls == [
        "graph",
    ]

    assert sql.queries == []

    assert result.status == ("blocked")

    assert result.handoffs == ()


def test_graph_error_fails_without_sql_execution() -> None:
    calls: list[str] = []

    graph = ErrorGraphExecutor(calls)

    sql = RecordingSqlExecutor(calls)

    runtime = BoundedLangGraphRuntime(
        graph_executor=graph,
        sql_executor=sql,
    )

    result = runtime.execute(_dependent_plan())

    assert calls == [
        "graph",
    ]

    assert sql.queries == []

    assert result.status == ("failed")

    assert result.results[0].status == "error"


def test_malformed_graph_result_fails_boundary_validation() -> None:
    calls: list[str] = []

    graph = MalformedGraphExecutor(calls)

    sql = RecordingSqlExecutor(calls)

    runtime = BoundedLangGraphRuntime(
        graph_executor=graph,
        sql_executor=sql,
    )

    result = runtime.execute(_dependent_plan())

    assert calls == [
        "graph",
    ]

    assert sql.queries == []

    assert result.status == ("failed")

    graph_result = result.results[0]

    assert graph_result.tool == ("graph")

    assert graph_result.status == ("error")

    assert graph_result.error is not None

    assert "malformed graph result" in graph_result.error
