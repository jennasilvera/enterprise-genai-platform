from enterprise_genai.execution.contracts import (
    GraphPath,
    GraphPayload,
    GraphQuery,
    PortfolioGraphPredicate,
    PortfolioGraphQuery,
    RetrievalPayload,
    RetrievalQuery,
    StructuredPayload,
    StructuredQuery,
    ToolExecutionPlan,
    ToolExecutionResult,
)
from enterprise_genai.execution.coordinator import (
    ToolExecutionCoordinator,
)


class _RecordingExecutor:
    def __init__(
        self,
        *,
        name: str,
        result: ToolExecutionResult,
        calls: list[str],
    ) -> None:
        self.name = name
        self.result = result
        self.calls = calls

    def execute(
        self,
        query: object,
    ) -> ToolExecutionResult:
        del query

        self.calls.append(self.name)

        return self.result


class _RaisingExecutor:
    def __init__(
        self,
        *,
        name: str,
        calls: list[str],
    ) -> None:
        self.name = name
        self.calls = calls

    def execute(
        self,
        query: object,
    ) -> ToolExecutionResult:
        del query

        self.calls.append(self.name)

        raise RuntimeError("simulated executor failure")


def _retrieval_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="retrieval",
        status="empty",
        payload=RetrievalPayload(hits=()),
        duration_ms=0.0,
    )


def _sql_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="sql",
        status="ok",
        payload=StructuredPayload(
            operation="metric_value",
            value=1,
            unit="count",
            source_rows=(),
        ),
        duration_ms=0.0,
    )


def _graph_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="graph",
        status="empty",
        payload=GraphPayload(
            nodes=(),
            edges=(),
            empty_reason=("start_entity_not_found"),
        ),
        duration_ms=0.0,
    )


def _all_three_plan() -> ToolExecutionPlan:
    return ToolExecutionPlan(
        route_label=("retrieval+sql+graph"),
        retrieval=RetrievalQuery(question="test question"),
        sql=StructuredQuery(
            company_id="PC-001",
            period="2026Q2",
            operation="metric_value",
            metric="customer_count",
        ),
        graph=GraphQuery(
            start_entity_type=("company"),
            start_entity_id="PC-001",
            paths=(
                GraphPath(
                    hops=("company_customers",),
                ),
            ),
        ),
    )


def test_coordinator_executes_all_tools_in_canonical_order() -> None:
    calls: list[str] = []

    coordinator = ToolExecutionCoordinator(
        retrieval_executor=(
            _RecordingExecutor(
                name="retrieval",
                result=(_retrieval_result()),
                calls=calls,
            )
        ),
        sql_executor=(
            _RecordingExecutor(
                name="sql",
                result=_sql_result(),
                calls=calls,
            )
        ),
        graph_executor=(
            _RecordingExecutor(
                name="graph",
                result=(_graph_result()),
                calls=calls,
            )
        ),
    )

    batch = coordinator.execute(_all_three_plan())

    assert calls == [
        "retrieval",
        "sql",
        "graph",
    ]

    assert [result.tool for result in batch.results] == [
        "retrieval",
        "sql",
        "graph",
    ]


def test_coordinator_executes_only_planned_tool() -> None:
    calls: list[str] = []

    coordinator = ToolExecutionCoordinator(
        retrieval_executor=(
            _RecordingExecutor(
                name="retrieval",
                result=(_retrieval_result()),
                calls=calls,
            )
        ),
    )

    plan = ToolExecutionPlan(
        route_label="retrieval",
        retrieval=RetrievalQuery(question="test question"),
    )

    batch = coordinator.execute(plan)

    assert calls == ["retrieval"]

    assert [result.tool for result in batch.results] == ["retrieval"]


def test_executor_exception_isolated_and_later_tools_continue() -> None:
    calls: list[str] = []

    coordinator = ToolExecutionCoordinator(
        retrieval_executor=(
            _RecordingExecutor(
                name="retrieval",
                result=(_retrieval_result()),
                calls=calls,
            )
        ),
        sql_executor=(
            _RaisingExecutor(
                name="sql",
                calls=calls,
            )
        ),
        graph_executor=(
            _RecordingExecutor(
                name="graph",
                result=(_graph_result()),
                calls=calls,
            )
        ),
    )

    batch = coordinator.execute(_all_three_plan())

    assert calls == [
        "retrieval",
        "sql",
        "graph",
    ]

    assert [result.status for result in batch.results] == [
        "empty",
        "error",
        "empty",
    ]

    sql_result = batch.results[1]

    assert sql_result.tool == "sql"
    assert sql_result.error is not None

    assert "RuntimeError" in sql_result.error


