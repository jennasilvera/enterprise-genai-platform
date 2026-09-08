from dataclasses import dataclass

from enterprise_genai.retrieval.bm25 import (
    BM25SearchResult,
)
from enterprise_genai.retrieval.dense import (
    DenseSearchResult,
)

RRF_VERSION = "rrf-k60-v1"
RRF_K = 60


@dataclass(frozen=True)
class RRFConfig:
    k: int = RRF_K

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError("RRF k must be positive.")


@dataclass(frozen=True)
class RRFSearchResult:
    rank: int
    score: float
    chunk_id: str
    document_id: str
    evidence_id: str
    text: str
    source_fact_ids: tuple[str, ...]
    bm25_rank: int | None
    dense_rank: int | None
    bm25_score: float | None
    dense_score: float | None
    bm25_contribution: float
    dense_contribution: float


def _validate_ranking(
    results: list[BM25SearchResult | DenseSearchResult],
    *,
    source_name: str,
) -> None:
    seen: set[str] = set()

    for expected_rank, result in enumerate(
        results,
        start=1,
    ):
        if result.rank != expected_rank:
            raise ValueError(f"{source_name} ranking is not contiguous from rank 1.")

        if result.chunk_id in seen:
            raise ValueError(f"{source_name} ranking contains duplicate chunk {result.chunk_id}.")

        seen.add(result.chunk_id)


def fuse_ranked_results(
    bm25_results: list[BM25SearchResult],
    dense_results: list[DenseSearchResult],
    *,
    config: RRFConfig | None = None,
    top_k: int | None = None,
) -> list[RRFSearchResult]:
    if top_k is not None and top_k <= 0:
        raise ValueError("top_k must be positive.")

    effective_config = config or RRFConfig()

    _validate_ranking(
        bm25_results,
        source_name="BM25",
    )

    _validate_ranking(
        dense_results,
        source_name="dense",
    )

    bm25_by_chunk = {result.chunk_id: result for result in bm25_results}

    dense_by_chunk = {result.chunk_id: result for result in dense_results}

    chunk_ids = sorted(set(bm25_by_chunk) | set(dense_by_chunk))

    scored: list[
        tuple[
            float,
            str,
            str,
            str,
            str,
            tuple[str, ...],
            int | None,
            int | None,
            float | None,
            float | None,
            float,
            float,
        ]
    ] = []

    for chunk_id in chunk_ids:
        bm25 = bm25_by_chunk.get(chunk_id)

        dense = dense_by_chunk.get(chunk_id)

        if bm25 is not None and dense is not None:
            bm25_identity = (
                bm25.document_id,
                bm25.evidence_id,
                bm25.source_fact_ids,
            )

            dense_identity = (
                dense.document_id,
                dense.evidence_id,
                dense.source_fact_ids,
            )

            if bm25_identity != dense_identity:
                raise ValueError(f"RRF source metadata differs for chunk {chunk_id}.")

        source = dense if dense is not None else bm25

        if source is None:
            raise RuntimeError("RRF source resolution failed.")

        bm25_rank = bm25.rank if bm25 is not None else None

        dense_rank = dense.rank if dense is not None else None

        bm25_contribution = 1.0 / (effective_config.k + bm25_rank) if bm25_rank is not None else 0.0

        dense_contribution = (
            1.0 / (effective_config.k + dense_rank) if dense_rank is not None else 0.0
        )

        score = bm25_contribution + dense_contribution

        scored.append(
            (
                score,
                chunk_id,
                source.document_id,
                source.evidence_id,
                source.text,
                source.source_fact_ids,
                bm25_rank,
                dense_rank,
                (bm25.score if bm25 is not None else None),
                (dense.score if dense is not None else None),
                bm25_contribution,
                dense_contribution,
            )
        )

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    if top_k is not None:
        scored = scored[:top_k]

    return [
        RRFSearchResult(
            rank=rank,
            score=score,
            chunk_id=chunk_id,
            document_id=document_id,
            evidence_id=evidence_id,
            text=text,
            source_fact_ids=(source_fact_ids),
            bm25_rank=bm25_rank,
            dense_rank=dense_rank,
            bm25_score=bm25_score,
            dense_score=dense_score,
            bm25_contribution=(bm25_contribution),
            dense_contribution=(dense_contribution),
        )
        for rank, (
            score,
            chunk_id,
            document_id,
            evidence_id,
            text,
            source_fact_ids,
            bm25_rank,
            dense_rank,
            bm25_score,
            dense_score,
            bm25_contribution,
            dense_contribution,
        ) in enumerate(
            scored,
            start=1,
        )
    ]
