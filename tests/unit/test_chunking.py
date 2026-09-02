from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.retrieval.chunking import (
    EVIDENCE_BLOCK_STRATEGY,
    build_evidence_chunks,
    chunk_id_for,
)


def test_evidence_strategy_produces_80_chunks() -> None:
    chunk_corpus = build_evidence_chunks(build_core_corpus())

    assert len(chunk_corpus.chunks) == 80


def test_every_evidence_block_maps_to_one_chunk() -> None:
    corpus = build_core_corpus()

    chunk_corpus = build_evidence_chunks(corpus)

    evidence_ids = {
        block.evidence_id for document in corpus.documents for block in document.evidence
    }

    chunk_evidence_ids = [chunk.evidence_id for chunk in chunk_corpus.chunks]

    assert set(chunk_evidence_ids) == evidence_ids
    assert len(chunk_evidence_ids) == len(evidence_ids)


def test_chunk_ids_are_deterministic() -> None:
    first = build_evidence_chunks(build_core_corpus())

    second = build_evidence_chunks(build_core_corpus())

    assert [chunk.chunk_id for chunk in first.chunks] == [chunk.chunk_id for chunk in second.chunks]


def test_document_order_does_not_change_chunk_ids() -> None:
    corpus = build_core_corpus()

    reordered = corpus.model_copy(update={"documents": list(reversed(corpus.documents))})

    first = build_evidence_chunks(corpus)
    second = build_evidence_chunks(reordered)

    assert [chunk.chunk_id for chunk in first.chunks] == [chunk.chunk_id for chunk in second.chunks]


def test_chunk_preserves_evidence_text_and_provenance() -> None:
    corpus = build_core_corpus()
    chunks = build_evidence_chunks(corpus)

    evidence = {
        block.evidence_id: block for document in corpus.documents for block in document.evidence
    }

    for chunk in chunks.chunks:
        source = evidence[chunk.evidence_id]

        assert chunk.text == source.text
        assert chunk.source_fact_ids == source.source_fact_ids
        assert chunk.character_count == len(source.text)
        assert chunk.word_count == len(source.text.split())


def test_chunk_text_hashes_are_valid_sha256() -> None:
    chunks = build_evidence_chunks(build_core_corpus())

    for chunk in chunks.chunks:
        assert len(chunk.text_sha256) == 64
        assert all(character in "0123456789abcdef" for character in chunk.text_sha256)


def test_chunk_identity_changes_with_strategy_version() -> None:
    corpus = build_core_corpus()
    document = corpus.documents[0]
    evidence = document.evidence[0]

    first = chunk_id_for(
        dataset_version=corpus.dataset_version,
        document_id=document.document_id,
        evidence_id=evidence.evidence_id,
        chunk_ordinal=0,
        strategy_version=(EVIDENCE_BLOCK_STRATEGY),
    )

    second = chunk_id_for(
        dataset_version=corpus.dataset_version,
        document_id=document.document_id,
        evidence_id=evidence.evidence_id,
        chunk_ordinal=0,
        strategy_version="evidence-block-v2",
    )

    assert first != second
