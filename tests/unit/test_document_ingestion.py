from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.db.document_ingestion import (
    corpus_fingerprint,
    expected_document_row_counts,
    normalized_corpus_payload,
)


def test_document_counts_match_core_corpus() -> None:
    corpus = build_core_corpus()

    counts = expected_document_row_counts(corpus)

    assert counts["documents"] == 32
    assert counts["evidence_blocks"] == 80
    assert counts["evidence_source_facts"] > 80


def test_document_fingerprint_is_deterministic() -> None:
    assert corpus_fingerprint(build_core_corpus()) == corpus_fingerprint(build_core_corpus())


def test_document_fingerprint_ignores_top_level_document_order() -> None:
    corpus = build_core_corpus()

    reordered = corpus.model_copy(update={"documents": list(reversed(corpus.documents))})

    assert corpus_fingerprint(corpus) == corpus_fingerprint(reordered)


def test_document_fingerprint_detects_evidence_order_change() -> None:
    corpus = build_core_corpus()

    first_document = corpus.documents[0]

    changed_document = first_document.model_copy(
        update={"evidence": list(reversed(first_document.evidence))}
    )

    changed = corpus.model_copy(
        update={
            "documents": [
                changed_document,
                *corpus.documents[1:],
            ]
        }
    )

    assert corpus_fingerprint(corpus) != corpus_fingerprint(changed)


def test_document_fingerprint_detects_source_order_change() -> None:
    corpus = build_core_corpus()

    document = next(
        item
        for item in corpus.documents
        if any(len(block.source_fact_ids) > 1 for block in item.evidence)
    )

    block_index = next(
        index for index, block in enumerate(document.evidence) if len(block.source_fact_ids) > 1
    )

    block = document.evidence[block_index]

    changed_block = block.model_copy(
        update={"source_fact_ids": list(reversed(block.source_fact_ids))}
    )

    changed_evidence = list(document.evidence)

    changed_evidence[block_index] = changed_block

    changed_document = document.model_copy(update={"evidence": changed_evidence})

    changed_documents = [
        changed_document if item.document_id == document.document_id else item
        for item in corpus.documents
    ]

    changed = corpus.model_copy(update={"documents": changed_documents})

    assert corpus_fingerprint(corpus) != corpus_fingerprint(changed)


def test_normalized_payload_preserves_evidence_order() -> None:
    corpus = build_core_corpus()

    payload = normalized_corpus_payload(corpus)

    source_documents = {document.document_id: document for document in corpus.documents}

    for document_payload in payload["documents"]:
        source = source_documents[document_payload["document_id"]]

        assert [block["evidence_id"] for block in document_payload["evidence"]] == [
            block.evidence_id for block in source.evidence
        ]
