from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from enterprise_genai.data.routing_models import (
    RouteLabel,
    RoutingCase,
    ToolFamily,
)
from enterprise_genai.evaluation.routing_metrics import (
    routing_metrics,
)
from enterprise_genai.routing.lora_training_config import (
    ROUTE_ORDER,
    TRAINING_SEEDS,
)


def route_label_to_tools(
    route_label: RouteLabel,
) -> tuple[ToolFamily, ...]:
    return cast(
        tuple[ToolFamily, ...],
        tuple(route_label.split("+")),
    )


def evaluate_route_predictions(
    cases: Sequence[RoutingCase],
    predicted_labels: Sequence[RouteLabel],
    *,
    probability_rows: (
        Sequence[
            Mapping[
                RouteLabel,
                float,
            ]
        ]
        | None
    ) = None,
) -> dict[str, object]:
    if len(cases) != len(predicted_labels):
        raise ValueError("Cases and predictions must have matching lengths.")

    if probability_rows is not None and len(probability_rows) != len(cases):
        raise ValueError("Probability rows and cases must have matching lengths.")

    gold_routes: list[tuple[ToolFamily, ...]] = []

    predicted_routes: list[tuple[ToolFamily, ...]] = []

    case_reports: list[dict[str, object]] = []

    for index, (
        case,
        predicted_label,
    ) in enumerate(
        zip(
            cases,
            predicted_labels,
            strict=True,
        )
    ):
        if predicted_label not in ROUTE_ORDER:
            raise ValueError(f"Unknown predicted route {predicted_label!r}.")

        gold_tools = tuple(case.required_tools)

        predicted_tools = route_label_to_tools(predicted_label)

        gold_routes.append(gold_tools)

        predicted_routes.append(predicted_tools)

        missing = [tool for tool in gold_tools if tool not in predicted_tools]

        extra = [tool for tool in predicted_tools if tool not in gold_tools]

        report: dict[
            str,
            object,
        ] = {
            "routing_id": (case.routing_id),
            "question": (case.question),
            "template_family": (case.template_family),
            "difficulty": (case.difficulty),
            "gold_tools": list(gold_tools),
            "gold_route_label": (case.route_label),
            "predicted_tools": list(predicted_tools),
            "predicted_route_label": (predicted_label),
            "exact_match": (gold_tools == predicted_tools),
            "missing_required_tools": (missing),
            "unnecessary_tools": (extra),
        }

        if probability_rows is not None:
            row = probability_rows[index]

            if set(row) != set(ROUTE_ORDER):
                raise ValueError("Probability row must contain exactly seven canonical routes.")

            probability_report = []

            total = 0.0

            for route in ROUTE_ORDER:
                value = float(row[route])

                if not math.isfinite(value):
                    raise ValueError(f"Route probability for {route!r} must be finite.")

                if value < 0.0 or value > 1.0:
                    raise ValueError(f"Route probability for {route!r} must lie in [0, 1].")

                total += value

                probability_report.append(
                    {
                        "route_label": (route),
                        "probability": (value),
                    }
                )

            if not math.isclose(
                total,
                1.0,
                rel_tol=1e-5,
                abs_tol=1e-5,
            ):
                raise ValueError("Route probabilities must sum to one.")

            report["route_probabilities"] = probability_report

        case_reports.append(report)

    return {
        "metrics": routing_metrics(
            gold_routes,
            predicted_routes,
        ),
        "cases": (case_reports),
    }


def _metric(
    metrics: Mapping[
        str,
        object,
    ],
    key: str,
) -> float:
    value = metrics[key]

    if not isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        raise TypeError(f"Metric {key!r} must be numeric.")

    value = float(value)

    if not math.isfinite(value):
        raise ValueError(f"Metric {key!r} must be finite.")

    return value


def checkpoint_rank(
    record: Mapping[
        str,
        object,
    ],
) -> tuple[
    float,
    float,
    float,
    float,
    int,
]:
    epoch = record["epoch"]

    metrics = record["metrics"]

    if not isinstance(
        epoch,
        int,
    ):
        raise TypeError("Epoch must be int.")

    if not isinstance(
        metrics,
        Mapping,
    ):
        raise TypeError("Metrics must be a mapping.")

    return (
        _metric(
            metrics,
            "exact_route_set_accuracy",
        ),
        _metric(
            metrics,
            "macro_f1",
        ),
        -_metric(
            metrics,
            "required_tool_omission_rate",
        ),
        -_metric(
            metrics,
            "unnecessary_tool_addition_rate",
        ),
        -epoch,
    )


def select_best_epoch(
    records: Sequence[
        Mapping[
            str,
            object,
        ]
    ],
) -> Mapping[
    str,
    object,
]:
    if not records:
        raise ValueError("At least one epoch record is required.")

    return max(
        records,
        key=checkpoint_rank,
    )


def seed_rank(
    record: Mapping[
        str,
        object,
    ],
) -> tuple[
    float,
    float,
    float,
    float,
    int,
]:
    seed = record["seed"]

    metrics = record["best_metrics"]

    if not isinstance(
        seed,
        int,
    ):
        raise TypeError("Seed must be int.")

    if seed not in TRAINING_SEEDS:
        raise ValueError("Seed is not in the frozen seed set.")

    if not isinstance(
        metrics,
        Mapping,
    ):
        raise TypeError("Best metrics must be a mapping.")

    seed_position = TRAINING_SEEDS.index(seed)

    return (
        _metric(
            metrics,
            "exact_route_set_accuracy",
        ),
        _metric(
            metrics,
            "macro_f1",
        ),
        -_metric(
            metrics,
            "required_tool_omission_rate",
        ),
        -_metric(
            metrics,
            "unnecessary_tool_addition_rate",
        ),
        -seed_position,
    )


def select_best_seed(
    records: Sequence[
        Mapping[
            str,
            object,
        ]
    ],
) -> Mapping[
    str,
    object,
]:
    if not records:
        raise ValueError("At least one seed record is required.")

    return max(
        records,
        key=seed_rank,
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def adapter_manifest(
    adapter_dir: Path,
) -> dict[str, object]:
    expected = (
        "adapter_config.json",
        "adapter_model.safetensors",
    )

    observed = tuple(sorted(path.name for path in adapter_dir.iterdir() if path.is_file()))

    if observed != expected:
        raise RuntimeError(f"Unexpected adapter files: {observed!r}.")

    return {
        "files": [
            {
                "name": name,
                "bytes": (adapter_dir.joinpath(name).stat().st_size),
                "sha256": (sha256_file(adapter_dir / name)),
            }
            for name in expected
        ],
    }


def deterministic_lora_report_bytes(
    report: Mapping[
        str,
        object,
    ],
) -> bytes:
    payload = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    return (payload + "\n").encode()


def write_lora_report(
    report: Mapping[
        str,
        object,
    ],
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(deterministic_lora_report_bytes(report))
