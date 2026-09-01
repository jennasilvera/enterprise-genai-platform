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
