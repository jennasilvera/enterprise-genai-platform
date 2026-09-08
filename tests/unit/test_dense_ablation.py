from enterprise_genai.evaluation.dense_ablation import (
    BASELINE_REPRESENTATION,
    CANDIDATE_REPRESENTATION,
    compare_dense_reports,
    select_dense_representation,
)


def _report(
    representation: str,
    *,
    ndcg: float,
    mrr: float,
    recall: float,
):
    return {
        "representation_version": (representation),
        "summary": {
            "retrieval_eligible": {
                "mean_ndcg_at_10": ndcg,
                "mean_canonical_reciprocal_rank": (mrr),
                "mean_recall_at_10": recall,
            }
        },
    }


def test_primary_metric_selects_candidate() -> None:
    baseline = _report(
        BASELINE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.80,
        recall=0.90,
    )

    candidate = _report(
        CANDIDATE_REPRESENTATION,
        ndcg=0.61,
        mrr=0.10,
        recall=0.10,
    )

    assert (
        select_dense_representation(
            baseline,
            candidate,
        )
        == CANDIDATE_REPRESENTATION
    )


def test_primary_metric_can_retain_baseline() -> None:
    baseline = _report(
        BASELINE_REPRESENTATION,
        ndcg=0.61,
        mrr=0.10,
        recall=0.10,
    )

    candidate = _report(
        CANDIDATE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.99,
        recall=1.0,
    )

    assert (
        select_dense_representation(
            baseline,
            candidate,
        )
        == BASELINE_REPRESENTATION
    )


def test_secondary_metric_breaks_primary_tie() -> None:
    baseline = _report(
        BASELINE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.50,
        recall=1.0,
    )

    candidate = _report(
        CANDIDATE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.51,
        recall=0.0,
    )

    assert (
        select_dense_representation(
            baseline,
            candidate,
        )
        == CANDIDATE_REPRESENTATION
    )


def test_tertiary_metric_breaks_first_two_ties() -> None:
    baseline = _report(
        BASELINE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.50,
        recall=0.80,
    )

    candidate = _report(
        CANDIDATE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.50,
        recall=0.90,
    )

    assert (
        select_dense_representation(
            baseline,
            candidate,
        )
        == CANDIDATE_REPRESENTATION
    )


def test_exact_tie_retains_baseline() -> None:
    baseline = _report(
        BASELINE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.50,
        recall=0.80,
    )

    candidate = _report(
        CANDIDATE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.50,
        recall=0.80,
    )

    assert (
        select_dense_representation(
            baseline,
            candidate,
        )
        == BASELINE_REPRESENTATION
    )


def test_comparison_records_preregistered_policy() -> None:
    baseline = _report(
        BASELINE_REPRESENTATION,
        ndcg=0.60,
        mrr=0.50,
        recall=0.80,
    )

    candidate = _report(
        CANDIDATE_REPRESENTATION,
        ndcg=0.61,
        mrr=0.51,
        recall=0.90,
    )

    comparison = compare_dense_reports(
        baseline,
        candidate,
    )

    assert comparison["selection_policy"]["primary"] == "mean_ndcg_at_10"

    assert comparison["selection_policy"]["secondary"] == ("mean_canonical_reciprocal_rank")

    assert comparison["selection_policy"]["tertiary"] == "mean_recall_at_10"

    assert comparison["selection_policy"]["exact_tie"] == BASELINE_REPRESENTATION
