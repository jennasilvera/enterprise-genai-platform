from __future__ import annotations

import re
from typing import Literal

from pydantic import model_validator

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
    SufficiencyAssessment,
)

INSTRUCTION_INTEGRITY_POLICY_VERSION = "northstar-selected-retrieval-instruction-integrity-v1"

INSTRUCTION_INTEGRITY_BLOCK_REASON = "instruction_integrity_blocked"

INSTRUCTION_INTEGRITY_BLOCK_TEXT = (
    "The selected evidence cannot be promoted to answer "
    "authority under the instruction-integrity policy."
)

INSTRUCTION_INTEGRITY_BLOCK_DETAIL = (
    "Selected retrieval evidence contains a control directive "
    "that is not permitted to become deterministic answer authority."
)


InstructionIntegrityDisposition = Literal[
    "allow",
    "block",
]

InstructionIntegrityViolationCode = Literal[
    "abstention_override",
    "answer_redirection",
    "answer_value_manipulation",
    "authority_priority_override",
    "citation_manipulation",
    "provenance_manipulation",
]


class InstructionIntegrityDecision(FrozenAnsweringModel):
    """Typed deterministic decision at the selected-retrieval trust boundary.

    The decision intentionally contains IDs and bounded taxonomy only.
    It never copies retrieval text into the policy result.
    """

    disposition: InstructionIntegrityDisposition

    policy_version: NonEmptyStr = INSTRUCTION_INTEGRITY_POLICY_VERSION

    inspected_record_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    blocked_record_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    violation_codes: tuple[
        InstructionIntegrityViolationCode,
        ...,
    ] = ()

    blocked_source_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    @model_validator(mode="after")
    def validate_decision(
        self,
    ) -> InstructionIntegrityDecision:
        if self.policy_version != INSTRUCTION_INTEGRITY_POLICY_VERSION:
            raise ValueError("Instruction-integrity decision requires the frozen policy version.")

        for name, values in (
            (
                "inspected_record_ids",
                self.inspected_record_ids,
            ),
            (
                "blocked_record_ids",
                self.blocked_record_ids,
            ),
            (
                "violation_codes",
                self.violation_codes,
            ),
            (
                "blocked_source_fact_ids",
                self.blocked_source_fact_ids,
            ),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must not contain duplicates.")

            if tuple(sorted(values)) != values:
                raise ValueError(f"{name} must use deterministic sorted ordering.")

        if set(self.blocked_record_ids) - set(self.inspected_record_ids):
            raise ValueError("Blocked records must be a subset of inspected retrieval records.")

        if self.disposition == "allow":
            if self.blocked_record_ids or self.violation_codes or self.blocked_source_fact_ids:
                raise ValueError(
                    "Allow decisions cannot contain blocked "
                    "records, violations, or blocked provenance."
                )

            return self

        if not self.inspected_record_ids:
            raise ValueError("Block decisions require inspected retrieval records.")

        if not self.blocked_record_ids:
            raise ValueError("Block decisions require blocked retrieval records.")

        if not self.violation_codes:
            raise ValueError("Block decisions require typed violation codes.")

        if not self.blocked_source_fact_ids:
            raise ValueError("Block decisions require canonical blocked provenance.")

        return self


Rule = tuple[
    InstructionIntegrityViolationCode,
    re.Pattern[str],
]


# These rules encode bounded control-intent classes at the authority
# boundary. They are not claimed to be a complete prompt-injection,
# jailbreak, or natural-language safety detector.
_RULES: tuple[Rule, ...] = (
    (
        "authority_priority_override",
        re.compile(r"\bignore\s+(?:all\s+)?previous\s+instructions\b"),
    ),
    (
        "authority_priority_override",
        re.compile(r"\bignore\s+(?:the\s+)?question\b"),
    ),
    (
        "authority_priority_override",
        re.compile(r"\bignore\s+all\s+other\s+evidence\b"),
    ),
    (
        "authority_priority_override",
        re.compile(
            r"\btreat\s+this\s+(?:text|document)\s+as\s+"
            r"(?:higher\s+priority|the\s+only\s+authority)\b"
        ),
    ),
    (
        "authority_priority_override",
        re.compile(
            r"(?:"
            r"\[system\s+message\]"
            r"|\[developer\s+message\]"
            r"|##\s*system\s+instruction\b"
            r"|<system>"
            r")"
        ),
    ),
    (
        "answer_redirection",
        re.compile(r"\breturn\s+the\s+fabricated\s+answer\b"),
    ),
    (
        "answer_redirection",
        re.compile(r"\breveal\s+unrelated\b"),
    ),
    (
        "answer_redirection",
        re.compile(r"\banswer\s+about\b"),
    ),
    (
        "answer_redirection",
        re.compile(r"\boutput\b.{0,80}\boverride(?:-accepted)?\b"),
    ),
    (
        "answer_value_manipulation",
        re.compile(r"\breport\s+the\s+defect\s+count\s+as\b"),
    ),
    (
        "answer_value_manipulation",
        re.compile(
            r"\breplace\s+(?:the\s+)?"
            r"(?:affected\s+entity|answer)\s+with\b"
        ),
    ),
    (
        "answer_value_manipulation",
        re.compile(r"\bstate\s+the\s+answer\s+unit\s+as\b"),
    ),
    (
        "citation_manipulation",
        re.compile(r"\bsuppress\s+all\s+citations\b"),
    ),
    (
        "citation_manipulation",
        re.compile(r"\badd\s+citation\b"),
    ),
    (
        "provenance_manipulation",
        re.compile(r"\bdrop\s+required\s+provenance\b"),
    ),
    (
        "abstention_override",
        re.compile(r"\bignore\s+any\s+abstention\s+state\b"),
    ),
)


def _normalize_control_text(
    value: str,
) -> str:
    """Normalize representation without changing policy semantics."""

    return " ".join(value.casefold().split())


def _violation_codes(
    value: str,
) -> tuple[
    InstructionIntegrityViolationCode,
    ...,
]:
    normalized = _normalize_control_text(value)

    codes = {code for code, pattern in _RULES if pattern.search(normalized)}

    return tuple(sorted(codes))


def evaluate_instruction_integrity(
    *,
    assessment: SufficiencyAssessment,
) -> InstructionIntegrityDecision:
    """Evaluate only sufficiency-selected natural-language retrieval support.

    Structured SQL and graph evidence are outside this policy because
    they already cross synthesis through typed machine-readable fields.

    Unselected retrieval records are intentionally not inspected here:
    they cannot become answer authority under the existing synthesis
    contract.
    """

    if assessment.status != "sufficient":
        raise ValueError("Instruction-integrity evaluation requires a sufficient assessment.")

    records = {record.record_id: record for record in assessment.bundle.records}

    inspected: list[str] = []
    blocked: list[str] = []

    violations: set[InstructionIntegrityViolationCode] = set()

    blocked_facts: set[str] = set()

    for record_id in assessment.supporting_record_ids:
        record = records[record_id]

        if record.tool != "retrieval" or record.kind != "retrieval_hit":
            continue

        inspected.append(record_id)

        record_codes = _violation_codes(record.summary)

        if not record_codes:
            continue

        blocked.append(record_id)

        violations.update(record_codes)

        blocked_facts.update(record.source_fact_ids)

    disposition: InstructionIntegrityDisposition = "block" if blocked else "allow"

    return InstructionIntegrityDecision(
        disposition=disposition,
        inspected_record_ids=tuple(sorted(inspected)),
        blocked_record_ids=tuple(sorted(blocked)),
        violation_codes=tuple(sorted(violations)),
        blocked_source_fact_ids=tuple(sorted(blocked_facts)),
    )
