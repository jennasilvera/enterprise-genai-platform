import pytest

from enterprise_genai.retrieval.bm25 import (
    BM25SearchResult,
)
from enterprise_genai.retrieval.dense import (
    DenseSearchResult,
)
from enterprise_genai.retrieval.rrf import (
    RRFConfig,
    fuse_ranked_results,
)


def _bm25(
    rank: int,
    chunk_id: str,
    *,
    evidence_id: str | None = None,
) -> BM25SearchResult:
    return BM25SearchResult(
        rank=rank,
        score=float(10 - rank),
        chunk_id=chunk_id,
        document_id="DOC-1",
        evidence_id=(evidence_id or f"E-{chunk_id}"),
        text=f"text {chunk_id}",
        source_fact_ids=(f"FACT-{chunk_id}",),
        matched_terms=("term",),
    )


def _dense(
    rank: int,
    chunk_id: str,
    *,
    evidence_id: str | None = None,
) -> DenseSearchResult:
    return DenseSearchResult(
        rank=rank,
        score=(1.0 / rank),
        chunk_id=chunk_id,
        document_id="DOC-1",
        evidence_id=(evidence_id or f"E-{chunk_id}"),
        text=f"text {chunk_id}",
        source_fact_ids=(f"FACT-{chunk_id}",),
    )


def test_rrf_config_requires_positive_k() -> None:
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        RRFConfig(k=0)


def test_rrf_combines_rank_contributions() -> None:
    results = fuse_ranked_results(
        [
            _bm25(1, "A"),
            _bm25(2, "B"),
        ],
        [
            _dense(1, "B"),
            _dense(2, "C"),
        ],
    )

    assert results[0].chunk_id == "B"

    assert results[0].score == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_missing_source_contributes_zero() -> None:
    results = fuse_ranked_results(
        [
            _bm25(1, "A"),
        ],
        [
            _dense(1, "B"),
        ],
    )

    by_id = {result.chunk_id: result for result in results}

    assert by_id["B"].bm25_rank is None

    assert by_id["B"].bm25_contribution == 0.0


def test_rrf_tie_breaks_by_chunk_id() -> None:
    results = fuse_ranked_results(
        [
            _bm25(1, "A"),
            _bm25(2, "B"),
        ],
        [
            _dense(1, "B"),
            _dense(2, "A"),
        ],
    )

    assert [result.chunk_id for result in results] == [
        "A",
        "B",
    ]

    assert results[0].score == results[1].score


def test_rrf_rejects_duplicate_source_chunks() -> None:
    with pytest.raises(
        ValueError,
        match="duplicate",
    ):
        fuse_ranked_results(
            [
                _bm25(1, "A"),
                _bm25(2, "A"),
            ],
            [],
        )


def test_rrf_rejects_identity_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="metadata differs",
    ):
        fuse_ranked_results(
            [
                _bm25(
                    1,
                    "A",
                    evidence_id="E-1",
                ),
            ],
            [
                _dense(
                    1,
                    "A",
                    evidence_id="E-2",
                ),
            ],
        )


def test_rrf_top_k_limits_output() -> None:
    results = fuse_ranked_results(
        [
            _bm25(1, "A"),
            _bm25(2, "B"),
        ],
        [
            _dense(1, "B"),
            _dense(2, "C"),
        ],
        top_k=2,
    )

    assert len(results) == 2

    assert [result.rank for result in results] == [
        1,
        2,
    ]
