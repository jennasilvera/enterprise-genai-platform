from __future__ import annotations

from typing import Literal, Protocol

from pydantic import model_validator

from enterprise_genai.answering.contracts import (
    EvidenceKind,
    EvidenceRecord,
    EvidenceTool,
    FrozenAnsweringModel,
    NonEmptyStr,
    SufficiencyReason,
)
from enterprise_genai.answering.outcomes import (
    AbstentionOutcome,
    AnswerOutcome,
    GroundedAnswer,
    GroundedAnswerType,
)

GROUNDING_POLICY_VERSION = "northstar-grounded-generation-policy-v1"

GenerationAuthorityOutcome = Literal[
    "answer",
    "abstain",
]

GenerationValue = (
    str
    | int
    | float
    | bool
    | tuple[
        NonEmptyStr,
        ...,
    ]
)


def _validate_authoritative_answer_value(
    *,
    answer_type: GroundedAnswerType,
    value: GenerationValue,
    unit: str | None,
) -> None:
    """Mirror deterministic GroundedAnswer value invariants."""

    if answer_type in {
        "text",
        "entity",
    }:
        if (
            not isinstance(
                value,
                str,
            )
            or not value.strip()
        ):
            raise ValueError(f"{answer_type} authority requires a non-empty string value.")

    elif answer_type == "entities":
        if (
            not isinstance(
                value,
                tuple,
            )
            or not value
        ):
            raise ValueError("entities authority requires a non-empty tuple.")

        if not all(
            isinstance(
                item,
                str,
            )
            and item.strip()
            for item in value
        ):
            raise ValueError("entities authority requires non-empty string values.")

        if len(set(value)) != len(value):
            raise ValueError("entities authority must not contain duplicates.")

    elif answer_type == "number":
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
            raise ValueError("number authority requires an int or float value.")

    elif answer_type == "boolean":
        if not isinstance(
            value,
            bool,
        ):
            raise ValueError("boolean authority requires a bool value.")

    else:
        raise AssertionError("Unreachable grounded answer type.")

    if answer_type != "number" and unit is not None:
        raise ValueError("Only numeric answer authority may define a unit.")


class GenerationEvidence(FrozenAnsweringModel):
    """One sufficiency-selected evidence record exposed to generation."""

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
    ) -> GenerationEvidence:
        if not self.source_fact_ids:
            raise ValueError("Generation evidence requires canonical source facts.")

        if len(set(self.source_fact_ids)) != len(self.source_fact_ids):
            raise ValueError("Generation evidence source facts must be unique.")

        if tuple(sorted(self.source_fact_ids)) != self.source_fact_ids:
            raise ValueError(
                "Generation evidence source facts must use deterministic sorted ordering."
            )

        return self


