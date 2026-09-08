from typing import Any

from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
)
from enterprise_genai.retrieval.rrf import (
    RRF_VERSION,
)

HYBRID_EXPERIMENT_VERSION = "hybrid-rrf-baseline-v1"

DENSE_REFERENCE_ID = "dense:" + DENSE_DOCUMENT_TITLE_TEXT_VERSION

HYBRID_CANDIDATE_ID = "hybrid:" + RRF_VERSION

PRIMARY_METRIC = "mean_ndcg_at_10"

SECONDARY_METRIC = "mean_canonical_reciprocal_rank"

TERTIARY_METRIC = "mean_recall_at_10"


def _dense_summary(
    report: dict[str, Any],
) -> dict[str, Any]:
    return report["candidate_benchmark"]["summary"]["retrieval_eligible"]


def _hybrid_summary(
    report: dict[str, Any],
) -> dict[str, Any]:
    return report["summary"]["retrieval_eligible"]


def select_hybrid_or_dense(
    dense_report: dict[str, Any],
    hybrid_report: dict[str, Any],
) -> str:
    dense = _dense_summary(dense_report)

    hybrid = _hybrid_summary(hybrid_report)

    for metric in (
        PRIMARY_METRIC,
        SECONDARY_METRIC,
        TERTIARY_METRIC,
    ):
        dense_value = dense[metric]

        hybrid_value = hybrid[metric]

        if hybrid_value > dense_value:
            return HYBRID_CANDIDATE_ID

        if hybrid_value < dense_value:
            return DENSE_REFERENCE_ID

    return DENSE_REFERENCE_ID


def compare_hybrid_to_dense(
    dense_report: dict[str, Any],
    hybrid_report: dict[str, Any],
) -> dict[str, Any]:
    if dense_report["selected_representation"] != DENSE_DOCUMENT_TITLE_TEXT_VERSION:
        raise ValueError("Unexpected frozen dense reference representation.")

    if hybrid_report["fusion"]["version"] != RRF_VERSION:
        raise ValueError("Unexpected hybrid fusion version.")

    dense = _dense_summary(dense_report)

    hybrid = _hybrid_summary(hybrid_report)

    comparison = {}

    for metric in (
        PRIMARY_METRIC,
        SECONDARY_METRIC,
        TERTIARY_METRIC,
    ):
        dense_value = float(dense[metric])

        hybrid_value = float(hybrid[metric])

        absolute = hybrid_value - dense_value

        relative = absolute / dense_value if dense_value != 0 else 0.0

        comparison[metric] = {
            "dense_reference": (dense_value),
            "hybrid_candidate": (hybrid_value),
            "absolute_delta": (absolute),
            "relative_delta": (relative),
        }

    selected = select_hybrid_or_dense(
        dense_report,
        hybrid_report,
    )

    return {
        "experiment_version": (HYBRID_EXPERIMENT_VERSION),
        "scope": "development-only",
        "dense_reference": (DENSE_REFERENCE_ID),
        "hybrid_candidate": (HYBRID_CANDIDATE_ID),
        "selection_policy": {
            "primary": (PRIMARY_METRIC),
            "secondary": (SECONDARY_METRIC),
            "tertiary": (TERTIARY_METRIC),
            "exact_tie": (DENSE_REFERENCE_ID),
        },
        "comparison": comparison,
        "selected_retriever": (selected),
    }
