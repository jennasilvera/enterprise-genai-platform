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


class MechanicalMetricResult(FrozenAnsweringModel):
    metric: MechanicalMetric
    passed: bool
    detail: NonEmptyStr


class GenerationSystemScore(FrozenAnsweringModel):
    system: GenerationSystem
    query_id: NonEmptyStr
    text: NonEmptyStr
    metric_results: tuple[
        MechanicalMetricResult,
        ...,
    ]

    @property
    def passed(
        self,
    ) -> int:
        return sum(item.passed for item in self.metric_results)

    @property
    def total(
        self,
    ) -> int:
        return len(self.metric_results)


def _normalized(
    value: str,
) -> str:
    return " ".join(value.casefold().split())


def _contains_exact_normalized(
    *,
    text: str,
    expected: str,
) -> bool:
    return _normalized(expected) in _normalized(text)


def score_comparison_text(
    *,
    case: GenerationComparisonCase,
    system: GenerationSystem,
    text: str,
    authority_outcome: str,
    authority_answer_type: str | None,
    authority_value: object,
    authority_unit: str | None,
    authority_reason: str | None,
    presented_outcome: str | None,
    presented_reason: str | None,
    unauthorized_numeric_present: bool,
    unauthorized_citation_present: bool,
    rejected_raw_exposed: bool,
) -> GenerationSystemScore:
    results: list[MechanicalMetricResult] = []

    for metric in case.metrics:
        if metric == "authority_preserved":
            if authority_outcome == "abstain":
                passed = presented_outcome == "abstain" and presented_reason == authority_reason

                detail = (
                    "Typed abstention authority preserved exactly."
                    if passed
                    else ("Presented output did not preserve the typed abstention authority.")
                )

            elif authority_answer_type == "text":
                passed = isinstance(
                    authority_value,
                    str,
                ) and _contains_exact_normalized(
                    text=text,
                    expected=authority_value,
                )

                detail = (
                    "Strict normalized authority text preserved."
                    if passed
                    else ("Strict normalized authority text not preserved.")
                )

            elif authority_answer_type == "entity":
                passed = isinstance(
                    authority_value,
                    str,
                ) and _contains_exact_normalized(
                    text=text,
                    expected=authority_value,
                )

                detail = (
                    "Authoritative entity preserved."
                    if passed
                    else ("Authoritative entity not preserved.")
                )

            elif authority_answer_type == "number":
                passed = (
                    not isinstance(
                        authority_value,
                        bool,
                    )
                    and authority_value is not None
                    and str(authority_value) in text
                )

                detail = (
                    "Authoritative numeric literal preserved."
                    if passed
                    else ("Authoritative numeric literal not preserved.")
                )

            else:
                passed = True
                detail = "No additional authority preservation rule applies."

        elif metric == "abstention_preserved":
            passed = (
                authority_outcome == "abstain"
                and presented_outcome == "abstain"
                and presented_reason == authority_reason
            )

            detail = (
                "Deterministic abstention preserved."
                if passed
                else ("Deterministic abstention was not preserved.")
            )

        elif metric == "numeric_literal_preserved":
            passed = (
                authority_answer_type == "number"
                and authority_value is not None
                and str(authority_value) in text
            )

            detail = (
                "Exact numeric literal preserved."
                if passed
                else ("Exact numeric literal not preserved.")
            )

        elif metric == "unit_preserved":
            passed = authority_unit is not None and _contains_exact_normalized(
                text=text,
                expected=authority_unit,
            )

            detail = "Authority unit preserved." if passed else "Authority unit not preserved."

        elif metric == "entity_preserved":
            passed = (
                authority_answer_type == "entity"
                and isinstance(
                    authority_value,
                    str,
                )
                and _contains_exact_normalized(
                    text=text,
                    expected=authority_value,
                )
            )

            detail = "Authority entity preserved." if passed else "Authority entity not preserved."

        elif metric == "unauthorized_numeric_absent":
            passed = not unauthorized_numeric_present

            detail = (
                "No unauthorized numeric literal."
                if passed
                else ("Unauthorized numeric literal present.")
            )

        elif metric == "unauthorized_citation_absent":
            passed = not unauthorized_citation_present

            detail = (
                "No unauthorized citation ID." if passed else ("Unauthorized citation ID present.")
            )

        elif metric == "rejected_raw_not_exposed":
            passed = not rejected_raw_exposed

            detail = (
                "Rejected raw generation was not exposed."
                if passed
                else ("Rejected raw generation crossed the presentation boundary.")
            )

        else:
            raise AssertionError(f"Unhandled metric: {metric}")

        results.append(
            MechanicalMetricResult(
                metric=metric,
                passed=passed,
                detail=detail,
            )
        )

    return GenerationSystemScore(
        system=system,
        query_id=case.query_id,
        text=text,
        metric_results=tuple(results),
    )
