from collections.abc import Iterator
from datetime import date
from decimal import Decimal

from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from enterprise_genai.db.models import (
    CanonicalFactRow,
    CompanyRow,
    FinancialMetricRow,
)
from enterprise_genai.execution.contracts import (
    StructuredPayload,
    StructuredQuery,
)
from enterprise_genai.execution.structured_sql import (
    StructuredSqlExecutor,
    build_portfolio_financial_statement,
)

VERSION = "northstar-v1"


class _FakeSession:
    def __init__(
        self,
        scalar_batches: list[list[object]],
        *,
        scalar_error: (SQLAlchemyError | None) = None,
    ) -> None:
        self.scalar_batches = list(scalar_batches)
        self.scalar_error = scalar_error
        self.statements: list[object] = []

        self.facts: dict[
            tuple[str, str],
            CanonicalFactRow,
        ] = {}

        for batch in scalar_batches:
            for row in batch:
                if isinstance(
                    row,
                    FinancialMetricRow,
                ):
                    fact_id = f"FIN-{row.company_id}-{row.period}"

                    self.facts[
                        (
                            row.dataset_version,
                            fact_id,
                        )
                    ] = CanonicalFactRow(
                        dataset_version=(row.dataset_version),
                        fact_id=fact_id,
                        fact_type=("financial_metric"),
                    )

    def scalars(
        self,
        statement: object,
    ) -> Iterator[object]:
        self.statements.append(statement)

        if self.scalar_error is not None:
            raise self.scalar_error

        if not self.scalar_batches:
            return iter(())

        return iter(self.scalar_batches.pop(0))

    def get(
        self,
        model: type[CanonicalFactRow],
        identity: tuple[
            str,
            str,
        ],
    ) -> CanonicalFactRow | None:
        assert model is CanonicalFactRow

        return self.facts.get(identity)


class _Clock:
    def __init__(
        self,
    ) -> None:
        self.values = iter(
            (
                1.0,
                1.002,
            )
        )

    def __call__(
        self,
    ) -> float:
        return next(self.values)


def _company(
    company_id: str,
    name: str,
) -> CompanyRow:
    return CompanyRow(
        dataset_version=VERSION,
        company_id=company_id,
        fund_id="FUND-001",
        name=name,
        industry="Test",
        headquarters_country="US",
        investment_date=date(
            2020,
            1,
            1,
        ),
        ownership_pct=Decimal("50.000"),
    )


def _row(
    company_id: str,
    *,
    period: str = "2026Q2",
    revenue_usd: int = 100,
    ebitda_usd: int = 20,
    net_retention_pct: (Decimal | None) = Decimal("105"),
) -> FinancialMetricRow:
    return FinancialMetricRow(
        dataset_version=VERSION,
        company_id=company_id,
        period=period,
        revenue_usd=revenue_usd,
        ebitda_usd=ebitda_usd,
        gross_margin_pct=Decimal("40.000"),
        net_retention_pct=(net_retention_pct),
        customer_count=10,
        employee_count=100,
    )


def _executor(
    *batches: list[object],
) -> StructuredSqlExecutor:
    session = _FakeSession(list(batches))

    return StructuredSqlExecutor(
        session,  # type: ignore[arg-type]
        clock=_Clock(),
    )


