import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from enterprise_genai.data.models import (
    Company,
    CompanyCustomer,
    CompanySupplier,
    Customer,
    DatasetMetadata,
    EnterpriseUniverse,
    FinancialMetric,
    Firm,
    Fund,
    GeographicExposure,
    OperationalMetric,
    Risk,
    Supplier,
    Transaction,
)
from enterprise_genai.db.models import (
    CanonicalFactRow,
    CompanyCustomerRow,
    CompanyRow,
    CompanySupplierRow,
    CustomerRow,
    DatasetVersionRow,
    FinancialMetricRow,
    FirmRow,
    FundRow,
    GeographicExposureRow,
    OperationalMetricRow,
    RiskRow,
    SupplierRow,
    TransactionRow,
)


class DatasetVersionConflictError(RuntimeError):
    """Raised when an immutable dataset version already has different contents."""


@dataclass(frozen=True)
class IngestionResult:
    dataset_version: str
    inserted: bool
    fingerprint: str
    row_counts: dict[str, int]


def _sorted_payload(
    items: list[Any],
    key: Callable[[dict[str, Any]], Any],
) -> list[dict[str, Any]]:
    payloads = [item.model_dump(mode="json") for item in items]

    return sorted(
        payloads,
        key=key,
    )


def normalized_universe_payload(
    universe: EnterpriseUniverse,
) -> dict[str, Any]:
    """Return an order-independent canonical representation."""

    return {
        "metadata": universe.metadata.model_dump(mode="json"),
        "firms": _sorted_payload(
            universe.firms,
            lambda item: item["firm_id"],
        ),
        "funds": _sorted_payload(
            universe.funds,
            lambda item: item["fund_id"],
        ),
        "companies": _sorted_payload(
            universe.companies,
            lambda item: item["company_id"],
        ),
        "customers": _sorted_payload(
            universe.customers,
            lambda item: item["customer_id"],
        ),
        "suppliers": _sorted_payload(
            universe.suppliers,
            lambda item: item["supplier_id"],
        ),
        "company_customers": _sorted_payload(
            universe.company_customers,
            lambda item: item["relationship_id"],
        ),
        "company_suppliers": _sorted_payload(
            universe.company_suppliers,
            lambda item: item["relationship_id"],
        ),
        "financial_metrics": _sorted_payload(
            universe.financial_metrics,
            lambda item: (
                item["company_id"],
                item["period"],
            ),
        ),
        "operational_metrics": _sorted_payload(
            universe.operational_metrics,
            lambda item: item["metric_id"],
        ),
        "geographic_exposures": _sorted_payload(
            universe.geographic_exposures,
            lambda item: item["exposure_id"],
        ),
        "risks": _sorted_payload(
            universe.risks,
            lambda item: item["risk_id"],
        ),
        "transactions": _sorted_payload(
            universe.transactions,
            lambda item: item["transaction_id"],
        ),
    }


def universe_fingerprint(
    universe: EnterpriseUniverse,
) -> str:
    """Compute a deterministic semantic fingerprint of the universe."""

    payload = normalized_universe_payload(universe)

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def canonical_fact_records(
    universe: EnterpriseUniverse,
) -> list[dict[str, str]]:
    """Build the canonical fact registry derived from structured truth."""

    dataset_version = universe.metadata.dataset_version

    records: list[dict[str, str]] = []

    def add(
        fact_id: str,
        fact_type: str,
    ) -> None:
        records.append(
            {
                "dataset_version": dataset_version,
                "fact_id": fact_id,
                "fact_type": fact_type,
            }
        )

    for item in universe.firms:
        add(item.firm_id, "firm")

    for item in universe.funds:
        add(item.fund_id, "fund")

    for item in universe.companies:
        add(item.company_id, "company")

    for item in universe.customers:
        add(item.customer_id, "customer")

    for item in universe.suppliers:
        add(item.supplier_id, "supplier")

    for item in universe.company_customers:
        add(
            item.relationship_id,
            "company_customer",
        )

    for item in universe.company_suppliers:
        add(
            item.relationship_id,
            "company_supplier",
        )

    for item in universe.financial_metrics:
        add(
            f"FIN-{item.company_id}-{item.period}",
            "financial_metric",
        )

    for item in universe.operational_metrics:
        add(
            item.metric_id,
            "operational_metric",
        )

    for item in universe.geographic_exposures:
        add(
            item.exposure_id,
            "geographic_exposure",
        )

    for item in universe.risks:
        add(item.risk_id, "risk")

    for item in universe.transactions:
        add(
            item.transaction_id,
            "transaction",
        )

    records.sort(key=lambda record: record["fact_id"])

    fact_ids = [record["fact_id"] for record in records]

    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("Canonical fact registry contains duplicate fact IDs.")

    return records


