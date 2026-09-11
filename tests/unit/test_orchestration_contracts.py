from typing import Literal

import pytest
from pydantic import ValidationError

from enterprise_genai.execution.contracts import (
    PortfolioGraphPredicate,
    PortfolioGraphQuery,
    RetrievalQuery,
    StructuredQuery,
    ToolExecutionPlan,
    ToolExecutionResult,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    DependencyHandoff,
    ExecutionDependency,
    OrchestrationStateSnapshot,
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


def _candidate_rank_query() -> StructuredQuery:
    return StructuredQuery(
        period="2026Q2",
        operation=("portfolio_metric_rank"),
        metric="revenue_usd",
        rank_order="lowest",
        result_limit=1,
    )


def test_single_tool_plan_mode() -> None:
    plan = BoundedOrchestrationPlan(
        question=("Which company had the highest revenue growth?"),
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql",
                sql=StructuredQuery(
                    period="2026Q2",
                    operation=("portfolio_growth_rank"),
                    metric="revenue_usd",
                    comparison_period=("2025Q2"),
                    rank_order="highest",
                    result_limit=1,
                ),
            )
        ),
    )

    assert plan.mode() == "single_tool"


def test_independent_multi_tool_plan_mode() -> None:
    plan = BoundedOrchestrationPlan(
        question=("Which company has low retention and supporting document evidence?"),
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

    assert plan.mode() == "independent"


def test_graph_to_sql_dependency_mode() -> None:
    plan = BoundedOrchestrationPlan(
        question=("Among companies with critical suppliers in Germany, which had lower revenue?"),
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql+graph",
                sql=(_candidate_rank_query()),
                graph=(_graph_query()),
            )
        ),
        dependencies=(ExecutionDependency(),),
    )

    assert plan.mode() == "dependent"


def test_dependency_requires_graph_request() -> None:
    with pytest.raises(
        ValidationError,
        match=("requires a graph request"),
    ):
        BoundedOrchestrationPlan(
            question="Dependent query",
            execution_plan=(
                ToolExecutionPlan(
                    route_label="sql",
                    sql=(_candidate_rank_query()),
                )
            ),
            dependencies=(ExecutionDependency(),),
        )


def test_dependency_requires_portfolio_graph_query() -> None:
    from enterprise_genai.execution.contracts import (
        GraphPath,
        GraphQuery,
    )

    with pytest.raises(
        ValidationError,
        match=("requires PortfolioGraphQuery"),
    ):
        BoundedOrchestrationPlan(
            question="Dependent query",
            execution_plan=(
                ToolExecutionPlan(
                    route_label="sql+graph",
                    sql=(_candidate_rank_query()),
                    graph=GraphQuery(
                        start_entity_type=("company"),
                        start_entity_id=("PC-002"),
                        paths=(GraphPath(hops=("company_suppliers",)),),
                    ),
                )
            ),
            dependencies=(ExecutionDependency(),),
        )


def test_dependency_rejects_prepopulated_sql_candidates() -> None:
    with pytest.raises(
        ValidationError,
        match=("must start without candidate IDs"),
    ):
        BoundedOrchestrationPlan(
            question="Dependent query",
            execution_plan=(
                ToolExecutionPlan(
                    route_label="sql+graph",
                    sql=StructuredQuery(
                        period="2026Q2",
                        operation=("portfolio_metric_rank"),
                        metric="revenue_usd",
                        candidate_company_ids=(
                            "PC-002",
                            "PC-008",
                        ),
                        rank_order="lowest",
                        result_limit=1,
                    ),
                    graph=(_graph_query()),
                )
            ),
            dependencies=(ExecutionDependency(),),
        )


def test_dependency_handoff_requires_exact_candidate_scope() -> None:
    query = StructuredQuery(
        period="2026Q2",
        operation=("portfolio_metric_rank"),
        metric="revenue_usd",
        candidate_company_ids=(
            "PC-002",
            "PC-008",
        ),
        rank_order="lowest",
        result_limit=1,
    )

    handoff = DependencyHandoff(
        company_ids=(
            "PC-002",
            "PC-008",
        ),
        downstream_query=query,
    )

    assert handoff.downstream_query.candidate_company_ids == handoff.company_ids


