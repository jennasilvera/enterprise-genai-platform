from enterprise_genai.evaluation.hybrid_selection import (
    DENSE_REFERENCE_ID,
    HYBRID_CANDIDATE_ID,
    select_hybrid_or_dense,
)
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
)
from enterprise_genai.retrieval.rrf import (
    RRF_VERSION,
)


def _dense_report(
    *,
    ndcg: float,
    mrr: float,
    recall: float,
):
    return {
        "selected_representation": (DENSE_DOCUMENT_TITLE_TEXT_VERSION),
        "candidate_benchmark": {
            "summary": {
                "retrieval_eligible": {
                    "mean_ndcg_at_10": (ndcg),
                    "mean_canonical_reciprocal_rank": (mrr),
                    "mean_recall_at_10": (recall),
                }
            }
        },
    }


def _hybrid_report(
    *,
    ndcg: float,
    mrr: float,
    recall: float,
):
    return {
        "fusion": {"version": RRF_VERSION},
        "summary": {
            "retrieval_eligible": {
                "mean_ndcg_at_10": ndcg,
                "mean_canonical_reciprocal_rank": (mrr),
                "mean_recall_at_10": (recall),
            }
        },
    }


def test_primary_metric_selects_hybrid() -> None:
    assert (
        select_hybrid_or_dense(
            _dense_report(
                ndcg=0.70,
                mrr=0.90,
                recall=1.0,
            ),
            _hybrid_report(
                ndcg=0.71,
                mrr=0.10,
                recall=0.1,
            ),
        )
        == HYBRID_CANDIDATE_ID
    )


def test_primary_metric_can_retain_dense() -> None:
    assert (
        select_hybrid_or_dense(
            _dense_report(
                ndcg=0.71,
                mrr=0.10,
                recall=0.1,
            ),
            _hybrid_report(
                ndcg=0.70,
                mrr=1.0,
                recall=1.0,
            ),
        )
        == DENSE_REFERENCE_ID
    )


def test_secondary_breaks_primary_tie() -> None:
    assert (
        select_hybrid_or_dense(
            _dense_report(
                ndcg=0.70,
                mrr=0.60,
                recall=1.0,
            ),
            _hybrid_report(
                ndcg=0.70,
                mrr=0.61,
                recall=0.1,
            ),
        )
        == HYBRID_CANDIDATE_ID
    )


def test_tertiary_breaks_first_two_ties() -> None:
    assert (
        select_hybrid_or_dense(
            _dense_report(
                ndcg=0.70,
                mrr=0.60,
                recall=0.8,
            ),
            _hybrid_report(
                ndcg=0.70,
                mrr=0.60,
                recall=0.9,
            ),
        )
        == HYBRID_CANDIDATE_ID
    )


def test_exact_tie_retains_dense() -> None:
    assert (
        select_hybrid_or_dense(
            _dense_report(
                ndcg=0.70,
                mrr=0.60,
                recall=0.8,
            ),
            _hybrid_report(
                ndcg=0.70,
                mrr=0.60,
                recall=0.8,
            ),
        )
        == DENSE_REFERENCE_ID
    )
