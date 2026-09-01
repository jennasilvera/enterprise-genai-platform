from datetime import date

import pytest

from enterprise_genai.data.document_models import (
    DocumentCorpus,
    EnterpriseDocument,
    EvidenceBlock,
)
from enterprise_genai.data.provenance import (
    canonical_fact_ids,
    validate_document_provenance,
)
from enterprise_genai.data.universe import build_universe


def _corpus(source_fact_ids: list[str]) -> DocumentCorpus:
    return DocumentCorpus(
        dataset_version="northstar-v1",
        documents=[
            EnterpriseDocument(
                document_id="DOC-PC002-RISK-001",
                company_id="PC-002",
                document_type="risk_review",
                title="Alder Manufacturing Risk Review",
                document_date=date(2026, 6, 30),
                confidentiality="confidential",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC002-SUPPLIER-001",
                        heading="Critical supplier dependency",
                        text=(
                            "Alder remains dependent on a single-source German titanium supplier."
                        ),
                        source_fact_ids=source_fact_ids,
                    )
                ],
            )
        ],
    )


def test_canonical_fact_ids_include_relationship_and_risk_ids() -> None:
    universe = build_universe()

    fact_ids = canonical_fact_ids(universe)

    assert "CS-003" in fact_ids
    assert "SUP-005" in fact_ids
    assert "RISK-002" in fact_ids
    assert "GEO-002" in fact_ids


def test_canonical_fact_ids_include_financial_observations() -> None:
    universe = build_universe()

    fact_ids = canonical_fact_ids(universe)

    assert "FIN-PC-005-2026Q2" in fact_ids


def test_valid_document_provenance_passes() -> None:
    universe = build_universe()
    corpus = _corpus(
        [
            "CS-003",
            "SUP-005",
            "RISK-002",
            "GEO-002",
        ]
    )

    validate_document_provenance(corpus, universe)


def test_unknown_provenance_id_is_rejected() -> None:
    universe = build_universe()
    corpus = _corpus(
        [
            "CS-003",
            "RISK-999",
        ]
    )

    with pytest.raises(
        ValueError,
        match="RISK-999",
    ):
        validate_document_provenance(corpus, universe)