def test_dependency_handoff_rejects_scope_mismatch() -> None:
    query = StructuredQuery(
        period="2026Q2",
        operation=("portfolio_metric_rank"),
        metric="revenue_usd",
        candidate_company_ids=("PC-008",),
        rank_order="lowest",
        result_limit=1,
    )

    with pytest.raises(
        ValidationError,
        match=("must exactly equal"),
    ):
        DependencyHandoff(
            company_ids=(
                "PC-002",
                "PC-008",
            ),
            downstream_query=query,
        )


def test_state_rejects_unplanned_tool_result() -> None:
    plan = BoundedOrchestrationPlan(
        question="SQL only",
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql",
                sql=(_candidate_rank_query()),
            )
        ),
    )

    graph_result = ToolExecutionResult(
        tool="graph",
        status="error",
        duration_ms=0.0,
        error=("synthetic test error"),
    )

    with pytest.raises(
        ValidationError,
        match=("results for unplanned tools"),
    ):
        OrchestrationStateSnapshot(
            plan=plan,
            results=(graph_result,),
        )


def _dependent_plan() -> BoundedOrchestrationPlan:
    return BoundedOrchestrationPlan(
        question="Dependent graph to SQL query",
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql+graph",
                sql=(_candidate_rank_query()),
                graph=(_graph_query()),
            )
        ),
        dependencies=(ExecutionDependency(),),
    )


def _error_result(
    tool: Literal[
        "retrieval",
        "sql",
        "graph",
    ],
) -> ToolExecutionResult:
    return ToolExecutionResult(
        tool=tool,
        status="error",
        duration_ms=0.0,
        error="synthetic test error",
    )


def test_pending_state_rejects_results() -> None:
    plan = BoundedOrchestrationPlan(
        question="SQL only",
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql",
                sql=(_candidate_rank_query()),
            )
        ),
    )

    with pytest.raises(
        ValidationError,
        match=("Pending orchestration state"),
    ):
        OrchestrationStateSnapshot(
            plan=plan,
            results=(_error_result("sql"),),
            status="pending",
        )


def test_completed_state_requires_all_planned_results() -> None:
    plan = BoundedOrchestrationPlan(
        question="Independent retrieval plus SQL",
        execution_plan=(
            ToolExecutionPlan(
                route_label="retrieval+sql",
                retrieval=RetrievalQuery(question=("supporting evidence")),
                sql=(_candidate_rank_query()),
            )
        ),
    )

    with pytest.raises(
        ValidationError,
        match=("exactly one result for every planned tool"),
    ):
        OrchestrationStateSnapshot(
            plan=plan,
            results=(_error_result("sql"),),
            status="completed",
        )


def test_completed_dependency_requires_handoff() -> None:
    plan = _dependent_plan()

    with pytest.raises(
        ValidationError,
        match=("requires its dependency handoff"),
    ):
        OrchestrationStateSnapshot(
            plan=plan,
            results=(
                _error_result("graph"),
                _error_result("sql"),
            ),
            status="completed",
        )


def test_handoff_requires_graph_result() -> None:
    plan = _dependent_plan()

    downstream = StructuredQuery(
        period="2026Q2",
        operation=("portfolio_metric_rank"),
        metric="revenue_usd",
        candidate_company_ids=(
            "PC-002",
            "PC-008",
        ),
        rank_order="lowest",
        result_limit=1,
    )

    handoff = DependencyHandoff(
        company_ids=(
            "PC-002",
            "PC-008",
        ),
        downstream_query=downstream,
    )

    with pytest.raises(
        ValidationError,
        match=("requires an upstream graph result"),
    ):
        OrchestrationStateSnapshot(
            plan=plan,
            handoffs=(handoff,),
            status="running",
        )
