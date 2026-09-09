import pytest

from enterprise_genai.evaluation.routing_metrics import (
    routing_metrics,
)


def test_perfect_routing_metrics() -> None:
    metrics = routing_metrics(
        [
            ("retrieval",),
            (
                "sql",
                "graph",
            ),
        ],
        [
            ("retrieval",),
            (
                "sql",
                "graph",
            ),
        ],
    )

    assert metrics["exact_route_set_accuracy"] == 1.0

    assert metrics["macro_f1"] == 1.0

    assert metrics["required_tool_omission_rate"] == 0.0

    assert metrics["unnecessary_tool_addition_rate"] == 0.0

    assert metrics["hamming_loss"] == 0.0


def test_mixed_routing_metrics() -> None:
    metrics = routing_metrics(
        [
            ("retrieval",),
            (
                "sql",
                "graph",
            ),
        ],
        [
            ("retrieval",),
            (
                "retrieval",
                "sql",
            ),
        ],
    )

    assert metrics["exact_route_set_accuracy"] == 0.5

    assert metrics["required_tool_omission_rate"] == pytest.approx(1 / 3)

    assert metrics["unnecessary_tool_addition_rate"] == pytest.approx(1 / 3)

    assert metrics["under_routing_case_rate"] == 0.5

    assert metrics["over_routing_case_rate"] == 0.5

    assert metrics["hamming_loss"] == pytest.approx(1 / 3)

    assert metrics["macro_f1"] == pytest.approx(((2 / 3) + 1 + 0) / 3)


def test_length_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="lengths must match",
    ):
        routing_metrics(
            [
                ("retrieval",),
            ],
            [
                ("retrieval",),
                ("sql",),
            ],
        )


def test_unknown_tool_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Unknown routing tools",
    ):
        routing_metrics(
            [
                ("retrieval",),
            ],
            [
                ("unknown",),
            ],
        )
