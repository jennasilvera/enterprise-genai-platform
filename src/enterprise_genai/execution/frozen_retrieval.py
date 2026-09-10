from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Protocol

from sqlalchemy.orm import Session

from enterprise_genai.data.chunk_models import (
    ChunkCorpus,
    RetrievalChunk,
)
from enterprise_genai.data.document_models import (
    DocumentCorpus,
)
from enterprise_genai.db.chunk_ingestion import (
    load_chunk_corpus,
)
from enterprise_genai.db.document_ingestion import (
    load_document_corpus,
)
from enterprise_genai.execution.contracts import (
    RetrievalHit,
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.retrieval.bm25 import (
    BM25Config,
    BM25Index,
    BM25SearchResult,
)
from enterprise_genai.retrieval.chunking import (
    EVIDENCE_BLOCK_STRATEGY,
)
from enterprise_genai.retrieval.dense import (
    DENSE_VERSION,
    EMBEDDING_DIMENSION,
    MODEL_ID,
    MODEL_REVISION,
    DenseConfig,
    DenseEncoder,
    DenseEncoderProtocol,
    DenseIndex,
    DenseSearchResult,
)
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
    build_dense_index_corpus,
)
from enterprise_genai.retrieval.lexical_representation import (
    build_lexical_index_corpus,
)
from enterprise_genai.retrieval.rrf import (
    RRF_K,
    RRF_VERSION,
    RRFConfig,
    fuse_ranked_results,
)

FROZEN_LEXICAL_REPRESENTATION = "document-title-text-v1"

FROZEN_DENSE_REPRESENTATION = DENSE_DOCUMENT_TITLE_TEXT_VERSION

FROZEN_RETRIEVER_VERSION = f"hybrid:{RRF_VERSION}"

FROZEN_BATCH_SIZE = 16
FROZEN_DEVICE = "cpu"


class _BM25IndexProtocol(Protocol):
    config: BM25Config
    chunks: tuple[
        RetrievalChunk,
        ...,
    ]

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
    ) -> list[BM25SearchResult]: ...


class _DenseIndexProtocol(Protocol):
    encoder: DenseEncoderProtocol
    chunks: tuple[
        RetrievalChunk,
        ...,
    ]

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
    ) -> list[DenseSearchResult]: ...


def _chunk_identity(
    chunk: RetrievalChunk,
) -> tuple[
    str,
    str,
    str,
    tuple[str, ...],
]:
    return (
        chunk.chunk_id,
        chunk.document_id,
        chunk.evidence_id,
        tuple(chunk.source_fact_ids),
    )


