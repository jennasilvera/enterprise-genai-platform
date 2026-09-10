from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from enterprise_genai.db.models import (
    CanonicalFactRow,
    FinancialMetricRow,
)
from enterprise_genai.execution.contracts import (
    StructuredPayload,
    StructuredQuery,
)
from enterprise_genai.execution.structured_sql import (
    StructuredSqlExecutor,
)


class _ScalarResult:
    def __init__(
        self,
        row: FinancialMetricRow | None,
    ) -> None:
        self._row = row

    def scalar_one_or_none(
        self,
    ) -> FinancialMetricRow | None:
        return self._row


class _FakeSession:
    def __init__(
        self,
        rows: list[FinancialMetricRow | None],
        *,
        facts: dict[
            tuple[str, str],
            CanonicalFactRow,
        ]
        | None = None,
        execute_error: (SQLAlchemyError | None) = None,
    ) -> None:
        self.rows = list(rows)
        self.facts = facts or {}
        self.execute_error = execute_error
        self.statements: list[object] = []

    def execute(
        self,
        statement: object,
    ) -> _ScalarResult:
        self.statements.append(statement)

        if self.execute_error is not None:
            raise self.execute_error

        if not self.rows:
            return _ScalarResult(None)

        return _ScalarResult(self.rows.pop(0))

    def get(
        self,
        model: type[CanonicalFactRow],
        identity: tuple[str, str],
    ) -> CanonicalFactRow | None:
        assert model is CanonicalFactRow

        return self.facts.get(identity)


class _Clock:
    def __init__(
        self,
    ) -> None:
        self._values: Iterator[float] = iter(
            (
                10.0,
                10.001,
            )
        )

    def __call__(
        self,
    ) -> float:
        return next(self._values)


def _row(
    *,
    company_id: str = "PC-004",
    period: str = "2026Q2",
    revenue_usd: int = 92_000_000,
    ebitda_usd: int = 23_000_000,
    gross_margin_pct: Decimal = Decimal("42.000"),
    net_retention_pct: (Decimal | None) = Decimal("105.000"),
    customer_count: int | None = 100,
    employee_count: int | None = 500,
) -> FinancialMetricRow:
    return FinancialMetricRow(
        dataset_version="northstar-v1",
        company_id=company_id,
        period=period,
        revenue_usd=revenue_usd,
        ebitda_usd=ebitda_usd,
        gross_margin_pct=(gross_margin_pct),
        net_retention_pct=(net_retention_pct),
        customer_count=customer_count,
        employee_count=employee_count,
    )


def _fact(
    row: FinancialMetricRow,
) -> CanonicalFactRow:
    return CanonicalFactRow(
        dataset_version=(row.dataset_version),
        fact_id=(f"FIN-{row.company_id}-{row.period}"),
        fact_type="financial_metric",
    )


def _session(
    *rows: FinancialMetricRow | None,
) -> _FakeSession:
    facts = {
        (
            row.dataset_version,
            (f"FIN-{row.company_id}-{row.period}"),
        ): _fact(row)
        for row in rows
        if row is not None
    }

    return _FakeSession(
        list(rows),
        facts=facts,
    )


def _executor(
    session: _FakeSession,
) -> StructuredSqlExecutor:
    return StructuredSqlExecutor(
        session,  # type: ignore[arg-type]
        clock=_Clock(),
    )


def test_metric_value_returns_exact_row_provenance() -> None:
    row = _row()
    result = _executor(_session(row)).execute(
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation="metric_value",
            metric="revenue_usd",
        )
    )

    assert result.status == "ok"
    assert result.duration_ms == pytest.approx(1.0)

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert result.payload.value == 92_000_000
    assert result.payload.unit == "USD"
    assert result.payload.empty_reason is None

    assert len(result.payload.source_rows) == 1

    source = result.payload.source_rows[0]

    assert source.table == ("financial_metrics")

    assert source.primary_key == {
        "dataset_version": ("northstar-v1"),
        "company_id": "PC-004",
        "period": "2026Q2",
    }

    assert source.canonical_fact_ids == ("FIN-PC-004-2026Q2",)


