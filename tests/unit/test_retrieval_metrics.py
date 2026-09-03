import pytest

from enterprise_genai.evaluation.retrieval_metrics import (
    canonical_reciprocal_rank,
    ndcg_at_k,
    recall_at_k,
)


def test_recall_at_k() -> None:
    ranked = [
        "EVID-A",
        "EVID-X",
        "EVID-B",
    ]

    relevant = {
        "EVID-A",
        "EVID-B",
    }

    assert (
        recall_at_k(
            ranked,
            relevant,
            1,
        )
        == 0.5
    )

    assert (
        recall_at_k(
            ranked,
            relevant,
            3,
        )
        == 1.0
    )


def test_canonical_reciprocal_rank() -> None:
    ranked = [
        "EVID-WEAK",
        "EVID-CANONICAL",
    ]

    assert canonical_reciprocal_rank(
        ranked,
        {"EVID-CANONICAL"},
    ) == pytest.approx(0.5)


def test_ndcg_rewards_canonical_evidence_first() -> None:
    relevance = {
        "EVID-CANONICAL": 3,
        "EVID-SUPPORT": 1,
    }

    ideal = ndcg_at_k(
        [
            "EVID-CANONICAL",
            "EVID-SUPPORT",
        ],
        relevance,
        2,
    )

    reversed_order = ndcg_at_k(
        [
            "EVID-SUPPORT",
            "EVID-CANONICAL",
        ],
        relevance,
        2,
    )

    assert ideal == pytest.approx(1.0)
    assert reversed_order < ideal
