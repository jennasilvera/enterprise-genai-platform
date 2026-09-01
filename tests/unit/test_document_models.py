from datetime import date

import pytest
from pydantic import ValidationError

from enterprise_genai.data.document_models import (
    DocumentCorpus,
    EnterpriseDocument,
    EvidenceBlock,
)


def _document(
    *,
    document_id: str = "DOC-PC001-RISK-001",
    evidence_id: str = "EVID-PC001-RISK-001",
) -> EnterpriseDocument:
    return EnterpriseDocument(
        document_id=document_id,
        company_id="PC-001",
        document_type="risk_review",
        title="Meridian Health Systems Risk Review",
        document_date=date(2026, 6, 30),
        confidentiality="confidential",
        version=1,
        evidence=[
            EvidenceBlock(
                evidence_id=evidence_id,
                heading="Customer concentration",
                text=(
                    "A single healthcare network represents a material share of company revenue."
                ),
                source_fact_ids=[
                    "RISK-001",
                    "CC-001",
                ],
            )
        ],
    )


def test_valid_document_corpus() -> None:
    corpus = DocumentCorpus(
        dataset_version="northstar-v1",
        documents=[_document()],
    )

    assert len(corpus.documents) == 1
    assert corpus.documents[0].evidence[0].source_fact_ids == [
        "RISK-001",
        "CC-001",
    ]


def test_duplicate_document_ids_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DocumentCorpus(
            dataset_version="northstar-v1",
            documents=[
                _document(),
                _document(evidence_id="EVID-PC001-RISK-002"),
            ],
        )


def test_duplicate_evidence_ids_across_documents_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DocumentCorpus(
            dataset_version="northstar-v1",
            documents=[
                _document(),
                _document(
                    document_id="DOC-PC001-BOARD-001",
                ),
            ],
        )


def test_empty_source_provenance_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceBlock(
            evidence_id="EVID-INVALID",
            heading="Invalid",
            text="This block lacks provenance.",
            source_fact_ids=[],
        )
