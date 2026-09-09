from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

ToolFamily = Literal[
    "retrieval",
    "sql",
    "graph",
]

RouteLabel = Literal[
    "retrieval",
    "sql",
    "graph",
    "retrieval+sql",
    "retrieval+graph",
    "sql+graph",
    "retrieval+sql+graph",
]

RoutingSplit = Literal[
    "train",
    "development",
    "locked_holdout",
]

RoutingDifficulty = Literal[
    "easy",
    "medium",
    "hard",
]

TOOL_ORDER: tuple[ToolFamily, ...] = (
    "retrieval",
    "sql",
    "graph",
)

VALID_ROUTE_LABELS: tuple[
    RouteLabel,
    ...,
] = (
    "retrieval",
    "sql",
    "graph",
    "retrieval+sql",
    "retrieval+graph",
    "sql+graph",
    "retrieval+sql+graph",
)

LEGACY_RETRIEVAL_TOOLS = {
    "lexical_retrieval",
    "dense_retrieval",
    "hybrid_retrieval",
}


def canonical_route_label(
    tools: Iterable[str],
) -> RouteLabel:
    supplied = list(tools)

    if not supplied:
        raise ValueError("A route requires at least one tool.")

    unknown = set(supplied) - set(TOOL_ORDER)

    if unknown:
        raise ValueError(f"Unknown tool families: {sorted(unknown)}.")

    if len(supplied) != len(set(supplied)):
        raise ValueError("Route tools must be unique.")

    ordered = [tool for tool in TOOL_ORDER if tool in supplied]

    label = "+".join(ordered)

    if label not in VALID_ROUTE_LABELS:
        raise ValueError(f"Invalid route label: {label}.")

    return label  # type: ignore[return-value]


def normalize_legacy_required_tools(
    tools: Iterable[str],
) -> list[ToolFamily]:
    supplied = set(tools)

    known = LEGACY_RETRIEVAL_TOOLS | {
        "sql",
        "graph",
    }

    unknown = supplied - known

    if unknown:
        raise ValueError(f"Unknown legacy required tools: {sorted(unknown)}.")

    normalized: list[ToolFamily] = []

    if LEGACY_RETRIEVAL_TOOLS & supplied:
        normalized.append("retrieval")

    if "sql" in supplied:
        normalized.append("sql")

    if "graph" in supplied:
        normalized.append("graph")

    if not normalized:
        raise ValueError("Legacy route normalized to no tools.")

    return normalized


class RoutingCase(BaseModel):
    routing_id: str = Field(min_length=1)

    question: str = Field(min_length=1)

    split: RoutingSplit

    template_family: str = Field(min_length=1)

    difficulty: RoutingDifficulty

    required_tools: list[ToolFamily] = Field(
        min_length=1,
        max_length=3,
    )

    route_label: RouteLabel

    rationale: str = Field(min_length=1)

    source_entity_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_route(
        self,
    ) -> Self:
        if len(self.required_tools) != len(set(self.required_tools)):
            raise ValueError("required_tools contains duplicates.")

        expected_tools = [tool for tool in TOOL_ORDER if tool in self.required_tools]

        if self.required_tools != expected_tools:
            raise ValueError("required_tools must use canonical tool order.")

        expected_label = canonical_route_label(self.required_tools)

        if self.route_label != expected_label:
            raise ValueError("route_label does not match required_tools.")

        if len(self.source_entity_ids) != len(set(self.source_entity_ids)):
            raise ValueError("source_entity_ids contains duplicates.")

        return self


class RoutingSet(BaseModel):
    dataset_version: str = Field(min_length=1)

    routing_version: str = Field(min_length=1)

    cases: list[RoutingCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_set(
        self,
    ) -> Self:
        ids = [case.routing_id for case in self.cases]

        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate routing_id.")

        questions = [case.question for case in self.cases]

        if len(questions) != len(set(questions)):
            raise ValueError("Duplicate routing question.")

        family_splits: dict[
            str,
            set[str],
        ] = {}

        for case in self.cases:
            family_splits.setdefault(
                case.template_family,
                set(),
            ).add(case.split)

        leaking = sorted(family for family, splits in family_splits.items() if len(splits) != 1)

        if leaking:
            raise ValueError(f"Template families leak across splits: {leaking}.")

        return self
