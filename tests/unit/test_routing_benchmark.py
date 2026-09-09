from pathlib import Path

import pytest

from enterprise_genai.data.routing_models import (
    RoutingCase,
    RoutingSet,
    canonical_route_label,
)
from enterprise_genai.evaluation.routing_benchmark import (
    deterministic_report_bytes,
    run_heuristic_router_benchmark,
    write_routing_report,
)
from enterprise_genai.routing.heuristic import (
    HeuristicRouter,
)


def _case(
    routing_id: str,
    question: str,
    tools: list[str],
    *,
    split: str = "development",
) -> RoutingCase:
    return RoutingCase(
        routing_id=routing_id,
        question=question,
        split=split,
        template_family=(f"synthetic-{routing_id}"),
        difficulty="easy",
        required_tools=tools,
        route_label=(canonical_route_label(tools)),
        rationale=("Synthetic unit-test case."),
        source_entity_ids=[f"ENTITY-{routing_id}"],
    )


def _synthetic_set() -> RoutingSet:
    return RoutingSet(
        dataset_version=("synthetic-routing-unit"),
        routing_version=("synthetic-routing-unit-v1"),
        cases=[
            _case(
                "SYN-001",
                ("Why is management concerned about supplier concentration at ExampleCo?"),
                [
                    "retrieval",
                ],
            ),
            _case(
                "SYN-002",
                ("What was ExampleCo's EBITDA margin in 2026Q2?"),
                [
                    "sql",
                ],
            ),
            _case(
                "SYN-003",
                (
                    "Which customers are "
                    "served by the same "
                    "portfolio company that "
                    "buys from Example Supply?"
                ),
                [
                    "graph",
                ],
            ),
            _case(
                "SYN-004",
                (
                    "Which portfolio company "
                    "buys from Example Supply, "
                    "what was its EBITDA margin "
                    "in 2026Q2, and why is "
                    "management worried about "
                    "supply concentration?"
                ),
                [
                    "retrieval",
                    "sql",
                    "graph",
                ],
            ),
            _case(
                "SYN-TRAIN-001",
                "Tell me about TrainingCo.",
                [
                    "retrieval",
                ],
                split="train",
            ),
        ],
    )


def test_benchmark_uses_only_requested_split() -> None:
    report = run_heuristic_router_benchmark(
        _synthetic_set(),
        split="development",
        router=HeuristicRouter(),
    )

    assert report["benchmark"]["cases"] == 4

    routing_ids = {case["routing_id"] for case in report["cases"]}

    assert "SYN-TRAIN-001" not in routing_ids


def test_synthetic_benchmark_is_perfect() -> None:
    report = run_heuristic_router_benchmark(
        _synthetic_set(),
        split="development",
    )

    metrics = report["metrics"]

    assert metrics["exact_route_set_accuracy"] == 1.0

    assert metrics["macro_f1"] == 1.0

    assert metrics["required_tool_omission_rate"] == 0.0


def test_missing_split_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="no cases",
    ):
        run_heuristic_router_benchmark(
            _synthetic_set(),
            split="locked_holdout",
        )


def test_report_serialization_is_deterministic(
    tmp_path: Path,
) -> None:
    report = run_heuristic_router_benchmark(
        _synthetic_set(),
        split="development",
    )

    first = tmp_path / "first.json"

    second = tmp_path / "second.json"

    write_routing_report(
        report,
        first,
    )

    write_routing_report(
        report,
        second,
    )

    assert first.read_bytes() == second.read_bytes()

    assert first.read_bytes() == deterministic_report_bytes(report)

    assert first.read_bytes().endswith(b"\n")
