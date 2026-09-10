import pytest

from enterprise_genai.routing.nli_router import (
    ROUTE_HYPOTHESES,
    ROUTE_ORDER,
    route_label_to_tools,
    select_route_from_scores,
)


def test_all_seven_route_hypotheses_exist() -> None:
    assert tuple(ROUTE_HYPOTHESES) == ROUTE_ORDER

    assert len(ROUTE_HYPOTHESES) == 7

    assert all(hypothesis.strip() for hypothesis in ROUTE_HYPOTHESES.values())


@pytest.mark.parametrize(
    (
        "route",
        "tools",
    ),
    [
        (
            "retrieval",
            ("retrieval",),
        ),
        (
            "sql",
            ("sql",),
        ),
        (
            "graph",
            ("graph",),
        ),
        (
            "retrieval+sql",
            (
                "retrieval",
                "sql",
            ),
        ),
        (
            "retrieval+graph",
            (
                "retrieval",
                "graph",
            ),
        ),
        (
            "sql+graph",
            (
                "sql",
                "graph",
            ),
        ),
        (
            "retrieval+sql+graph",
            (
                "retrieval",
                "sql",
                "graph",
            ),
        ),
    ],
)
def test_route_label_to_tools(
    route: str,
    tools: tuple[str, ...],
) -> None:
    assert route_label_to_tools(route) == tools


@pytest.mark.parametrize(
    "winning_route",
    ROUTE_ORDER,
)
def test_score_selection_can_choose_each_route(
    winning_route: str,
) -> None:
    scores = {route: 0.1 for route in ROUTE_ORDER}

    scores[winning_route] = 0.9

    assert select_route_from_scores(scores) == winning_route


def test_score_tie_uses_frozen_route_order() -> None:
    scores = {route: 0.5 for route in ROUTE_ORDER}

    assert select_route_from_scores(scores) == "retrieval"


def test_incomplete_scores_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="seven canonical",
    ):
        select_route_from_scores(
            {
                "retrieval": 1.0,
            }
        )


def test_frozen_router_configuration_fingerprint() -> None:
    from enterprise_genai.routing.nli_router import (
        FROZEN_ROUTER_CONFIG_SHA256,
        nli_router_config_sha256,
    )

    assert (
        nli_router_config_sha256()
        == FROZEN_ROUTER_CONFIG_SHA256
        == "72d8ce61cdce386bb189cb70698d0f899bf94fa63b8f42796f1a19eaaca3e924"
    )


def test_non_finite_score_is_rejected() -> None:
    scores = {route: 0.5 for route in ROUTE_ORDER}

    scores["sql"] = float("nan")

    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        select_route_from_scores(scores)