def structured_row_counts(
    universe: EnterpriseUniverse,
) -> dict[str, int]:
    return {
        "dataset_versions": 1,
        "canonical_facts": len(canonical_fact_records(universe)),
        "firms": len(universe.firms),
        "funds": len(universe.funds),
        "companies": len(universe.companies),
        "customers": len(universe.customers),
        "suppliers": len(universe.suppliers),
        "company_customers": len(universe.company_customers),
        "company_suppliers": len(universe.company_suppliers),
        "financial_metrics": len(universe.financial_metrics),
        "operational_metrics": len(universe.operational_metrics),
        "geographic_exposures": len(universe.geographic_exposures),
        "risks": len(universe.risks),
        "transactions": len(universe.transactions),
    }


def _insert_rows(
    session: Session,
    model: type[Any],
    rows: list[dict[str, Any]],
) -> None:
    if rows:
        session.execute(
            insert(model),
            rows,
        )


def _domain_rows(
    universe: EnterpriseUniverse,
) -> list[tuple[type[Any], list[dict[str, Any]]]]:
    version = universe.metadata.dataset_version

    def dump(
        items: list[Any],
    ) -> list[dict[str, Any]]:
        return [
            {
                "dataset_version": version,
                **item.model_dump(),
            }
            for item in items
        ]

    return [
        (FirmRow, dump(universe.firms)),
        (FundRow, dump(universe.funds)),
        (CompanyRow, dump(universe.companies)),
        (CustomerRow, dump(universe.customers)),
        (SupplierRow, dump(universe.suppliers)),
        (
            CompanyCustomerRow,
            dump(universe.company_customers),
        ),
        (
            CompanySupplierRow,
            dump(universe.company_suppliers),
        ),
        (
            FinancialMetricRow,
            dump(universe.financial_metrics),
        ),
        (
            OperationalMetricRow,
            dump(universe.operational_metrics),
        ),
        (
            GeographicExposureRow,
            dump(universe.geographic_exposures),
        ),
        (RiskRow, dump(universe.risks)),
        (
            TransactionRow,
            dump(universe.transactions),
        ),
    ]


def _optional_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    return float(value)


