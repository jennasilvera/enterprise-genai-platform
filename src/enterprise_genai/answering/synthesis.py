from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from enterprise_genai.answering.contracts import (
    EvidenceRecord,
    FrozenAnsweringModel,
    GraphEntityEvidenceData,
    NonEmptyStr,
    StructuredEntityEvidenceData,
    StructuredValueEvidenceData,
    SufficiencyAssessment,
)
from enterprise_genai.answering.outcomes import (
    AbstentionOutcome,
    AnswerOutcome,
    GroundedAnswer,
    GroundedAnswerType,
)

SYNTHESIS_VERSION = "northstar-deterministic-grounded-synthesis-v1"

SynthesisMode = Literal[
    "retrieval_text",
    "structured_value",
    "entity_name",
    "entity_names",
]


class SynthesisInstruction(FrozenAnsweringModel):
    """Explicit bounded instruction for deterministic answer construction."""

    mode: SynthesisMode

    answer_type: GroundedAnswerType

    answer_record_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    @model_validator(mode="after")
    def validate_instruction(
        self,
    ) -> SynthesisInstruction:
        if not self.answer_record_ids:
            raise ValueError("Synthesis instruction requires at least one answer record.")

        if len(set(self.answer_record_ids)) != len(self.answer_record_ids):
            raise ValueError("Synthesis answer record IDs must not contain duplicates.")

        if tuple(sorted(self.answer_record_ids)) != self.answer_record_ids:
            raise ValueError("Synthesis answer record IDs must use deterministic sorted ordering.")

        expected_type = {
            "retrieval_text": "text",
            "entity_name": "entity",
            "entity_names": "entities",
        }

        if self.mode in expected_type and self.answer_type != expected_type[self.mode]:
            raise ValueError(
                f"Synthesis mode {self.mode!r} requires answer_type={expected_type[self.mode]!r}."
            )

        if (
            self.mode
            in {
                "retrieval_text",
                "structured_value",
                "entity_name",
            }
            and len(self.answer_record_ids) != 1
        ):
            raise ValueError(f"Synthesis mode {self.mode!r} requires exactly one answer record.")

        return self


def _abstention(
    assessment: SufficiencyAssessment,
) -> AbstentionOutcome:
    return AbstentionOutcome(
        assessment=assessment,
        reason=assessment.reason,
        missing_information=(assessment.missing_information),
        supporting_record_ids=(assessment.supporting_record_ids),
        policy_version=(assessment.policy_version),
    )


def _supporting_records(
    assessment: SufficiencyAssessment,
) -> dict[str, EvidenceRecord]:
    support_ids = set(assessment.supporting_record_ids)

    return {
        record.record_id: record
        for record in assessment.bundle.records
        if record.record_id in support_ids
    }


def _source_fact_ids(
    *,
    assessment: SufficiencyAssessment,
    supporting_records: dict[
        str,
        EvidenceRecord,
    ],
) -> tuple[str, ...]:
    facts: set[str] = set()

    for record_id in assessment.supporting_record_ids:
        record = supporting_records[record_id]

        facts.update(record.source_fact_ids)

    return tuple(sorted(facts))


def synthesize_answer(
    *,
    assessment: SufficiencyAssessment,
    instruction: SynthesisInstruction | None = None,
) -> AnswerOutcome:
    """Construct one bounded answer from sufficiency-selected evidence.

    Version 1 does not infer synthesis instructions from natural
    language and does not use evidence outside supporting_record_ids.
    """

    if assessment.status == "insufficient":
        return _abstention(assessment)

    if instruction is None:
        raise ValueError("Sufficient assessment requires an explicit synthesis instruction.")

    allowed_ids = set(assessment.supporting_record_ids)

    requested_ids = set(instruction.answer_record_ids)

    outside_support = requested_ids - allowed_ids

    if outside_support:
        raise ValueError(
            "Synthesis instruction references "
            "records not selected by the "
            "sufficiency assessment: "
            f"{sorted(outside_support)!r}."
        )

    records = _supporting_records(assessment)

    if set(records) != allowed_ids:
        raise ValueError("Sufficiency-selected evidence could not be resolved exactly.")

    answer_records = tuple(records[record_id] for record_id in instruction.answer_record_ids)

    value: str | int | float | bool | tuple[str, ...]

    unit: str | None = None

    if instruction.mode == "retrieval_text":
        record = answer_records[0]

        if record.tool != "retrieval" or record.kind != "retrieval_hit":
            raise ValueError("retrieval_text synthesis requires retrieval evidence.")

        value = record.summary

    elif instruction.mode == "structured_value":
        record = answer_records[0]

        if not isinstance(
            record.data,
            StructuredValueEvidenceData,
        ):
            raise ValueError(
                "structured_value synthesis requires typed structured scalar evidence."
            )

        value = record.data.value

        if instruction.answer_type == "number":
            if isinstance(
                value,
                bool,
            ) or not isinstance(
                value,
                (
                    int,
                    float,
                ),
            ):
                raise ValueError("Numeric synthesis requires a machine-readable numeric value.")

            unit = record.data.unit

        elif instruction.answer_type == "boolean":
            if not isinstance(
                value,
                bool,
            ):
                raise ValueError("Boolean synthesis requires a machine-readable boolean value.")

            if record.data.unit is not None:
                raise ValueError("Boolean synthesis cannot discard a structured unit.")

        elif instruction.answer_type == "text":
            if not isinstance(
                value,
                str,
            ):
                raise ValueError("Text structured-value synthesis requires a string.")

            if record.data.unit is not None:
                raise ValueError("Text synthesis cannot discard a structured unit.")

        else:
            raise ValueError(
                "structured_value synthesis supports only text, number, or boolean answer types."
            )

    elif instruction.mode == "entity_name":
        record = answer_records[0]

        data = record.data

        if isinstance(
            data,
            (
                StructuredEntityEvidenceData,
                GraphEntityEvidenceData,
            ),
        ):
            value = data.entity_name
        else:
            raise ValueError("entity_name synthesis requires typed entity evidence.")

    elif instruction.mode == "entity_names":
        names: list[str] = []

        for record in answer_records:
            data = record.data

            if not isinstance(
                data,
                (
                    StructuredEntityEvidenceData,
                    GraphEntityEvidenceData,
                ),
            ):
                raise ValueError("entity_names synthesis requires typed entity evidence.")

            names.append(data.entity_name)

        value = tuple(sorted(names))

    else:
        raise AssertionError("Unreachable synthesis mode.")

    provenance = _source_fact_ids(
        assessment=assessment,
        supporting_records=records,
    )

    return GroundedAnswer(
        assessment=assessment,
        answer_type=(instruction.answer_type),
        value=value,
        unit=unit,
        supporting_record_ids=(assessment.supporting_record_ids),
        source_fact_ids=provenance,
        synthesis_version=(SYNTHESIS_VERSION),
    )
