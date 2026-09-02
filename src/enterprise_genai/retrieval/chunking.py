import hashlib

from enterprise_genai.data.chunk_models import (
    ChunkCorpus,
    RetrievalChunk,
)
from enterprise_genai.data.document_models import (
    DocumentCorpus,
)

EVIDENCE_BLOCK_STRATEGY = "evidence-block-v1"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_id_for(
    *,
    dataset_version: str,
    document_id: str,
    evidence_id: str,
    chunk_ordinal: int,
    strategy_version: str,
) -> str:
    identity = "\x1f".join(
        [
            dataset_version,
            document_id,
            evidence_id,
            str(chunk_ordinal),
            strategy_version,
        ]
    )

    return f"CHK-{_sha256(identity)}"


def build_evidence_chunks(
    corpus: DocumentCorpus,
    *,
    strategy_version: str = EVIDENCE_BLOCK_STRATEGY,
) -> ChunkCorpus:
    """Create one deterministic retrieval chunk per evidence block."""

    chunks: list[RetrievalChunk] = []

    for document in sorted(
        corpus.documents,
        key=lambda item: item.document_id,
    ):
        for block in document.evidence:
            text = block.text

            chunks.append(
                RetrievalChunk(
                    chunk_id=chunk_id_for(
                        dataset_version=(corpus.dataset_version),
                        document_id=(document.document_id),
                        evidence_id=(block.evidence_id),
                        chunk_ordinal=0,
                        strategy_version=(strategy_version),
                    ),
                    document_id=(document.document_id),
                    evidence_id=block.evidence_id,
                    chunk_ordinal=0,
                    strategy_version=(strategy_version),
                    text=text,
                    text_sha256=_sha256(text),
                    character_count=len(text),
                    word_count=len(text.split()),
                    source_fact_ids=list(block.source_fact_ids),
                )
            )

    return ChunkCorpus(
        dataset_version=corpus.dataset_version,
        strategy_version=strategy_version,
        chunks=chunks,
    )
