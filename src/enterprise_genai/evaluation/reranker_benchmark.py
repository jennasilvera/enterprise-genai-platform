from __future__ import annotations

import math
from typing import Any

from enterprise_genai.data.chunk_models import ChunkCorpus
from enterprise_genai.data.evaluation_models import EvaluationSet
from enterprise_genai.evaluation.bm25_benchmark import (
    _case_metrics,
    _summary,
    is_retrieval_eligible,
)
from enterprise_genai.retrieval.bm25 import (
    BM25_VERSION,
    BM25Config,
    BM25Index,
)
from enterprise_genai.retrieval.dense import (
    DENSE_VERSION,
    DenseEncoderProtocol,
    DenseIndex,
)
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
)
from enterprise_genai.retrieval.reranker import (
    CANDIDATE_K,
    RERANKER_REPRESENTATION_VERSION,
    RERANKER_VERSION,
    RerankerProtocol,
    rerank_rrf_candidates,
)
from enterprise_genai.retrieval.rrf import (
    RRF_VERSION,
    RRFConfig,
    RRFSearchResult,
    fuse_ranked_results,
)
from enterprise_genai.retrieval.tokenization import TOKENIZER_VERSION

RERANKER_BENCHMARK_VERSION = "northstar-cross-encoder-reranker-development-v1"

LEXICAL_REPRESENTATION_VERSION = "document-title-text-v1"

EXPECTED_DEVELOPMENT_QUERY_IDS = (
    "Q-0001",
    "Q-0002",
    "Q-0004",
    "Q-0006",
    "Q-0008",
    "Q-0009",
    "Q-0017",
    "Q-0019",
    "Q-0020",
    "Q-0021",
)


def _validate_corpora(
    lexical_chunks: ChunkCorpus,
    dense_chunks: ChunkCorpus,
) -> None:
    if lexical_chunks.dataset_version != dense_chunks.dataset_version:
        raise ValueError("Reranker corpora use different dataset versions.")

    if lexical_chunks.strategy_version != dense_chunks.strategy_version:
        raise ValueError("Reranker corpora use different chunk strategies.")

    lexical_ids = {chunk.chunk_id for chunk in lexical_chunks.chunks}

    dense_ids = {chunk.chunk_id for chunk in dense_chunks.chunks}

    if lexical_ids != dense_ids:
        raise ValueError("Reranker corpora contain different chunk identities.")


def _serialize_rrf_result(
    result: RRFSearchResult,
) -> dict[str, Any]:
    return {
        "rank": result.rank,
        "rrf_score": result.score,
        "chunk_id": result.chunk_id,
        "document_id": result.document_id,
        "evidence_id": result.evidence_id,
        "bm25_rank": result.bm25_rank,
        "dense_rank": result.dense_rank,
        "bm25_score": result.bm25_score,
        "dense_score": result.dense_score,
        "bm25_contribution": (result.bm25_contribution),
        "dense_contribution": (result.dense_contribution),
        "source_fact_ids": list(result.source_fact_ids),
        "text": result.text,
    }


def _serialize_reranked_result(
    result: Any,
) -> dict[str, Any]:
    return {
        "rank": result.rank,
        "cross_encoder_score": (result.cross_encoder_score),
        "original_rrf_rank": (result.original_rrf_rank),
        "rrf_score": result.rrf_score,
        "chunk_id": result.chunk_id,
        "document_id": result.document_id,
        "evidence_id": result.evidence_id,
        "bm25_rank": result.bm25_rank,
        "dense_rank": result.dense_rank,
        "bm25_score": result.bm25_score,
        "dense_score": result.dense_score,
        "source_fact_ids": list(result.source_fact_ids),
        "text": result.text,
    }


