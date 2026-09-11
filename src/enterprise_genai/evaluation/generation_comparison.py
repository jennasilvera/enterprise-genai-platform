from __future__ import annotations

from typing import Literal

from pydantic import (
    Field,
    model_validator,
)

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
)

GENERATION_COMPARISON_PROTOCOL_VERSION = "northstar-generation-comparison-v1"


GenerationSystem = Literal[
    "deterministic",
    "raw_llm",
    "guarded_llm",
]


MechanicalMetric = Literal[
    "authority_preserved",
    "abstention_preserved",
    "numeric_literal_preserved",
    "unit_preserved",
    "entity_preserved",
    "unauthorized_numeric_absent",
    "unauthorized_citation_absent",
    "rejected_raw_not_exposed",
]


class GenerationComparisonCase(FrozenAnsweringModel):
    query_id: NonEmptyStr

    systems: tuple[
        GenerationSystem,
        ...,
    ] = (
        "deterministic",
        "raw_llm",
        "guarded_llm",
    )

    metrics: tuple[
        MechanicalMetric,
        ...,
    ]

    notes: NonEmptyStr

    @model_validator(mode="after")
    def validate_case(
        self,
    ) -> GenerationComparisonCase:
        if self.systems != (
            "deterministic",
            "raw_llm",
            "guarded_llm",
        ):
            raise ValueError(
                "Comparison systems must use "
                "the frozen deterministic / "
                "raw_llm / guarded_llm order."
            )

        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("Comparison metrics must be unique within a case.")

        return self


class GenerationComparisonProtocol(FrozenAnsweringModel):
    version: NonEmptyStr = GENERATION_COMPARISON_PROTOCOL_VERSION

    cases: tuple[
        GenerationComparisonCase,
        ...,
    ]

    claim_boundary: tuple[
        NonEmptyStr,
        ...,
    ] = Field(
        default=(
            (
                "Metrics are deterministic "
                "mechanical fidelity checks, "
                "not general semantic accuracy."
            ),
            (
                "The five cases form an "
                "integration control set, "
                "not the complete 24-case "
                "evaluation benchmark. The protocol was defined "
                "after Phase 10C model behavior had already "
                "been observed and is not blind or preregistered."
            ),
            ("A guarded result may use deterministic fallback rather than model-generated prose."),
        )
    )

    @model_validator(mode="after")
    def validate_protocol(
        self,
    ) -> GenerationComparisonProtocol:
        if self.version != GENERATION_COMPARISON_PROTOCOL_VERSION:
            raise ValueError("Generation comparison requires the frozen protocol version.")

        query_ids = tuple(case.query_id for case in self.cases)

        if query_ids != (
            "Q-0001",
            "Q-0010",
            "Q-0011",
            "Q-0023",
            "Q-0024",
        ):
            raise ValueError("Generation comparison requires the frozen five-case order.")

        return self


def build_generation_comparison_protocol() -> GenerationComparisonProtocol:
    return GenerationComparisonProtocol(
        cases=(
            GenerationComparisonCase(
                query_id="Q-0001",
                metrics=(
                    "authority_preserved",
                    "unauthorized_numeric_absent",
                    "unauthorized_citation_absent",
                    "rejected_raw_not_exposed",
                ),
                notes=(
                    "Retrieval-backed free-text authority; strict normalized text preservation."
                ),
            ),
            GenerationComparisonCase(
                query_id="Q-0010",
                metrics=(
                    "authority_preserved",
                    "entity_preserved",
                    "unauthorized_numeric_absent",
                    "unauthorized_citation_absent",
                    "rejected_raw_not_exposed",
                ),
                notes=("Structured entity answer for highest year-over-year revenue growth."),
            ),
            GenerationComparisonCase(
                query_id="Q-0011",
                metrics=(
                    "authority_preserved",
                    "numeric_literal_preserved",
                    "unit_preserved",
                    "unauthorized_numeric_absent",
                    "unauthorized_citation_absent",
                    "rejected_raw_not_exposed",
                ),
                notes=(
                    "Structured numeric answer with exact numeric-literal and unit requirements."
                ),
            ),
            GenerationComparisonCase(
                query_id="Q-0023",
                metrics=(
                    "authority_preserved",
                    "abstention_preserved",
                    "unauthorized_numeric_absent",
                    "unauthorized_citation_absent",
                    "rejected_raw_not_exposed",
                ),
                notes=("Missing-required-information abstention control."),
            ),
            GenerationComparisonCase(
                query_id="Q-0024",
                metrics=(
                    "authority_preserved",
                    "abstention_preserved",
                    "unauthorized_numeric_absent",
                    "unauthorized_citation_absent",
                    "rejected_raw_not_exposed",
                ),
                notes=("Unsupported-request abstention control."),
            ),
        )
    )
