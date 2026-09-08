import hashlib

import numpy as np
import pytest

from enterprise_genai.data.chunk_models import (
    RetrievalChunk,
)
from enterprise_genai.retrieval.dense import (
    DenseConfig,
    DenseIndex,
)


class FakeEncoder:
    embedding_dimension = 2

    @property
    def metadata(self):
        return {
            "model_id": "fake",
        }

    def encode_passages(
        self,
        texts,
    ):
        mapping = {
            "alpha": np.array(
                [1.0, 0.0],
                dtype=np.float32,
            ),
            "beta": np.array(
                [0.0, 1.0],
                dtype=np.float32,
            ),
            "gamma": np.array(
                [0.0, 1.0],
                dtype=np.float32,
            ),
        }

        return np.stack([mapping[text] for text in texts])

    def encode_queries(
        self,
        texts,
    ):
        mapping = {
            "find alpha": np.array(
                [1.0, 0.0],
                dtype=np.float32,
            ),
            "find vertical": np.array(
                [0.0, 1.0],
                dtype=np.float32,
            ),
        }

        return np.stack([mapping[text] for text in texts])


def _chunk(
    chunk_id: str,
    text: str,
) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id=(f"DOC-{chunk_id}"),
        evidence_id=(f"EVID-{chunk_id}"),
        chunk_ordinal=0,
        strategy_version="test-v1",
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        character_count=len(text),
        word_count=len(text.split()),
        source_fact_ids=[f"FACT-{chunk_id}"],
    )


def test_dense_config_requires_positive_batch_size() -> None:
    with pytest.raises(
        ValueError,
        match="batch_size",
    ):
        DenseConfig(batch_size=0)


def test_dense_index_requires_chunks() -> None:
    with pytest.raises(
        ValueError,
        match="at least one chunk",
    ):
        DenseIndex(
            [],
            encoder=FakeEncoder(),
        )


def test_dense_search_ranks_by_inner_product() -> None:
    index = DenseIndex(
        [
            _chunk(
                "CHK-B",
                "beta",
            ),
            _chunk(
                "CHK-A",
                "alpha",
            ),
        ],
        encoder=FakeEncoder(),
    )

    results = index.search("find alpha")

    assert [result.chunk_id for result in results] == [
        "CHK-A",
        "CHK-B",
    ]

    assert results[0].rank == 1

    assert results[0].score == (pytest.approx(1.0))

    assert results[0].evidence_id == "EVID-CHK-A"

    assert results[0].source_fact_ids == ("FACT-CHK-A",)


def test_dense_search_uses_stable_chunk_id_tiebreak() -> None:
    index = DenseIndex(
        [
            _chunk(
                "CHK-C",
                "gamma",
            ),
            _chunk(
                "CHK-B",
                "beta",
            ),
        ],
        encoder=FakeEncoder(),
    )

    results = index.search("find vertical")

    assert [result.chunk_id for result in results] == [
        "CHK-B",
        "CHK-C",
    ]


def test_dense_search_validates_top_k() -> None:
    index = DenseIndex(
        [
            _chunk(
                "CHK-A",
                "alpha",
            ),
        ],
        encoder=FakeEncoder(),
    )

    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        index.search(
            "find alpha",
            top_k=0,
        )


class NonNormalizedEncoder(FakeEncoder):
    def encode_passages(
        self,
        texts,
    ):
        return np.full(
            (
                len(texts),
                2,
            ),
            2.0,
            dtype=np.float32,
        )


def test_dense_index_rejects_non_normalized_embeddings() -> None:
    with pytest.raises(
        ValueError,
        match="L2 normalized",
    ):
        DenseIndex(
            [
                _chunk(
                    "CHK-A",
                    "alpha",
                ),
            ],
            encoder=(NonNormalizedEncoder()),
        )


class WrongDimensionEncoder(FakeEncoder):
    embedding_dimension = 3

    def encode_passages(
        self,
        texts,
    ):
        return np.ones(
            (
                len(texts),
                2,
            ),
            dtype=np.float32,
        )


def test_dense_index_rejects_wrong_dimension() -> None:
    with pytest.raises(
        ValueError,
        match="shape",
    ):
        DenseIndex(
            [
                _chunk(
                    "CHK-A",
                    "alpha",
                ),
            ],
            encoder=(WrongDimensionEncoder()),
        )


def test_dense_search_empty_query_returns_no_results() -> None:
    index = DenseIndex(
        [
            _chunk(
                "CHK-A",
                "alpha",
            ),
        ],
        encoder=FakeEncoder(),
    )

    assert index.search("   ") == []


def test_dense_config_requires_representation_version() -> None:
    with pytest.raises(
        ValueError,
        match="representation_version",
    ):
        DenseConfig(representation_version="   ")
