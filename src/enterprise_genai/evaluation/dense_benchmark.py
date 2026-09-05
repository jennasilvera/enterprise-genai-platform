from collections import Counter
from statistics import mean
from typing import Any

from enterprise_genai.data.chunk_models import (
    ChunkCorpus,
)
from enterprise_genai.data.evaluation_models import (
    EvaluationCase,
    EvaluationSet,
)
from enterprise_genai.evaluation.bm25_benchmark import (
    is_retrieval_eligible,
)
from enterprise_genai.evaluation.retrieval_metrics import (
    canonical_reciprocal_rank,
    ndcg_at_k,
    recall_at_k,
)
from enterprise_genai.retrieval.dense import (
    DENSE_REPRESENTATION_VERSION,
    DENSE_VERSION,
    DenseEncoderProtocol,
    DenseIndex,
)

DENSE_BENCHMARK_VERSION = "northstar-dense-baseline-v1"

K_VALUES = (
    1,
    3,
    5,
    10,
)


def build_development_retrieval_evaluation(
    evaluation: EvaluationSet,
) -> EvaluationSet:
    cases = [
        case
        for case in evaluation.cases
        if (case.split == "development" and is_retrieval_eligible(case))
    ]

    return EvaluationSet(
        dataset_version=(evaluation.dataset_version),
        evaluation_version=(evaluation.evaluation_version),
        cases=cases,
    )


def _validate_qrel_chunk_mapping(
    evaluation: EvaluationSet,
    chunks: ChunkCorpus,
) -> None:
    chunks_by_evidence: Counter[str] = Counter(chunk.evidence_id for chunk in chunks.chunks)

    referenced = {
        judgment.evidence_id for case in evaluation.cases for judgment in case.relevance_judgments
    }

    invalid = sorted(
        evidence_id for evidence_id in referenced if (chunks_by_evidence[evidence_id] != 1)
    )

    if invalid:
        raise ValueError(
            "Dense evidence-block benchmark "
            "requires exactly one chunk per "
            f"qrel evidence ID: {invalid}"
        )


def _case_metrics(
    case: EvaluationCase,
    ranked_evidence_ids: list[str],
) -> dict[str, float]:
    relevance_by_id = {
        judgment.evidence_id: (judgment.relevance_grade) for judgment in case.relevance_judgments
    }

    relevant_ids = set(relevance_by_id)

    canonical_ids = {evidence_id for evidence_id, grade in relevance_by_id.items() if grade == 3}

    metrics: dict[str, float] = {}

    for k in K_VALUES:
        metrics[f"recall_at_{k}"] = recall_at_k(
            ranked_evidence_ids,
            relevant_ids,
            k,
        )

        metrics[f"ndcg_at_{k}"] = ndcg_at_k(
            ranked_evidence_ids,
            relevance_by_id,
            k,
        )

    metrics["canonical_reciprocal_rank"] = canonical_reciprocal_rank(
        ranked_evidence_ids,
        canonical_ids,
    )

    return metrics


def _summary(
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    if not case_results:
        return {
            "cases": 0,
        }

    metric_names = tuple(case_results[0]["metrics"].keys())

    summary: dict[str, Any] = {
        "cases": len(case_results),
    }

    for metric_name in metric_names:
        summary[f"mean_{metric_name}"] = mean(
            result["metrics"][metric_name] for result in case_results
        )

    return summary


def run_dense_benchmark(
    evaluation: EvaluationSet,
    chunks: ChunkCorpus,
    *,
    encoder: DenseEncoderProtocol,
) -> dict[str, Any]:
    _validate_qrel_chunk_mapping(
        evaluation,
        chunks,
    )

    index = DenseIndex(
        chunks.chunks,
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
        results = index.search(case.question)

        ranked_evidence_ids = [result.evidence_id for result in results]

        case_results.append(
            {
                "query_id": (case.query_id),
                "question": (case.question),
                "query_type": (case.query_type),
                "split": case.split,
                "difficulty": (case.difficulty),
                "retrieved": len(results),
                "metrics": (
                    _case_metrics(
                        case,
                        ranked_evidence_ids,
                    )
                ),
                "top_results": [
                    {
                        "rank": (result.rank),
                        "score": (result.score),
                        "chunk_id": (result.chunk_id),
                        "document_id": (result.document_id),
                        "evidence_id": (result.evidence_id),
                        "source_fact_ids": (list(result.source_fact_ids)),
                        "text": (result.text),
                    }
                    for result in results[:10]
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
        "benchmark_version": (DENSE_BENCHMARK_VERSION),
        "dataset_version": (evaluation.dataset_version),
        "evaluation_version": (evaluation.evaluation_version),
        "chunk_strategy_version": (chunks.strategy_version),
        "dense_version": (DENSE_VERSION),
        "representation_version": (DENSE_REPRESENTATION_VERSION),
        "encoder": (encoder.metadata),
        "corpus": {
            "chunks": len(chunks.chunks),
            "embedding_dimension": (encoder.embedding_dimension),
        },
        "evaluation": {
            "all_cases": len(evaluation.cases),
            "retrieval_eligible_cases": (len(eligible_cases)),
            "excluded_cases": (excluded_cases),
        },
        "summary": {
            "retrieval_eligible": (_summary(case_results)),
            "by_query_type": (by_query_type),
            "by_split": (by_split),
            "by_difficulty": (by_difficulty),
        },
        "cases": case_results,
    }
