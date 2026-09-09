from typing import Any

from enterprise_genai.data.chunk_models import ChunkCorpus
from enterprise_genai.data.evaluation_models import EvaluationSet
from enterprise_genai.evaluation.bm25_confirmation import (
    build_test_retrieval_evaluation,
)
from enterprise_genai.evaluation.dense_benchmark import (
    run_dense_benchmark,
)
from enterprise_genai.evaluation.hybrid_rrf import (
    run_hybrid_rrf_benchmark,
)
from enterprise_genai.retrieval.dense import DenseEncoderProtocol
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
)
from enterprise_genai.retrieval.rrf import RRF_VERSION

CONFIRMATION_VERSION = "hybrid-rrf-test-confirmation-v1"

FROZEN_SELECTED_RETRIEVER = f"hybrid:{RRF_VERSION}"

TEST_SPLIT_STATUS = "previously-inspected-non-pristine"

EXPECTED_TEST_QUERY_IDS = (
    "Q-0003",
    "Q-0005",
    "Q-0007",
    "Q-0018",
)


def _summary(
    benchmark: dict[str, Any],
) -> dict[str, Any]:
    return benchmark["summary"]["retrieval_eligible"]


def _metric_comparison(
    dense_benchmark: dict[str, Any],
    hybrid_benchmark: dict[str, Any],
) -> dict[str, dict[str, float]]:
    dense = _summary(dense_benchmark)

    hybrid = _summary(hybrid_benchmark)

    metrics = (
        "mean_canonical_reciprocal_rank",
        "mean_ndcg_at_10",
        "mean_recall_at_10",
    )

    comparison = {}

    for metric in metrics:
        dense_value = float(dense[metric])

        hybrid_value = float(hybrid[metric])

        absolute_delta = hybrid_value - dense_value

        relative_delta = absolute_delta / dense_value if dense_value != 0 else 0.0

        comparison[metric] = {
            "dense_reference": dense_value,
            "hybrid_confirmation": hybrid_value,
            "absolute_delta": absolute_delta,
            "relative_delta": relative_delta,
        }

    return comparison


def run_hybrid_test_confirmation(
    evaluation: EvaluationSet,
    lexical_chunks: ChunkCorpus,
    dense_chunks: ChunkCorpus,
    *,
    encoder: DenseEncoderProtocol,
) -> dict[str, Any]:
    """Confirm the frozen Phase 6A hybrid on the existing test split."""

    test_evaluation = build_test_retrieval_evaluation(evaluation)

    actual_query_ids = tuple(case.query_id for case in test_evaluation.cases)

    if actual_query_ids != EXPECTED_TEST_QUERY_IDS:
        raise ValueError("Unexpected retrieval-eligible test query IDs.")

    dense_benchmark = run_dense_benchmark(
        test_evaluation,
        dense_chunks,
        encoder=encoder,
        representation_version=(DENSE_DOCUMENT_TITLE_TEXT_VERSION),
    )

    hybrid_benchmark = run_hybrid_rrf_benchmark(
        test_evaluation,
        lexical_chunks,
        dense_chunks,
        encoder=encoder,
    )

    if hybrid_benchmark["fusion"]["version"] != RRF_VERSION:
        raise ValueError("Hybrid confirmation did not use the frozen RRF version.")

    return {
        "confirmation_version": (CONFIRMATION_VERSION),
        "frozen_selected_retriever": (FROZEN_SELECTED_RETRIEVER),
        "selection_status": ("frozen-before-test-confirmation"),
        "scope": "test-confirmation",
        "test_split_status": (TEST_SPLIT_STATUS),
        "expected_test_query_ids": list(EXPECTED_TEST_QUERY_IDS),
        "dense_reference_benchmark": (dense_benchmark),
        "hybrid_benchmark": (hybrid_benchmark),
        "comparison_vs_dense_reference": (
            _metric_comparison(
                dense_benchmark,
                hybrid_benchmark,
            )
        ),
    }
