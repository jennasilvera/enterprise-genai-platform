from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from time import perf_counter

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from enterprise_genai.db.models import (
    CanonicalFactRow,
    CompanyRow,
    FinancialMetricRow,
)
from enterprise_genai.execution.contracts import (
    DatabaseRowReference,
    StructuredEntity,
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


def build_portfolio_company_statement(
    query: StructuredQuery,
) -> Select[tuple[CompanyRow]]:
    """Build deterministic bounded company-scope SQL."""

    statement = select(CompanyRow).where(CompanyRow.dataset_version == query.dataset_version)

    if query.candidate_company_ids:
        statement = statement.where(CompanyRow.company_id.in_(query.candidate_company_ids))

    return statement.order_by(CompanyRow.company_id)


def build_portfolio_financial_statement(
    query: StructuredQuery,
    *,
    period: str,
    company_ids: tuple[str, ...],
) -> Select[tuple[FinancialMetricRow]]:
    """Build deterministic financial SQL for a resolved scope."""

    if not company_ids:
        raise ValueError("Portfolio financial scope must not be empty.")

    return (
        select(FinancialMetricRow)
        .where(
            FinancialMetricRow.dataset_version == query.dataset_version,
            FinancialMetricRow.period == period,
            FinancialMetricRow.company_id.in_(company_ids),
        )
        .order_by(FinancialMetricRow.company_id)
    )


def _ordered_scored_companies(
    scored: list[
        tuple[
            CompanyRow,
            int | Decimal,
            tuple[str, ...],
        ]
    ],
    *,
    rank_order: str,
) -> list[
    tuple[
        CompanyRow,
        int | Decimal,
        tuple[str, ...],
    ]
]:
    """Sort by score, then company ID for deterministic ties."""

    if rank_order == "highest":
        return sorted(
            scored,
            key=lambda item: (
                -_decimal(item[1]),
                item[0].company_id,
            ),
        )

    if rank_order == "lowest":
        return sorted(
            scored,
            key=lambda item: (
                _decimal(item[1]),
                item[0].company_id,
            ),
        )

    raise StructuredDataIntegrityError("Unexpected structured rank order.")


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

    def _load_portfolio_companies(
        self,
        query: StructuredQuery,
    ) -> tuple[
        CompanyRow,
        ...,
    ]:
        rows = tuple(self._session.scalars(build_portfolio_company_statement(query)))

        if query.candidate_company_ids:
            expected = set(query.candidate_company_ids)

            observed = {row.company_id for row in rows}

            missing = sorted(expected - observed)

            if missing:
                raise StructuredDataIntegrityError(
                    f"Portfolio candidate scope contains unknown company IDs: {missing}."
                )

        return rows

    def _load_portfolio_financial_rows(
        self,
        query: StructuredQuery,
        *,
        period: str,
        companies: tuple[
            CompanyRow,
            ...,
        ],
    ) -> tuple[
        FinancialMetricRow,
        ...,
    ]:
        company_ids = tuple(company.company_id for company in companies)

        if not company_ids:
            return ()

        rows = tuple(
            self._session.scalars(
                build_portfolio_financial_statement(
                    query,
                    period=period,
                    company_ids=company_ids,
                )
            )
        )

        observed_ids = [row.company_id for row in rows]

        if len(set(observed_ids)) != len(observed_ids):
            raise StructuredDataIntegrityError(
                "Portfolio financial scope contains duplicate company rows."
            )

        expected = set(company_ids)

        observed = set(observed_ids)

        missing = sorted(expected - observed)

        if missing:
            raise StructuredDataIntegrityError(
                f"Portfolio financial coverage is incomplete for {period}: {missing}."
            )

        return rows

    def _portfolio_sources(
        self,
        *row_groups: tuple[
            FinancialMetricRow,
            ...,
        ],
    ) -> tuple[
        DatabaseRowReference,
        ...,
    ]:
        return tuple(self._source_reference(row) for rows in row_groups for row in rows)

    @staticmethod
    def _structured_entity(
        *,
        company: CompanyRow,
        score: int | Decimal,
        fact_ids: tuple[str, ...],
    ) -> StructuredEntity:
        return StructuredEntity(
            company_id=(company.company_id),
            name=company.name,
            score=score,
            canonical_fact_ids=(fact_ids),
        )

    def _portfolio_metric_sum_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        companies = self._load_portfolio_companies(query)

        unit = _METRIC_UNITS[query.metric]

        if not companies:
            return (
                "empty",
                StructuredPayload(
                    operation=query.operation,
                    value=None,
                    unit=unit,
                    empty_reason=("row_not_found"),
                    source_rows=(),
                ),
            )

        rows = self._load_portfolio_financial_rows(
            query,
            period=query.period,
            companies=companies,
        )

        sources = self._portfolio_sources(rows)

        values = [
            _metric_value(
                row,
                query.metric,
            )
            for row in rows
        ]

        if any(value is None for value in values):
            return (
                "empty",
                StructuredPayload(
                    operation=query.operation,
                    value=None,
                    unit=unit,
                    empty_reason=("metric_is_null"),
                    source_rows=sources,
                ),
            )

        non_null = [value for value in values if value is not None]

        if all(
            isinstance(
                value,
                int,
            )
            for value in non_null
        ):
            total: int | Decimal = sum(non_null)
        else:
            total = sum(
                (_decimal(value) for value in non_null),
                Decimal(0),
            )

        return (
            "ok",
            StructuredPayload(
                operation=query.operation,
                value=total,
                unit=unit,
                source_rows=sources,
            ),
        )

    def _portfolio_metric_filter_payload(
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
                "Validated portfolio filter lost comparator or threshold."
            )

        companies = self._load_portfolio_companies(query)

        unit = _METRIC_UNITS[query.metric]

        if not companies:
            return (
                "empty",
                StructuredPayload(
                    operation=query.operation,
                    value=None,
                    unit=unit,
                    empty_reason=("row_not_found"),
                    source_rows=(),
                ),
            )

        rows = self._load_portfolio_financial_rows(
            query,
            period=query.period,
            companies=companies,
        )

        sources = self._portfolio_sources(rows)

        companies_by_id = {company.company_id: company for company in companies}

        entities: list[StructuredEntity] = []

        comparable = 0

        for row in rows:
            value = _metric_value(
                row,
                query.metric,
            )

            if value is None:
                continue

            comparable += 1

            if not _compare(
                comparator,
                _decimal(value),
                threshold,
            ):
                continue

            fact_id = financial_fact_id(
                company_id=(row.company_id),
                period=row.period,
            )

            entities.append(
                self._structured_entity(
                    company=(companies_by_id[row.company_id]),
                    score=value,
                    fact_ids=(fact_id,),
                )
            )

        entities.sort(key=lambda entity: entity.company_id)

        if not entities:
            empty_reason = "metric_is_null" if comparable == 0 else "no_matches"

            return (
                "empty",
                StructuredPayload(
                    operation=query.operation,
                    value=None,
                    unit=unit,
                    empty_reason=(empty_reason),
                    source_rows=sources,
                ),
            )

        return (
            "ok",
            StructuredPayload(
                operation=query.operation,
                value=None,
                entities=tuple(entities),
                unit=unit,
                source_rows=sources,
            ),
        )

    def _portfolio_metric_rank_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        rank_order = query.rank_order
        result_limit = query.result_limit

        if rank_order is None or result_limit is None:
            raise StructuredDataIntegrityError(
                "Validated portfolio metric rank lost ranking arguments."
            )

        companies = self._load_portfolio_companies(query)

        unit = _METRIC_UNITS[query.metric]

        if not companies:
            return (
                "empty",
                StructuredPayload(
                    operation=query.operation,
                    value=None,
                    unit=unit,
                    empty_reason=("row_not_found"),
                    source_rows=(),
                ),
            )

        rows = self._load_portfolio_financial_rows(
            query,
            period=query.period,
            companies=companies,
        )

        sources = self._portfolio_sources(rows)

        companies_by_id = {company.company_id: company for company in companies}

        scored: list[
            tuple[
                CompanyRow,
                int | Decimal,
                tuple[str, ...],
            ]
        ] = []

        for row in rows:
            value = _metric_value(
                row,
                query.metric,
            )

            if value is None:
                return (
                    "empty",
                    StructuredPayload(
                        operation=query.operation,
                        value=None,
                        unit=unit,
                        empty_reason=("metric_is_null"),
                        source_rows=sources,
                    ),
                )

            scored.append(
                (
                    companies_by_id[row.company_id],
                    value,
                    (
                        financial_fact_id(
                            company_id=(row.company_id),
                            period=row.period,
                        ),
                    ),
                )
            )

        ordered = _ordered_scored_companies(
            scored,
            rank_order=rank_order,
        )

        entities = tuple(
            self._structured_entity(
                company=company,
                score=score,
                fact_ids=fact_ids,
            )
            for (
                company,
                score,
                fact_ids,
            ) in ordered[:result_limit]
        )

        return (
            "ok",
            StructuredPayload(
                operation=query.operation,
                value=None,
                entities=entities,
                unit=unit,
                source_rows=sources,
            ),
        )

    def _portfolio_growth_rank_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        comparison_period = query.comparison_period

        rank_order = query.rank_order

        result_limit = query.result_limit

        if comparison_period is None or rank_order is None or result_limit is None:
            raise StructuredDataIntegrityError(
                "Validated portfolio growth rank lost required arguments."
            )

        companies = self._load_portfolio_companies(query)

        if not companies:
            return (
                "empty",
                StructuredPayload(
                    operation=query.operation,
                    value=None,
                    unit="ratio",
                    empty_reason=("row_not_found"),
                    source_rows=(),
                ),
            )

        current_rows = self._load_portfolio_financial_rows(
            query,
            period=query.period,
            companies=companies,
        )

        previous_rows = self._load_portfolio_financial_rows(
            query,
            period=comparison_period,
            companies=companies,
        )

        sources = self._portfolio_sources(
            current_rows,
            previous_rows,
        )

        current_by_id = {row.company_id: row for row in current_rows}

        previous_by_id = {row.company_id: row for row in previous_rows}

        scored: list[
            tuple[
                CompanyRow,
                int | Decimal,
                tuple[str, ...],
            ]
        ] = []

        for company in companies:
            current = current_by_id[company.company_id]

            previous = previous_by_id[company.company_id]

            current_value = _metric_value(
                current,
                query.metric,
            )

            previous_value = _metric_value(
                previous,
                query.metric,
            )

            if current_value is None or previous_value is None:
                return (
                    "empty",
                    StructuredPayload(
                        operation=query.operation,
                        value=None,
                        unit="ratio",
                        empty_reason=("metric_is_null"),
                        source_rows=sources,
                    ),
                )

            previous_decimal = _decimal(previous_value)

            if previous_decimal == 0:
                return (
                    "empty",
                    StructuredPayload(
                        operation=query.operation,
                        value=None,
                        unit="ratio",
                        empty_reason=("zero_denominator"),
                        source_rows=sources,
                    ),
                )

            growth = (_decimal(current_value) - previous_decimal) / previous_decimal

            scored.append(
                (
                    company,
                    growth,
                    (
                        financial_fact_id(
                            company_id=(company.company_id),
                            period=query.period,
                        ),
                        financial_fact_id(
                            company_id=(company.company_id),
                            period=(comparison_period),
                        ),
                    ),
                )
            )

        ordered = _ordered_scored_companies(
            scored,
            rank_order=rank_order,
        )

        entities = tuple(
            self._structured_entity(
                company=company,
                score=score,
                fact_ids=fact_ids,
            )
            for (
                company,
                score,
                fact_ids,
            ) in ordered[:result_limit]
        )

        return (
            "ok",
            StructuredPayload(
                operation=query.operation,
                value=None,
                entities=entities,
                unit="ratio",
                source_rows=sources,
            ),
        )

    def _portfolio_ratio_rank_payload(
        self,
        query: StructuredQuery,
    ) -> tuple[
        str,
        StructuredPayload,
    ]:
        denominator_metric = query.denominator_metric

        rank_order = query.rank_order

        result_limit = query.result_limit

        if denominator_metric is None or rank_order is None or result_limit is None:
            raise StructuredDataIntegrityError(
                "Validated portfolio ratio rank lost required arguments."
            )

        companies = self._load_portfolio_companies(query)

        unit = _ratio_unit(
            query.metric,
            denominator_metric,
        )

        if not companies:
            return (
                "empty",
                StructuredPayload(
                    operation=query.operation,
                    value=None,
                    unit=unit,
                    empty_reason=("row_not_found"),
                    source_rows=(),
                ),
            )

        rows = self._load_portfolio_financial_rows(
            query,
            period=query.period,
            companies=companies,
        )

        sources = self._portfolio_sources(rows)

        rows_by_id = {row.company_id: row for row in rows}

        scored: list[
            tuple[
                CompanyRow,
                int | Decimal,
                tuple[str, ...],
            ]
        ] = []

        for company in companies:
            row = rows_by_id[company.company_id]

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
                        operation=query.operation,
                        value=None,
                        unit=unit,
                        empty_reason=("metric_is_null"),
                        source_rows=sources,
                    ),
                )

            denominator_decimal = _decimal(denominator)

            if denominator_decimal == 0:
                return (
                    "empty",
                    StructuredPayload(
                        operation=query.operation,
                        value=None,
                        unit=unit,
                        empty_reason=("zero_denominator"),
                        source_rows=sources,
                    ),
                )

            ratio = _decimal(numerator) / denominator_decimal

            scored.append(
                (
                    company,
                    ratio,
                    (
                        financial_fact_id(
                            company_id=(company.company_id),
                            period=query.period,
                        ),
                    ),
                )
            )

        ordered = _ordered_scored_companies(
            scored,
            rank_order=rank_order,
        )

        entities = tuple(
            self._structured_entity(
                company=company,
                score=score,
                fact_ids=fact_ids,
            )
            for (
                company,
                score,
                fact_ids,
            ) in ordered[:result_limit]
        )

        return (
            "ok",
            StructuredPayload(
                operation=query.operation,
                value=None,
                entities=entities,
                unit=unit,
                source_rows=sources,
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

        if query.operation == "portfolio_metric_sum":
            return self._portfolio_metric_sum_payload(query)

        if query.operation == "portfolio_metric_filter":
            return self._portfolio_metric_filter_payload(query)

        if query.operation == "portfolio_metric_rank":
            return self._portfolio_metric_rank_payload(query)

        if query.operation == "portfolio_growth_rank":
            return self._portfolio_growth_rank_payload(query)

        if query.operation == "portfolio_ratio_rank":
            return self._portfolio_ratio_rank_payload(query)

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
