from collections import Counter

from enterprise_genai.data.metrics import PERIODS
from enterprise_genai.data.universe import build_universe


def test_every_company_has_eight_financial_quarters() -> None:
    universe = build_universe()

    observations = Counter(metric.company_id for metric in universe.financial_metrics)

    assert len(universe.financial_metrics) == 64
    assert set(observations.values()) == {8}
    assert {metric.period for metric in universe.financial_metrics} == set(PERIODS)


def test_every_company_has_eight_operational_observations() -> None:
    universe = build_universe()

    observations = Counter(metric.company_id for metric in universe.operational_metrics)

    assert len(universe.operational_metrics) == 64
    assert set(observations.values()) == {8}


def test_heliogrid_has_largest_2026q2_yoy_revenue_growth() -> None:
    universe = build_universe()

    metrics = {(metric.company_id, metric.period): metric for metric in universe.financial_metrics}

    growth_by_company = {}

    for company in universe.companies:
        current = metrics[(company.company_id, "2026Q2")]
        prior = metrics[(company.company_id, "2025Q2")]

        growth_by_company[company.company_id] = (
            current.revenue_usd - prior.revenue_usd
        ) / prior.revenue_usd

    winner = max(
        growth_by_company,
        key=lambda company_id: growth_by_company[company_id],
    )

    assert winner == "PC-004"


def test_2026q2_portfolio_revenue_is_735_million() -> None:
    universe = build_universe()

    total_revenue = sum(
        metric.revenue_usd for metric in universe.financial_metrics if metric.period == "2026Q2"
    )

    assert total_revenue == 735_000_000


def test_vantage_revenue_grows_while_retention_deteriorates() -> None:
    universe = build_universe()

    metrics = {(metric.company_id, metric.period): metric for metric in universe.financial_metrics}

    prior = metrics[("PC-005", "2025Q2")]
    current = metrics[("PC-005", "2026Q2")]

    assert current.revenue_usd > prior.revenue_usd
    assert current.net_retention_pct == 97
    assert prior.net_retention_pct == 112
    assert current.net_retention_pct < prior.net_retention_pct


def test_orbis_incident_quarter_has_uptime_deterioration_and_recovery() -> None:
    universe = build_universe()

    uptime = {
        metric.period: metric.metric_value
        for metric in universe.operational_metrics
        if metric.company_id == "PC-006" and metric.metric_name == "platform_uptime_pct"
    }

    assert uptime["2026Q1"] == 99.72
    assert uptime["2026Q1"] < uptime["2025Q4"]
    assert uptime["2026Q2"] > uptime["2026Q1"]
