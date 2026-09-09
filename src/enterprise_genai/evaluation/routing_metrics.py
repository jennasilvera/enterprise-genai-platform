from __future__ import annotations

from collections.abc import Iterable, Sequence

from enterprise_genai.data.routing_models import (
    TOOL_ORDER,
)


def _safe_divide(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def _f1(
    precision: float,
    recall: float,
) -> float:
    denominator = precision + recall

    if denominator == 0:
        return 0.0

    return 2 * precision * recall / denominator


def routing_metrics(
    gold_routes: Sequence[Iterable[str]],
    predicted_routes: Sequence[Iterable[str]],
) -> dict[str, object]:
    if not gold_routes:
        raise ValueError("Routing metrics require at least one case.")

    if len(gold_routes) != len(predicted_routes):
        raise ValueError("Gold and prediction lengths must match.")

    valid_tools = set(TOOL_ORDER)

    normalized_gold: list[set[str]] = []

    normalized_predicted: list[set[str]] = []

    for gold, predicted in zip(
        gold_routes,
        predicted_routes,
        strict=True,
    ):
        gold_set = set(gold)

        predicted_set = set(predicted)

        unknown = (gold_set | predicted_set) - valid_tools

        if unknown:
            raise ValueError(f"Unknown routing tools: {sorted(unknown)}.")

        if not gold_set:
            raise ValueError("Gold route cannot be empty.")

        if not predicted_set:
            raise ValueError("Predicted route cannot be empty.")

        normalized_gold.append(gold_set)

        normalized_predicted.append(predicted_set)

    cases = len(normalized_gold)

    exact_matches = 0
    hamming_errors = 0
    missing_required = 0
    required_total = 0
    unnecessary_added = 0
    unnecessary_opportunities = 0
    under_routed_cases = 0
    over_routed_cases = 0

    per_tool: dict[
        str,
        dict[str, float | int],
    ] = {}

    for gold, predicted in zip(
        normalized_gold,
        normalized_predicted,
        strict=True,
    ):
        if gold == predicted:
            exact_matches += 1

        missing = gold - predicted

        extra = predicted - gold

        if missing:
            under_routed_cases += 1

        if extra:
            over_routed_cases += 1

        missing_required += len(missing)

        required_total += len(gold)

        unnecessary_added += len(extra)

        unnecessary_opportunities += len(valid_tools) - len(gold)

        hamming_errors += len(gold ^ predicted)

    f1_values: list[float] = []

    precision_values: list[float] = []

    recall_values: list[float] = []

    for tool in TOOL_ORDER:
        true_positive = sum(
            1
            for gold, predicted in zip(
                normalized_gold,
                normalized_predicted,
                strict=True,
            )
            if (tool in gold and tool in predicted)
        )

        false_positive = sum(
            1
            for gold, predicted in zip(
                normalized_gold,
                normalized_predicted,
                strict=True,
            )
            if (tool not in gold and tool in predicted)
        )

        false_negative = sum(
            1
            for gold, predicted in zip(
                normalized_gold,
                normalized_predicted,
                strict=True,
            )
            if (tool in gold and tool not in predicted)
        )

        precision = _safe_divide(
            true_positive,
            (true_positive + false_positive),
        )

        recall = _safe_divide(
            true_positive,
            (true_positive + false_negative),
        )

        f1 = _f1(
            precision,
            recall,
        )

        precision_values.append(precision)

        recall_values.append(recall)

        f1_values.append(f1)

        per_tool[tool] = {
            "true_positive": (true_positive),
            "false_positive": (false_positive),
            "false_negative": (false_negative),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return {
        "cases": cases,
        "exact_route_set_accuracy": (exact_matches / cases),
        "macro_precision": (sum(precision_values) / len(precision_values)),
        "macro_recall": (sum(recall_values) / len(recall_values)),
        "macro_f1": (sum(f1_values) / len(f1_values)),
        "hamming_loss": (hamming_errors / (cases * len(valid_tools))),
        "required_tool_omission_rate": (
            _safe_divide(
                missing_required,
                required_total,
            )
        ),
        "unnecessary_tool_addition_rate": (
            _safe_divide(
                unnecessary_added,
                unnecessary_opportunities,
            )
        ),
        "under_routing_case_rate": (under_routed_cases / cases),
        "over_routing_case_rate": (over_routed_cases / cases),
        "per_tool": per_tool,
    }
