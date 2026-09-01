from enterprise_genai.data.models import FinancialMetric, OperationalMetric

MILLION = 1_000_000

PERIODS = (
    "2024Q3",
    "2024Q4",
    "2025Q1",
    "2025Q2",
    "2025Q3",
    "2025Q4",
    "2026Q1",
    "2026Q2",
)


def _financial_series(
    *,
    company_id: str,
    revenue_millions: list[int],
    ebitda_millions: list[int],
    gross_margin_pct: list[float],
    net_retention_pct: list[float | None],
    customer_count: list[int | None],
    employee_count: list[int | None],
) -> list[FinancialMetric]:
    series = (
        revenue_millions,
        ebitda_millions,
        gross_margin_pct,
        net_retention_pct,
        customer_count,
        employee_count,
    )

    if any(len(values) != len(PERIODS) for values in series):
        raise ValueError(f"Incomplete financial series for {company_id}.")

    return [
        FinancialMetric(
            company_id=company_id,
            period=period,
            revenue_usd=revenue_millions[index] * MILLION,
            ebitda_usd=ebitda_millions[index] * MILLION,
            gross_margin_pct=gross_margin_pct[index],
            net_retention_pct=net_retention_pct[index],
            customer_count=customer_count[index],
            employee_count=employee_count[index],
        )
        for index, period in enumerate(PERIODS)
    ]


def build_financial_metrics() -> list[FinancialMetric]:
    """Build eight quarters of canonical financial observations."""

    metrics: list[FinancialMetric] = []

    metrics.extend(
        _financial_series(
            company_id="PC-001",
            revenue_millions=[72, 75, 78, 82, 85, 89, 93, 98],
            ebitda_millions=[12, 13, 14, 15, 16, 17, 18, 20],
            gross_margin_pct=[69.0, 69.5, 70.0, 70.2, 70.5, 71.0, 71.2, 71.5],
            net_retention_pct=[112, 113, 114, 115, 114, 113, 112, 111],
            customer_count=[118, 122, 126, 131, 135, 139, 143, 147],
            employee_count=[420, 431, 445, 458, 469, 480, 491, 505],
        )
    )

    metrics.extend(
        _financial_series(
            company_id="PC-002",
            revenue_millions=[95, 97, 98, 100, 101, 103, 104, 106],
            ebitda_millions=[14, 14, 15, 15, 15, 16, 15, 16],
            gross_margin_pct=[31.0, 31.2, 31.5, 31.8, 31.6, 31.4, 30.8, 30.5],
            net_retention_pct=[None] * 8,
            customer_count=[64, 65, 65, 66, 66, 67, 67, 68],
            employee_count=[615, 620, 626, 631, 637, 642, 646, 650],
        )
    )

    metrics.extend(
        _financial_series(
            company_id="PC-003",
            revenue_millions=[61, 63, 64, 66, 67, 69, 70, 72],
            ebitda_millions=[10, 10, 11, 11, 11, 12, 12, 13],
            gross_margin_pct=[57.0, 57.3, 57.5, 57.8, 58.0, 58.1, 58.0, 57.9],
            net_retention_pct=[107, 107, 106, 106, 105, 104, 102, 101],
            customer_count=[202, 207, 211, 216, 219, 222, 224, 226],
            employee_count=[338, 344, 350, 357, 363, 368, 371, 374],
        )
    )

    metrics.extend(
        _financial_series(
            company_id="PC-004",
            revenue_millions=[54, 58, 62, 68, 72, 77, 83, 92],
            ebitda_millions=[8, 9, 10, 11, 12, 14, 15, 18],
            gross_margin_pct=[38.0, 38.4, 38.8, 39.2, 39.6, 40.0, 40.3, 40.8],
            net_retention_pct=[None] * 8,
            customer_count=[18, 19, 19, 20, 20, 21, 22, 23],
            employee_count=[281, 294, 309, 326, 340, 356, 371, 389],
        )
    )

    metrics.extend(
        _financial_series(
            company_id="PC-005",
            revenue_millions=[48, 51, 55, 60, 64, 68, 73, 79],
            ebitda_millions=[8, 9, 10, 11, 12, 13, 15, 17],
            gross_margin_pct=[74.0, 74.2, 74.5, 74.8, 75.0, 75.2, 75.4, 75.5],
            net_retention_pct=[118, 117, 115, 112, 108, 104, 101, 97],
            customer_count=[86, 91, 96, 103, 111, 119, 127, 136],
            employee_count=[249, 261, 276, 291, 307, 323, 341, 360],
        )
    )

    metrics.extend(
        _financial_series(
            company_id="PC-006",
            revenue_millions=[83, 88, 92, 97, 102, 108, 114, 121],
            ebitda_millions=[18, 19, 21, 23, 24, 26, 27, 30],
            gross_margin_pct=[79.0, 79.2, 79.5, 79.7, 80.0, 80.2, 80.1, 80.4],
            net_retention_pct=[121, 121, 120, 120, 119, 118, 115, 117],
            customer_count=[321, 337, 352, 369, 386, 404, 421, 440],
            employee_count=[512, 531, 550, 571, 592, 615, 637, 661],
        )
    )

    metrics.extend(
        _financial_series(
            company_id="PC-007",
            revenue_millions=[69, 71, 73, 76, 78, 80, 82, 84],
            ebitda_millions=[12, 13, 13, 14, 14, 15, 15, 16],
            gross_margin_pct=[66.0, 66.2, 66.5, 66.7, 66.9, 67.0, 67.1, 67.3],
            net_retention_pct=[109, 109, 108, 108, 107, 107, 106, 106],
            customer_count=[144, 148, 151, 155, 158, 161, 164, 167],
            employee_count=[395, 402, 410, 418, 425, 432, 439, 446],
        )
    )

    metrics.extend(
        _financial_series(
            company_id="PC-008",
            revenue_millions=[57, 60, 63, 67, 70, 74, 78, 83],
            ebitda_millions=[9, 10, 10, 11, 12, 12, 13, 14],
            gross_margin_pct=[51.0, 51.2, 51.5, 51.8, 52.0, 52.2, 52.0, 51.9],
            net_retention_pct=[None] * 8,
            customer_count=[73, 75, 78, 81, 84, 87, 90, 94],
            employee_count=[466, 474, 483, 493, 504, 515, 528, 542],
        )
    )

    return metrics


