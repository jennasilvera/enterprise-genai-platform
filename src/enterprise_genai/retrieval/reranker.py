from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from typing import Protocol

import numpy as np
import torch
from sentence_transformers import CrossEncoder

from enterprise_genai.retrieval.rrf import (
    RRFSearchResult,
)

RERANKER_VERSION = "cross-encoder-ms-marco-minilm-l6-v2-v1"

RERANKER_REPRESENTATION_VERSION = "cross-encoder-document-title-text-v1"

MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"

MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"

CANDIDATE_K = 20

BATCH_SIZE = 16

DEVICE = "cpu"


class RerankerProtocol(Protocol):
    @property
    def metadata(
        self,
    ) -> dict[str, object]: ...

    def score(
        self,
        query: str,
        passages: list[str],
    ) -> np.ndarray: ...


class CrossEncoderReranker:
    """Pinned CPU cross-encoder relevance scorer."""

    def __init__(
        self,
    ) -> None:
        self._model = CrossEncoder(
            MODEL_ID,
            revision=MODEL_REVISION,
            device=DEVICE,
            trust_remote_code=False,
            backend="torch",
        )

    @property
    def metadata(
        self,
    ) -> dict[str, object]:
        return {
            "reranker_version": (RERANKER_VERSION),
            "representation_version": (RERANKER_REPRESENTATION_VERSION),
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "device": DEVICE,
            "batch_size": BATCH_SIZE,
            "backend": "torch",
            "candidate_k": CANDIDATE_K,
            "activation": "identity",
            "apply_softmax": False,
            "numpy_version": version("numpy"),
            "torch_version": version("torch"),
            "transformers_version": version("transformers"),
            "sentence_transformers_version": (version("sentence-transformers")),
        }

    def score(
        self,
        query: str,
        passages: list[str],
    ) -> np.ndarray:
        if not query.strip():
            raise ValueError("Reranker query must be non-empty.")

        if not passages:
            return np.empty(
                (0,),
                dtype=np.float32,
            )

        pairs = [
            (
                query,
                passage,
            )
            for passage in passages
        ]

        with torch.inference_mode():
            scores = self._model.predict(
                pairs,
                batch_size=BATCH_SIZE,
                show_progress_bar=False,
                activation_fn=(torch.nn.Identity()),
                apply_softmax=False,
                convert_to_numpy=True,
                convert_to_tensor=False,
                device=DEVICE,
            )

        array = np.asarray(
            scores,
            dtype=np.float32,
        ).reshape(-1)

        if array.shape != (len(passages),):
            raise ValueError(f"Unexpected cross-encoder score shape: {array.shape}.")

        if not np.isfinite(array).all():
            raise ValueError("Cross-encoder scores contain non-finite values.")

        return array


@dataclass(frozen=True)
class RerankedSearchResult:
    rank: int
    cross_encoder_score: float | None
    original_rrf_rank: int
    rrf_score: float
    chunk_id: str
    document_id: str
    evidence_id: str
    text: str
    source_fact_ids: tuple[str, ...]
    bm25_rank: int | None
    dense_rank: int | None
    bm25_score: float | None
    dense_score: float | None


def _validate_rrf_results(
    results: list[RRFSearchResult],
) -> None:
    if not results:
        raise ValueError("Reranking requires at least one RRF result.")

    seen: set[str] = set()

    for expected_rank, result in enumerate(
        results,
        start=1,
    ):
        if result.rank != expected_rank:
            raise ValueError("RRF ranking must be contiguous from rank 1.")

        if result.chunk_id in seen:
            raise ValueError(f"RRF ranking contains duplicate chunk {result.chunk_id}.")

        seen.add(result.chunk_id)


def rerank_rrf_candidates(
    query: str,
    rrf_results: list[RRFSearchResult],
    *,
    reranker: RerankerProtocol,
) -> list[RerankedSearchResult]:
    _validate_rrf_results(rrf_results)

    if len(rrf_results) < CANDIDATE_K:
        raise ValueError(f"RRF ranking is smaller than candidate_k={CANDIDATE_K}.")

    candidates = rrf_results[:CANDIDATE_K]

    passages = [result.text for result in candidates]

    scores = reranker.score(
        query,
        passages,
    )

    scores = np.asarray(
        scores,
        dtype=np.float32,
    ).reshape(-1)

    if scores.shape != (CANDIDATE_K,):
        raise ValueError("Reranker returned an unexpected number of candidate scores.")

    if not np.isfinite(scores).all():
        raise ValueError("Reranker candidate scores contain non-finite values.")

    scored_candidates = [
        (
            float(score),
            result,
        )
        for score, result in zip(
            scores,
            candidates,
            strict=True,
        )
    ]

    scored_candidates.sort(
        key=lambda item: (
            -item[0],
            item[1].rank,
            item[1].chunk_id,
        )
    )

    reordered: list[
        tuple[
            RRFSearchResult,
            float | None,
        ]
    ] = [
        (
            result,
            score,
        )
        for score, result in (scored_candidates)
    ]

    reordered.extend(
        (
            result,
            None,
        )
        for result in rrf_results[CANDIDATE_K:]
    )

    return [
        RerankedSearchResult(
            rank=rank,
            cross_encoder_score=(cross_encoder_score),
            original_rrf_rank=(result.rank),
            rrf_score=result.score,
            chunk_id=(result.chunk_id),
            document_id=(result.document_id),
            evidence_id=(result.evidence_id),
            text=result.text,
            source_fact_ids=(result.source_fact_ids),
            bm25_rank=(result.bm25_rank),
            dense_rank=(result.dense_rank),
            bm25_score=(result.bm25_score),
            dense_score=(result.dense_score),
        )
        for rank, (
            result,
            cross_encoder_score,
        ) in enumerate(
            reordered,
            start=1,
        )
    ]
