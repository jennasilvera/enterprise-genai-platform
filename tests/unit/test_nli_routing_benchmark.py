from dataclasses import dataclass
from pathlib import Path

import pytest

from enterprise_genai.data.routing_models import (
    RouteLabel,
    RoutingCase,
    RoutingSet,
    ToolFamily,
    canonical_route_label,
)
from enterprise_genai.evaluation.nli_routing_benchmark import (
    deterministic_nli_report_bytes,
    run_pretrained_nli_router_benchmark,
    write_nli_routing_report,
)
from enterprise_genai.routing.nli_router import (
    ROUTE_HYPOTHESES,
    ROUTE_ORDER,
    route_label_to_tools,
)


@dataclass(frozen=True)
class FakeRouteScore:
    route_label: RouteLabel
    hypothesis: str
    entailment_probability: float


@dataclass(frozen=True)
class FakePrediction:
    predicted_tools: tuple[ToolFamily, ...]
    route_label: RouteLabel
    route_scores: tuple[FakeRouteScore, ...]


class FakeRouter:
    def __init__(
        self,
        predictions: dict[
            str,
            RouteLabel,
        ],
    ) -> None:
        self._predictions = predictions

    def predict(
        self,
        question: str,
    ) -> FakePrediction:
        selected = self._predictions[question]

        scores = tuple(
            FakeRouteScore(
                route_label=route,
                hypothesis=(ROUTE_HYPOTHESES[route]),
                entailment_probability=(0.9 if route == selected else 0.1),
            )
            for route in ROUTE_ORDER
        )

        return FakePrediction(
            predicted_tools=(route_label_to_tools(selected)),
            route_label=selected,
            route_scores=scores,
        )

    def metadata(
        self,
    ) -> dict[
        str,
        object,
    ]:
        return {
            "router_version": ("fake-router-v1"),
            "training_performed": (False),
        }


def _case(
    routing_id: str,
    question: str,
    tools: list[ToolFamily],
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
        rationale=("Synthetic benchmark case."),
        source_entity_ids=[f"ENTITY-{routing_id}"],
    )


def _synthetic_set() -> RoutingSet:
    return RoutingSet(
        dataset_version=("synthetic-routing-unit"),
        routing_version=("synthetic-routing-nli-v1"),
        cases=[
            _case(
                "NLI-001",
                "Synthetic retrieval question.",
                [
                    "retrieval",
                ],
            ),
            _case(
                "NLI-002",
                "Synthetic SQL question.",
                [
                    "sql",
                ],
            ),
            _case(
                "NLI-003",
                "Synthetic graph question.",
                [
                    "graph",
                ],
            ),
            _case(
                "NLI-004",
                "Synthetic all-tools question.",
                [
                    "retrieval",
                    "sql",
                    "graph",
                ],
            ),
            _case(
                "NLI-TRAIN-001",
                "Synthetic training question.",
                [
                    "retrieval",
                ],
                split="train",
            ),
        ],
    )


def _perfect_router() -> FakeRouter:
    return FakeRouter(
        {
            "Synthetic retrieval question.": ("retrieval"),
            "Synthetic SQL question.": ("sql"),
            "Synthetic graph question.": ("graph"),
            "Synthetic all-tools question.": ("retrieval+sql+graph"),
        }
    )


def test_benchmark_uses_only_requested_split() -> None:
    report = run_pretrained_nli_router_benchmark(
        _synthetic_set(),
        split="development",
        router=_perfect_router(),
    )

    assert report["benchmark"]["cases"] == 4

    routing_ids = {case["routing_id"] for case in report["cases"]}

    assert "NLI-TRAIN-001" not in routing_ids


def test_synthetic_benchmark_is_perfect() -> None:
    report = run_pretrained_nli_router_benchmark(
        _synthetic_set(),
        split="development",
        router=_perfect_router(),
    )

    metrics = report["metrics"]

    assert metrics["exact_route_set_accuracy"] == 1.0

    assert metrics["macro_f1"] == 1.0

    assert metrics["required_tool_omission_rate"] == 0.0


def test_route_scores_are_retained_in_frozen_order() -> None:
    report = run_pretrained_nli_router_benchmark(
        _synthetic_set(),
        split="development",
        router=_perfect_router(),
    )

    first = report["cases"][0]

    assert tuple(score["route_label"] for score in first["route_scores"]) == ROUTE_ORDER


def test_missing_split_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="no cases",
    ):
        run_pretrained_nli_router_benchmark(
            _synthetic_set(),
            split="locked_holdout",
            router=_perfect_router(),
        )


def test_report_serialization_is_deterministic(
    tmp_path: Path,
) -> None:
    report = run_pretrained_nli_router_benchmark(
        _synthetic_set(),
        split="development",
        router=_perfect_router(),
    )

    first = tmp_path / "first.json"

    second = tmp_path / "second.json"

    write_nli_routing_report(
        report,
        first,
    )

    write_nli_routing_report(
        report,
        second,
    )

    assert first.read_bytes() == second.read_bytes()

    assert first.read_bytes() == deterministic_nli_report_bytes(report)
