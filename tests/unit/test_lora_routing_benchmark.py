from pathlib import Path

import pytest

from enterprise_genai.data.routing_models import (
    RoutingCase,
)
from enterprise_genai.evaluation.lora_routing_benchmark import (
    adapter_manifest,
    deterministic_lora_report_bytes,
    evaluate_route_predictions,
    route_label_to_tools,
    select_best_epoch,
    select_best_seed,
)
from enterprise_genai.routing.lora_training_config import (
    ROUTE_ORDER,
)


@pytest.mark.parametrize(
    "route",
    ROUTE_ORDER,
)
def test_route_label_to_tools(
    route: str,
) -> None:
    assert "+".join(route_label_to_tools(route)) == route


def _case(
    routing_id: str,
    route: str,
) -> RoutingCase:
    return RoutingCase(
        routing_id=(routing_id),
        question=(f"Synthetic {routing_id}."),
        split="development",
        template_family=(f"synthetic-{routing_id}"),
        difficulty="easy",
        required_tools=(route.split("+")),
        route_label=route,
        rationale=("Synthetic unit case."),
        source_entity_ids=[routing_id],
    )


def test_perfect_prediction_metrics() -> None:
    cases = [
        _case(
            f"SYN-{index}",
            route,
        )
        for index, route in enumerate(ROUTE_ORDER)
    ]

    result = evaluate_route_predictions(
        cases,
        list(ROUTE_ORDER),
    )

    assert result["metrics"]["exact_route_set_accuracy"] == 1.0


def _metrics(
    *,
    exact: float,
    f1: float,
    omission: float,
    addition: float,
) -> dict[str, float]:
    return {
        "exact_route_set_accuracy": (exact),
        "macro_f1": f1,
        "required_tool_omission_rate": (omission),
        "unnecessary_tool_addition_rate": (addition),
    }


def test_checkpoint_selection_hierarchy() -> None:
    records = [
        {
            "epoch": 1,
            "metrics": _metrics(
                exact=0.8,
                f1=0.9,
                omission=0.0,
                addition=0.0,
            ),
        },
        {
            "epoch": 2,
            "metrics": _metrics(
                exact=0.9,
                f1=0.1,
                omission=1.0,
                addition=1.0,
            ),
        },
    ]

    assert select_best_epoch(records)["epoch"] == 2


def test_checkpoint_tie_prefers_earlier_epoch() -> None:
    metrics = _metrics(
        exact=1.0,
        f1=1.0,
        omission=0.0,
        addition=0.0,
    )

    records = [
        {
            "epoch": 1,
            "metrics": metrics,
        },
        {
            "epoch": 2,
            "metrics": metrics,
        },
    ]

    assert select_best_epoch(records)["epoch"] == 1


def test_seed_selection_hierarchy() -> None:
    records = [
        {
            "seed": 1729,
            "best_metrics": _metrics(
                exact=0.7,
                f1=1.0,
                omission=0.0,
                addition=0.0,
            ),
        },
        {
            "seed": 2718,
            "best_metrics": _metrics(
                exact=0.8,
                f1=0.1,
                omission=1.0,
                addition=1.0,
            ),
        },
    ]

    assert select_best_seed(records)["seed"] == 2718


def test_seed_tie_prefers_frozen_order() -> None:
    metrics = _metrics(
        exact=1.0,
        f1=1.0,
        omission=0.0,
        addition=0.0,
    )

    records = [
        {
            "seed": 1729,
            "best_metrics": metrics,
        },
        {
            "seed": 2718,
            "best_metrics": metrics,
        },
    ]

    assert select_best_seed(records)["seed"] == 1729


def test_report_serialization_is_deterministic() -> None:
    report = {
        "b": 2,
        "a": 1,
    }

    first = deterministic_lora_report_bytes(report)

    second = deterministic_lora_report_bytes(report)

    assert first == second

    assert first.endswith(b"\n")


def test_adapter_manifest(
    tmp_path: Path,
) -> None:
    (tmp_path / "adapter_config.json").write_bytes(b'{"test":true}\n')

    (tmp_path / "adapter_model.safetensors").write_bytes(b"synthetic-model")

    first = adapter_manifest(tmp_path)

    second = adapter_manifest(tmp_path)

    assert first == second

    assert len(first["files"]) == 2
