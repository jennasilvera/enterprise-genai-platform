from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
)

import enterprise_genai.db.models  # noqa: F401
from enterprise_genai.db.base import Base

EXPECTED_TABLES = {
    "chunk_source_facts",
    "chunks",
    "dataset_versions",
    "canonical_facts",
    "firms",
    "funds",
    "companies",
    "customers",
    "suppliers",
    "company_customers",
    "company_suppliers",
    "financial_metrics",
    "operational_metrics",
    "geographic_exposures",
    "risks",
    "transactions",
    "documents",
    "evidence_blocks",
    "evidence_source_facts",
    "human_review_requests",
}


def _constraint_names(table, constraint_type):
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
    }


def _foreign_key_targets(table):
    return {
        tuple(element.target_fullname for element in constraint.elements)
        for constraint in table.constraints
        if isinstance(
            constraint,
            ForeignKeyConstraint,
        )
    }


def test_relational_metadata_contains_expected_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_versioned_entity_primary_keys_include_dataset_version() -> None:
    expected = {
        "firms": "firm_id",
        "funds": "fund_id",
        "companies": "company_id",
        "customers": "customer_id",
        "suppliers": "supplier_id",
        "risks": "risk_id",
        "transactions": "transaction_id",
        "documents": "document_id",
        "evidence_blocks": "evidence_id",
    }

    for table_name, stable_id in expected.items():
        table = Base.metadata.tables[table_name]

        assert list(table.primary_key.columns.keys()) == [
            "dataset_version",
            stable_id,
        ]


def test_financial_metrics_use_company_period_primary_key() -> None:
    table = Base.metadata.tables["financial_metrics"]

    assert list(table.primary_key.columns.keys()) == [
        "dataset_version",
        "company_id",
        "period",
    ]


def test_operational_metric_uniqueness_matches_canonical_model() -> None:
    table = Base.metadata.tables["operational_metrics"]

    assert "uq_operational_metrics_company_period_metric" in _constraint_names(
        table,
        UniqueConstraint,
    )


def test_percentage_checks_are_present() -> None:
    expected = {
        "companies": "ck_companies_ownership_pct",
        "company_customers": ("ck_company_customers_revenue_share_pct"),
        "company_suppliers": ("ck_company_suppliers_spend_share_pct"),
        "geographic_exposures": ("ck_geographic_exposures_pct"),
    }

    for table_name, check_name in expected.items():
        table = Base.metadata.tables[table_name]

        assert check_name in _constraint_names(
            table,
            CheckConstraint,
        )


def test_document_evidence_foreign_key_is_composite() -> None:
    table = Base.metadata.tables["evidence_blocks"]

    assert (
        "documents.dataset_version",
        "documents.document_id",
    ) in _foreign_key_targets(table)


def test_evidence_sources_reference_evidence_and_canonical_facts() -> None:
    table = Base.metadata.tables["evidence_source_facts"]

    targets = _foreign_key_targets(table)

    assert (
        "evidence_blocks.dataset_version",
        "evidence_blocks.evidence_id",
    ) in targets

    assert (
        "canonical_facts.dataset_version",
        "canonical_facts.fact_id",
    ) in targets


def test_evidence_ordering_constraints_are_present() -> None:
    evidence = Base.metadata.tables["evidence_blocks"]
    source = Base.metadata.tables["evidence_source_facts"]

    assert "uq_evidence_blocks_document_ordinal" in _constraint_names(
        evidence,
        UniqueConstraint,
    )

    assert "ck_evidence_blocks_ordinal" in _constraint_names(
        evidence,
        CheckConstraint,
    )

    assert "uq_evidence_source_facts_ordinal" in _constraint_names(
        source,
        UniqueConstraint,
    )

    assert "ck_evidence_source_facts_ordinal" in _constraint_names(
        source,
        CheckConstraint,
    )
