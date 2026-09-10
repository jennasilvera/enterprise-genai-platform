import hashlib

import numpy as np
import pytest

from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.execution.contracts import (
    RetrievalPayload,
    RetrievalQuery,
)
from enterprise_genai.execution.frozen_retrieval import (
    FROZEN_BATCH_SIZE,
    FROZEN_DENSE_REPRESENTATION,
    FROZEN_DEVICE,
    FROZEN_LEXICAL_REPRESENTATION,
    FROZEN_RETRIEVER_VERSION,
    FrozenHybridRetrievalExecutor,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)
from enterprise_genai.retrieval.dense import (
    DENSE_VERSION,
    EMBEDDING_DIMENSION,
    MODEL_ID,
    MODEL_REVISION,
)


class FrozenTestEncoder:
    embedding_dimension = EMBEDDING_DIMENSION

    @property
    def metadata(
        self,
    ) -> dict[
        str,
        object,
    ]:
        return {
            "dense_version": (DENSE_VERSION),
            "representation_version": (FROZEN_DENSE_REPRESENTATION),
            "model_id": MODEL_ID,
            "model_revision": (MODEL_REVISION),
            "embedding_dimension": (EMBEDDING_DIMENSION),
            "device": (FROZEN_DEVICE),
            "batch_size": (FROZEN_BATCH_SIZE),
        }

    def _encode(
        self,
        texts: list[str],
    ) -> np.ndarray:
        if not texts:
            return np.empty(
                (
                    0,
                    EMBEDDING_DIMENSION,
                ),
                dtype=np.float32,
            )

        vectors: list[np.ndarray] = []

        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()

            base = np.frombuffer(
                digest,
                dtype=np.uint8,
            ).astype(np.float32)

            vector = np.resize(
                base,
                EMBEDDING_DIMENSION,
            ).astype(np.float32)

            vector += 1.0

            vector /= np.linalg.norm(vector)

            vectors.append(vector)

        return np.stack(vectors).astype(np.float32)

    def encode_passages(
        self,
        texts: list[str],
    ) -> np.ndarray:
        return self._encode(texts)

    def encode_queries(
        self,
        texts: list[str],
    ) -> np.ndarray:
        return self._encode(texts)


class WrongRepresentationEncoder(FrozenTestEncoder):
    @property
    def metadata(
        self,
    ) -> dict[
        str,
        object,
    ]:
        metadata = dict(super().metadata)

        metadata["representation_version"] = "e5-evidence-text-v1"

        return metadata


def _executor() -> FrozenHybridRetrievalExecutor:
    documents = build_core_corpus()

    chunks = build_evidence_chunks(documents)

    return FrozenHybridRetrievalExecutor.from_corpora(
        chunks=chunks,
        documents=documents,
        encoder=(FrozenTestEncoder()),
    )


def test_frozen_retrieval_metadata_is_exact() -> None:
    executor = _executor()

    metadata = executor.metadata

    assert metadata["retriever_version"] == FROZEN_RETRIEVER_VERSION == "hybrid:rrf-k60-v1"

    assert (
        metadata["lexical_representation"]
        == FROZEN_LEXICAL_REPRESENTATION
        == "document-title-text-v1"
    )

    assert (
        metadata["dense_representation"]
        == FROZEN_DENSE_REPRESENTATION
        == "e5-document-title-text-v1"
    )

    assert metadata["model_id"] == "intfloat/e5-small-v2"

    assert metadata["model_revision"] == ("ffb93f3bd4047442299a41ebb6fa998a38507c52")

    assert metadata["rrf_k"] == 60

    assert metadata["chunks"] == 80


def test_retrieval_maps_rank_content_and_fact_provenance() -> None:
    result = _executor().execute(
        RetrievalQuery(
            question="ORBIS-IDX-7",
            top_k=5,
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        RetrievalPayload,
    )

    assert len(result.payload.hits) == 5

    assert [hit.rank for hit in (result.payload.hits)] == [
        1,
        2,
        3,
        4,
        5,
    ]

    for hit in result.payload.hits:
        assert hit.text
        assert hit.chunk_id
        assert hit.document_id
        assert hit.evidence_id
        assert hit.source_fact_ids
        assert hit.bm25_rank is not None or hit.dense_rank is not None


def test_runtime_top_k_is_prefix_of_larger_fused_result() -> None:
    executor = _executor()

    small = executor.execute(
        RetrievalQuery(
            question=("Alder supplier risk"),
            top_k=3,
        )
    )

    large = executor.execute(
        RetrievalQuery(
            question=("Alder supplier risk"),
            top_k=10,
        )
    )

    assert isinstance(
        small.payload,
        RetrievalPayload,
    )

    assert isinstance(
        large.payload,
        RetrievalPayload,
    )

    assert [hit.chunk_id for hit in (small.payload.hits)] == [
        hit.chunk_id for hit in (large.payload.hits[:3])
    ]


def test_wrong_dense_representation_is_rejected() -> None:
    documents = build_core_corpus()

    chunks = build_evidence_chunks(documents)

    with pytest.raises(
        ValueError,
        match=("representation_version"),
    ):
        FrozenHybridRetrievalExecutor.from_corpora(
            chunks=chunks,
            documents=documents,
            encoder=(WrongRepresentationEncoder()),
        )


def test_dataset_version_mismatch_returns_error_result() -> None:
    result = _executor().execute(
        RetrievalQuery(
            dataset_version=("northstar-v2"),
            question=("supplier concentration"),
        )
    )

    assert result.status == ("error")

    assert result.payload is None
    assert result.error is not None

    assert "dataset version mismatch" in result.error
