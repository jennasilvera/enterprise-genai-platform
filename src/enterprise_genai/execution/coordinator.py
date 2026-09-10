from __future__ import annotations

from typing import Protocol

from enterprise_genai.execution.contracts import (
    GraphQuery,
    PortfolioGraphQuery,
    RetrievalQuery,
    StructuredQuery,
    ToolExecutionBatch,
    ToolExecutionPlan,
    ToolExecutionResult,
    ToolFamily,
)


class RetrievalExecutorProtocol(Protocol):
    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult: ...


class StructuredExecutorProtocol(Protocol):
    def execute(
        self,
        query: StructuredQuery,
    ) -> ToolExecutionResult: ...


class GraphExecutorProtocol(Protocol):
    def execute(
        self,
        query: GraphQuery | PortfolioGraphQuery,
    ) -> ToolExecutionResult: ...


class ToolExecutionCoordinator:
    """Execute an already-planned tool set in canonical order."""

    def __init__(
        self,
        *,
        retrieval_executor: (RetrievalExecutorProtocol | None) = None,
        sql_executor: (StructuredExecutorProtocol | None) = None,
        graph_executor: (GraphExecutorProtocol | None) = None,
    ) -> None:
        self._retrieval_executor = retrieval_executor
        self._sql_executor = sql_executor
        self._graph_executor = graph_executor

    @staticmethod
    def _dependency_error(
        tool: ToolFamily,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool=tool,
            status="error",
            duration_ms=0.0,
            error=(f"{tool} executor is not configured"),
        )

    @staticmethod
    def _isolated_failure(
        tool: ToolFamily,
        exc: Exception,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool=tool,
            status="error",
            duration_ms=0.0,
            error=(f"coordinator isolated {tool} executor failure: {type(exc).__name__}"),
        )

    @staticmethod
    def _validate_result_tool(
        *,
        expected_tool: ToolFamily,
        result: ToolExecutionResult,
    ) -> ToolExecutionResult:
        if result.tool == expected_tool:
            return result

        return ToolExecutionResult(
            tool=expected_tool,
            status="error",
            duration_ms=0.0,
            error=(f"executor returned result for {result.tool!r}; expected {expected_tool!r}"),
        )

    def _execute_retrieval(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        executor = self._retrieval_executor

        if executor is None:
            return self._dependency_error("retrieval")

        try:
            result = executor.execute(query)
        except Exception as exc:
            return self._isolated_failure(
                "retrieval",
                exc,
            )

        return self._validate_result_tool(
            expected_tool="retrieval",
            result=result,
        )

    def _execute_sql(
        self,
        query: StructuredQuery,
    ) -> ToolExecutionResult:
        executor = self._sql_executor

        if executor is None:
            return self._dependency_error("sql")

        try:
            result = executor.execute(query)
        except Exception as exc:
            return self._isolated_failure(
                "sql",
                exc,
            )

        return self._validate_result_tool(
            expected_tool="sql",
            result=result,
        )

    def _execute_graph(
        self,
        query: GraphQuery | PortfolioGraphQuery,
    ) -> ToolExecutionResult:
        executor = self._graph_executor

        if executor is None:
            return self._dependency_error("graph")

        try:
            result = executor.execute(query)
        except Exception as exc:
            return self._isolated_failure(
                "graph",
                exc,
            )

        return self._validate_result_tool(
            expected_tool="graph",
            result=result,
        )

    def execute(
        self,
        plan: ToolExecutionPlan,
    ) -> ToolExecutionBatch:
        """Execute exactly the tools present in the validated plan."""

        results: list[ToolExecutionResult] = []

        # Canonical execution order is part
        # of the execution contract.
        if plan.retrieval is not None:
            results.append(self._execute_retrieval(plan.retrieval))

        if plan.sql is not None:
            results.append(self._execute_sql(plan.sql))

        if plan.graph is not None:
            results.append(self._execute_graph(plan.graph))

        return ToolExecutionBatch(
            plan=plan,
            results=tuple(results),
        )
