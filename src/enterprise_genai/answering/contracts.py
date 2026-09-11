from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

NonEmptyStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]

EvidenceTool = Literal[
    "retrieval",
    "sql",
    "graph",
]

EvidenceKind = Literal[
    "retrieval_hit",
    "structured_value",
    "structured_entity",
    "graph_entity",
    "graph_relationship",
]

EvidenceBundleStatus = Literal[
    "completed",
    "blocked",
    "failed",
    "unsupported_request",
]

SufficiencyStatus = Literal[
    "sufficient",
    "insufficient",
]

SufficiencyReason = Literal[
    "evidence_supports_answer",
    "no_relevant_evidence",
    "missing_required_information",
    "unsupported_request",
    "execution_failed",
    "blocked_dependency",
    "conflicting_evidence",
]


class FrozenAnsweringModel(BaseModel):
    """Immutable strict contract for the answering boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


EvidenceScalar = int | float | bool | NonEmptyStr


class StructuredValueEvidenceData(FrozenAnsweringModel):
    """Machine-readable scalar preserved from structured execution."""

    kind: Literal["structured_value"] = "structured_value"

    value: EvidenceScalar

    unit: NonEmptyStr | None = None


class StructuredEntityEvidenceData(FrozenAnsweringModel):
    """Machine-readable entity selected by structured execution."""

    kind: Literal["structured_entity"] = "structured_entity"

    entity_id: NonEmptyStr

    entity_name: NonEmptyStr

    score: EvidenceScalar | None = None

    score_unit: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_score_unit(
        self,
    ) -> StructuredEntityEvidenceData:
        if self.score is None and self.score_unit is not None:
            raise ValueError("Structured entity score_unit requires a score.")

        return self


class GraphEntityEvidenceData(FrozenAnsweringModel):
    """Machine-readable identity for one graph node."""

    kind: Literal["graph_entity"] = "graph_entity"

    entity_type: NonEmptyStr

    entity_id: NonEmptyStr

    entity_name: NonEmptyStr


class GraphRelationshipEvidenceData(FrozenAnsweringModel):
    """Machine-readable identity for one graph relationship."""

    kind: Literal["graph_relationship"] = "graph_relationship"

    relationship_type: NonEmptyStr

    relationship_id: NonEmptyStr

    source_type: NonEmptyStr

    source_id: NonEmptyStr

    target_type: NonEmptyStr

    target_id: NonEmptyStr


EvidenceData = Annotated[
    (
        StructuredValueEvidenceData
        | StructuredEntityEvidenceData
        | GraphEntityEvidenceData
        | GraphRelationshipEvidenceData
    ),
    Field(discriminator="kind"),
]


class EvidenceRecord(FrozenAnsweringModel):
    """One normalized, provenance-bearing unit of evidence."""

    record_id: NonEmptyStr

    tool: EvidenceTool

    kind: EvidenceKind

    summary: NonEmptyStr

    source_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    document_id: NonEmptyStr | None = None

    rank: int | None = Field(
        default=None,
        ge=1,
    )

    data: EvidenceData | None = None

    @model_validator(mode="after")
    def validate_record(
        self,
    ) -> EvidenceRecord:
        if not self.source_fact_ids:
            raise ValueError("Evidence record requires at least one canonical source fact ID.")

        if len(set(self.source_fact_ids)) != len(self.source_fact_ids):
            raise ValueError("Evidence source fact IDs must not contain duplicates.")

        if tuple(sorted(self.source_fact_ids)) != self.source_fact_ids:
            raise ValueError("Evidence source fact IDs must use deterministic sorted ordering.")

        if self.tool == "retrieval":
            if self.data is not None:
                raise ValueError("Retrieval evidence must not contain structured synthesis data.")

            if self.kind != "retrieval_hit":
                raise ValueError("Retrieval evidence must use retrieval_hit kind.")

            if self.document_id is None:
                raise ValueError("Retrieval evidence requires document_id.")

            if self.rank is None:
                raise ValueError("Retrieval evidence requires rank.")

            return self

        if self.data is not None and self.data.kind != self.kind:
            raise ValueError("Evidence data kind must match the evidence record kind.")

        if self.tool == "sql" and self.kind not in {
            "structured_value",
            "structured_entity",
        }:
            raise ValueError("SQL evidence must use a structured evidence kind.")

        if self.tool == "graph" and self.kind not in {
            "graph_entity",
            "graph_relationship",
        }:
            raise ValueError("Graph evidence must use a graph evidence kind.")

        if self.document_id is not None or self.rank is not None:
            raise ValueError("Only retrieval evidence may contain document_id or rank.")

        return self


class EvidenceBundle(FrozenAnsweringModel):
    """Normalized evidence available for one user question."""

    question: NonEmptyStr

    status: EvidenceBundleStatus

    records: tuple[
        EvidenceRecord,
        ...,
    ] = ()

    detail: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_bundle(
        self,
    ) -> EvidenceBundle:
        record_ids = tuple(record.record_id for record in self.records)

        if len(set(record_ids)) != len(record_ids):
            raise ValueError("Evidence bundle cannot contain duplicate record IDs.")

        if self.status == "unsupported_request":
            if self.records:
                raise ValueError("Unsupported request must not contain execution evidence.")

            if self.detail is None:
                raise ValueError("Unsupported request requires a detail.")

            return self

        if (
            self.status
            in {
                "blocked",
                "failed",
            }
            and self.detail is None
        ):
            raise ValueError("Blocked or failed evidence bundle requires a detail.")

        return self


class SufficiencyAssessment(FrozenAnsweringModel):
    """Typed answerability decision over an exact evidence bundle."""

    bundle: EvidenceBundle

    status: SufficiencyStatus

    reason: SufficiencyReason

    policy_version: NonEmptyStr

    supporting_record_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    missing_information: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    @model_validator(mode="after")
    def validate_assessment(
        self,
    ) -> SufficiencyAssessment:
        if len(set(self.supporting_record_ids)) != len(self.supporting_record_ids):
            raise ValueError("Supporting record IDs must not contain duplicates.")

        if tuple(sorted(self.supporting_record_ids)) != self.supporting_record_ids:
            raise ValueError("Supporting record IDs must use deterministic sorted ordering.")

        available = {record.record_id for record in self.bundle.records}

        unknown = set(self.supporting_record_ids) - available

        if unknown:
            raise ValueError(
                f"Sufficiency assessment references unknown evidence records: {sorted(unknown)!r}."
            )

        if len(set(self.missing_information)) != len(self.missing_information):
            raise ValueError("Missing-information entries must not contain duplicates.")

        if self.status == "sufficient":
            if self.reason != "evidence_supports_answer":
                raise ValueError("Sufficient assessment requires evidence_supports_answer.")

            if not self.supporting_record_ids:
                raise ValueError("Sufficient assessment requires supporting evidence.")

            if self.missing_information:
                raise ValueError("Sufficient assessment cannot declare missing information.")

            return self

        if self.reason == "evidence_supports_answer":
            raise ValueError("Insufficient assessment cannot use evidence_supports_answer.")

        if not self.missing_information:
            raise ValueError(
                "Insufficient assessment must state what information is missing or unavailable."
            )

        return self
