import hashlib
from collections.abc import Mapping
from typing import Literal

from enterprise_genai.data.chunk_models import (
    ChunkCorpus,
    RetrievalChunk,
)
from enterprise_genai.data.document_models import (
    DocumentCorpus,
)

LexicalRepresentationVersion = Literal[
    "text-only-v1",
    "company-text-v1",
    "document-title-text-v1",
    "evidence-heading-text-v1",
    "document-context-text-v1",
]

LEXICAL_REPRESENTATION_VERSIONS: tuple[
    LexicalRepresentationVersion,
    ...,
] = (
    "text-only-v1",
    "company-text-v1",
    "document-title-text-v1",
    "evidence-heading-text-v1",
    "document-context-text-v1",
)


def _join_representation_parts(
    *parts: str,
) -> str:
    cleaned = [part.strip() for part in parts if part.strip()]

    return "\n".join(cleaned)


def _replace_index_text(
    chunk: RetrievalChunk,
    index_text: str,
) -> RetrievalChunk:
    """Create an ephemeral lexical index representation.

    Retrieval identity and provenance remain unchanged.
    Only the text presented to the lexical ranker changes.
    """

    return chunk.model_copy(
        update={
            "text": index_text,
            "text_sha256": hashlib.sha256(index_text.encode("utf-8")).hexdigest(),
            "character_count": len(index_text),
            "word_count": len(index_text.split()),
        }
    )


def build_lexical_index_corpus(
    chunks: ChunkCorpus,
    documents: DocumentCorpus,
    company_names: Mapping[str, str],
    *,
    representation_version: (LexicalRepresentationVersion),
) -> ChunkCorpus:
    """Build a deterministic ephemeral lexical index corpus."""

    if chunks.dataset_version != documents.dataset_version:
        raise ValueError("Chunk and document dataset versions do not match.")

    documents_by_id = {document.document_id: document for document in documents.documents}

    evidence_by_document = {
        document.document_id: {block.evidence_id: block for block in document.evidence}
        for document in documents.documents
    }

    represented_chunks: list[RetrievalChunk] = []

    for chunk in chunks.chunks:
        document = documents_by_id.get(chunk.document_id)

        if document is None:
            raise ValueError(f"Chunk references unknown document {chunk.document_id}.")

        evidence = evidence_by_document[document.document_id].get(chunk.evidence_id)

        if evidence is None:
            raise ValueError(
                "Chunk references evidence that "
                "does not belong to its document: "
                f"{chunk.evidence_id}."
            )

        if representation_version == ("text-only-v1"):
            index_text = chunk.text

        elif representation_version == ("company-text-v1"):
            company_name = company_names.get(document.company_id)

            if company_name is None:
                raise ValueError(
                    "Document references company "
                    "without a lexical display name: "
                    f"{document.company_id}."
                )

            index_text = _join_representation_parts(
                company_name,
                chunk.text,
            )

        elif representation_version == ("document-title-text-v1"):
            index_text = _join_representation_parts(
                document.title,
                chunk.text,
            )

        elif representation_version == ("evidence-heading-text-v1"):
            index_text = _join_representation_parts(
                evidence.heading,
                chunk.text,
            )

        elif representation_version == ("document-context-text-v1"):
            index_text = _join_representation_parts(
                document.title,
                evidence.heading,
                chunk.text,
            )

        else:
            raise ValueError(f"Unknown lexical representation {representation_version!r}.")

        represented_chunks.append(
            _replace_index_text(
                chunk,
                index_text,
            )
        )

    return ChunkCorpus(
        dataset_version=(chunks.dataset_version),
        strategy_version=(chunks.strategy_version),
        chunks=represented_chunks,
    )
