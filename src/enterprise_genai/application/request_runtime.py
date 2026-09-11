from __future__ import annotations

from typing import Protocol

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from enterprise_genai.execution.contracts import (
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.execution.relational_graph import (
    RelationalGraphExecutor,
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

REQUEST_SCOPED_RUNTIME_VERSION = "northstar-request-scoped-execution-runtime-v1"


class RetrievalExecutorProtocol(Protocol):
    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult: ...


class RequestScopedExecutionRuntime:
    """Execute one bounded plan with request-scoped database state.

    The persisted retrieval executor may be shared across requests.
    SQL and graph executors are constructed only inside a fresh
    SQLAlchemy Session for the current execution.
    """

    def __init__(
        self,
        *,
        engine: Engine,
        retrieval_executor: (RetrievalExecutorProtocol | None) = None,
    ) -> None:
        self._engine = engine
        self._retrieval_executor = retrieval_executor

    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot:
        tools = plan.execution_plan.required_tools()

        needs_database = "sql" in tools or "graph" in tools

        if not needs_database:
            runtime = BoundedLangGraphRuntime(
                retrieval_executor=(self._retrieval_executor),
            )

            return runtime.execute(plan)

        with Session(self._engine) as session:
            sql_executor = StructuredSqlExecutor(session) if "sql" in tools else None

            graph_executor = RelationalGraphExecutor(session) if "graph" in tools else None

            runtime = BoundedLangGraphRuntime(
                retrieval_executor=(self._retrieval_executor),
                sql_executor=(sql_executor),
                graph_executor=(graph_executor),
            )

            return runtime.execute(plan)
