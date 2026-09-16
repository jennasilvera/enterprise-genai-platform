from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from enterprise_genai.answering.contracts import (
    EvidenceKind,
    EvidenceTool,
    FrozenAnsweringModel,
    NonEmptyStr,
)
from enterprise_genai.answering.outcomes import (
    GroundedAnswerType,
    GroundedAnswerValue,
)

HUMAN_REVIEW_CONTRACT_VERSION = "northstar-human-review-contract-v1"

HumanReviewStatus = Literal[
    "awaiting_review",
    "approved",
    "rejected",
]

HumanReviewDisposition = Literal[
    "approve",
    "reject",
]


def _validate_sorted_unique(
    name: str,
    values: tuple[str, ...],
) -> None:
    if not values:
        raise ValueError(f"{name} must not be empty.")

    if len(set(values)) != len(values):
        raise ValueError(f"{name} must not contain duplicates.")

    if tuple(sorted(values)) != values:
        raise ValueError(f"{name} must use deterministic sorted ordering.")


def _validate_answer_value(
    *,
    answer_type: GroundedAnswerType,
    value: GroundedAnswerValue,
    unit: str | None,
) -> None:
    if answer_type in {
        "text",
        "entity",
    }:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{answer_type} review answers require a non-empty string.")

    elif answer_type == "entities":
        if not isinstance(value, tuple) or not value:
            raise ValueError("entities review answers require a non-empty tuple.")

        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("entities review answers require non-empty strings.")

        if len(set(value)) != len(value):
            raise ValueError("entities review answers must not contain duplicates.")

    elif answer_type == "number":
        if isinstance(value, bool) or not isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            raise ValueError("number review answers require an int or float.")

    elif answer_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError("boolean review answers require a bool.")

    else:
        raise AssertionError("Unreachable grounded answer type.")

    if answer_type != "number" and unit is not None:
        raise ValueError("Only numeric review answers may define a unit.")


class HumanReviewEvidence(FrozenAnsweringModel):
    """One selected evidence snapshot retained for approved continuation."""

    record_id: NonEmptyStr

    tool: EvidenceTool

    kind: EvidenceKind

    content: NonEmptyStr

    source_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    document_id: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_evidence(
        self,
    ) -> HumanReviewEvidence:
        _validate_sorted_unique(
            "Human-review evidence source_fact_ids",
            self.source_fact_ids,
        )

        if self.tool == "retrieval":
            if self.kind != "retrieval_hit":
                raise ValueError("Retrieval review evidence must use retrieval_hit kind.")

            if self.document_id is None:
                raise ValueError("Retrieval review evidence requires document_id.")

            return self

        if self.document_id is not None:
            raise ValueError("Only retrieval review evidence may define document_id.")

        return self


class HumanReviewRequest(FrozenAnsweringModel):
    """Durable prepared answer waiting for an external human decision."""

    review_id: NonEmptyStr

    question: NonEmptyStr

    status: HumanReviewStatus = "awaiting_review"

    answer_type: GroundedAnswerType

    answer_value: GroundedAnswerValue

    unit: NonEmptyStr | None = None

    supporting_record_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    citation_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    source_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    evidence: tuple[
        HumanReviewEvidence,
        ...,
    ]

    synthesis_version: NonEmptyStr

    sufficiency_policy_version: NonEmptyStr

    decision: HumanReviewDisposition | None = None

    reviewer_identity: NonEmptyStr | None = None

    revision: int = 1

    contract_version: NonEmptyStr = HUMAN_REVIEW_CONTRACT_VERSION

    @model_validator(mode="after")
    def validate_review(
        self,
    ) -> HumanReviewRequest:
        if self.contract_version != HUMAN_REVIEW_CONTRACT_VERSION:
            raise ValueError("Human-review request requires the frozen contract version.")

        _validate_answer_value(
            answer_type=self.answer_type,
            value=self.answer_value,
            unit=self.unit,
        )

        _validate_sorted_unique(
            "supporting_record_ids",
            self.supporting_record_ids,
        )

        _validate_sorted_unique(
            "citation_ids",
            self.citation_ids,
        )

        _validate_sorted_unique(
            "source_fact_ids",
            self.source_fact_ids,
        )

        if self.citation_ids != self.supporting_record_ids:
            raise ValueError("Human-review citation IDs must exactly match selected support.")

        evidence_ids = tuple(item.record_id for item in self.evidence)

        if evidence_ids != self.supporting_record_ids:
            raise ValueError(
                "Human-review evidence must exactly match selected support in deterministic order."
            )

        evidence_facts = tuple(
            sorted({fact_id for item in self.evidence for fact_id in item.source_fact_ids})
        )

        if evidence_facts != self.source_fact_ids:
            raise ValueError("Human-review evidence provenance must exactly match source_fact_ids.")

        if self.status == "awaiting_review":
            if self.decision is not None:
                raise ValueError("Awaiting review cannot contain a human decision.")

            if self.reviewer_identity is not None:
                raise ValueError("Awaiting review cannot contain reviewer identity.")

            if self.revision != 1:
                raise ValueError("Awaiting review must use revision 1.")

            return self

        if self.revision != 2:
            raise ValueError("Terminal human review must use revision 2.")

        if self.decision is None:
            raise ValueError("Terminal human review requires a decision.")

        if self.reviewer_identity is None:
            raise ValueError("Terminal human review requires reviewer identity.")

        if self.status == "approved" and self.decision != "approve":
            raise ValueError("Approved review requires approve disposition.")

        if self.status == "rejected" and self.decision != "reject":
            raise ValueError("Rejected review requires reject disposition.")

        return self


class HumanReviewDecision(FrozenAnsweringModel):
    """One externally supplied human decision."""

    review_id: NonEmptyStr

    disposition: HumanReviewDisposition

    reviewer_identity: NonEmptyStr

    contract_version: NonEmptyStr = HUMAN_REVIEW_CONTRACT_VERSION

    @model_validator(mode="after")
    def validate_decision(
        self,
    ) -> HumanReviewDecision:
        if self.contract_version != HUMAN_REVIEW_CONTRACT_VERSION:
            raise ValueError("Human-review decision requires the frozen contract version.")

        return self
