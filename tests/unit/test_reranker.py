import numpy as np
import pytest

from enterprise_genai.retrieval.reranker import (
    CANDIDATE_K,
    RERANKER_REPRESENTATION_VERSION,
    RERANKER_VERSION,
    rerank_rrf_candidates,
)
from enterprise_genai.retrieval.rrf import (
    RRFSearchResult,
)


class FakeReranker:
    def __init__(
        self,
        scores: np.ndarray,
    ) -> None:
        self.scores = scores

    @property
    def metadata(
        self,
    ) -> dict[str, object]:
        return {
            "reranker_version": (RERANKER_VERSION),
            "representation_version": (RERANKER_REPRESENTATION_VERSION),
            "candidate_k": (CANDIDATE_K),
        }

    def score(
        self,
        query: str,
        passages: list[str],
    ) -> np.ndarray:
        return self.scores


def _results(
    count: int = 30,
) -> list[RRFSearchResult]:
    return [
        RRFSearchResult(
            rank=index,
            score=(1.0 / (60 + index)),
            chunk_id=(f"CHK-{index:03d}"),
            document_id=(f"DOC-{index:03d}"),
            evidence_id=(f"EVID-{index:03d}"),
            text=(f"Document {index}\nEvidence {index}"),
            source_fact_ids=(f"FACT-{index:03d}",),
            bm25_rank=index,
            dense_rank=index,
            bm25_score=float(count - index),
            dense_score=float(count - index),
            bm25_contribution=(1.0 / (60 + index)),
            dense_contribution=0.0,
        )
        for index in range(
            1,
            count + 1,
        )
    ]


def test_reranks_top_20_and_preserves_tail() -> None:
    original = _results()

    scores = np.arange(
        CANDIDATE_K,
        dtype=np.float32,
    )

    reranked = rerank_rrf_candidates(
        "query",
        original,
        reranker=FakeReranker(scores),
    )

    assert reranked[0].original_rrf_rank == CANDIDATE_K

    assert [result.chunk_id for result in reranked[CANDIDATE_K:]] == [
        result.chunk_id for result in original[CANDIDATE_K:]
    ]


def test_score_tie_preserves_original_rrf_order() -> None:
    original = _results()

    scores = np.ones(
        CANDIDATE_K,
        dtype=np.float32,
    )

    reranked = rerank_rrf_candidates(
        "query",
        original,
        reranker=FakeReranker(scores),
    )

    assert [result.original_rrf_rank for result in reranked[:CANDIDATE_K]] == list(
        range(
            1,
            CANDIDATE_K + 1,
        )
    )


def test_rejects_ranking_shorter_than_candidate_k() -> None:
    with pytest.raises(
        ValueError,
        match="candidate_k",
    ):
        rerank_rrf_candidates(
            "query",
            _results(CANDIDATE_K - 1),
            reranker=FakeReranker(
                np.zeros(
                    CANDIDATE_K,
                    dtype=np.float32,
                )
            ),
        )


def test_rejects_wrong_score_shape() -> None:
    with pytest.raises(
        ValueError,
        match="unexpected number",
    ):
        rerank_rrf_candidates(
            "query",
            _results(),
            reranker=FakeReranker(
                np.zeros(
                    CANDIDATE_K - 1,
                    dtype=np.float32,
                )
            ),
        )


def test_rejects_nonfinite_scores() -> None:
    scores = np.zeros(
        CANDIDATE_K,
        dtype=np.float32,
    )

    scores[3] = np.inf

    with pytest.raises(
        ValueError,
        match="non-finite",
    ):
        rerank_rrf_candidates(
            "query",
            _results(),
            reranker=FakeReranker(scores),
        )
