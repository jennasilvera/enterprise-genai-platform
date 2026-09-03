from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.data.universe import (
    build_universe,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)
from enterprise_genai.retrieval.lexical_representation import (
    build_lexical_index_corpus,
)


def _inputs():
    documents = build_core_corpus()

    chunks = build_evidence_chunks(documents)

    universe = build_universe()

    company_names = {company.company_id: company.name for company in universe.companies}

    return (
        documents,
        chunks,
        company_names,
    )


def test_text_only_preserves_index_text() -> None:
    documents, chunks, names = _inputs()

    represented = build_lexical_index_corpus(
        chunks,
        documents,
        names,
        representation_version=("text-only-v1"),
    )

    assert [chunk.text for chunk in represented.chunks] == [chunk.text for chunk in chunks.chunks]


def test_text_only_preserves_text_hash() -> None:
    documents, chunks, names = _inputs()

    represented = build_lexical_index_corpus(
        chunks,
        documents,
        names,
        representation_version=("text-only-v1"),
    )

    assert [chunk.text_sha256 for chunk in represented.chunks] == [
        chunk.text_sha256 for chunk in chunks.chunks
    ]


def test_company_text_adds_company_name() -> None:
    documents, chunks, names = _inputs()

    represented = build_lexical_index_corpus(
        chunks,
        documents,
        names,
        representation_version=("company-text-v1"),
    )

    documents_by_id = {document.document_id: document for document in documents.documents}

    first_source = chunks.chunks[0]
    first_indexed = represented.chunks[0]

    company_id = documents_by_id[first_source.document_id].company_id

    assert first_indexed.text == (f"{names[company_id]}\n{first_source.text}")


def test_document_context_uses_title_heading_text() -> None:
    documents, chunks, names = _inputs()

    represented = build_lexical_index_corpus(
        chunks,
        documents,
        names,
        representation_version=("document-context-text-v1"),
    )

    documents_by_id = {document.document_id: document for document in documents.documents}

    first_source = chunks.chunks[0]
    first_indexed = represented.chunks[0]

    document = documents_by_id[first_source.document_id]

    evidence = next(
        block for block in document.evidence if (block.evidence_id == first_source.evidence_id)
    )

    assert first_indexed.text == (f"{document.title}\n{evidence.heading}\n{first_source.text}")


def test_representation_preserves_identity_and_provenance() -> None:
    documents, chunks, names = _inputs()

    represented = build_lexical_index_corpus(
        chunks,
        documents,
        names,
        representation_version=("company-text-v1"),
    )

    for source, indexed in zip(
        chunks.chunks,
        represented.chunks,
        strict=True,
    ):
        assert indexed.chunk_id == (source.chunk_id)
        assert indexed.document_id == (source.document_id)
        assert indexed.evidence_id == (source.evidence_id)
        assert indexed.source_fact_ids == source.source_fact_ids


def test_missing_company_name_is_rejected() -> None:
    documents, chunks, _ = _inputs()

    try:
        build_lexical_index_corpus(
            chunks,
            documents,
            {},
            representation_version=("company-text-v1"),
        )
    except ValueError as exc:
        assert "without a lexical display name" in str(exc)
    else:
        raise AssertionError("Missing company name was accepted.")


def test_document_title_text_uses_title_and_text() -> None:
    documents, chunks, names = _inputs()

    represented = build_lexical_index_corpus(
        chunks,
        documents,
        names,
        representation_version=("document-title-text-v1"),
    )

    documents_by_id = {document.document_id: document for document in documents.documents}

    source = chunks.chunks[0]
    indexed = represented.chunks[0]

    document = documents_by_id[source.document_id]

    assert indexed.text == (f"{document.title}\n{source.text}")


def test_evidence_heading_text_uses_heading_and_text() -> None:
    documents, chunks, names = _inputs()

    represented = build_lexical_index_corpus(
        chunks,
        documents,
        names,
        representation_version=("evidence-heading-text-v1"),
    )

    documents_by_id = {document.document_id: document for document in documents.documents}

    source = chunks.chunks[0]

    document = documents_by_id[source.document_id]

    evidence = next(
        block for block in document.evidence if (block.evidence_id == source.evidence_id)
    )

    indexed = represented.chunks[0]

    assert indexed.text == (f"{evidence.heading}\n{source.text}")
