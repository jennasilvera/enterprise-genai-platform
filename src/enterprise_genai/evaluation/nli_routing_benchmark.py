from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Protocol

from enterprise_genai.data.routing_models import (
    RouteLabel,
    RoutingSet,
    RoutingSplit,
    ToolFamily,
    canonical_route_label,
)
from enterprise_genai.data.routing_seed import (
    routing_seed_sha256,
)
from enterprise_genai.evaluation.routing_metrics import (
    routing_metrics,
)
from enterprise_genai.routing.nli_router import (
    ROUTE_ORDER,
    select_route_from_scores,
)

EXPERIMENT_VERSION = "pretrained-nli-router-development-v1"


class RouteScoreLike(Protocol):
    route_label: RouteLabel
    hypothesis: str
    entailment_probability: float


class PredictionLike(Protocol):
    predicted_tools: tuple[ToolFamily, ...]
    route_label: RouteLabel
    route_scores: tuple[RouteScoreLike, ...]


class NliRouterLike(Protocol):
    def predict(
        self,
        question: str,
    ) -> PredictionLike: ...

    def metadata(
        self,
    ) -> dict[
        str,
        object,
    ]: ...


def run_pretrained_nli_router_benchmark(
    routing: RoutingSet,
    *,
    split: RoutingSplit,
    router: NliRouterLike,
) -> dict[str, object]:
    selected_cases = [case for case in routing.cases if case.split == split]

    if not selected_cases:
        raise ValueError(f"Routing benchmark contains no cases for split={split!r}.")

    gold_routes: list[tuple[str, ...]] = []

    predicted_routes: list[tuple[str, ...]] = []

    case_reports: list[dict[str, object]] = []

    for case in selected_cases:
        prediction = router.predict(case.question)

        score_labels = tuple(score.route_label for score in prediction.route_scores)

        if score_labels != ROUTE_ORDER:
            raise RuntimeError("Route scores do not follow the frozen canonical route order.")

        score_map = {
            score.route_label: (score.entailment_probability) for score in prediction.route_scores
        }

        for route, value in score_map.items():
            if not math.isfinite(value):
                raise RuntimeError(f"Non-finite entailment score for {route!r}.")

        score_selected = select_route_from_scores(score_map)

        if score_selected != prediction.route_label:
            raise RuntimeError("Prediction route does not match frozen score decoding.")

        canonical_prediction = canonical_route_label(prediction.predicted_tools)

        if canonical_prediction != prediction.route_label:
            raise RuntimeError("Predicted tools do not match predicted route label.")

        gold_tools = tuple(case.required_tools)

        predicted_tools = tuple(prediction.predicted_tools)

        gold_routes.append(gold_tools)

        predicted_routes.append(predicted_tools)

        missing_tools = [tool for tool in gold_tools if tool not in predicted_tools]

        extra_tools = [tool for tool in predicted_tools if tool not in gold_tools]

        case_reports.append(
            {
                "routing_id": (case.routing_id),
                "question": (case.question),
                "template_family": (case.template_family),
                "difficulty": (case.difficulty),
                "gold_tools": list(gold_tools),
                "gold_route_label": (case.route_label),
                "predicted_tools": list(predicted_tools),
                "predicted_route_label": (prediction.route_label),
                "exact_match": (gold_tools == predicted_tools),
                "missing_required_tools": (missing_tools),
                "unnecessary_tools": (extra_tools),
                "route_scores": [
                    {
                        "route_label": (score.route_label),
                        "hypothesis": (score.hypothesis),
                        "entailment_probability": (score.entailment_probability),
                    }
                    for score in prediction.route_scores
                ],
            }
        )

    return {
        "experiment_version": (EXPERIMENT_VERSION),
        "scope": (f"{split}-routing-baseline"),
        "benchmark": {
            "dataset_version": (routing.dataset_version),
            "routing_version": (routing.routing_version),
            "routing_sha256": (routing_seed_sha256(routing)),
            "split": split,
            "cases": len(selected_cases),
        },
        "router": (router.metadata()),
        "metrics": routing_metrics(
            gold_routes,
            predicted_routes,
        ),
        "cases": case_reports,
    }


def deterministic_nli_report_bytes(
    report: dict[str, object],
) -> bytes:
    payload = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    return (payload + "\n").encode()


def write_nli_routing_report(
    report: dict[str, object],
    output: Path,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_bytes(deterministic_nli_report_bytes(report))
