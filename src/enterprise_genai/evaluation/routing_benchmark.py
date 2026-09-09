from __future__ import annotations

import json
from pathlib import Path

from enterprise_genai.data.routing_models import (
    RoutingSet,
    RoutingSplit,
)
from enterprise_genai.data.routing_seed import (
    routing_seed_sha256,
)
from enterprise_genai.evaluation.routing_metrics import (
    routing_metrics,
)
from enterprise_genai.routing.heuristic import (
    HeuristicRouter,
)

EXPERIMENT_VERSION = "heuristic-router-development-v1"


def run_heuristic_router_benchmark(
    routing: RoutingSet,
    *,
    split: RoutingSplit,
    router: HeuristicRouter | None = None,
) -> dict[str, object]:
    selected_cases = [case for case in routing.cases if case.split == split]

    if not selected_cases:
        raise ValueError(f"Routing benchmark contains no cases for split={split!r}.")

    active_router = router if router is not None else HeuristicRouter()

    gold_routes: list[tuple[str, ...]] = []

    predicted_routes: list[tuple[str, ...]] = []

    case_reports: list[dict[str, object]] = []

    for case in selected_cases:
        prediction = active_router.predict(case.question)

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
                "matched_rules": list(prediction.matched_rules),
                "fallback_used": (prediction.fallback_used),
            }
        )

    aggregate = routing_metrics(
        gold_routes,
        predicted_routes,
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
        "router": (active_router.metadata()),
        "metrics": aggregate,
        "cases": case_reports,
    }


def deterministic_report_bytes(
    report: dict[str, object],
) -> bytes:
    payload = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    return (payload + "\n").encode()


def write_routing_report(
    report: dict[str, object],
    output: Path,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_bytes(deterministic_report_bytes(report))
