import hashlib

from enterprise_genai.data.corpus import build_pilot_corpus
from enterprise_genai.data.provenance import validate_document_provenance
from enterprise_genai.data.universe import build_universe


def _evidence_by_id():
    corpus = build_pilot_corpus()

    return {
        block.evidence_id: block for document in corpus.documents for block in document.evidence
    }


def test_pilot_corpus_has_one_document_per_company() -> None:
    corpus = build_pilot_corpus()

    assert len(corpus.documents) == 8

    assert {document.company_id for document in corpus.documents} == {
        "PC-001",
        "PC-002",
        "PC-003",
        "PC-004",
        "PC-005",
        "PC-006",
        "PC-007",
        "PC-008",
    }


def test_pilot_corpus_has_sixteen_evidence_blocks() -> None:
    corpus = build_pilot_corpus()

    evidence_count = sum(len(document.evidence) for document in corpus.documents)

    assert evidence_count == 16


def test_pilot_provenance_is_valid() -> None:
    universe = build_universe()
    corpus = build_pilot_corpus()

    validate_document_provenance(corpus, universe)


def test_orbis_identifier_is_preserved_for_lexical_retrieval() -> None:
    evidence = _evidence_by_id()

    block = evidence["EVID-PC006-INCIDENT-001"]

    assert "ORBIS-IDX-7" in block.text


def test_vantage_semantic_case_avoids_retention_keyword() -> None:
    evidence = _evidence_by_id()

    block = evidence["EVID-PC005-COHORT-001"]

    assert "retention" not in block.text.lower()
    assert "renewal behavior" in block.text.lower()


def test_supplier_evidence_combines_multiple_canonical_facts() -> None:
    evidence = _evidence_by_id()

    alder = evidence["EVID-PC002-SUPPLIER-001"]
    novabio = evidence["EVID-PC008-SUPPLIER-001"]

    assert {
        "CS-003",
        "SUP-005",
        "RISK-002",
        "GEO-002",
    }.issubset(alder.source_fact_ids)

    assert {
        "CS-011",
        "SUP-011",
        "RISK-008",
        "GEO-008",
    }.issubset(novabio.source_fact_ids)


def test_pilot_corpus_serialization_is_deterministic() -> None:
    first = build_pilot_corpus().model_dump_json(indent=2)
    second = build_pilot_corpus().model_dump_json(indent=2)

    first_hash = hashlib.sha256(first.encode()).hexdigest()
    second_hash = hashlib.sha256(second.encode()).hexdigest()

    assert first_hash == second_hash
