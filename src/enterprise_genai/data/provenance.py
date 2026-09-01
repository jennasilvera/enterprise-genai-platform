from datetime import date

from enterprise_genai.data.document_models import DocumentCorpus
from enterprise_genai.data.models import EnterpriseUniverse


def canonical_fact_ids(universe: EnterpriseUniverse) -> set[str]:
    """Return all stable canonical fact identifiers in the enterprise universe."""

    ids: set[str] = set()

    ids.update(firm.firm_id for firm in universe.firms)
    ids.update(fund.fund_id for fund in universe.funds)
    ids.update(company.company_id for company in universe.companies)
    ids.update(customer.customer_id for customer in universe.customers)
    ids.update(supplier.supplier_id for supplier in universe.suppliers)

    ids.update(relationship.relationship_id for relationship in universe.company_customers)
    ids.update(relationship.relationship_id for relationship in universe.company_suppliers)

    ids.update(exposure.exposure_id for exposure in universe.geographic_exposures)
    ids.update(risk.risk_id for risk in universe.risks)
    ids.update(transaction.transaction_id for transaction in universe.transactions)
    ids.update(metric.metric_id for metric in universe.operational_metrics)

    ids.update(f"FIN-{metric.company_id}-{metric.period}" for metric in universe.financial_metrics)

    return ids


def _period_end_date(period: str) -> date:
    """Convert a canonical YYYYQn period into its quarter-end date."""

    year = int(period[:4])
    quarter = int(period[-1])

    quarter_ends = {
        1: (3, 31),
        2: (6, 30),
        3: (9, 30),
        4: (12, 31),
    }

    month, day = quarter_ends[quarter]

    return date(year, month, day)


def canonical_fact_dates(
    universe: EnterpriseUniverse,
) -> dict[str, date]:
    """Return availability dates for canonical facts with temporal semantics."""

    dates: dict[str, date] = {}

    dates.update(
        {
            relationship.relationship_id: relationship.relationship_start_date
            for relationship in universe.company_customers
        }
    )

    dates.update({risk.risk_id: risk.identified_date for risk in universe.risks})

    dates.update(
        {
            transaction.transaction_id: transaction.announcement_date
            for transaction in universe.transactions
        }
    )

    dates.update(
        {
            f"FIN-{metric.company_id}-{metric.period}": _period_end_date(metric.period)
            for metric in universe.financial_metrics
        }
    )

    dates.update(
        {
            metric.metric_id: _period_end_date(metric.period)
            for metric in universe.operational_metrics
        }
    )

    return dates


def validate_document_provenance(
    corpus: DocumentCorpus,
    universe: EnterpriseUniverse,
) -> None:
    """Raise when document evidence references unknown canonical facts."""

    valid_ids = canonical_fact_ids(universe)

    for document in corpus.documents:
        for block in document.evidence:
            unknown = set(block.source_fact_ids) - valid_ids

            if unknown:
                unknown_list = ", ".join(sorted(unknown))
                raise ValueError(
                    f"Evidence {block.evidence_id} references unknown "
                    f"canonical fact IDs: {unknown_list}"
                )


def validate_document_temporality(
    corpus: DocumentCorpus,
    universe: EnterpriseUniverse,
) -> None:
    """Reject evidence that references facts unavailable on the document date."""

    fact_dates = canonical_fact_dates(universe)

    for document in corpus.documents:
        for block in document.evidence:
            for fact_id in block.source_fact_ids:
                fact_date = fact_dates.get(fact_id)

                if fact_date is not None and fact_date > document.document_date:
                    raise ValueError(
                        f"Evidence {block.evidence_id} in "
                        f"{document.document_id} references future fact "
                        f"{fact_id} dated {fact_date.isoformat()} after "
                        f"document date "
                        f"{document.document_date.isoformat()}."
                    )
