import hashlib
from collections import Counter, defaultdict

from enterprise_genai.data.core_corpus import build_core_corpus
from enterprise_genai.data.provenance import (
    canonical_fact_dates,
    validate_document_provenance,
    validate_document_temporality,
)
from enterprise_genai.data.universe import build_universe

CORE_DOCUMENT_TYPES = {
    "investment_committee_memo",
    "quarterly_management_report",
    "board_update",
    "risk_review",
}


def _evidence_blocks():
    corpus = build_core_corpus()

    return [(document, block) for document in corpus.documents for block in document.evidence]


def test_core_corpus_contains_32_documents() -> None:
    corpus = build_core_corpus()

    assert len(corpus.documents) == 32


def test_each_company_has_exactly_four_core_documents() -> None:
    corpus = build_core_corpus()

    counts = Counter(document.company_id for document in corpus.documents)

    assert set(counts.values()) == {4}
    assert len(counts) == 8


def test_each_company_has_all_four_core_document_types() -> None:
    corpus = build_core_corpus()

    types_by_company = defaultdict(set)

    for document in corpus.documents:
        types_by_company[document.company_id].add(document.document_type)

    assert len(types_by_company) == 8

    for document_types in types_by_company.values():
        assert document_types == CORE_DOCUMENT_TYPES


def test_core_corpus_contains_80_evidence_blocks() -> None:
    corpus = build_core_corpus()

    evidence_count = sum(len(document.evidence) for document in corpus.documents)

    assert evidence_count == 80


def test_core_corpus_provenance_is_valid() -> None:
    validate_document_provenance(
        build_core_corpus(),
        build_universe(),
    )


def test_core_corpus_temporality_is_valid() -> None:
    validate_document_temporality(
        build_core_corpus(),
        build_universe(),
    )


def test_ic_memos_predate_northstar_investments() -> None:
    universe = build_universe()
    corpus = build_core_corpus()

    investment_dates = {
        company.company_id: company.investment_date for company in universe.companies
    }

    for document in corpus.documents:
        if document.document_type == "investment_committee_memo":
            assert document.document_date < investment_dates[document.company_id]


def test_ic_memos_do_not_reference_future_dated_facts() -> None:
    universe = build_universe()
    corpus = build_core_corpus()

    fact_dates = canonical_fact_dates(universe)

    for document in corpus.documents:
        if document.document_type != "investment_committee_memo":
            continue

        for block in document.evidence:
            for fact_id in block.source_fact_ids:
                fact_date = fact_dates.get(fact_id)

                if fact_date is not None:
                    assert fact_date <= document.document_date


def test_orbis_exact_identifier_occurs_only_once_in_core_evidence() -> None:
    matches = [
        (document.document_id, block.evidence_id)
        for document, block in _evidence_blocks()
        if "ORBIS-IDX-7" in block.text
    ]

    assert matches == [
        (
            "DOC-CORE-PC006-RISK-2026Q2",
            "EVID-CORE-PC006-RISK-PRIMARY",
        )
    ]


def test_vantage_semantic_signal_avoids_retention_keyword() -> None:
    blocks = {block.evidence_id: block for _, block in _evidence_blocks()}

    semantic_block = blocks["EVID-CORE-PC005-QMR-SIGNAL"]
    financial_block = blocks["EVID-CORE-PC005-QMR-FINANCIAL"]

    assert "retention" not in semantic_block.text.lower()
    assert "renewal behavior" in semantic_block.text.lower()
    assert "net retention" in financial_block.text.lower()


def test_german_distractor_exists_without_supplier_dependency() -> None:
    blocks = {block.evidence_id: block for _, block in _evidence_blocks()}

    orbis = blocks["EVID-CORE-PC006-RISK-CONTEXT"]

    assert "Germany" in orbis.text
    assert "commercial exposure" in orbis.text
    assert "rather than a critical-supplier dependency" in orbis.text


def test_core_corpus_serialization_is_deterministic() -> None:
    first = build_core_corpus().model_dump_json(indent=2)
    second = build_core_corpus().model_dump_json(indent=2)

    first_hash = hashlib.sha256(first.encode()).hexdigest()

    second_hash = hashlib.sha256(second.encode()).hexdigest()

    assert first_hash == second_hash
