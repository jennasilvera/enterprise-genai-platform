from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import (
    Literal,
    TypedDict,
    cast,
)

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from enterprise_genai.data.routing_models import (
    ToolFamily,
)
from enterprise_genai.execution.contracts import (
    GraphPayload,
    StructuredQuery,
    ToolExecutionResult,
)
from enterprise_genai.execution.coordinator import (
    GraphExecutorProtocol,
    RetrievalExecutorProtocol,
    StructuredExecutorProtocol,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    DependencyHandoff,
    OrchestrationStateSnapshot,
    OrchestrationStatus,
)


class RuntimeState(
    TypedDict,
    total=False,
):
    """Mutable LangGraph state internal to the runtime."""

    plan: BoundedOrchestrationPlan

    results: tuple[
        ToolExecutionResult,
        ...,
    ]

    handoffs: tuple[
        DependencyHandoff,
        ...,
    ]

    status: OrchestrationStatus

    effective_sql_query: StructuredQuery | None

    handoff_failed: bool


def _result_for(
    state: RuntimeState,
    tool: ToolFamily,
) -> ToolExecutionResult | None:
    for result in state.get(
        "results",
        (),
    ):
        if result.tool == tool:
            return result

    return None


def _append_result(
    state: RuntimeState,
    result: ToolExecutionResult,
) -> tuple[
    ToolExecutionResult,
    ...,
]:
    return (
        *state.get(
            "results",
            (),
        ),
        result,
    )