def load_universe(
    session: Session,
    dataset_version: str,
) -> EnterpriseUniverse:
    """Reconstruct an EnterpriseUniverse from PostgreSQL."""

    metadata = session.get(
        DatasetVersionRow,
        dataset_version,
    )

    if metadata is None:
        raise KeyError(f"Unknown dataset version: {dataset_version}")

    def rows(
        model: type[Any],
        order_by: Any,
    ) -> list[Any]:
        statement = select(model).where(model.dataset_version == dataset_version).order_by(order_by)

        return list(session.scalars(statement))

    firms = rows(
        FirmRow,
        FirmRow.firm_id,
    )
    funds = rows(
        FundRow,
        FundRow.fund_id,
    )
    companies = rows(
        CompanyRow,
        CompanyRow.company_id,
    )
    customers = rows(
        CustomerRow,
        CustomerRow.customer_id,
    )
    suppliers = rows(
        SupplierRow,
        SupplierRow.supplier_id,
    )
    company_customers = rows(
        CompanyCustomerRow,
        CompanyCustomerRow.relationship_id,
    )
    company_suppliers = rows(
        CompanySupplierRow,
        CompanySupplierRow.relationship_id,
    )

    financial_statement = (
        select(FinancialMetricRow)
        .where(FinancialMetricRow.dataset_version == dataset_version)
        .order_by(
            FinancialMetricRow.company_id,
            FinancialMetricRow.period,
        )
    )
    financial_metrics = list(session.scalars(financial_statement))

    operational_metrics = rows(
        OperationalMetricRow,
        OperationalMetricRow.metric_id,
    )
    geographic_exposures = rows(
        GeographicExposureRow,
        GeographicExposureRow.exposure_id,
    )
    risks = rows(
        RiskRow,
        RiskRow.risk_id,
    )
    transactions = rows(
        TransactionRow,
        TransactionRow.transaction_id,
    )

    return EnterpriseUniverse(
        metadata=DatasetMetadata(
            dataset_version=metadata.dataset_version,
            schema_version=metadata.schema_version,
            random_seed=metadata.random_seed,
        ),
        firms=[
            Firm(
                firm_id=row.firm_id,
                name=row.name,
            )
            for row in firms
        ],
        funds=[
            Fund(
                fund_id=row.fund_id,
                firm_id=row.firm_id,
                name=row.name,
                vintage_year=row.vintage_year,
                committed_capital_usd=(row.committed_capital_usd),
            )
            for row in funds
        ],
        companies=[
            Company(
                company_id=row.company_id,
                fund_id=row.fund_id,
                name=row.name,
                industry=row.industry,
                headquarters_country=(row.headquarters_country),
                investment_date=row.investment_date,
                ownership_pct=float(row.ownership_pct),
            )
            for row in companies
        ],
        customers=[
            Customer(
                customer_id=row.customer_id,
                name=row.name,
                industry=row.industry,
                country=row.country,
            )
            for row in customers
        ],
        suppliers=[
            Supplier(
                supplier_id=row.supplier_id,
                name=row.name,
                category=row.category,
                country=row.country,
            )
            for row in suppliers
        ],
        company_customers=[
            CompanyCustomer(
                relationship_id=(row.relationship_id),
                company_id=row.company_id,
                customer_id=row.customer_id,
                revenue_share_pct=float(row.revenue_share_pct),
                relationship_start_date=(row.relationship_start_date),
                relationship_status=(row.relationship_status),
            )
            for row in company_customers
        ],
        company_suppliers=[
            CompanySupplier(
                relationship_id=(row.relationship_id),
                company_id=row.company_id,
                supplier_id=row.supplier_id,
                spend_share_pct=float(row.spend_share_pct),
                criticality=row.criticality,
                single_source=row.single_source,
                relationship_status=(row.relationship_status),
            )
            for row in company_suppliers
        ],
        financial_metrics=[
            FinancialMetric(
                company_id=row.company_id,
                period=row.period,
                revenue_usd=row.revenue_usd,
                ebitda_usd=row.ebitda_usd,
                gross_margin_pct=float(row.gross_margin_pct),
                net_retention_pct=_optional_float(row.net_retention_pct),
                customer_count=row.customer_count,
                employee_count=row.employee_count,
            )
            for row in financial_metrics
        ],
        operational_metrics=[
            OperationalMetric(
                metric_id=row.metric_id,
                company_id=row.company_id,
                period=row.period,
                metric_name=row.metric_name,
                metric_value=float(row.metric_value),
                unit=row.unit,
            )
            for row in operational_metrics
        ],
        geographic_exposures=[
            GeographicExposure(
                exposure_id=row.exposure_id,
                company_id=row.company_id,
                country=row.country,
                exposure_type=row.exposure_type,
                exposure_pct=float(row.exposure_pct),
            )
            for row in geographic_exposures
        ],
        risks=[
            Risk(
                risk_id=row.risk_id,
                company_id=row.company_id,
                risk_category=row.risk_category,
                title=row.title,
                severity=row.severity,
                status=row.status,
                identified_date=(row.identified_date),
                description=row.description,
            )
            for row in risks
        ],
        transactions=[
            Transaction(
                transaction_id=row.transaction_id,
                company_id=row.company_id,
                transaction_type=(row.transaction_type),
                announcement_date=(row.announcement_date),
                close_date=row.close_date,
                value_usd=row.value_usd,
                counterparty=row.counterparty,
            )
            for row in transactions
        ],
    )


