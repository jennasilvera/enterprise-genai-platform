import hashlib

import pytest

from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)
from enterprise_genai.retrieval.dense import (
    DENSE_REPRESENTATION_VERSION,
)
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
    build_dense_index_corpus,
)


def _inputs():
    documents = build_core_corpus()

    chunks = build_evidence_chunks(documents)

    return documents, chunks


def test_dense_evidence_text_representation_preserves_text() -> None:
    documents, chunks = _inputs()

    represented = build_dense_index_corpus(
        chunks,
        documents,
        representation_version=(DENSE_REPRESENTATION_VERSION),
    )

    assert len(represented.chunks) == 80

    original_by_id = {chunk.chunk_id: chunk for chunk in chunks.chunks}

    for chunk in represented.chunks:
        original = original_by_id[chunk.chunk_id]

        assert chunk.text == original.text

        assert chunk.text_sha256 == original.text_sha256

        assert chunk.source_fact_ids == original.source_fact_ids


def test_dense_title_representation_changes_only_index_text() -> None:
    documents, chunks = _inputs()

    represented = build_dense_index_corpus(
        chunks,
        documents,
        representation_version=(DENSE_DOCUMENT_TITLE_TEXT_VERSION),
    )

    documents_by_id = {document.document_id: document for document in documents.documents}

    original_by_id = {chunk.chunk_id: chunk for chunk in chunks.chunks}

    for chunk in represented.chunks:
        original = original_by_id[chunk.chunk_id]

        document = documents_by_id[chunk.document_id]

        expected_text = f"{document.title}\n{original.text}"

        assert chunk.text == expected_text

        assert chunk.text_sha256 == hashlib.sha256(expected_text.encode("utf-8")).hexdigest()

        assert chunk.chunk_id == original.chunk_id

        assert chunk.document_id == original.document_id

        assert chunk.evidence_id == original.evidence_id

        assert chunk.chunk_ordinal == original.chunk_ordinal

        assert chunk.strategy_version == original.strategy_version

        assert chunk.source_fact_ids == original.source_fact_ids


def test_dense_representation_rejects_unknown_version() -> None:
    documents, chunks = _inputs()

    with pytest.raises(
        ValueError,
        match="Unsupported dense representation",
    ):
        build_dense_index_corpus(
            chunks,
            documents,
            representation_version=("unknown-dense-representation"),
        )