class BoundedLangGraphRuntime:
    """Deterministic LangGraph scheduler for frozen tools.

    Version 1 performs no planning, answer synthesis,
    retries, abstention policy, or arbitrary looping.
    """

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

        self._graph = self._build_graph()

    @staticmethod
    def _error_result(
        tool: ToolFamily,
        message: str,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool=tool,
            status="error",
            duration_ms=0.0,
            error=message,
        )

    @classmethod
    def _safe_call(
        cls,
        *,
        expected_tool: ToolFamily,
        call: (
            Callable[
                [],
                ToolExecutionResult,
            ]
            | None
        ),
    ) -> ToolExecutionResult:
        if call is None:
            return cls._error_result(
                expected_tool,
                (f"{expected_tool} executor is not configured"),
            )

        try:
            raw = call()
        except Exception as exc:
            return cls._error_result(
                expected_tool,
                (f"orchestration isolated {expected_tool} executor failure: {type(exc).__name__}"),
            )

        if not isinstance(
            raw,
            ToolExecutionResult,
        ):
            return cls._error_result(
                expected_tool,
                (f"orchestration received non-ToolExecutionResult from {expected_tool}"),
            )

        try:
            payload = raw.payload

            if payload is not None and hasattr(
                payload,
                "model_dump",
            ):
                payload = payload.model_dump(mode="python")

            validated = ToolExecutionResult.model_validate(
                {
                    "tool": raw.tool,
                    "status": raw.status,
                    "payload": payload,
                    "duration_ms": raw.duration_ms,
                    "error": raw.error,
                }
            )
        except Exception as exc:
            return cls._error_result(
                expected_tool,
                (f"orchestration rejected malformed {expected_tool} result: {type(exc).__name__}"),
            )

        if validated.tool != expected_tool:
            return cls._error_result(
                expected_tool,
                (
                    "orchestration received "
                    f"result for "
                    f"{validated.tool!r}; "
                    f"expected "
                    f"{expected_tool!r}"
                ),
            )

        return validated

    @staticmethod
    def _validate_node(
        state: RuntimeState,
    ) -> dict[
        str,
        object,
    ]:
        plan = BoundedOrchestrationPlan.model_validate(state["plan"].model_dump(mode="python"))

        OrchestrationStateSnapshot(
            plan=plan,
            status="pending",
        )

        return {
            "plan": plan,
            "results": (),
            "handoffs": (),
            "status": "running",
            "effective_sql_query": None,
            "handoff_failed": False,
        }

    def _execute_retrieval_node(
        self,
        state: RuntimeState,
    ) -> dict[
        str,
        object,
    ]:
        query = state["plan"].execution_plan.retrieval

        if query is None:
            return {}

        executor = self._retrieval_executor

        call: (
            Callable[
                [],
                ToolExecutionResult,
            ]
            | None
        )

        call = (
            None
            if executor is None
            else partial(
                executor.execute,
                query,
            )
        )

        result = self._safe_call(
            expected_tool="retrieval",
            call=call,
        )

        return {
            "results": _append_result(
                state,
                result,
            )
        }

    def _execute_sql_node(
        self,
        state: RuntimeState,
    ) -> dict[
        str,
        object,
    ]:
        plan = state["plan"]

        if plan.execution_plan.sql is None:
            return {}

        if plan.mode() == "dependent":
            query = state.get("effective_sql_query")

            if query is None:
                result = self._error_result(
                    "sql",
                    ("dependent SQL execution requires a materialized handoff"),
                )

                return {
                    "results": _append_result(
                        state,
                        result,
                    ),
                    "handoff_failed": True,
                }
        else:
            query = plan.execution_plan.sql

        executor = self._sql_executor

        call: (
            Callable[
                [],
                ToolExecutionResult,
            ]
            | None
        )

        call = (
            None
            if executor is None
            else partial(
                executor.execute,
                cast(
                    StructuredQuery,
                    query,
                ),
            )
        )

        result = self._safe_call(
            expected_tool="sql",
            call=call,
        )

        return {
            "results": _append_result(
                state,
                result,
            )
        }

    def _execute_graph_node(
        self,
        state: RuntimeState,
    ) -> dict[
        str,
        object,
    ]:
        query = state["plan"].execution_plan.graph

        if query is None:
            return {}

        executor = self._graph_executor

        call: (
            Callable[
                [],
                ToolExecutionResult,
            ]
            | None
        )

        call = (
            None
            if executor is None
            else partial(
                executor.execute,
                query,
            )
        )

        result = self._safe_call(
            expected_tool="graph",
            call=call,
        )

        return {
            "results": _append_result(
                state,
                result,
            )
        }

    @staticmethod
    def _materialize_handoff_node(
        state: RuntimeState,
    ) -> dict[
        str,
        object,
    ]:
        graph_result = _result_for(
            state,
            "graph",
        )

        if (
            graph_result is None
            or graph_result.status != "ok"
            or not isinstance(
                graph_result.payload,
                GraphPayload,
            )
        ):
            return {
                "handoff_failed": True,
            }

        company_ids = graph_result.payload.matched_company_ids

        if not company_ids:
            return {
                "handoff_failed": True,
            }

        original = state["plan"].execution_plan.sql

        if original is None:
            return {
                "handoff_failed": True,
            }

        data = original.model_dump(mode="python")

        data["candidate_company_ids"] = company_ids

        try:
            downstream = StructuredQuery.model_validate(data)

            handoff = DependencyHandoff(
                company_ids=(company_ids),
                downstream_query=(downstream),
            )
        except Exception:
            return {
                "handoff_failed": True,
            }

        return {
            "handoffs": (handoff,),
            "effective_sql_query": downstream,
            "handoff_failed": False,
        }

    @staticmethod
    def _route_after_retrieval(
        state: RuntimeState,
    ) -> Literal[
        "graph",
        "sql",
    ]:
        if state["plan"].mode() == "dependent":
            return "graph"

        return "sql"

    @staticmethod
    def _route_after_graph(
        state: RuntimeState,
    ) -> Literal[
        "handoff",
        "finalize",
    ]:
        if state["plan"].mode() != "dependent":
            return "finalize"

        graph_result = _result_for(
            state,
            "graph",
        )

        if graph_result is None or graph_result.status != "ok":
            return "finalize"

        return "handoff"

    @staticmethod
    def _route_after_handoff(
        state: RuntimeState,
    ) -> Literal[
        "sql",
        "finalize",
    ]:
        if state.get(
            "handoff_failed",
            False,
        ):
            return "finalize"

        return "sql"

    @staticmethod
    def _route_after_sql(
        state: RuntimeState,
    ) -> Literal[
        "graph",
        "finalize",
    ]:
        if state["plan"].mode() == "dependent":
            return "finalize"

        return "graph"

    @staticmethod
    def _finalize_node(
        state: RuntimeState,
    ) -> dict[
        str,
        object,
    ]:
        plan = state["plan"]

        results = state.get(
            "results",
            (),
        )

        handoffs = state.get(
            "handoffs",
            (),
        )

        result_tools = {result.tool for result in results}

        planned_tools = set(plan.execution_plan.required_tools())

        has_error = any(result.status == "error" for result in results)

        status: OrchestrationStatus

        if has_error:
            status = "failed"

        elif plan.mode() == "dependent":
            graph_result = _result_for(
                state,
                "graph",
            )

            if graph_result is None:
                status = "failed"

            elif graph_result.status == "empty":
                status = "blocked"

            elif (
                state.get(
                    "handoff_failed",
                    False,
                )
                or not handoffs
                or result_tools != planned_tools
            ):
                status = "failed"

            else:
                status = "completed"

        elif result_tools != planned_tools:
            status = "failed"

        else:
            status = "completed"

        snapshot = OrchestrationStateSnapshot(
            plan=plan,
            results=results,
            handoffs=handoffs,
            status=status,
        )

        return {
            "status": snapshot.status,
        }

    def _build_graph(
        self,
    ):
        builder = StateGraph(RuntimeState)

        builder.add_node(
            "validate",
            self._validate_node,
        )

        builder.add_node(
            "execute_retrieval",
            self._execute_retrieval_node,
        )

        builder.add_node(
            "execute_sql",
            self._execute_sql_node,
        )

        builder.add_node(
            "execute_graph",
            self._execute_graph_node,
        )

        builder.add_node(
            "materialize_handoff",
            self._materialize_handoff_node,
        )

        builder.add_node(
            "finalize",
            self._finalize_node,
        )

        builder.add_edge(
            START,
            "validate",
        )

        builder.add_edge(
            "validate",
            "execute_retrieval",
        )

        builder.add_conditional_edges(
            "execute_retrieval",
            self._route_after_retrieval,
            {
                "graph": "execute_graph",
                "sql": "execute_sql",
            },
        )

        builder.add_conditional_edges(
            "execute_graph",
            self._route_after_graph,
            {
                "handoff": "materialize_handoff",
                "finalize": "finalize",
            },
        )

        builder.add_conditional_edges(
            "materialize_handoff",
            self._route_after_handoff,
            {
                "sql": "execute_sql",
                "finalize": "finalize",
            },
        )

        builder.add_conditional_edges(
            "execute_sql",
            self._route_after_sql,
            {
                "graph": "execute_graph",
                "finalize": "finalize",
            },
        )

        builder.add_edge(
            "finalize",
            END,
        )

        return builder.compile(name=("bounded-enterprise-orchestration-v1"))

    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot:
        validated_plan = BoundedOrchestrationPlan.model_validate(plan.model_dump(mode="python"))

        output = cast(
            RuntimeState,
            self._graph.invoke(
                {
                    "plan": validated_plan,
                    "results": (),
                    "handoffs": (),
                    "status": "pending",
                    "effective_sql_query": None,
                    "handoff_failed": False,
                }
            ),
        )

        return OrchestrationStateSnapshot(
            plan=output["plan"],
            results=output.get(
                "results",
                (),
            ),
            handoffs=output.get(
                "handoffs",
                (),
            ),
            status=output["status"],
        )