class FrozenHybridRetrievalExecutor:
    """Runtime adapter for the frozen Phase 6A RRF retriever."""

    def __init__(
        self,
        *,
        dataset_version: str,
        bm25_index: _BM25IndexProtocol,
        dense_index: _DenseIndexProtocol,
        clock: Callable[
            [],
            float,
        ] = perf_counter,
    ) -> None:
        self.dataset_version = dataset_version
        self._bm25_index = bm25_index
        self._dense_index = dense_index
        self._clock = clock

        self._validate_frozen_stack()

    @property
    def metadata(
        self,
    ) -> dict[
        str,
        object,
    ]:
        return {
            "retriever_version": (FROZEN_RETRIEVER_VERSION),
            "lexical_representation": (FROZEN_LEXICAL_REPRESENTATION),
            "bm25_k1": (self._bm25_index.config.k1),
            "bm25_b": (self._bm25_index.config.b),
            "dense_version": (DENSE_VERSION),
            "dense_representation": (FROZEN_DENSE_REPRESENTATION),
            "model_id": MODEL_ID,
            "model_revision": (MODEL_REVISION),
            "embedding_dimension": (EMBEDDING_DIMENSION),
            "batch_size": (FROZEN_BATCH_SIZE),
            "device": FROZEN_DEVICE,
            "rrf_k": RRF_K,
            "chunks": len(self._dense_index.chunks),
        }

    def _validate_frozen_stack(
        self,
    ) -> None:
        expected_bm25 = BM25Config(
            k1=1.5,
            b=0.75,
        )

        if self._bm25_index.config != expected_bm25:
            raise ValueError("Retrieval executor requires frozen BM25 k1=1.5, b=0.75.")

        lexical_identities = tuple(_chunk_identity(chunk) for chunk in (self._bm25_index.chunks))

        dense_identities = tuple(_chunk_identity(chunk) for chunk in (self._dense_index.chunks))

        if lexical_identities != dense_identities:
            raise ValueError(
                "Frozen lexical and dense "
                "indices must contain identical "
                "chunk identities and provenance."
            )

        if not lexical_identities:
            raise ValueError("Frozen retrieval corpus must not be empty.")

        encoder = self._dense_index.encoder

        metadata = encoder.metadata

        required_metadata = {
            "dense_version": (DENSE_VERSION),
            "representation_version": (FROZEN_DENSE_REPRESENTATION),
            "model_id": MODEL_ID,
            "model_revision": (MODEL_REVISION),
            "embedding_dimension": (EMBEDDING_DIMENSION),
            "device": FROZEN_DEVICE,
            "batch_size": (FROZEN_BATCH_SIZE),
        }

        for (
            key,
            expected,
        ) in required_metadata.items():
            observed = metadata.get(key)

            if observed != expected:
                raise ValueError(
                    "Frozen dense metadata "
                    "mismatch for "
                    f"{key!r}: expected "
                    f"{expected!r}, observed "
                    f"{observed!r}."
                )

        if encoder.embedding_dimension != EMBEDDING_DIMENSION:
            raise ValueError("Frozen dense encoder has unexpected embedding dimension.")

        if RRFConfig().k != RRF_K:
            raise RuntimeError("Frozen RRF configuration does not match RRF_K.")

    @classmethod
    def from_corpora(
        cls,
        *,
        chunks: ChunkCorpus,
        documents: DocumentCorpus,
        encoder: DenseEncoderProtocol,
        clock: Callable[
            [],
            float,
        ] = perf_counter,
    ) -> FrozenHybridRetrievalExecutor:
        if chunks.dataset_version != documents.dataset_version:
            raise ValueError("Chunk and document dataset versions do not match.")

        lexical_chunks = build_lexical_index_corpus(
            chunks,
            documents,
            {},
            representation_version=(FROZEN_LEXICAL_REPRESENTATION),
        )

        dense_chunks = build_dense_index_corpus(
            chunks,
            documents,
            representation_version=(FROZEN_DENSE_REPRESENTATION),
        )

        bm25_index = BM25Index(
            lexical_chunks.chunks,
            config=BM25Config(
                k1=1.5,
                b=0.75,
            ),
        )

        dense_index = DenseIndex(
            dense_chunks.chunks,
            encoder=encoder,
        )

        return cls(
            dataset_version=(chunks.dataset_version),
            bm25_index=bm25_index,
            dense_index=dense_index,
            clock=clock,
        )

    @classmethod
    def from_persisted_corpus(
        cls,
        session: Session,
        dataset_version: str,
        *,
        encoder: (DenseEncoderProtocol | None) = None,
        clock: Callable[
            [],
            float,
        ] = perf_counter,
    ) -> FrozenHybridRetrievalExecutor:
        documents = load_document_corpus(
            session,
            dataset_version,
        )

        chunks = load_chunk_corpus(
            session,
            dataset_version,
            EVIDENCE_BLOCK_STRATEGY,
        )

        effective_encoder = encoder

        if effective_encoder is None:
            effective_encoder = DenseEncoder(
                config=DenseConfig(
                    batch_size=(FROZEN_BATCH_SIZE),
                    device=(FROZEN_DEVICE),
                    representation_version=(FROZEN_DENSE_REPRESENTATION),
                )
            )

        return cls.from_corpora(
            chunks=chunks,
            documents=documents,
            encoder=effective_encoder,
            clock=clock,
        )

    def _duration_ms(
        self,
        started_at: float,
    ) -> float:
        return max(
            0.0,
            (self._clock() - started_at) * 1000.0,
        )

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        """Execute frozen full-rank retrieval then truncate after RRF."""

        started_at = self._clock()

        if query.dataset_version != self.dataset_version:
            return ToolExecutionResult(
                tool="retrieval",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=("retrieval executor dataset version mismatch"),
            )

        try:
            # Phase 6A searched the complete
            # available BM25 and dense rankings.
            # Runtime top_k is applied only after
            # RRF so frozen ranking semantics are
            # not changed by candidate truncation.
            bm25_results = self._bm25_index.search(query.question)

            dense_results = self._dense_index.search(query.question)

            fused = fuse_ranked_results(
                bm25_results,
                dense_results,
                config=RRFConfig(),
                top_k=query.top_k,
            )

        except (
            OSError,
            RuntimeError,
            ValueError,
        ) as exc:
            return ToolExecutionResult(
                tool="retrieval",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=(f"frozen retrieval execution failed: {type(exc).__name__}"),
            )

        hits = tuple(
            RetrievalHit(
                rank=result.rank,
                chunk_id=(result.chunk_id),
                evidence_id=(result.evidence_id),
                document_id=(result.document_id),
                text=result.text,
                source_fact_ids=(result.source_fact_ids),
                rrf_score=(result.score),
                bm25_rank=(result.bm25_rank),
                dense_rank=(result.dense_rank),
            )
            for result in fused
        )

        return ToolExecutionResult(
            tool="retrieval",
            status=("ok" if hits else "empty"),
            payload=RetrievalPayload(hits=hits),
            duration_ms=(self._duration_ms(started_at)),
        )
