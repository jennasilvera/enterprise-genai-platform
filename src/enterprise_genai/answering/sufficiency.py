from __future__ import annotations

from pydantic import model_validator

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceKind,
    EvidenceRecord,
    EvidenceTool,
    FrozenAnsweringModel,
    NonEmptyStr,
    SufficiencyAssessment,
)

SUFFICIENCY_POLICY_VERSION = "northstar-deterministic-sufficiency-v1"


class EvidenceRequirement(FrozenAnsweringModel):
    """One explicit condition that answer evidence must satisfy.

    Version 1 intentionally performs bounded deterministic matching.
    It does not infer requirements from arbitrary natural-language
    questions and does not use benchmark answer-source fact IDs.
    """

    requirement_id: NonEmptyStr

    description: NonEmptyStr

    allowed_tools: tuple[
        EvidenceTool,
        ...,
    ] = ()

    allowed_kinds: tuple[
        EvidenceKind,
        ...,
    ] = ()

    all_terms: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    any_terms: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    @model_validator(mode="after")
    def validate_requirement(
        self,
    ) -> EvidenceRequirement:
        if not (self.allowed_tools or self.allowed_kinds or self.all_terms or self.any_terms):
            raise ValueError(
                "Evidence requirement must contain at least one bounded matching constraint."
            )

        for name, values in (
            (
                "allowed_tools",
                self.allowed_tools,
            ),
            (
                "allowed_kinds",
                self.allowed_kinds,
            ),
            (
                "all_terms",
                self.all_terms,
            ),
            (
                "any_terms",
                self.any_terms,
            ),
        ):
            normalized = tuple(value.casefold() for value in values)

            if len(set(normalized)) != len(normalized):
                raise ValueError(f"{name} must not contain duplicates.")

        return self


def _normalize_text(
    value: str,
) -> str:
    return " ".join(value.casefold().split())


def _record_matches(
    *,
    requirement: EvidenceRequirement,
    record: EvidenceRecord,
) -> bool:
    # Kept local and explicit so requirement semantics cannot
    # silently expand into arbitrary scoring behavior.
    tool = record.tool
    kind = record.kind
    summary = record.summary

    if requirement.allowed_tools and tool not in requirement.allowed_tools:
        return False

    if requirement.allowed_kinds and kind not in requirement.allowed_kinds:
        return False

    normalized_summary = _normalize_text(summary)

    if requirement.all_terms:
        all_match = all(
            _normalize_text(term) in normalized_summary for term in requirement.all_terms
        )

        if not all_match:
            return False

    if requirement.any_terms:
        any_match = any(
            _normalize_text(term) in normalized_summary for term in requirement.any_terms
        )

        if not any_match:
            return False

    return True


def _status_assessment(
    bundle: EvidenceBundle,
) -> SufficiencyAssessment | None:
    if bundle.status == "unsupported_request":
        return SufficiencyAssessment(
            bundle=bundle,
            status="insufficient",
            reason="unsupported_request",
            policy_version=(SUFFICIENCY_POLICY_VERSION),
            missing_information=(
                bundle.detail
                or ("The requested information is outside the bounded execution contract."),
            ),
        )

    if bundle.status == "failed":
        return SufficiencyAssessment(
            bundle=bundle,
            status="insufficient",
            reason="execution_failed",
            policy_version=(SUFFICIENCY_POLICY_VERSION),
            missing_information=(bundle.detail or ("Required execution did not complete."),),
        )

    if bundle.status == "blocked":
        return SufficiencyAssessment(
            bundle=bundle,
            status="insufficient",
            reason="blocked_dependency",
            policy_version=(SUFFICIENCY_POLICY_VERSION),
            missing_information=(
                bundle.detail or ("A required dependency could not be satisfied."),
            ),
        )

    return None


def evaluate_sufficiency(
    *,
    bundle: EvidenceBundle,
    requirements: tuple[
        EvidenceRequirement,
        ...,
    ],
) -> SufficiencyAssessment:
    """Evaluate explicit evidence requirements deterministically.

    Each requirement must be satisfied by at least one single
    evidence record. Different requirements may be satisfied by
    different records. Version 1 does not infer unstated facts or
    combine fragments into a new semantic claim.
    """

    status_assessment = _status_assessment(bundle)

    if status_assessment is not None:
        return status_assessment

    if not requirements:
        raise ValueError(
            "Completed evidence evaluation requires at least one explicit evidence requirement."
        )

    requirement_ids = tuple(requirement.requirement_id for requirement in requirements)

    if len(set(requirement_ids)) != len(requirement_ids):
        raise ValueError("Evidence requirement IDs must be unique.")

    if not bundle.records:
        return SufficiencyAssessment(
            bundle=bundle,
            status="insufficient",
            reason="no_relevant_evidence",
            policy_version=(SUFFICIENCY_POLICY_VERSION),
            missing_information=tuple(
                sorted(requirement.description for requirement in requirements)
            ),
        )

    support: set[str] = set()

    missing: list[str] = []

    for requirement in requirements:
        matches = tuple(
            record
            for record in bundle.records
            if _record_matches(
                requirement=requirement,
                record=record,
            )
        )

        if not matches:
            missing.append(requirement.description)

            continue

        # Bundle ordering is deterministic. One record is enough
        # to establish one bounded requirement, so select the first
        # matching record rather than inflating provenance.
        support.add(matches[0].record_id)

    sorted_support = tuple(sorted(support))

    if missing:
        return SufficiencyAssessment(
            bundle=bundle,
            status="insufficient",
            reason=("missing_required_information"),
            policy_version=(SUFFICIENCY_POLICY_VERSION),
            supporting_record_ids=(sorted_support),
            missing_information=tuple(sorted(missing)),
        )

    return SufficiencyAssessment(
        bundle=bundle,
        status="sufficient",
        reason="evidence_supports_answer",
        policy_version=(SUFFICIENCY_POLICY_VERSION),
        supporting_record_ids=(sorted_support),
    )
