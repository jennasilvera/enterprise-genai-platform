from collections import Counter

from enterprise_genai.data.universe import build_universe
from enterprise_genai.db.ingestion import (
    canonical_fact_records,
    structured_row_counts,
    universe_fingerprint,
)

EXPECTED_COUNTS = {
    "dataset_versions": 1,
    "canonical_facts": 215,
    "firms": 1,
    "funds": 1,
    "companies": 8,
    "customers": 14,
    "suppliers": 14,
    "company_customers": 14,
    "company_suppliers": 14,
    "financial_metrics": 64,
    "operational_metrics": 64,
    "geographic_exposures": 9,
    "risks": 8,
    "transactions": 4,
}


EXPECTED_FACT_TYPE_COUNTS = {
    "firm": 1,
    "fund": 1,
    "company": 8,
    "customer": 14,
    "supplier": 14,
    "company_customer": 14,
    "company_supplier": 14,
    "financial_metric": 64,
    "operational_metric": 64,
    "geographic_exposure": 9,
    "risk": 8,
    "transaction": 4,
}


def test_structured_row_counts_match_canonical_universe() -> None:
    assert structured_row_counts(build_universe()) == EXPECTED_COUNTS


def test_canonical_fact_registry_has_215_unique_facts() -> None:
    records = canonical_fact_records(build_universe())

    fact_ids = [record["fact_id"] for record in records]

    assert len(records) == 215
    assert len(fact_ids) == len(set(fact_ids))


def test_canonical_fact_type_distribution_is_expected() -> None:
    records = canonical_fact_records(build_universe())

    counts = Counter(record["fact_type"] for record in records)

    assert dict(counts) == EXPECTED_FACT_TYPE_COUNTS


def test_financial_fact_ids_are_registered() -> None:
    records = canonical_fact_records(build_universe())

    facts = {record["fact_id"]: record["fact_type"] for record in records}

    assert facts["FIN-PC-004-2026Q2"] == "financial_metric"
    assert facts["FIN-PC-005-2025Q2"] == "financial_metric"


def test_universe_fingerprint_is_order_independent() -> None:
    universe = build_universe()

    reordered = universe.model_copy(
        update={
            "companies": list(reversed(universe.companies)),
            "financial_metrics": list(reversed(universe.financial_metrics)),
            "risks": list(reversed(universe.risks)),
        }
    )

    assert universe_fingerprint(universe) == universe_fingerprint(reordered)


def test_universe_fingerprint_changes_when_truth_changes() -> None:
    universe = build_universe()

    first_company = universe.companies[0]

    changed_company = first_company.model_copy(update={"name": (f"{first_company.name} Changed")})

    changed = universe.model_copy(
        update={
            "companies": [
                changed_company,
                *universe.companies[1:],
            ]
        }
    )

    assert universe_fingerprint(universe) != universe_fingerprint(changed)
