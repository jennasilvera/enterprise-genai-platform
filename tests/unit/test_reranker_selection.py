from enterprise_genai.evaluation.reranker_selection import (
    BASELINE_NAME,
    CANDIDATE_NAME,
    select_reranker,
)


def _summary(
    *,
    recall: float,
    ndcg: float,
    mrr: float,
) -> dict[str, float]:
    return {
        "mean_recall_at_10": recall,
        "mean_ndcg_at_10": ndcg,
        "mean_canonical_reciprocal_rank": (mrr),
    }


def test_recall_guardrail_retains_baseline() -> None:
    result = select_reranker(
        _summary(
            recall=0.95,
            ndcg=0.80,
            mrr=0.80,
        ),
        _summary(
            recall=0.90,
            ndcg=0.99,
            mrr=1.00,
        ),
    )

    assert result["selected"] == BASELINE_NAME

    assert result["guardrail_passed"] is False


def test_higher_ndcg_selects_candidate() -> None:
    result = select_reranker(
        _summary(
            recall=0.95,
            ndcg=0.80,
            mrr=0.80,
        ),
        _summary(
            recall=0.95,
            ndcg=0.81,
            mrr=0.70,
        ),
    )

    assert result["selected"] == CANDIDATE_NAME


def test_lower_ndcg_retains_baseline() -> None:
    result = select_reranker(
        _summary(
            recall=0.95,
            ndcg=0.80,
            mrr=0.80,
        ),
        _summary(
            recall=0.95,
            ndcg=0.79,
            mrr=1.00,
        ),
    )

    assert result["selected"] == BASELINE_NAME


def test_ndcg_tie_higher_mrr_selects_candidate() -> None:
    result = select_reranker(
        _summary(
            recall=0.95,
            ndcg=0.80,
            mrr=0.80,
        ),
        _summary(
            recall=0.95,
            ndcg=0.80,
            mrr=0.81,
        ),
    )

    assert result["selected"] == CANDIDATE_NAME


def test_complete_tie_retains_baseline() -> None:
    result = select_reranker(
        _summary(
            recall=0.95,
            ndcg=0.80,
            mrr=0.80,
        ),
        _summary(
            recall=0.95,
            ndcg=0.80,
            mrr=0.80,
        ),
    )

    assert result["selected"] == BASELINE_NAME
