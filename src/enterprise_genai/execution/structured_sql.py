from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from time import perf_counter

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from enterprise_genai.db.models import (
    CanonicalFactRow,
    FinancialMetricRow,
)
from enterprise_genai.execution.contracts import (
    DatabaseRowReference,
    StructuredMetric,
    StructuredPayload,
    StructuredQuery,
    ToolExecutionResult,
)


class StructuredDataIntegrityError(RuntimeError):
    """Persisted structured truth violates its provenance contract."""


_METRIC_UNITS: dict[
    StructuredMetric,
    str,
] = {
    "revenue_usd": "USD",
    "ebitda_usd": "USD",
    "gross_margin_pct": "percent",
    "net_retention_pct": "percent",
    "customer_count": "count",
    "employee_count": "count",
}


def build_financial_metric_statement(
    query: StructuredQuery,
    period: str,
) -> Select[tuple[FinancialMetricRow]]:
    """Build a parameterized lookup for one persisted financial row."""

    return select(FinancialMetricRow).where(
        FinancialMetricRow.dataset_version == query.dataset_version,
        FinancialMetricRow.company_id == query.company_id,
        FinancialMetricRow.period == period,
    )


def financial_fact_id(
    *,
    company_id: str,
    period: str,
) -> str:
    """Return the canonical fact identity for one financial row."""

    return f"FIN-{company_id}-{period}"


def _metric_value(
    row: FinancialMetricRow,
    metric: StructuredMetric,
) -> int | Decimal | None:
    value = getattr(
        row,
        metric,
    )

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ) or not isinstance(
        value,
        (
            int,
            Decimal,
        ),
    ):
        raise StructuredDataIntegrityError(
            f"Financial metric has an unexpected persisted type: {metric!r}."
        )

    return value


def _decimal(
    value: int | Decimal,
) -> Decimal:
    if isinstance(
        value,
        Decimal,
    ):
        return value

    return Decimal(value)


def _difference(
    current: int | Decimal,
    previous: int | Decimal,
) -> int | Decimal:
    if isinstance(current, int) and isinstance(previous, int):
        return current - previous

    return _decimal(current) - _decimal(previous)


def _difference_unit(
    metric: StructuredMetric,
) -> str:
    unit = _METRIC_UNITS[metric]

    if unit == "percent":
        return "percentage_points"

    return unit


def _ratio_unit(
    numerator_metric: StructuredMetric,
    denominator_metric: StructuredMetric,
) -> str:
    numerator_unit = _METRIC_UNITS[numerator_metric]

    denominator_unit = _METRIC_UNITS[denominator_metric]

    if numerator_unit == denominator_unit:
        return "ratio"

    return f"{numerator_unit}/{denominator_unit}"


def _compare(
    comparator: str,
    left: Decimal,
    right: Decimal,
) -> bool:
    if comparator == "lt":
        return left < right

    if comparator == "lte":
        return left <= right

    if comparator == "gt":
        return left > right

    if comparator == "gte":
        return left >= right

    if comparator == "eq":
        return left == right

    raise StructuredDataIntegrityError("Unexpected threshold comparator.")


