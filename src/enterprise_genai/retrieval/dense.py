from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from typing import Protocol

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from enterprise_genai.data.chunk_models import (
    RetrievalChunk,
)

DENSE_VERSION = "dense-e5-small-v2-v1"

DENSE_REPRESENTATION_VERSION = "e5-evidence-text-v1"

MODEL_ID = "intfloat/e5-small-v2"

MODEL_REVISION = "ffb93f3bd4047442299a41ebb6fa998a38507c52"

EMBEDDING_DIMENSION = 384

QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "


@dataclass(frozen=True)
class DenseConfig:
    batch_size: int = 16
    device: str = "cpu"
    representation_version: str = DENSE_REPRESENTATION_VERSION

    def __post_init__(self) -> None:
        if self.batch_size <= 0:
            raise ValueError("Dense batch_size must be positive.")

        if not self.device.strip():
            raise ValueError("Dense device must be non-empty.")

        if not self.representation_version.strip():
            raise ValueError("Dense representation_version must be non-empty.")


@dataclass(frozen=True)
class DenseSearchResult:
    rank: int
    score: float
    chunk_id: str
    document_id: str
    evidence_id: str
    text: str
    source_fact_ids: tuple[str, ...]


class DenseEncoderProtocol(Protocol):
    @property
    def embedding_dimension(self) -> int: ...

    @property
    def metadata(self) -> dict[str, object]: ...

    def encode_passages(
        self,
        texts: list[str],
    ) -> np.ndarray: ...

    def encode_queries(
        self,
        texts: list[str],
    ) -> np.ndarray: ...


class DenseEncoder:
    """Pinned E5 encoder for asymmetric query/passage retrieval."""

    def __init__(
        self,
        *,
        config: DenseConfig | None = None,
    ) -> None:
        self.config = config or DenseConfig()

        self._model = SentenceTransformer(
            MODEL_ID,
            revision=MODEL_REVISION,
            device=self.config.device,
        )

        self._model.eval()

        dimension = self._model.get_embedding_dimension()

        if dimension is None:
            raise ValueError("Embedding model did not expose an embedding dimension.")

        self._embedding_dimension = int(dimension)

        if self._embedding_dimension != EMBEDDING_DIMENSION:
            raise ValueError(f"Unexpected E5 embedding dimension: {self._embedding_dimension}.")

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "dense_version": DENSE_VERSION,
            "representation_version": (self.config.representation_version),
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "embedding_dimension": (self.embedding_dimension),
            "max_sequence_length": (self._model.max_seq_length),
            "query_prefix": QUERY_PREFIX,
            "passage_prefix": PASSAGE_PREFIX,
            "normalize_embeddings": True,
            "similarity": ("inner_product_of_l2_normalized_vectors"),
            "device": self.config.device,
            "batch_size": (self.config.batch_size),
            "numpy_version": version("numpy"),
            "torch_version": version("torch"),
            "transformers_version": version("transformers"),
            "sentence_transformers_version": (version("sentence-transformers")),
        }

    def _encode(
        self,
        texts: list[str],
        *,
        prefix: str,
    ) -> np.ndarray:
        if not texts:
            return np.empty(
                (
                    0,
                    self.embedding_dimension,
                ),
                dtype=np.float32,
            )

        prefixed = [f"{prefix}{text}" for text in texts]

        with torch.inference_mode():
            embeddings = self._model.encode(
                prefixed,
                batch_size=(self.config.batch_size),
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

        matrix = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        self._validate_matrix(
            matrix,
            expected_rows=len(texts),
        )

        return matrix

    def _validate_matrix(
        self,
        matrix: np.ndarray,
        *,
        expected_rows: int,
    ) -> None:
        expected_shape = (
            expected_rows,
            self.embedding_dimension,
        )

        if matrix.shape != expected_shape:
            raise ValueError(
                f"Unexpected embedding shape: {matrix.shape}; expected {expected_shape}."
            )

        if not np.isfinite(matrix).all():
            raise ValueError("Embedding matrix contains non-finite values.")

        norms = np.linalg.norm(
            matrix,
            axis=1,
        )

        if not np.allclose(
            norms,
            1.0,
            atol=1e-5,
            rtol=1e-5,
        ):
            raise ValueError("Dense embeddings must be L2 normalized.")

    def encode_passages(
        self,
        texts: list[str],
    ) -> np.ndarray:
        return self._encode(
            texts,
            prefix=PASSAGE_PREFIX,
        )

    def encode_queries(
        self,
        texts: list[str],
    ) -> np.ndarray:
        return self._encode(
            texts,
            prefix=QUERY_PREFIX,
        )


class DenseIndex:
    """Deterministic in-memory dense retrieval index."""

    def __init__(
        self,
        chunks: list[RetrievalChunk],
        *,
        encoder: DenseEncoderProtocol,
    ) -> None:
        if not chunks:
            raise ValueError("Dense retrieval requires at least one chunk.")

        if encoder.embedding_dimension <= 0:
            raise ValueError("Dense encoder dimension must be positive.")

        self.encoder = encoder

        self.chunks = tuple(
            sorted(
                chunks,
                key=lambda chunk: chunk.chunk_id,
            )
        )

        passages = [chunk.text for chunk in self.chunks]

        embeddings = self.encoder.encode_passages(passages)

        self.embeddings = self._validate_embeddings(
            embeddings,
            expected_rows=len(self.chunks),
        )

    def _validate_embeddings(
        self,
        embeddings: np.ndarray,
        *,
        expected_rows: int,
    ) -> np.ndarray:
        matrix = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        expected_shape = (
            expected_rows,
            self.encoder.embedding_dimension,
        )

        if matrix.shape != expected_shape:
            raise ValueError(
                f"Unexpected dense index shape: {matrix.shape}; expected {expected_shape}."
            )

        if not np.isfinite(matrix).all():
            raise ValueError("Dense index contains non-finite embeddings.")

        norms = np.linalg.norm(
            matrix,
            axis=1,
        )

        if not np.allclose(
            norms,
            1.0,
            atol=1e-5,
            rtol=1e-5,
        ):
            raise ValueError("Dense index embeddings must be L2 normalized.")

        return matrix

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
    ) -> list[DenseSearchResult]:
        if top_k is not None and top_k <= 0:
            raise ValueError("top_k must be positive.")

        if not query.strip():
            return []

        query_matrix = self.encoder.encode_queries([query])

        query_matrix = self._validate_embeddings(
            query_matrix,
            expected_rows=1,
        )

        query_embedding = query_matrix[0]

        scores = self.embeddings @ query_embedding

        scored = [
            (
                float(score),
                chunk,
            )
            for score, chunk in zip(
                scores,
                self.chunks,
                strict=True,
            )
        ]

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].chunk_id,
            )
        )

        if top_k is not None:
            scored = scored[:top_k]

        return [
            DenseSearchResult(
                rank=rank,
                score=score,
                chunk_id=chunk.chunk_id,
                document_id=(chunk.document_id),
                evidence_id=(chunk.evidence_id),
                text=chunk.text,
                source_fact_ids=tuple(chunk.source_fact_ids),
            )
            for rank, (
                score,
                chunk,
            ) in enumerate(
                scored,
                start=1,
            )
        ]