def test_portfolio_metric_sum_uses_all_rows_and_provenance() -> None:
    companies = [
        _company(
            "PC-001",
            "One",
        ),
        _company(
            "PC-002",
            "Two",
        ),
    ]

    rows = [
        _row(
            "PC-001",
            revenue_usd=100,
        ),
        _row(
            "PC-002",
            revenue_usd=200,
        ),
    ]

    result = _executor(
        companies,
        rows,
    ).execute(
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_metric_sum"),
            metric="revenue_usd",
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert result.payload.value == 300

    assert result.payload.unit == "USD"

    assert [source.canonical_fact_ids[0] for source in (result.payload.source_rows)] == [
        "FIN-PC-001-2026Q2",
        "FIN-PC-002-2026Q2",
    ]


def test_portfolio_filter_treats_null_as_non_comparable() -> None:
    companies = [
        _company(
            "PC-001",
            "One",
        ),
        _company(
            "PC-002",
            "Two",
        ),
        _company(
            "PC-003",
            "Three",
        ),
    ]

    rows = [
        _row(
            "PC-001",
            net_retention_pct=None,
        ),
        _row(
            "PC-002",
            net_retention_pct=(Decimal("97")),
        ),
        _row(
            "PC-003",
            net_retention_pct=(Decimal("105")),
        ),
    ]

    result = _executor(
        companies,
        rows,
    ).execute(
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_metric_filter"),
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

    assert [entity.company_id for entity in (result.payload.entities)] == ["PC-002"]

    entity = result.payload.entities[0]

    assert entity.score == Decimal("97")

    assert entity.canonical_fact_ids == ("FIN-PC-002-2026Q2",)

    assert len(result.payload.source_rows) == 3


def test_portfolio_filter_no_matches_is_distinct_empty_state() -> None:
    companies = [
        _company(
            "PC-001",
            "One",
        ),
        _company(
            "PC-002",
            "Two",
        ),
    ]

    rows = [
        _row(
            "PC-001",
            net_retention_pct=(Decimal("105")),
        ),
        _row(
            "PC-002",
            net_retention_pct=(Decimal("110")),
        ),
    ]

    result = _executor(
        companies,
        rows,
    ).execute(
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_metric_filter"),
            metric=("net_retention_pct"),
            comparator="lt",
            threshold=Decimal("100"),
        )
    )

    assert result.status == ("empty")

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert result.payload.empty_reason == "no_matches"


def test_portfolio_metric_rank_uses_company_id_tie_break() -> None:
    companies = [
        _company(
            "PC-001",
            "One",
        ),
        _company(
            "PC-002",
            "Two",
        ),
        _company(
            "PC-003",
            "Three",
        ),
    ]

    rows = [
        _row(
            "PC-001",
            revenue_usd=100,
        ),
        _row(
            "PC-002",
            revenue_usd=100,
        ),
        _row(
            "PC-003",
            revenue_usd=90,
        ),
    ]

    result = _executor(
        companies,
        rows,
    ).execute(
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_metric_rank"),
            metric="revenue_usd",
            rank_order="highest",
            result_limit=2,
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert [entity.company_id for entity in (result.payload.entities)] == [
        "PC-001",
        "PC-002",
    ]


def test_candidate_scope_supports_downstream_graph_composition() -> None:
    companies = [
        _company(
            "PC-002",
            "Alder",
        ),
        _company(
            "PC-008",
            "NovaBio",
        ),
    ]

    rows = [
        _row(
            "PC-002",
            revenue_usd=106,
        ),
        _row(
            "PC-008",
            revenue_usd=83,
        ),
    ]

    result = _executor(
        companies,
        rows,
    ).execute(
        StructuredQuery(
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
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert result.payload.entities[0].company_id == "PC-008"


def test_growth_rank_uses_relative_growth_not_absolute_change() -> None:
    companies = [
        _company(
            "PC-001",
            "One",
        ),
        _company(
            "PC-002",
            "Two",
        ),
    ]

    current = [
        _row(
            "PC-001",
            revenue_usd=130,
        ),
        _row(
            "PC-002",
            revenue_usd=20,
        ),
    ]

    previous = [
        _row(
            "PC-001",
            period="2025Q2",
            revenue_usd=100,
        ),
        _row(
            "PC-002",
            period="2025Q2",
            revenue_usd=10,
        ),
    ]

    result = _executor(
        companies,
        current,
        previous,
    ).execute(
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_growth_rank"),
            metric="revenue_usd",
            comparison_period=("2025Q2"),
            rank_order="highest",
            result_limit=1,
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    winner = result.payload.entities[0]

    assert winner.company_id == "PC-002"

    assert winner.score == Decimal("1")

    assert winner.canonical_fact_ids == (
        "FIN-PC-002-2026Q2",
        "FIN-PC-002-2025Q2",
    )

    assert len(result.payload.source_rows) == 4


def test_ratio_rank_computes_ratio_before_ranking() -> None:
    companies = [
        _company(
            "PC-001",
            "One",
        ),
        _company(
            "PC-002",
            "Two",
        ),
    ]

    rows = [
        _row(
            "PC-001",
            revenue_usd=100,
            ebitda_usd=20,
        ),
        _row(
            "PC-002",
            revenue_usd=100,
            ebitda_usd=30,
        ),
    ]

    result = _executor(
        companies,
        rows,
    ).execute(
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_ratio_rank"),
            metric="ebitda_usd",
            denominator_metric=("revenue_usd"),
            rank_order="highest",
            result_limit=1,
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    winner = result.payload.entities[0]

    assert winner.company_id == "PC-002"

    assert winner.score == Decimal("0.3")


def test_incomplete_portfolio_financial_coverage_is_error() -> None:
    companies = [
        _company(
            "PC-001",
            "One",
        ),
        _company(
            "PC-002",
            "Two",
        ),
    ]

    rows = [
        _row(
            "PC-001",
            revenue_usd=100,
        ),
    ]

    result = _executor(
        companies,
        rows,
    ).execute(
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_metric_sum"),
            metric="revenue_usd",
        )
    )

    assert result.status == ("error")

    assert result.error is not None

    assert "coverage is incomplete" in result.error


def test_growth_rank_zero_denominator_returns_typed_empty() -> None:
    companies = [
        _company(
            "PC-001",
            "One",
        ),
    ]

    current = [
        _row(
            "PC-001",
            revenue_usd=10,
        ),
    ]

    previous = [
        _row(
            "PC-001",
            period="2025Q2",
            revenue_usd=0,
        ),
    ]

    result = _executor(
        companies,
        current,
        previous,
    ).execute(
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_growth_rank"),
            metric="revenue_usd",
            comparison_period=("2025Q2"),
            rank_order="highest",
            result_limit=1,
        )
    )

    assert result.status == ("empty")

    assert isinstance(
        result.payload,
        StructuredPayload,
    )

    assert result.payload.empty_reason == "zero_denominator"


def test_portfolio_sql_uses_bound_candidate_parameters() -> None:
    injected = "PC-002' OR 1=1 --"

    query = StructuredQuery(
        period="2026Q2",
        operation=("portfolio_metric_rank"),
        metric="revenue_usd",
        candidate_company_ids=(injected,),
        rank_order="highest",
        result_limit=1,
    )

    statement = build_portfolio_financial_statement(
        query,
        period="2026Q2",
        company_ids=(injected,),
    )

    compiled = statement.compile(
        dialect=(postgresql.dialect()),
        compile_kwargs={
            "literal_binds": False,
        },
    )

    sql = str(compiled)

    assert injected not in sql

    def contains_injected(
        value: object,
    ) -> bool:
        if value == injected:
            return True

        if isinstance(
            value,
            (
                tuple,
                list,
                set,
            ),
        ):
            return injected in value

        return False

    assert any(contains_injected(value) for value in (compiled.params.values()))
