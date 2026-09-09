from typing import Any

BASELINE_NAME = "hybrid:rrf-k60-v1"

CANDIDATE_NAME = "reranker:cross-encoder-ms-marco-minilm-l6-v2-v1"

GUARDRAIL_METRIC = "mean_recall_at_10"

PRIMARY_METRIC = "mean_ndcg_at_10"

SECONDARY_METRIC = "mean_canonical_reciprocal_rank"


def select_reranker(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    baseline_recall = float(baseline[GUARDRAIL_METRIC])

    candidate_recall = float(candidate[GUARDRAIL_METRIC])

    if candidate_recall < baseline_recall:
        return {
            "selected": (BASELINE_NAME),
            "reason": ("recall_at_10_guardrail_failed"),
            "guardrail_passed": False,
        }

    baseline_primary = float(baseline[PRIMARY_METRIC])

    candidate_primary = float(candidate[PRIMARY_METRIC])

    if candidate_primary > baseline_primary:
        return {
            "selected": (CANDIDATE_NAME),
            "reason": ("higher_ndcg_at_10"),
            "guardrail_passed": True,
        }

    if candidate_primary < baseline_primary:
        return {
            "selected": (BASELINE_NAME),
            "reason": ("lower_ndcg_at_10"),
            "guardrail_passed": True,
        }

    baseline_secondary = float(baseline[SECONDARY_METRIC])

    candidate_secondary = float(candidate[SECONDARY_METRIC])

    if candidate_secondary > baseline_secondary:
        return {
            "selected": (CANDIDATE_NAME),
            "reason": ("ndcg_tie_higher_canonical_mrr"),
            "guardrail_passed": True,
        }

    return {
        "selected": BASELINE_NAME,
        "reason": ("retain_frozen_rrf_on_tie_or_lower_mrr"),
        "guardrail_passed": True,
    }
