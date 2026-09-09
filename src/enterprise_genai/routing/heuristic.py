from __future__ import annotations

import re
from dataclasses import dataclass

from enterprise_genai.data.routing_models import (
    RouteLabel,
    ToolFamily,
    canonical_route_label,
)

ROUTER_VERSION = "heuristic-router-v1"
QUESTION_REPRESENTATION_VERSION = "question-text-v1"
FALLBACK_TOOL: ToolFamily = "retrieval"

_PERIOD_RE = re.compile(
    r"\b20\d{2}q[1-4]\b",
    flags=re.IGNORECASE,
)

_SQL_METRIC_CUES = (
    "revenue",
    "ebitda",
    "net retention",
    "ownership stake",
)

_SQL_QUANTITATIVE_CUES = (
    "what percentage",
    "by what percentage",
    "how much",
    "below",
    "above",
    "exceed",
    "account for more than",
    "margin",
    "change from",
)

_SQL_CUSTOMER_COUNT_CUES = (
    "how many customers",
    "customer count",
)

_GRAPH_RELATION_CUES = (
    "which portfolio company buys from",
    "which portfolio company serves",
    "who supplies",
    "which suppliers",
    "which customers",
    "customers and suppliers",
    "customers does",
    "suppliers does",
    "same portfolio company",
    "buys from",
    "served by",
    "serves",
)

_RETRIEVAL_INTENT_CUES = (
    "explanation",
    "concern",
    "concerned",
    "worried",
    "highlighted",
    "characterize",
    "impact",
    "why",
)


@dataclass(frozen=True)
class HeuristicRoutePrediction:
    predicted_tools: tuple[ToolFamily, ...]
    route_label: RouteLabel
    matched_rules: tuple[str, ...]
    fallback_used: bool


def _contains_any(
    text: str,
    phrases: tuple[str, ...],
) -> bool:
    return any(phrase in text for phrase in phrases)


def _has_retrieval_intent(
    text: str,
) -> bool:
    management_intent = "management" in text and _contains_any(
        text,
        _RETRIEVAL_INTENT_CUES,
    )

    descriptive_intent = "circumstances are described" in text

    return management_intent or descriptive_intent


def _has_sql_intent(
    text: str,
) -> bool:
    if _contains_any(
        text,
        _SQL_CUSTOMER_COUNT_CUES,
    ):
        return True

    has_metric = _contains_any(
        text,
        _SQL_METRIC_CUES,
    )

    if not has_metric:
        return False

    has_period = _PERIOD_RE.search(text) is not None

    has_quantitative_operator = _contains_any(
        text,
        _SQL_QUANTITATIVE_CUES,
    )

    return has_period or has_quantitative_operator


def _has_graph_intent(
    text: str,
) -> bool:
    return _contains_any(
        text,
        _GRAPH_RELATION_CUES,
    )


class HeuristicRouter:
    def predict(
        self,
        question: str,
    ) -> HeuristicRoutePrediction:
        normalized = " ".join(question.casefold().split())

        if not normalized:
            raise ValueError("Routing question must not be blank.")

        tools: list[ToolFamily] = []

        matched_rules: list[str] = []

        if _has_retrieval_intent(normalized):
            tools.append("retrieval")
            matched_rules.append("retrieval-intent-v1")

        if _has_sql_intent(normalized):
            tools.append("sql")
            matched_rules.append("sql-intent-v1")

        if _has_graph_intent(normalized):
            tools.append("graph")
            matched_rules.append("graph-intent-v1")

        fallback_used = False

        if not tools:
            tools.append(FALLBACK_TOOL)
            matched_rules.append("fallback-retrieval-v1")
            fallback_used = True

        predicted_tools = tuple(tools)

        return HeuristicRoutePrediction(
            predicted_tools=predicted_tools,
            route_label=(canonical_route_label(predicted_tools)),
            matched_rules=tuple(matched_rules),
            fallback_used=(fallback_used),
        )

    def metadata(
        self,
    ) -> dict[
        str,
        object,
    ]:
        return {
            "router_version": (ROUTER_VERSION),
            "question_representation_version": (QUESTION_REPRESENTATION_VERSION),
            "fallback_tool": (FALLBACK_TOOL),
            "period_pattern": (_PERIOD_RE.pattern),
            "retrieval_intent_cues": list(_RETRIEVAL_INTENT_CUES),
            "sql_metric_cues": list(_SQL_METRIC_CUES),
            "sql_quantitative_cues": list(_SQL_QUANTITATIVE_CUES),
            "sql_customer_count_cues": list(_SQL_CUSTOMER_COUNT_CUES),
            "graph_relation_cues": list(_GRAPH_RELATION_CUES),
        }