class GenerationAuthority(FrozenAnsweringModel):
    """Deterministic facts the generative model is not allowed to alter."""

    outcome: GenerationAuthorityOutcome

    answer_type: GroundedAnswerType | None = None

    value: GenerationValue | None = None

    unit: NonEmptyStr | None = None

    reason: SufficiencyReason | None = None

    missing_information: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    supporting_record_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    source_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    @model_validator(mode="after")
    def validate_authority(
        self,
    ) -> GenerationAuthority:
        for name, values in (
            (
                "supporting_record_ids",
                self.supporting_record_ids,
            ),
            (
                "source_fact_ids",
                self.source_fact_ids,
            ),
            (
                "missing_information",
                self.missing_information,
            ),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must be unique.")

        if tuple(sorted(self.supporting_record_ids)) != self.supporting_record_ids:
            raise ValueError("Supporting record IDs must use deterministic sorted ordering.")

        if tuple(sorted(self.source_fact_ids)) != self.source_fact_ids:
            raise ValueError("Source fact IDs must use deterministic sorted ordering.")

        if self.outcome == "answer":
            if self.answer_type is None or self.value is None:
                raise ValueError(
                    "Answer generation authority requires an answer type and authoritative value."
                )

            if self.reason is not None:
                raise ValueError("Answer generation authority cannot define an abstention reason.")

            if self.missing_information:
                raise ValueError("Answer generation authority cannot define missing information.")

            if not self.supporting_record_ids:
                raise ValueError("Answer generation authority requires supporting records.")

            if not self.source_fact_ids:
                raise ValueError("Answer generation authority requires canonical source facts.")

            _validate_authoritative_answer_value(
                answer_type=self.answer_type,
                value=self.value,
                unit=self.unit,
            )

            return self

        if self.answer_type is not None:
            raise ValueError("Abstention authority cannot define an answer type.")

        if self.value is not None:
            raise ValueError("Abstention authority cannot define an answer value.")

        if self.unit is not None:
            raise ValueError("Abstention authority cannot define an answer unit.")

        if self.reason is None:
            raise ValueError("Abstention authority requires a typed reason.")

        if not self.missing_information:
            raise ValueError("Abstention authority requires missing-information detail.")

        return self


class GroundedGenerationRequest(FrozenAnsweringModel):
    """Sanitized request presented to an untrusted generation provider."""

    question: NonEmptyStr

    authority: GenerationAuthority

    evidence: tuple[
        GenerationEvidence,
        ...,
    ] = ()

    allowed_citation_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    policy_version: NonEmptyStr = GROUNDING_POLICY_VERSION

    @model_validator(mode="after")
    def validate_request(
        self,
    ) -> GroundedGenerationRequest:
        if self.policy_version != GROUNDING_POLICY_VERSION:
            raise ValueError(
                "Grounded generation request requires the frozen grounding policy version."
            )

        record_ids = tuple(record.record_id for record in self.evidence)

        if len(set(record_ids)) != len(record_ids):
            raise ValueError("Generation evidence record IDs must be unique.")

        if tuple(sorted(record_ids)) != record_ids:
            raise ValueError("Generation evidence must use deterministic record ordering.")

        if record_ids != self.authority.supporting_record_ids:
            raise ValueError("Generation evidence must exactly match authority-selected support.")

        if self.allowed_citation_ids != self.authority.supporting_record_ids:
            raise ValueError("Allowed citation IDs must exactly match authority-selected support.")

        facts = tuple(
            sorted({fact_id for record in self.evidence for fact_id in record.source_fact_ids})
        )

        if facts != self.authority.source_fact_ids:
            raise ValueError(
                "Generation evidence provenance must exactly match authority source facts."
            )

        return self


class GenerationProviderMetadata(FrozenAnsweringModel):
    """Minimal reproducibility metadata for one generation backend."""

    provider_id: NonEmptyStr

    model_id: NonEmptyStr

    model_revision: NonEmptyStr

    device: NonEmptyStr

    dtype: NonEmptyStr


class RawGeneration(FrozenAnsweringModel):
    """Untrusted text emitted by a generation provider."""

    text: NonEmptyStr

    metadata: GenerationProviderMetadata


class GenerationProvider(Protocol):
    """Provider boundary for probabilistic text generation."""

    def generate(
        self,
        request: GroundedGenerationRequest,
    ) -> RawGeneration: ...


def _selected_records(
    outcome: AnswerOutcome,
) -> tuple[
    EvidenceRecord,
    ...,
]:
    selected_ids = outcome.supporting_record_ids

    records = {record.record_id: record for record in outcome.assessment.bundle.records}

    missing = tuple(record_id for record_id in selected_ids if record_id not in records)

    if missing:
        raise ValueError(f"Generation request could not resolve selected evidence: {missing!r}.")

    return tuple(records[record_id] for record_id in selected_ids)


def _generation_evidence(
    records: tuple[
        EvidenceRecord,
        ...,
    ],
) -> tuple[
    GenerationEvidence,
    ...,
]:
    return tuple(
        GenerationEvidence(
            record_id=record.record_id,
            tool=record.tool,
            kind=record.kind,
            content=record.summary,
            source_fact_ids=(record.source_fact_ids),
            document_id=(record.document_id),
        )
        for record in records
    )


def generation_request_from_outcome(
    *,
    question: str,
    outcome: AnswerOutcome,
) -> GroundedGenerationRequest:
    """Expose only deterministic authority and selected support."""

    if question != outcome.assessment.bundle.question:
        raise ValueError(
            "Generation question must exactly match the deterministic outcome question."
        )

    records = _selected_records(outcome)

    evidence = _generation_evidence(records)

    facts = tuple(sorted({fact_id for record in records for fact_id in record.source_fact_ids}))

    if isinstance(
        outcome,
        GroundedAnswer,
    ):
        if facts != outcome.source_fact_ids:
            raise ValueError("Grounded answer provenance changed before generation.")

        authority = GenerationAuthority(
            outcome="answer",
            answer_type=(outcome.answer_type),
            value=outcome.value,
            unit=outcome.unit,
            supporting_record_ids=(outcome.supporting_record_ids),
            source_fact_ids=(outcome.source_fact_ids),
        )

    elif isinstance(
        outcome,
        AbstentionOutcome,
    ):
        authority = GenerationAuthority(
            outcome="abstain",
            reason=outcome.reason,
            missing_information=(outcome.missing_information),
            supporting_record_ids=(outcome.supporting_record_ids),
            source_fact_ids=facts,
        )

    else:
        raise TypeError("Unsupported deterministic answer outcome.")

    return GroundedGenerationRequest(
        question=question,
        authority=authority,
        evidence=evidence,
        allowed_citation_ids=(authority.supporting_record_ids),
    )