class StructuredSqlExecutor:
    """Execute bounded structured requests against canonical PostgreSQL truth."""

    def __init__(
        self,
        session: Session,
        *,
        clock: Callable[
            [],
            float,
        ] = perf_counter,
    ) -> None:
        self._session = session
        self._clock = clock

    def _duration_ms(
        self,
        started_at: float,
    ) -> float:
        return max(
            0.0,
            (self._clock() - started_at) * 1000.0,
        )

    def _load_row(
        self,
        query: StructuredQuery,
        period: str,
    ) -> FinancialMetricRow | None:
        statement = build_financial_metric_statement(
            query,
            period,
        )

        return self._session.execute(statement).scalar_one_or_none()

    def _source_reference(
        self,
        row: FinancialMetricRow,
    ) -> DatabaseRowReference:
        fact_id = financial_fact_id(
            company_id=row.company_id,
            period=row.period,
        )

        fact = self._session.get(
            CanonicalFactRow,
            (
                row.dataset_version,
                fact_id,
            ),
        )

        if fact is None:
            raise StructuredDataIntegrityError(
                f"Financial row is missing its canonical fact registry entry: {fact_id}."
            )

        if fact.fact_type != "financial_metric":
            raise StructuredDataIntegrityError(
                f"Financial canonical fact has unexpected fact_type: {fact_id}."
            )

        return DatabaseRowReference(
            table="financial_metrics",
            primary_key={
                "dataset_version": (row.dataset_version),
                "company_id": (row.company_id),
                "period": row.period,
            },
            canonical_fact_ids=(fact_id,),
        )

    def _metric_value_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        row = self._load_row(
            query,
            query.period,
        )

        unit = _METRIC_UNITS[query.metric]

        if row is None:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit=unit,
                    empty_reason=("row_not_found"),
                    source_rows=(),
                ),
            )

        source = self._source_reference(row)

        value = _metric_value(
            row,
            query.metric,
        )

        if value is None:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit=unit,
                    empty_reason=("metric_is_null"),
                    source_rows=(source,),
                ),
            )

        return (
            "ok",
            StructuredPayload(
                operation=(query.operation),
                value=value,
                unit=unit,
                source_rows=(source,),
            ),
        )

    def _metric_difference_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        comparison_period = query.comparison_period

        if comparison_period is None:
            raise StructuredDataIntegrityError(
                "Validated metric_difference lost comparison_period."
            )

        current = self._load_row(
            query,
            query.period,
        )

        comparison = self._load_row(
            query,
            comparison_period,
        )

        unit = _difference_unit(query.metric)

        existing_rows = tuple(
            row
            for row in (
                current,
                comparison,
            )
            if row is not None
        )

        sources = tuple(self._source_reference(row) for row in existing_rows)

        if current is None or comparison is None:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit=unit,
                    empty_reason=("row_not_found"),
                    source_rows=sources,
                ),
            )

        current_value = _metric_value(
            current,
            query.metric,
        )

        comparison_value = _metric_value(
            comparison,
            query.metric,
        )

        if current_value is None or comparison_value is None:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit=unit,
                    empty_reason=("metric_is_null"),
                    source_rows=sources,
                ),
            )

        return (
            "ok",
            StructuredPayload(
                operation=(query.operation),
                value=_difference(
                    current_value,
                    comparison_value,
                ),
                unit=unit,
                source_rows=sources,
            ),
        )

    def _metric_ratio_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        denominator_metric = query.denominator_metric

        if denominator_metric is None:
            raise StructuredDataIntegrityError("Validated metric_ratio lost denominator_metric.")

        row = self._load_row(
            query,
            query.period,
        )

        unit = _ratio_unit(
            query.metric,
            denominator_metric,
        )

        if row is None:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit=unit,
                    empty_reason=("row_not_found"),
                    source_rows=(),
                ),
            )

        source = self._source_reference(row)

        numerator = _metric_value(
            row,
            query.metric,
        )

        denominator = _metric_value(
            row,
            denominator_metric,
        )

        if numerator is None or denominator is None:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit=unit,
                    empty_reason=("metric_is_null"),
                    source_rows=(source,),
                ),
            )

        denominator_decimal = _decimal(denominator)

        if denominator_decimal == 0:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit=unit,
                    empty_reason=("zero_denominator"),
                    source_rows=(source,),
                ),
            )

        value = _decimal(numerator) / denominator_decimal

        return (
            "ok",
            StructuredPayload(
                operation=(query.operation),
                value=value,
                unit=unit,
                source_rows=(source,),
            ),
        )

    def _metric_threshold_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        comparator = query.comparator
        threshold = query.threshold

        if comparator is None or threshold is None:
            raise StructuredDataIntegrityError(
                "Validated metric_threshold lost comparator or threshold."
            )

        row = self._load_row(
            query,
            query.period,
        )

        if row is None:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit="boolean",
                    empty_reason=("row_not_found"),
                    source_rows=(),
                ),
            )

        source = self._source_reference(row)

        metric_value = _metric_value(
            row,
            query.metric,
        )

        if metric_value is None:
            return (
                "empty",
                StructuredPayload(
                    operation=(query.operation),
                    value=None,
                    unit="boolean",
                    empty_reason=("metric_is_null"),
                    source_rows=(source,),
                ),
            )

        result = _compare(
            comparator,
            _decimal(metric_value),
            threshold,
        )

        return (
            "ok",
            StructuredPayload(
                operation=(query.operation),
                value=result,
                unit="boolean",
                source_rows=(source,),
            ),
        )

    def _execute_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        if query.operation == "metric_value":
            return self._metric_value_payload(query)

        if query.operation == "metric_difference":
            return self._metric_difference_payload(query)

        if query.operation == "metric_ratio":
            return self._metric_ratio_payload(query)

        if query.operation == "metric_threshold":
            return self._metric_threshold_payload(query)

        raise StructuredDataIntegrityError("Unexpected structured operation.")

    def execute(
        self,
        query: StructuredQuery,
    ) -> ToolExecutionResult:
        """Execute one validated structured request."""

        started_at = self._clock()

        try:
            (
                status,
                payload,
            ) = self._execute_payload(query)

        except StructuredDataIntegrityError as exc:
            return ToolExecutionResult(
                tool="sql",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=(f"structured data integrity failure: {exc}"),
            )

        except SQLAlchemyError as exc:
            return ToolExecutionResult(
                tool="sql",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=(f"structured SQL execution failed: {type(exc).__name__}"),
            )

        return ToolExecutionResult(
            tool="sql",
            status=status,
            payload=payload,
            duration_ms=(self._duration_ms(started_at)),
        )
