from __future__ import annotations

from typing import cast

from sqlalchemy import Engine

from enterprise_genai.application import (
    request_runtime,
)
from enterprise_genai.application.request_runtime import (
    REQUEST_SCOPED_RUNTIME_VERSION,
    RequestScopedExecutionRuntime,
)
from enterprise_genai.execution.contracts import (
    RetrievalPayload,
    RetrievalQuery,
    StructuredQuery,
    ToolExecutionPlan,
    ToolExecutionResult,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
)


class EmptyRetrievalExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        self.calls += 1

        return ToolExecutionResult(
            tool="retrieval",
            status="empty",
            payload=RetrievalPayload(hits=()),
            duration_ms=0.0,
        )


def _retrieval_plan() -> BoundedOrchestrationPlan:
    question = "Unknown retrieval question?"

    return BoundedOrchestrationPlan(
        question=question,
        execution_plan=(
            ToolExecutionPlan(
                route_label="retrieval",
                retrieval=RetrievalQuery(
                    question=question,
                ),
            )
        ),
    )


def _sql_plan() -> BoundedOrchestrationPlan:
    question = "What was total portfolio revenue in 2026 Q2?"

    return BoundedOrchestrationPlan(
        question=question,
        execution_plan=(
            ToolExecutionPlan(
                route_label="sql",
                sql=StructuredQuery(
                    period="2026Q2",
                    operation=("portfolio_metric_sum"),
                    metric="revenue_usd",
                ),
            )
        ),
    )


def test_request_scoped_runtime_version_is_frozen() -> None:
    assert REQUEST_SCOPED_RUNTIME_VERSION == "northstar-request-scoped-execution-runtime-v1"


def test_retrieval_only_execution_does_not_open_database_session(
    monkeypatch,
) -> None:
    retrieval = EmptyRetrievalExecutor()

    def forbidden_session(*args, **kwargs):
        raise AssertionError("retrieval-only execution must not open a database session")

    monkeypatch.setattr(
        request_runtime,
        "Session",
        forbidden_session,
    )

    runtime = RequestScopedExecutionRuntime(
        engine=cast(
            Engine,
            object(),
        ),
        retrieval_executor=retrieval,
    )

    snapshot = runtime.execute(_retrieval_plan())

    assert snapshot.status == "completed"

    assert tuple(result.tool for result in snapshot.results) == ("retrieval",)

    assert retrieval.calls == 1


def test_sql_execution_uses_fresh_scoped_session(
    monkeypatch,
) -> None:
    engine = cast(
        Engine,
        object(),
    )

    sessions = []
    exits = []

    class FakeSessionContext:
        def __init__(
            self,
            session_id: int,
        ) -> None:
            self.session_id = session_id

        def __enter__(self):
            sessions.append(self)

            return self

        def __exit__(
            self,
            exc_type,
            exc,
            traceback,
        ):
            exits.append(self.session_id)

            return False

    def fake_session(
        observed_engine,
    ):
        assert observed_engine is engine

        return FakeSessionContext(len(sessions) + 1)

    sql_sessions = []

    class FakeSqlExecutor:
        def __init__(
            self,
            session,
        ) -> None:
            sql_sessions.append(session)

    class FakeGraphExecutor:
        def __init__(
            self,
            session,
        ) -> None:
            raise AssertionError("SQL-only plan must not construct graph executor")

    runtime_inputs = []

    class FakeRuntime:
        def __init__(
            self,
            *,
            retrieval_executor=None,
            sql_executor=None,
            graph_executor=None,
        ) -> None:
            runtime_inputs.append(
                (
                    retrieval_executor,
                    sql_executor,
                    graph_executor,
                )
            )

        def execute(
            self,
            plan,
        ):
            return plan

    monkeypatch.setattr(
        request_runtime,
        "Session",
        fake_session,
    )

    monkeypatch.setattr(
        request_runtime,
        "StructuredSqlExecutor",
        FakeSqlExecutor,
    )

    monkeypatch.setattr(
        request_runtime,
        "RelationalGraphExecutor",
        FakeGraphExecutor,
    )

    monkeypatch.setattr(
        request_runtime,
        "BoundedLangGraphRuntime",
        FakeRuntime,
    )

    runtime = RequestScopedExecutionRuntime(
        engine=engine,
    )

    plan = _sql_plan()

    first = runtime.execute(plan)

    second = runtime.execute(plan)

    assert first is plan
    assert second is plan

    assert len(sessions) == 2

    assert sessions[0] is not sessions[1]

    assert sql_sessions == sessions

    assert exits == [
        1,
        2,
    ]

    assert len(runtime_inputs) == 2

    for (
        retrieval_executor,
        sql_executor,
        graph_executor,
    ) in runtime_inputs:
        assert retrieval_executor is None

        assert sql_executor is not None

        assert graph_executor is None
