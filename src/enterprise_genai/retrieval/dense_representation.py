import hashlib

from enterprise_genai.data.chunk_models import (
    ChunkCorpus,
    RetrievalChunk,
)
from enterprise_genai.data.document_models import (
    DocumentCorpus,
)
from enterprise_genai.retrieval.dense import (
    DENSE_REPRESENTATION_VERSION,
)

DENSE_DOCUMENT_TITLE_TEXT_VERSION = "e5-document-title-text-v1"

SUPPORTED_DENSE_REPRESENTATIONS = {
    DENSE_REPRESENTATION_VERSION,
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
}


def build_dense_index_corpus(
    chunks: ChunkCorpus,
    documents: DocumentCorpus,
    *,
    representation_version: str,
) -> ChunkCorpus:
    if representation_version not in SUPPORTED_DENSE_REPRESENTATIONS:
        raise ValueError(f"Unsupported dense representation: {representation_version}.")

    documents_by_id = {document.document_id: document for document in documents.documents}

    missing_documents = sorted(
        {chunk.document_id for chunk in chunks.chunks if (chunk.document_id not in documents_by_id)}
    )

    if missing_documents:
        raise ValueError(
            f"Dense representation is missing documents for chunk IDs: {missing_documents}"
        )

    represented_chunks: list[RetrievalChunk] = []

    for chunk in chunks.chunks:
        document = documents_by_id[chunk.document_id]

        if representation_version == DENSE_REPRESENTATION_VERSION:
            text = chunk.text
        else:
            text = f"{document.title}\n{chunk.text}"

        represented_chunks.append(
            RetrievalChunk(
                chunk_id=chunk.chunk_id,
                document_id=(chunk.document_id),
                evidence_id=(chunk.evidence_id),
                chunk_ordinal=(chunk.chunk_ordinal),
                strategy_version=(chunk.strategy_version),
                text=text,
                text_sha256=(hashlib.sha256(text.encode("utf-8")).hexdigest()),
                character_count=len(text),
                word_count=len(text.split()),
                source_fact_ids=list(chunk.source_fact_ids),
            )
        )

    return ChunkCorpus(
        dataset_version=(chunks.dataset_version),
        strategy_version=(chunks.strategy_version),
        chunks=represented_chunks,
    )
