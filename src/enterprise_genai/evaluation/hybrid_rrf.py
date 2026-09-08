from typing import Any

from enterprise_genai.data.chunk_models import (
    ChunkCorpus,
)
from enterprise_genai.data.evaluation_models import (
    EvaluationSet,
)
from enterprise_genai.evaluation.bm25_benchmark import (
    _case_metrics,
    _summary,
    is_retrieval_eligible,
)
from enterprise_genai.retrieval.bm25 import (
    BM25Config,
    BM25Index,
    BM25_VERSION,
)
from enterprise_genai.retrieval.dense import (
    DENSE_VERSION,
    DenseEncoderProtocol,
    DenseIndex,
)
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
)
from enterprise_genai.retrieval.rrf import (
    RRFConfig,
    RRF_VERSION,
    fuse_ranked_results,
)
from enterprise_genai.retrieval.tokenization import (
    TOKENIZER_VERSION,
)

HYBRID_BENCHMARK_VERSION = "northstar-hybrid-rrf-baseline-v1"

LEXICAL_REPRESENTATION_VERSION = "document-title-text-v1"


def _validate_corpora(
    lexical_chunks: ChunkCorpus,
    dense_chunks: ChunkCorpus,
) -> None:
    if lexical_chunks.dataset_version != dense_chunks.dataset_version:
        raise ValueError("Hybrid corpora use different dataset versions.")

    if lexical_chunks.strategy_version != dense_chunks.strategy_version:
        raise ValueError("Hybrid corpora use different chunk strategies.")

    lexical_ids = {chunk.chunk_id for chunk in lexical_chunks.chunks}

    dense_ids = {chunk.chunk_id for chunk in dense_chunks.chunks}

    if lexical_ids != dense_ids:
        raise ValueError("Hybrid corpora contain different chunk identities.")


def run_hybrid_rrf_benchmark(
    evaluation: EvaluationSet,
    lexical_chunks: ChunkCorpus,
    dense_chunks: ChunkCorpus,
    *,
    encoder: DenseEncoderProtocol,
) -> dict[str, Any]:
    _validate_corpora(
        lexical_chunks,
        dense_chunks,
    )

    encoder_representation = encoder.metadata.get("representation_version")

    if encoder_representation != DENSE_DOCUMENT_TITLE_TEXT_VERSION:
        raise ValueError("Hybrid benchmark requires frozen dense document-title representation.")

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

    eligible_cases = [case for case in evaluation.cases if is_retrieval_eligible(case)]

    excluded_cases = [
        {
            "query_id": case.query_id,
            "query_type": (case.query_type),
            "split": case.split,
            "reason": ("unanswerable" if not case.answerable else "no_document_qrels"),
        }
        for case in evaluation.cases
        if not is_retrieval_eligible(case)
    ]

    case_results: list[dict[str, Any]] = []

    for case in eligible_cases:
        bm25_results = bm25_index.search(case.question)

        dense_results = dense_index.search(case.question)

        fused_results = fuse_ranked_results(
            bm25_results,
            dense_results,
            config=rrf_config,
        )

        ranked_evidence_ids = [result.evidence_id for result in fused_results]

        case_results.append(
            {
                "query_id": (case.query_id),
                "question": (case.question),
                "query_type": (case.query_type),
                "split": case.split,
                "difficulty": (case.difficulty),
                "retrieved_bm25": (len(bm25_results)),
                "retrieved_dense": (len(dense_results)),
                "retrieved_fused": (len(fused_results)),
                "metrics": (
                    _case_metrics(
                        case,
                        ranked_evidence_ids,
                    )
                ),
                "top_results": [
                    {
                        "rank": (result.rank),
                        "rrf_score": (result.score),
                        "chunk_id": (result.chunk_id),
                        "document_id": (result.document_id),
                        "evidence_id": (result.evidence_id),
                        "bm25_rank": (result.bm25_rank),
                        "dense_rank": (result.dense_rank),
                        "bm25_score": (result.bm25_score),
                        "dense_score": (result.dense_score),
                        "bm25_contribution": (result.bm25_contribution),
                        "dense_contribution": (result.dense_contribution),
                        "source_fact_ids": (list(result.source_fact_ids)),
                        "text": (result.text),
                    }
                    for result in fused_results[:10]
                ],
            }
        )

    by_query_type = {}

    for query_type in sorted({result["query_type"] for result in case_results}):
        group = [result for result in case_results if (result["query_type"] == query_type)]

        by_query_type[query_type] = _summary(group)

    by_split = {}

    for split in sorted({result["split"] for result in case_results}):
        group = [result for result in case_results if result["split"] == split]

        by_split[split] = _summary(group)

    by_difficulty = {}

    for difficulty in sorted({result["difficulty"] for result in case_results}):
        group = [result for result in case_results if (result["difficulty"] == difficulty)]

        by_difficulty[difficulty] = _summary(group)

    return {
        "benchmark_version": (HYBRID_BENCHMARK_VERSION),
        "dataset_version": (evaluation.dataset_version),
        "evaluation_version": (evaluation.evaluation_version),
        "chunk_strategy_version": (lexical_chunks.strategy_version),
        "fusion": {
            "version": RRF_VERSION,
            "k": rrf_config.k,
            "formula": ("sum(1 / (k + rank))"),
            "missing_rank_contribution": (0.0),
            "tie_breaker": ("chunk_id"),
        },
        "lexical": {
            "bm25_version": BM25_VERSION,
            "tokenizer_version": (TOKENIZER_VERSION),
            "representation_version": (LEXICAL_REPRESENTATION_VERSION),
            "parameters": {
                "k1": bm25_config.k1,
                "b": bm25_config.b,
            },
            "zero_overlap_policy": ("excluded"),
        },
        "dense": {
            "dense_version": (DENSE_VERSION),
            "representation_version": (DENSE_DOCUMENT_TITLE_TEXT_VERSION),
            "encoder": (encoder.metadata),
        },
        "corpus": {
            "chunks": len(lexical_chunks.chunks),
        },
        "evaluation": {
            "all_cases": len(evaluation.cases),
            "retrieval_eligible_cases": (len(eligible_cases)),
            "excluded_cases": (excluded_cases),
        },
        "summary": {
            "retrieval_eligible": (_summary(case_results)),
            "by_query_type": (by_query_type),
            "by_split": by_split,
            "by_difficulty": (by_difficulty),
        },
        "cases": case_results,
    }
