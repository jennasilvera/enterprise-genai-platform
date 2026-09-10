from decimal import Decimal

import pytest

from enterprise_genai.execution.contracts import (
    StructuredEntity,
    StructuredPayload,
    StructuredQuery,
)


def test_existing_operation_still_requires_company_id() -> None:
    with pytest.raises(
        ValueError,
        match="require company_id",
    ):
        StructuredQuery(
            period="2026Q2",
            operation="metric_value",
            metric="revenue_usd",
        )

    query = StructuredQuery(
        company_id="PC-004",
        period="2026Q2",
        operation="metric_value",
        metric="revenue_usd",
    )

    assert query.company_id == "PC-004"


def test_portfolio_sum_uses_full_or_bounded_candidate_set() -> None:
    full = StructuredQuery(
        period="2026Q2",
        operation="portfolio_metric_sum",
        metric="revenue_usd",
    )

    assert full.candidate_company_ids == ()

    bounded = StructuredQuery(
        period="2026Q2",
        operation="portfolio_metric_sum",
        metric="revenue_usd",
        candidate_company_ids=(
            "PC-002",
            "PC-008",
        ),
    )

    assert bounded.candidate_company_ids == (
        "PC-002",
        "PC-008",
    )


def test_portfolio_operations_reject_single_company_id() -> None:
    with pytest.raises(
        ValueError,
        match="do not accept company_id",
    ):
        StructuredQuery(
            company_id="PC-004",
            period="2026Q2",
            operation="portfolio_metric_rank",
            metric="revenue_usd",
            rank_order="highest",
            result_limit=1,
        )


def test_portfolio_filter_requires_threshold_contract() -> None:
    with pytest.raises(
        ValueError,
        match="requires comparator",
    ):
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_metric_filter"),
            metric=("net_retention_pct"),
        )

    query = StructuredQuery(
        period="2026Q2",
        operation=("portfolio_metric_filter"),
        metric="net_retention_pct",
        comparator="lt",
        threshold=Decimal("100"),
    )

    assert query.comparator == "lt"
    assert query.threshold == Decimal("100")


def test_portfolio_growth_rank_requires_explicit_period_and_order() -> None:
    query = StructuredQuery(
        period="2026Q2",
        operation="portfolio_growth_rank",
        metric="revenue_usd",
        comparison_period="2025Q2",
        rank_order="highest",
        result_limit=1,
    )

    assert query.comparison_period == "2025Q2"
    assert query.rank_order == "highest"
    assert query.result_limit == 1

    with pytest.raises(
        ValueError,
        match="distinct periods",
    ):
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_growth_rank"),
            metric="revenue_usd",
            comparison_period="2026Q2",
            rank_order="highest",
            result_limit=1,
        )


def test_portfolio_ratio_rank_requires_distinct_denominator() -> None:
    query = StructuredQuery(
        period="2026Q2",
        operation="portfolio_ratio_rank",
        metric="ebitda_usd",
        denominator_metric=("revenue_usd"),
        rank_order="highest",
        result_limit=1,
    )

    assert query.denominator_metric == "revenue_usd"

    with pytest.raises(
        ValueError,
        match="must differ",
    ):
        StructuredQuery(
            period="2026Q2",
            operation=("portfolio_ratio_rank"),
            metric="revenue_usd",
            denominator_metric=("revenue_usd"),
            rank_order="highest",
            result_limit=1,
        )


def test_candidate_company_ids_must_be_unique() -> None:
    with pytest.raises(
        ValueError,
        match="must not contain duplicates",
    ):
        StructuredQuery(
            period="2026Q2",
            operation="portfolio_metric_sum",
            metric="revenue_usd",
            candidate_company_ids=(
                "PC-002",
                "PC-002",
            ),
        )


def test_structured_payload_supports_entity_results_exclusively() -> None:
    entity = StructuredEntity(
        company_id="PC-004",
        name="HelioGrid Energy",
        score=Decimal("0.352941176470588235"),
    )

    payload = StructuredPayload(
        operation=("portfolio_growth_rank"),
        value=None,
        entities=(entity,),
        unit="ratio",
        source_rows=(),
    )

    assert payload.value is None
    assert payload.entities == (entity,)

    with pytest.raises(
        ValueError,
        match="both a scalar value",
    ):
        StructuredPayload(
            operation=("portfolio_growth_rank"),
            value=1,
            entities=(entity,),
            unit="ratio",
            source_rows=(),
        )
