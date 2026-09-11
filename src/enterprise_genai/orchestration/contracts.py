from __future__ import annotations

from typing import Literal

from pydantic import (
    Field,
    model_validator,
)

from enterprise_genai.execution.contracts import (
    FrozenContractModel,
    NonEmptyStr,
    PortfolioGraphQuery,
    StructuredQuery,
    ToolExecutionPlan,
    ToolExecutionResult,
)

OrchestrationMode = Literal[
    "single_tool",
    "independent",
    "dependent",
]

OrchestrationStatus = Literal[
    "pending",
    "running",
    "completed",
    "blocked",
    "failed",
]

DependencyKind = Literal["graph_company_ids_to_sql_candidates",]


class ExecutionDependency(FrozenContractModel):
    """One explicitly supported tool dependency."""

    kind: DependencyKind = "graph_company_ids_to_sql_candidates"

    upstream_tool: Literal["graph"] = "graph"

    downstream_tool: Literal["sql"] = "sql"


class BoundedOrchestrationPlan(FrozenContractModel):
    """Validated orchestration around a frozen tool plan.

    Version 1 supports either independent execution or
    one graph-to-SQL company-candidate dependency.
    """

    question: NonEmptyStr

    execution_plan: ToolExecutionPlan

    dependencies: tuple[
        ExecutionDependency,
        ...,
    ] = Field(
        default=(),
        max_length=1,
    )

    def mode(
        self,
    ) -> OrchestrationMode:
        if self.dependencies:
            return "dependent"

        if len(self.execution_plan.required_tools()) == 1:
            return "single_tool"

        return "independent"

    @model_validator(mode="after")
    def validate_dependencies(
        self,
    ) -> BoundedOrchestrationPlan:
        if not self.dependencies:
            return self

        dependency = self.dependencies[0]

        if dependency.kind != ("graph_company_ids_to_sql_candidates"):
            raise ValueError("Unsupported execution dependency.")

        graph_query = self.execution_plan.graph

        sql_query = self.execution_plan.sql

        if graph_query is None:
            raise ValueError("Graph-to-SQL dependency requires a graph request.")

        if sql_query is None:
            raise ValueError("Graph-to-SQL dependency requires a SQL request.")

        if not isinstance(
            graph_query,
            PortfolioGraphQuery,
        ):
            raise ValueError(
                "Graph-to-SQL dependency requires PortfolioGraphQuery company discovery."
            )

        if sql_query.candidate_company_ids:
            raise ValueError(
                "Dependent SQL request must "
                "start without candidate IDs; "
                "the graph handoff supplies them."
            )

        portfolio_operations = {
            "portfolio_metric_sum",
            "portfolio_metric_filter",
            "portfolio_metric_rank",
            "portfolio_growth_rank",
            "portfolio_ratio_rank",
        }

        if sql_query.operation not in portfolio_operations:
            raise ValueError("Graph-to-SQL dependency requires a portfolio structured operation.")

        return self


class DependencyHandoff(FrozenContractModel):
    """Materialized output of one bounded dependency."""

    kind: DependencyKind = "graph_company_ids_to_sql_candidates"

    company_ids: tuple[
        NonEmptyStr,
        ...,
    ] = Field(
        min_length=1,
    )

    downstream_query: StructuredQuery

    @model_validator(mode="after")
    def validate_handoff(
        self,
    ) -> DependencyHandoff:
        if len(set(self.company_ids)) != len(self.company_ids):
            raise ValueError("Dependency company IDs must be unique.")

        if tuple(sorted(self.company_ids)) != self.company_ids:
            raise ValueError("Dependency company IDs must be sorted.")

        if self.downstream_query.candidate_company_ids != self.company_ids:
            raise ValueError(
                "Downstream SQL candidate IDs must exactly equal the dependency company IDs."
            )

        return self


class OrchestrationStateSnapshot(FrozenContractModel):
    """Immutable validated snapshot of orchestration state.

    The LangGraph runtime may use a mutable mapping in
    Phase 9B, but snapshots are validated at explicit
    orchestration boundaries.
    """

    plan: BoundedOrchestrationPlan

    results: tuple[
        ToolExecutionResult,
        ...,
    ] = ()

    handoffs: tuple[
        DependencyHandoff,
        ...,
    ] = Field(
        default=(),
        max_length=1,
    )

    status: OrchestrationStatus = "pending"

    @model_validator(mode="after")
    def validate_state(
        self,
    ) -> OrchestrationStateSnapshot:
        result_tools = tuple(result.tool for result in self.results)

        if len(set(result_tools)) != len(result_tools):
            raise ValueError("Orchestration state cannot contain duplicate tool results.")

        planned_tools = set(self.plan.execution_plan.required_tools())

        unexpected = set(result_tools) - planned_tools

        if unexpected:
            raise ValueError(
                f"Orchestration state contains results for unplanned tools: {sorted(unexpected)!r}."
            )

        if self.handoffs and not self.plan.dependencies:
            raise ValueError("Independent orchestration cannot contain a dependency handoff.")

        if self.status == "pending" and (self.results or self.handoffs):
            raise ValueError("Pending orchestration state cannot contain results or handoffs.")

        if self.status == "completed" and set(result_tools) != planned_tools:
            raise ValueError(
                "Completed orchestration state "
                "must contain exactly one result "
                "for every planned tool."
            )

        if self.status == "completed" and self.plan.dependencies and not self.handoffs:
            raise ValueError("Completed dependent orchestration requires its dependency handoff.")

        if self.handoffs and "graph" not in result_tools:
            raise ValueError("Dependency handoff requires an upstream graph result.")

        return self
