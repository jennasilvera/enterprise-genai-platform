import pytest

from enterprise_genai.routing.heuristic import (
    HeuristicRouter,
)


@pytest.fixture
def router() -> HeuristicRouter:
    return HeuristicRouter()


@pytest.mark.parametrize(
    (
        "question",
        "expected",
    ),
    [
        (
            ("Why is management concerned about supplier concentration at Acme?"),
            "retrieval",
        ),
        (
            ("What was Acme's EBITDA margin in 2026Q2?"),
            "sql",
        ),
        (
            (
                "Which customers are served by "
                "the same portfolio company that "
                "buys from Example Supplier?"
            ),
            "graph",
        ),
        (
            (
                "How did Acme's revenue change "
                "from 2025Q2 to 2026Q2, and why "
                "is management concerned about "
                "customer concentration?"
            ),
            "retrieval+sql",
        ),
        (
            (
                "Which portfolio company buys "
                "from Example Supplier, and why "
                "is management worried about its "
                "supply risk?"
            ),
            "retrieval+graph",
        ),
        (
            (
                "Which portfolio company buys "
                "from Example Supplier, and was "
                "its 2026Q2 net retention below "
                "100 percent?"
            ),
            "sql+graph",
        ),
        (
            (
                "Which portfolio company buys "
                "from Example Supplier, what was "
                "its EBITDA margin in 2026Q2, "
                "and why is management worried "
                "about supply risk?"
            ),
            "retrieval+sql+graph",
        ),
    ],
)
def test_route_examples(
    router: HeuristicRouter,
    question: str,
    expected: str,
) -> None:
    prediction = router.predict(question)

    assert prediction.route_label == expected

    assert not (prediction.fallback_used)


def test_financial_term_alone_does_not_force_sql(
    router: HeuristicRouter,
) -> None:
    prediction = router.predict("Why is management concerned about revenue concentration at Acme?")

    assert prediction.route_label == "retrieval"


def test_generic_question_uses_retrieval_fallback(
    router: HeuristicRouter,
) -> None:
    prediction = router.predict("Tell me about Acme.")

    assert prediction.route_label == "retrieval"

    assert prediction.fallback_used is True


def test_blank_question_is_rejected(
    router: HeuristicRouter,
) -> None:
    with pytest.raises(
        ValueError,
        match="must not be blank",
    ):
        router.predict("   ")
