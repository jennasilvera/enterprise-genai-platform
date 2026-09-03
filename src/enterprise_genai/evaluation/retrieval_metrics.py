import math


def recall_at_k(
    ranked_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    if not relevant_ids:
        raise ValueError("Recall requires at least one relevant item.")

    retrieved = set(ranked_ids[:k])

    return len(retrieved & relevant_ids) / len(relevant_ids)


def canonical_reciprocal_rank(
    ranked_ids: list[str],
    canonical_ids: set[str],
) -> float:
    if not canonical_ids:
        raise ValueError("Canonical reciprocal rank requires grade-3 evidence.")

    for rank, item_id in enumerate(
        ranked_ids,
        start=1,
    ):
        if item_id in canonical_ids:
            return 1.0 / rank

    return 0.0


def dcg_at_k(
    ranked_ids: list[str],
    relevance_by_id: dict[str, int],
    k: int,
) -> float:
    score = 0.0

    for rank, item_id in enumerate(
        ranked_ids[:k],
        start=1,
    ):
        relevance = relevance_by_id.get(
            item_id,
            0,
        )

        gain = (2**relevance) - 1

        score += gain / math.log2(rank + 1)

    return score


def ndcg_at_k(
    ranked_ids: list[str],
    relevance_by_id: dict[str, int],
    k: int,
) -> float:
    actual = dcg_at_k(
        ranked_ids,
        relevance_by_id,
        k,
    )

    ideal_grades = sorted(
        relevance_by_id.values(),
        reverse=True,
    )[:k]

    ideal = sum(
        ((2**grade) - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(
            ideal_grades,
            start=1,
        )
    )

    if ideal == 0:
        return 0.0

    return actual / ideal