def test_missing_dependency_returns_typed_error_and_continues() -> None:
    calls: list[str] = []

    coordinator = ToolExecutionCoordinator(
        retrieval_executor=(
            _RecordingExecutor(
                name="retrieval",
                result=(_retrieval_result()),
                calls=calls,
            )
        ),
        graph_executor=(
            _RecordingExecutor(
                name="graph",
                result=(_graph_result()),
                calls=calls,
            )
        ),
    )

    batch = coordinator.execute(_all_three_plan())

    assert [result.tool for result in batch.results] == [
        "retrieval",
        "sql",
        "graph",
    ]

    assert batch.results[1].status == "error"

    assert batch.results[1].error == "sql executor is not configured"

    assert calls == [
        "retrieval",
        "graph",
    ]


def test_wrong_executor_tool_is_converted_to_expected_tool_error() -> None:
    calls: list[str] = []

    wrong = ToolExecutionResult(
        tool="graph",
        status="empty",
        payload=GraphPayload(
            nodes=(),
            edges=(),
            empty_reason=("start_entity_not_found"),
        ),
        duration_ms=0.0,
    )

    coordinator = ToolExecutionCoordinator(
        retrieval_executor=(
            _RecordingExecutor(
                name="retrieval",
                result=wrong,
                calls=calls,
            )
        ),
    )

    batch = coordinator.execute(
        ToolExecutionPlan(
            route_label="retrieval",
            retrieval=RetrievalQuery(question="test question"),
        )
    )

    result = batch.results[0]

    assert result.tool == ("retrieval")
    assert result.status == "error"
    assert result.error is not None

    assert "expected 'retrieval'" in result.error


def test_existing_typed_tool_error_is_preserved() -> None:
    calls: list[str] = []

    typed_error = ToolExecutionResult(
        tool="sql",
        status="error",
        duration_ms=0.0,
        error=("structured SQL execution failed: SQLAlchemyError"),
    )

    coordinator = ToolExecutionCoordinator(
        sql_executor=(
            _RecordingExecutor(
                name="sql",
                result=typed_error,
                calls=calls,
            )
        )
    )

    plan = ToolExecutionPlan(
        route_label="sql",
        sql=StructuredQuery(
            company_id="PC-001",
            period="2026Q2",
            operation="metric_value",
            metric="customer_count",
        ),
    )

    batch = coordinator.execute(plan)

    assert batch.results == (typed_error,)

    assert calls == ["sql"]


def test_coordinator_forwards_portfolio_graph_query_unchanged() -> None:
    captured: list[object] = []

    class _CapturingGraphExecutor:
        def execute(
            self,
            query: object,
        ) -> ToolExecutionResult:
            captured.append(query)

            return ToolExecutionResult(
                tool="graph",
                status="empty",
                payload=GraphPayload(
                    nodes=(),
                    edges=(),
                    matched_company_ids=(),
                    empty_reason="no_matches",
                ),
                duration_ms=0.0,
            )

    query = PortfolioGraphQuery(
        predicates=(
            PortfolioGraphPredicate(
                relationship_type=("company_supplier"),
                target_country="Germany",
                criticality="critical",
            ),
        )
    )

    plan = ToolExecutionPlan(
        route_label="graph",
        graph=query,
    )

    assert isinstance(
        plan.graph,
        PortfolioGraphQuery,
    )

    assert plan.required_tools() == ("graph",)

    #
    # Prove the union also survives
    # serialization/deserialization rather
    # than only accepting a pre-built object.
    #
    restored = ToolExecutionPlan.model_validate(plan.model_dump(mode="json"))

    assert isinstance(
        restored.graph,
        PortfolioGraphQuery,
    )

    assert restored.graph == query

    coordinator = ToolExecutionCoordinator(graph_executor=(_CapturingGraphExecutor()))

    batch = coordinator.execute(restored)

    assert len(batch.results) == 1

    assert batch.results[0].tool == "graph"

    assert batch.results[0].status == "empty"

    assert len(captured) == 1

    #
    # Coordinator must pass the exact object
    # held by the validated execution plan.
    #
    assert captured[0] is restored.graph

    assert batch.plan == restored