def _operational_series(
    *,
    company_id: str,
    metric_code: str,
    metric_name: str,
    values: list[float],
    unit: str,
) -> list[OperationalMetric]:
    if len(values) != len(PERIODS):
        raise ValueError(f"Incomplete operational series for {company_id}.")

    return [
        OperationalMetric(
            metric_id=f"OP-{company_id}-{period}-{metric_code}",
            company_id=company_id,
            period=period,
            metric_name=metric_name,
            metric_value=value,
            unit=unit,
        )
        for period, value in zip(PERIODS, values, strict=True)
    ]


def build_operational_metrics() -> list[OperationalMetric]:
    """Build company-specific operational metric histories."""

    metrics: list[OperationalMetric] = []

    metrics.extend(
        _operational_series(
            company_id="PC-001",
            metric_code="BACKLOG",
            metric_name="implementation_backlog_sites",
            values=[42, 45, 49, 53, 58, 64, 70, 76],
            unit="sites",
        )
    )

    metrics.extend(
        _operational_series(
            company_id="PC-002",
            metric_code="YIELD",
            metric_name="production_yield_pct",
            values=[96.2, 96.5, 96.7, 96.8, 96.4, 95.9, 94.8, 94.2],
            unit="percent",
        )
    )

    metrics.extend(
        _operational_series(
            company_id="PC-003",
            metric_code="FREIGHT",
            metric_name="freight_volume_million_shipments",
            values=[12.4, 12.8, 13.0, 13.3, 13.5, 13.4, 13.0, 12.7],
            unit="million_shipments",
        )
    )

    metrics.extend(
        _operational_series(
            company_id="PC-004",
            metric_code="CAPACITY",
            metric_name="installed_capacity_mw",
            values=[410, 445, 480, 530, 580, 640, 705, 770],
            unit="megawatts",
        )
    )

    metrics.extend(
        _operational_series(
            company_id="PC-005",
            metric_code="JOBS",
            metric_name="forecast_jobs_million",
            values=[44, 48, 53, 59, 66, 74, 83, 93],
            unit="million_jobs",
        )
    )

    metrics.extend(
        _operational_series(
            company_id="PC-006",
            metric_code="UPTIME",
            metric_name="platform_uptime_pct",
            values=[99.98, 99.98, 99.99, 99.99, 99.98, 99.97, 99.72, 99.97],
            unit="percent",
        )
    )

    metrics.extend(
        _operational_series(
            company_id="PC-007",
            metric_code="VOLUME",
            metric_name="transaction_volume_billion_usd",
            values=[24.0, 25.6, 27.1, 28.9, 30.5, 32.2, 33.8, 35.7],
            unit="usd_billions",
        )
    )

    metrics.extend(
        _operational_series(
            company_id="PC-008",
            metric_code="SHIPMENTS",
            metric_name="instrument_shipments",
            values=[820, 860, 900, 950, 1000, 1060, 1110, 1175],
            unit="units",
        )
    )

    return metrics