def _grouped_summary(
    case_results: list[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    values = sorted({str(result[key]) for result in case_results})

    return {
        value: _summary([result for result in case_results if str(result[key]) == value])
        for value in values
    }


def run_reranker_development_benchmark(
    evaluation: EvaluationSet,
    lexical_chunks: ChunkCorpus,
    dense_chunks: ChunkCorpus,
    *,
    encoder: DenseEncoderProtocol,
    reranker: RerankerProtocol,
) -> dict[str, Any]:
    _validate_corpora(
        lexical_chunks,
        dense_chunks,
    )

    if encoder.metadata.get("representation_version") != DENSE_DOCUMENT_TITLE_TEXT_VERSION:
        raise ValueError(
            "Reranker benchmark requires the frozen dense document-title representation."
        )

    reranker_metadata = reranker.metadata

    if reranker_metadata.get("reranker_version") != RERANKER_VERSION:
        raise ValueError("Unexpected reranker version.")

    if reranker_metadata.get("representation_version") != RERANKER_REPRESENTATION_VERSION:
        raise ValueError("Unexpected reranker representation.")

    if reranker_metadata.get("candidate_k") != CANDIDATE_K:
        raise ValueError("Unexpected reranker candidate_k.")

    eligible_cases = [
        case
        for case in evaluation.cases
        if (case.split == "development" and is_retrieval_eligible(case))
    ]

    actual_ids = tuple(case.query_id for case in eligible_cases)

    if actual_ids != EXPECTED_DEVELOPMENT_QUERY_IDS:
        raise ValueError("Unexpected retrieval-eligible development query IDs.")

    bm25_config = BM25Config(
        k1=1.5,
        b=0.75,
    )

    rrf_config = RRFConfig()

    bm25_index = BM25Index(
        lexical_chunks.chunks,
        config=bm25_config,
    )

    dense_index = DenseIndex(
        dense_chunks.chunks,
        encoder=encoder,
    )

    baseline_cases: list[dict[str, Any]] = []

    reranked_cases: list[dict[str, Any]] = []

    expected_fused_count = len(dense_chunks.chunks)

    for case in eligible_cases:
        bm25_results = bm25_index.search(case.question)

        dense_results = dense_index.search(case.question)

        fused_results = fuse_ranked_results(
            bm25_results,
            dense_results,
            config=rrf_config,
        )

        if len(fused_results) != expected_fused_count:
            raise ValueError("Frozen RRF regeneration did not produce the full corpus.")

        reranked_results = rerank_rrf_candidates(
            case.question,
            fused_results,
            reranker=reranker,
        )

        if len(reranked_results) != len(fused_results):
            raise ValueError("Reranker changed ranking size.")

        fused_chunk_ids = [result.chunk_id for result in fused_results]

        reranked_chunk_ids = [result.chunk_id for result in reranked_results]

        if set(fused_chunk_ids) != set(reranked_chunk_ids):
            raise ValueError("Reranker changed candidate set.")

        if reranked_chunk_ids[CANDIDATE_K:] != fused_chunk_ids[CANDIDATE_K:]:
            raise ValueError("Reranker changed frozen RRF tail ordering.")

        baseline_ranked_ids = [result.evidence_id for result in fused_results]

        reranked_ranked_ids = [result.evidence_id for result in reranked_results]

        shared = {
            "query_id": case.query_id,
            "question": case.question,
            "query_type": (case.query_type),
            "split": case.split,
            "difficulty": (case.difficulty),
        }

        baseline_cases.append(
            {
                **shared,
                "retrieved_bm25": (len(bm25_results)),
                "retrieved_dense": (len(dense_results)),
                "retrieved_fused": (len(fused_results)),
                "metrics": _case_metrics(
                    case,
                    baseline_ranked_ids,
                ),
                "top_results": [_serialize_rrf_result(result) for result in (fused_results[:10])],
            }
        )

        reranked_cases.append(
            {
                **shared,
                "candidate_k": (CANDIDATE_K),
                "retrieved_reranked": (len(reranked_results)),
                "candidate_set_preserved": (True),
                "tail_order_preserved": (True),
                "metrics": _case_metrics(
                    case,
                    reranked_ranked_ids,
                ),
                "original_top_20": [
                    _serialize_rrf_result(result) for result in (fused_results[:CANDIDATE_K])
                ],
                "reranked_top_20": [
                    _serialize_reranked_result(result)
                    for result in (reranked_results[:CANDIDATE_K])
                ],
                "top_results": [
                    _serialize_reranked_result(result) for result in (reranked_results[:10])
                ],
            }
        )

    baseline_summary = {
        "retrieval_eligible": _summary(baseline_cases),
        "by_query_type": (
            _grouped_summary(
                baseline_cases,
                "query_type",
            )
        ),
        "by_difficulty": (
            _grouped_summary(
                baseline_cases,
                "difficulty",
            )
        ),
    }

    reranked_summary = {
        "retrieval_eligible": _summary(reranked_cases),
        "by_query_type": (
            _grouped_summary(
                reranked_cases,
                "query_type",
            )
        ),
        "by_difficulty": (
            _grouped_summary(
                reranked_cases,
                "difficulty",
            )
        ),
    }

    return {
        "benchmark_version": (RERANKER_BENCHMARK_VERSION),
        "dataset_version": (evaluation.dataset_version),
        "evaluation_version": (evaluation.evaluation_version),
        "chunk_strategy_version": (lexical_chunks.strategy_version),
        "candidate_generator": {
            "selected_retriever": (f"hybrid:{RRF_VERSION}"),
            "fusion": {
                "version": RRF_VERSION,
                "k": rrf_config.k,
                "formula": ("sum(1 / (k + rank))"),
                "missing_rank_contribution": (0.0),
                "tie_breaker": ("chunk_id"),
            },
            "lexical": {
                "bm25_version": (BM25_VERSION),
                "tokenizer_version": (TOKENIZER_VERSION),
                "representation_version": (LEXICAL_REPRESENTATION_VERSION),
                "parameters": {
                    "k1": (bm25_config.k1),
                    "b": (bm25_config.b),
                },
                "zero_overlap_policy": ("excluded"),
            },
            "dense": {
                "dense_version": (DENSE_VERSION),
                "representation_version": (DENSE_DOCUMENT_TITLE_TEXT_VERSION),
                "encoder": (encoder.metadata),
            },
        },
        "reranker": (reranker_metadata),
        "ranking_policy": {
            "candidate_k": (CANDIDATE_K),
            "candidate_order": ("cross_encoder_score_desc,original_rrf_rank_asc,chunk_id_asc"),
            "tail_policy": ("original_rrf_ranks_21_to_80_preserved"),
            "score_interpolation": (False),
        },
        "corpus": {
            "chunks": len(lexical_chunks.chunks),
        },
        "evaluation": {
            "split": "development",
            "retrieval_eligible_cases": (len(eligible_cases)),
            "query_ids": list(actual_ids),
        },
        "baseline_benchmark": {
            "summary": (baseline_summary),
            "cases": (baseline_cases),
        },
        "reranked_benchmark": {
            "summary": (reranked_summary),
            "cases": (reranked_cases),
        },
    }


def verify_phase6a_regeneration(
    frozen_phase6a: dict[str, Any],
    regenerated: dict[str, Any],
) -> dict[str, Any]:
    if frozen_phase6a.get("selected_retriever") != "hybrid:rrf-k60-v1":
        raise ValueError("Frozen Phase 6A selected retriever is unexpected.")

    reference = frozen_phase6a["hybrid_benchmark"]

    candidate = regenerated["baseline_benchmark"]

    reference_summary = reference["summary"]["retrieval_eligible"]

    candidate_summary = candidate["summary"]["retrieval_eligible"]

    if reference_summary["cases"] != candidate_summary["cases"]:
        raise ValueError("Phase 6A regeneration case count differs.")

    for metric, reference_value in reference_summary.items():
        if metric == "cases":
            continue

        candidate_value = candidate_summary[metric]

        if not math.isclose(
            float(reference_value),
            float(candidate_value),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"Phase 6A regeneration summary differs for {metric}.")

    reference_cases = {case["query_id"]: case for case in reference["cases"]}

    candidate_cases = {case["query_id"]: case for case in candidate["cases"]}

    if tuple(candidate_cases) != EXPECTED_DEVELOPMENT_QUERY_IDS:
        raise ValueError("Regenerated development case order differs.")

    if set(reference_cases) != set(candidate_cases):
        raise ValueError("Phase 6A regeneration query identity differs.")

    for query_id in EXPECTED_DEVELOPMENT_QUERY_IDS:
        reference_case = reference_cases[query_id]

        candidate_case = candidate_cases[query_id]

        for metric, reference_value in reference_case["metrics"].items():
            candidate_value = candidate_case["metrics"][metric]

            if not math.isclose(
                float(reference_value),
                float(candidate_value),
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    f"Phase 6A regeneration case metric differs for {query_id} {metric}."
                )

        reference_top = reference_case["top_results"]

        candidate_top = candidate_case["top_results"]

        reference_identity = [
            (
                result["chunk_id"],
                result["evidence_id"],
            )
            for result in reference_top
        ]

        candidate_identity = [
            (
                result["chunk_id"],
                result["evidence_id"],
            )
            for result in candidate_top
        ]

        if reference_identity != candidate_identity:
            raise ValueError(f"Phase 6A regeneration top-10 identity differs for {query_id}.")

        for (
            reference_result,
            candidate_result,
        ) in zip(
            reference_top,
            candidate_top,
            strict=True,
        ):
            if not math.isclose(
                float(reference_result["rrf_score"]),
                float(candidate_result["rrf_score"]),
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise ValueError(f"Phase 6A regeneration RRF score differs for {query_id}.")

    return {
        "verified": True,
        "development_cases": (len(EXPECTED_DEVELOPMENT_QUERY_IDS)),
        "top_k_identity_checked": 10,
        "aggregate_metrics_checked": (True),
        "per_case_metrics_checked": (True),
        "rrf_scores_checked": True,
    }
