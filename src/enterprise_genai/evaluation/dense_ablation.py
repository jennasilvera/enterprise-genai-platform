from typing import Any

from enterprise_genai.retrieval.dense import (
    DENSE_REPRESENTATION_VERSION,
)
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
)

DENSE_ABLATION_VERSION = "dense-representation-ablation-v1"

BASELINE_REPRESENTATION = DENSE_REPRESENTATION_VERSION

CANDIDATE_REPRESENTATION = DENSE_DOCUMENT_TITLE_TEXT_VERSION

PRIMARY_METRIC = "mean_ndcg_at_10"

SECONDARY_METRIC = "mean_canonical_reciprocal_rank"

TERTIARY_METRIC = "mean_recall_at_10"


def _summary(
    report: dict[str, Any],
) -> dict[str, Any]:
    return report["summary"]["retrieval_eligible"]


def select_dense_representation(
    baseline_report: dict[str, Any],
    candidate_report: dict[str, Any],
) -> str:
    baseline = _summary(baseline_report)

    candidate = _summary(candidate_report)

    for metric in (
        PRIMARY_METRIC,
        SECONDARY_METRIC,
        TERTIARY_METRIC,
    ):
        baseline_value = baseline[metric]

        candidate_value = candidate[metric]

        if candidate_value > baseline_value:
            return CANDIDATE_REPRESENTATION

        if candidate_value < baseline_value:
            return BASELINE_REPRESENTATION

    return BASELINE_REPRESENTATION


def compare_dense_reports(
    baseline_report: dict[str, Any],
    candidate_report: dict[str, Any],
) -> dict[str, Any]:
    if baseline_report["representation_version"] != BASELINE_REPRESENTATION:
        raise ValueError("Unexpected baseline dense representation.")

    if candidate_report["representation_version"] != CANDIDATE_REPRESENTATION:
        raise ValueError("Unexpected candidate dense representation.")

    baseline = _summary(baseline_report)

    candidate = _summary(candidate_report)

    comparison: dict[
        str,
        dict[str, float],
    ] = {}

    for metric in (
        PRIMARY_METRIC,
        SECONDARY_METRIC,
        TERTIARY_METRIC,
    ):
        baseline_value = float(baseline[metric])

        candidate_value = float(candidate[metric])

        absolute = candidate_value - baseline_value

        relative = absolute / baseline_value if baseline_value != 0 else 0.0

        comparison[metric] = {
            "baseline": baseline_value,
            "candidate": candidate_value,
            "absolute_delta": absolute,
            "relative_delta": relative,
        }

    selected = select_dense_representation(
        baseline_report,
        candidate_report,
    )

    return {
        "experiment_version": (DENSE_ABLATION_VERSION),
        "scope": "development-only",
        "baseline_representation": (BASELINE_REPRESENTATION),
        "candidate_representation": (CANDIDATE_REPRESENTATION),
        "selection_policy": {
            "primary": PRIMARY_METRIC,
            "secondary": (SECONDARY_METRIC),
            "tertiary": (TERTIARY_METRIC),
            "exact_tie": (BASELINE_REPRESENTATION),
        },
        "comparison": comparison,
        "selected_representation": (selected),
    }
