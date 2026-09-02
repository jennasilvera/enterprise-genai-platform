from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.db.chunk_ingestion import (
    chunk_corpus_fingerprint,
    expected_chunk_row_counts,
    normalized_chunk_payload,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)


def build_chunks():
    return build_evidence_chunks(build_core_corpus())


def test_expected_chunk_row_counts_are_80_and_186() -> None:
    assert expected_chunk_row_counts(build_chunks()) == {
        "chunks": 80,
        "chunk_source_facts": 186,
    }


def test_chunk_corpus_fingerprint_is_deterministic() -> None:
    assert chunk_corpus_fingerprint(build_chunks()) == chunk_corpus_fingerprint(build_chunks())


def test_chunk_fingerprint_ignores_top_level_order() -> None:
    corpus = build_chunks()

    reordered = corpus.model_copy(update={"chunks": list(reversed(corpus.chunks))})

    assert chunk_corpus_fingerprint(corpus) == chunk_corpus_fingerprint(reordered)


def test_chunk_fingerprint_detects_text_change() -> None:
    corpus = build_chunks()
    first = corpus.chunks[0]

    changed_chunk = first.model_copy(update={"text": (f"{first.text} changed")})

    changed = corpus.model_copy(
        update={
            "chunks": [
                changed_chunk,
                *corpus.chunks[1:],
            ]
        }
    )

    assert chunk_corpus_fingerprint(corpus) != chunk_corpus_fingerprint(changed)


def test_chunk_fingerprint_detects_source_order_change() -> None:
    corpus = build_chunks()

    index = next(
        index for index, chunk in enumerate(corpus.chunks) if len(chunk.source_fact_ids) > 1
    )

    original = corpus.chunks[index]

    changed_chunk = original.model_copy(
        update={"source_fact_ids": list(reversed(original.source_fact_ids))}
    )

    changed_chunks = list(corpus.chunks)
    changed_chunks[index] = changed_chunk

    changed = corpus.model_copy(update={"chunks": changed_chunks})

    assert chunk_corpus_fingerprint(corpus) != chunk_corpus_fingerprint(changed)


def test_normalized_payload_sorts_chunks_by_id() -> None:
    payload = normalized_chunk_payload(build_chunks())

    chunk_ids = [chunk["chunk_id"] for chunk in payload["chunks"]]

    assert chunk_ids == sorted(chunk_ids)


def test_strategy_version_changes_chunk_snapshot() -> None:
    source = build_core_corpus()

    first = build_evidence_chunks(
        source,
        strategy_version="evidence-block-v1",
    )

    second = build_evidence_chunks(
        source,
        strategy_version="evidence-block-v2",
    )

    assert chunk_corpus_fingerprint(first) != chunk_corpus_fingerprint(second)
