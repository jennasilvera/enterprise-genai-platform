from datetime import date

import pytest

from enterprise_genai.data.corpus import build_pilot_corpus
from enterprise_genai.data.document_models import (
    DocumentCorpus,
    EnterpriseDocument,
    EvidenceBlock,
)
from enterprise_genai.data.provenance import (
    canonical_fact_dates,
    validate_document_temporality,
)
from enterprise_genai.data.universe import build_universe


def _corpus_with_fact(
    *,
    fact_id: str,
    document_date: date,
) -> DocumentCorpus:
    return DocumentCorpus(
        dataset_version="northstar-v1",
        documents=[
            EnterpriseDocument(
                document_id="DOC-TEMPORAL-TEST",
                company_id="PC-006",
                document_type="risk_review",
                title="Temporal Validation Test",
                document_date=document_date,
                confidentiality="confidential",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-TEMPORAL-TEST",
                        heading="Temporal test",
                        text="Synthetic evidence used for temporal validation.",
                        source_fact_ids=[fact_id],
                    )
                ],
            )
        ],
    )


def test_canonical_fact_dates_include_dated_fact_types() -> None:
    dates = canonical_fact_dates(build_universe())

    assert dates["RISK-006"] == date(2026, 2, 27)
    assert dates["FIN-PC-006-2026Q2"] == date(2026, 6, 30)
    assert dates["OP-PC-006-2026Q2-UPTIME"] == date(2026, 6, 30)
    assert dates["CC-001"] == date(2020, 6, 1)


def test_pilot_corpus_is_temporally_valid() -> None:
    validate_document_temporality(
        build_pilot_corpus(),
        build_universe(),
    )


def test_future_financial_fact_is_rejected() -> None:
    corpus = _corpus_with_fact(
        fact_id="FIN-PC-006-2026Q2",
        document_date=date(2026, 6, 1),
    )

    with pytest.raises(
        ValueError,
        match="FIN-PC-006-2026Q2",
    ):
        validate_document_temporality(
            corpus,
            build_universe(),
        )


def test_future_risk_fact_is_rejected() -> None:
    corpus = _corpus_with_fact(
        fact_id="RISK-006",
        document_date=date(2026, 2, 1),
    )

    with pytest.raises(
        ValueError,
        match="RISK-006",
    ):
        validate_document_temporality(
            corpus,
            build_universe(),
        )