COUNT_MODELS = {
    "dataset_versions": DatasetVersionRow,
    "canonical_facts": CanonicalFactRow,
    "firms": FirmRow,
    "funds": FundRow,
    "companies": CompanyRow,
    "customers": CustomerRow,
    "suppliers": SupplierRow,
    "company_customers": CompanyCustomerRow,
    "company_suppliers": CompanySupplierRow,
    "financial_metrics": FinancialMetricRow,
    "operational_metrics": OperationalMetricRow,
    "geographic_exposures": GeographicExposureRow,
    "risks": RiskRow,
    "transactions": TransactionRow,
}


def database_row_counts(
    session: Session,
    dataset_version: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for name, model in COUNT_MODELS.items():
        statement = (
            select(func.count()).select_from(model).where(model.dataset_version == dataset_version)
        )

        counts[name] = session.execute(statement).scalar_one()

    return counts


def _fact_registry_matches(
    session: Session,
    universe: EnterpriseUniverse,
) -> bool:
    version = universe.metadata.dataset_version

    actual = list(
        session.execute(
            select(
                CanonicalFactRow.fact_id,
                CanonicalFactRow.fact_type,
            )
            .where(CanonicalFactRow.dataset_version == version)
            .order_by(CanonicalFactRow.fact_id)
        ).all()
    )

    expected = [
        (
            record["fact_id"],
            record["fact_type"],
        )
        for record in canonical_fact_records(universe)
    ]

    return actual == expected


def ingest_universe(
    session: Session,
    universe: EnterpriseUniverse,
) -> IngestionResult:
    """Persist one immutable canonical universe transactionally."""

    version = universe.metadata.dataset_version
    expected_fingerprint = universe_fingerprint(universe)
    expected_counts = structured_row_counts(universe)

    existing = session.get(
        DatasetVersionRow,
        version,
    )

    if existing is not None:
        persisted = load_universe(
            session,
            version,
        )

        persisted_fingerprint = universe_fingerprint(persisted)

        actual_counts = database_row_counts(
            session,
            version,
        )

        if (
            persisted_fingerprint != expected_fingerprint
            or actual_counts != expected_counts
            or not _fact_registry_matches(
                session,
                universe,
            )
        ):
            raise DatasetVersionConflictError(
                f"Dataset version {version} already exists with different persisted contents."
            )

        return IngestionResult(
            dataset_version=version,
            inserted=False,
            fingerprint=expected_fingerprint,
            row_counts=actual_counts,
        )

    session.execute(
        insert(DatasetVersionRow),
        [
            {
                "dataset_version": version,
                "schema_version": (universe.metadata.schema_version),
                "random_seed": (universe.metadata.random_seed),
            }
        ],
    )

    for model, records in _domain_rows(universe):
        _insert_rows(
            session,
            model,
            records,
        )

    _insert_rows(
        session,
        CanonicalFactRow,
        canonical_fact_records(universe),
    )

    persisted = load_universe(
        session,
        version,
    )

    persisted_fingerprint = universe_fingerprint(persisted)

    if persisted_fingerprint != expected_fingerprint:
        raise RuntimeError(
            "PostgreSQL round-trip fingerprint does not match the canonical universe."
        )

    actual_counts = database_row_counts(
        session,
        version,
    )

    if actual_counts != expected_counts:
        raise RuntimeError("PostgreSQL row counts do not match canonical structured row counts.")

    if not _fact_registry_matches(
        session,
        universe,
    ):
        raise RuntimeError("Canonical fact registry does not match structured truth.")

    return IngestionResult(
        dataset_version=version,
        inserted=True,
        fingerprint=expected_fingerprint,
        row_counts=actual_counts,
    )