def test_metric_difference_uses_both_source_rows() -> None:
    current = _row(
        period="2026Q2",
        revenue_usd=92_000_000,
    )

    previous = _row(
        period="2025Q2",
        revenue_usd=68_000_000,
    )

    result = _executor(
        _session(
            current,
            previous,
        )
    ).execute(
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation=("metric_difference"),
            metric="revenue_usd",
            comparison_period=("2025Q2"),
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert result.payload.value == 24_000_000

    assert result.payload.unit == "USD"

    assert [row.canonical_fact_ids[0] for row in (result.payload.source_rows)] == [
        "FIN-PC-004-2026Q2",
        "FIN-PC-004-2025Q2",
    ]


def test_metric_ratio_and_zero_denominator_are_distinct() -> None:
    row = _row(
        revenue_usd=92_000_000,
        ebitda_usd=23_000_000,
    )

    result = _executor(_session(row)).execute(
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation="metric_ratio",
            metric="ebitda_usd",
            denominator_metric=("revenue_usd"),
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert result.payload.value == Decimal("0.25")

    assert result.payload.unit == "ratio"

    zero_row = _row(
        revenue_usd=0,
        ebitda_usd=1,
    )

    zero = _executor(_session(zero_row)).execute(
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation="metric_ratio",
            metric="ebitda_usd",
            denominator_metric=("revenue_usd"),
        )
    )

    assert zero.status == "empty"

    assert isinstance(
        zero.payload,
        StructuredPayload,
    )

    assert zero.payload.value is None
    assert zero.payload.empty_reason == "zero_denominator"

    assert len(zero.payload.source_rows) == 1


def test_metric_threshold_returns_boolean() -> None:
    row = _row(
        company_id="PC-005",
        net_retention_pct=Decimal("97.000"),
    )

    result = _executor(_session(row)).execute(
        StructuredQuery(
            company_id="PC-005",
            period="2026Q2",
            operation=("metric_threshold"),
            metric=("net_retention_pct"),
            comparator="lt",
            threshold=Decimal("100"),
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert result.payload.value is True

    assert result.payload.unit == "boolean"


def test_missing_row_and_null_metric_have_different_empty_reasons() -> None:
    missing = _executor(_session(None)).execute(
        StructuredQuery(
            company_id="PC-999",
            period="2026Q2",
            operation="metric_value",
            metric="revenue_usd",
        )
    )

    assert missing.status == ("empty")

    assert isinstance(
        missing.payload,
        StructuredPayload,
    )

    assert missing.payload.empty_reason == "row_not_found"

    assert missing.payload.source_rows == ()

    row = _row(net_retention_pct=None)

    null_metric = _executor(_session(row)).execute(
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation="metric_value",
            metric=("net_retention_pct"),
        )
    )

    assert null_metric.status == "empty"

    assert isinstance(
        null_metric.payload,
        StructuredPayload,
    )

    assert null_metric.payload.empty_reason == "metric_is_null"

    assert len(null_metric.payload.source_rows) == 1


def test_database_failure_returns_error_result() -> None:
    session = _FakeSession(
        [],
        execute_error=(SQLAlchemyError("simulated")),
    )

    result = _executor(session).execute(
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation="metric_value",
            metric="revenue_usd",
        )
    )

    assert result.status == ("error")
    assert result.payload is None
    assert result.error is not None
    assert "SQLAlchemyError" in result.error


def test_missing_canonical_fact_is_integrity_error() -> None:
    row = _row()

    session = _FakeSession(
        [row],
        facts={},
    )

    result = _executor(session).execute(
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation="metric_value",
            metric="revenue_usd",
        )
    )

    assert result.status == ("error")

    assert result.payload is None
    assert result.error is not None

    assert "canonical fact registry" in result.error


def test_sqlalchemy_statement_uses_bound_parameters() -> None:
    injected = "PC-004' OR 1=1 --"

    session = _session(None)

    result = _executor(session).execute(
        StructuredQuery(
            company_id=injected,
            period="2026Q2",
            operation="metric_value",
            metric="revenue_usd",
        )
    )

    assert result.status == ("empty")

    statement = session.statements[0]

    compiled = statement.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={
            "literal_binds": False,
        },
    )

    sql = str(compiled)

    assert injected not in sql

    assert injected in (compiled.params.values())
