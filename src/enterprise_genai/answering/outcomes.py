from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
    SufficiencyAssessment,
    SufficiencyReason,
)

GroundedAnswerType = Literal[
    "text",
    "entity",
    "entities",
    "number",
    "boolean",
]

GroundedAnswerValue = (
    str
    | int
    | float
    | bool
    | tuple[
        NonEmptyStr,
        ...,
    ]
)


class GroundedAnswer(FrozenAnsweringModel):
    """Typed answer grounded only in selected sufficient evidence."""

    outcome: Literal["answer"] = "answer"

    assessment: SufficiencyAssessment

    answer_type: GroundedAnswerType

    value: GroundedAnswerValue

    unit: NonEmptyStr | None = None

    supporting_record_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    source_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    synthesis_version: NonEmptyStr

    @model_validator(mode="after")
    def validate_grounded_answer(
        self,
    ) -> GroundedAnswer:
        if self.assessment.status != "sufficient":
            raise ValueError("Grounded answer requires a sufficient assessment.")

        if self.supporting_record_ids != self.assessment.supporting_record_ids:
            raise ValueError(
                "Grounded answer supporting "
                "record IDs must exactly match "
                "the sufficiency assessment."
            )

        if not self.source_fact_ids:
            raise ValueError("Grounded answer requires canonical source fact IDs.")

        if len(set(self.source_fact_ids)) != len(self.source_fact_ids):
            raise ValueError("Grounded answer source fact IDs must not contain duplicates.")

        if tuple(sorted(self.source_fact_ids)) != self.source_fact_ids:
            raise ValueError(
                "Grounded answer source fact IDs must use deterministic sorted ordering."
            )

        records = {record.record_id: record for record in self.assessment.bundle.records}

        expected_source_fact_ids = tuple(
            sorted(
                {
                    fact_id
                    for record_id in self.supporting_record_ids
                    for fact_id in records[record_id].source_fact_ids
                }
            )
        )

        if self.source_fact_ids != expected_source_fact_ids:
            raise ValueError(
                "Grounded answer source fact "
                "IDs must exactly equal the "
                "canonical provenance of the "
                "selected supporting records."
            )

        if self.answer_type in {
            "text",
            "entity",
        }:
            if (
                not isinstance(
                    self.value,
                    str,
                )
                or not self.value.strip()
            ):
                raise ValueError(f"{self.answer_type} answers require a non-empty string value.")

        elif self.answer_type == "entities":
            if (
                not isinstance(
                    self.value,
                    tuple,
                )
                or not self.value
            ):
                raise ValueError("entities answers require a non-empty tuple of entity strings.")

            if not all(
                isinstance(
                    item,
                    str,
                )
                and item.strip()
                for item in self.value
            ):
                raise ValueError("entities answers require non-empty string values.")

            if len(set(self.value)) != len(self.value):
                raise ValueError("entities answers must not contain duplicates.")

        elif self.answer_type == "number":
            if isinstance(
                self.value,
                bool,
            ) or not isinstance(
                self.value,
                (
                    int,
                    float,
                ),
            ):
                raise ValueError("number answers require an int or float value.")

        elif self.answer_type == "boolean" and not isinstance(
            self.value,
            bool,
        ):
            raise ValueError("boolean answers require a bool value.")

        if self.answer_type != "number" and self.unit is not None:
            raise ValueError("Only numeric grounded answers may define a unit.")

        return self


class AbstentionOutcome(FrozenAnsweringModel):
    """Typed non-answer emitted for an insufficient assessment."""

    outcome: Literal["abstain"] = "abstain"

    assessment: SufficiencyAssessment

    reason: SufficiencyReason

    missing_information: tuple[
        NonEmptyStr,
        ...,
    ]

    supporting_record_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    policy_version: NonEmptyStr

    @model_validator(mode="after")
    def validate_abstention(
        self,
    ) -> AbstentionOutcome:
        if self.assessment.status != "insufficient":
            raise ValueError("Abstention outcome requires an insufficient assessment.")

        if self.reason != self.assessment.reason:
            raise ValueError("Abstention reason must exactly match the sufficiency assessment.")

        if self.missing_information != self.assessment.missing_information:
            raise ValueError(
                "Abstention missing information must exactly match the sufficiency assessment."
            )

        if self.supporting_record_ids != self.assessment.supporting_record_ids:
            raise ValueError(
                "Abstention supporting record IDs must exactly match the sufficiency assessment."
            )

        if self.policy_version != self.assessment.policy_version:
            raise ValueError(
                "Abstention policy version must exactly match the sufficiency assessment."
            )

        return self


AnswerOutcome = Annotated[
    GroundedAnswer | AbstentionOutcome,
    Field(discriminator="outcome"),
]
