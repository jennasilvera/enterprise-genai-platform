from __future__ import annotations

import re
from typing import Literal

from pydantic import model_validator

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
)
from enterprise_genai.generation.contracts import (
    GroundedGenerationRequest,
    RawGeneration,
)

GENERATION_FIDELITY_POLICY_VERSION = "northstar-generation-fidelity-v1"


GenerationFidelityStatus = Literal[
    "accepted",
    "rejected",
]


GenerationViolationCode = Literal[
    "abstention_semantics_violation",
    "authority_boolean_violation",
    "authority_entity_violation",
    "authority_numeric_violation",
    "authority_text_violation",
    "authority_unit_violation",
    "unauthorized_citation",
    "unauthorized_numeric_claim",
]


class GenerationViolation(FrozenAnsweringModel):
    """One deterministic reason raw generation cannot be trusted."""

    code: GenerationViolationCode

    detail: NonEmptyStr

    expected: NonEmptyStr | None = None

    observed: NonEmptyStr | None = None


class GenerationFidelityAssessment(FrozenAnsweringModel):
    """Typed decision over one untrusted raw generation."""

    request: GroundedGenerationRequest

    raw_generation: RawGeneration

    status: GenerationFidelityStatus

    violations: tuple[
        GenerationViolation,
        ...,
    ] = ()

    policy_version: NonEmptyStr = GENERATION_FIDELITY_POLICY_VERSION

    @model_validator(mode="after")
    def validate_assessment(
        self,
    ) -> GenerationFidelityAssessment:
        if self.policy_version != GENERATION_FIDELITY_POLICY_VERSION:
            raise ValueError(
                "Generation fidelity assessment requires the frozen fidelity policy version."
            )

        keys = tuple(
            (
                violation.code,
                violation.detail,
                violation.expected or "",
                violation.observed or "",
            )
            for violation in self.violations
        )

        if len(set(keys)) != len(keys):
            raise ValueError("Generation violations must be unique.")

        if tuple(sorted(keys)) != keys:
            raise ValueError("Generation violations must use deterministic sorted ordering.")

        if self.status == "accepted":
            if self.violations:
                raise ValueError("Accepted generation cannot contain violations.")

            return self

        if not self.violations:
            raise ValueError("Rejected generation requires at least one violation.")

        return self

    @property
    def safe_text(
        self,
    ) -> str | None:
        """Expose model text only after successful validation."""

        if self.status != "accepted":
            return None

        return self.raw_generation.text


def _normalize_space(
    value: str,
) -> str:
    return " ".join(value.split())


def _contains_normalized_text(
    *,
    text: str,
    expected: str,
) -> bool:
    return _normalize_space(expected).casefold() in _normalize_space(text).casefold()


def _numeric_literals(
    text: str,
) -> tuple[
    str,
    ...,
]:
    """Extract deterministic digit-based numeric literals."""

    pattern = re.compile(
        r"(?<![A-Za-z0-9])"
        r"[-+]?"
        r"\d[\d,]*"
        r"(?:\.\d+)?"
        r"(?![A-Za-z0-9])"
    )

    values = []

    for match in pattern.finditer(text):
        value = match.group(0).replace(
            ",",
            "",
        )

        if value.startswith("+"):
            value = value[1:]

        values.append(value)

    return tuple(values)


def _allowed_numeric_literals(
    request: GroundedGenerationRequest,
) -> set[str]:
    sources = [
        request.question,
    ]

    sources.extend(record.content for record in request.evidence)

    authority = request.authority

    if authority.outcome == "answer" and authority.value is not None:
        if authority.answer_type == "entities":
            assert isinstance(
                authority.value,
                tuple,
            )

            sources.extend(authority.value)

        else:
            sources.append(str(authority.value))

    sources.extend(authority.missing_information)

    return {literal for source in sources for literal in _numeric_literals(source)}


def _citation_ids(
    text: str,
) -> tuple[
    str,
    ...,
]:
    """Extract execution/evidence IDs that look like citations."""

    pattern = re.compile(
        r"(?:"
        r"RET:\d{3}:[A-Za-z0-9._:-]+"
        r"|SQL:[A-Za-z0-9._:-]+"
        r"|GRAPH:[A-Za-z0-9._:-]+"
        r")"
    )

    return tuple(match.group(0).rstrip(".,;!?)]}") for match in pattern.finditer(text))


def _sorted_violations(
    violations: list[GenerationViolation],
) -> tuple[
    GenerationViolation,
    ...,
]:
    return tuple(
        sorted(
            violations,
            key=lambda violation: (
                violation.code,
                violation.detail,
                violation.expected or "",
                violation.observed or "",
            ),
        )
    )


def assess_generation_fidelity(
    *,
    request: GroundedGenerationRequest,
    raw_generation: RawGeneration,
) -> GenerationFidelityAssessment:
    """Deterministically assess untrusted model text.

    Version 1 is intentionally conservative. It does not attempt to
    infer semantic equivalence between free-form paraphrases.
    """

    text = raw_generation.text

    authority = request.authority

    violations: list[GenerationViolation] = []

    # -----------------------------------------------------
    # Deterministic abstentions are never delegated to the
    # probabilistic presentation layer in fidelity v1.
    # -----------------------------------------------------

    if authority.outcome == "abstain":
        violations.append(
            GenerationViolation(
                code=("abstention_semantics_violation"),
                detail=(
                    "Probabilistic generation is "
                    "not authorized for a "
                    "deterministic abstention "
                    "outcome."
                ),
                expected=(authority.reason),
                observed=text,
            )
        )

    else:
        assert authority.answer_type is not None

        assert authority.value is not None

        if authority.answer_type == "text":
            assert isinstance(
                authority.value,
                str,
            )

            if not _contains_normalized_text(
                text=text,
                expected=authority.value,
            ):
                violations.append(
                    GenerationViolation(
                        code=("authority_text_violation"),
                        detail=(
                            "Generated text did not "
                            "preserve the authoritative "
                            "text under strict "
                            "normalized-text matching."
                        ),
                        expected=(authority.value),
                        observed=text,
                    )
                )

        elif authority.answer_type == "entity":
            assert isinstance(
                authority.value,
                str,
            )

            if not _contains_normalized_text(
                text=text,
                expected=authority.value,
            ):
                violations.append(
                    GenerationViolation(
                        code=("authority_entity_violation"),
                        detail=("Generated text did not preserve the authoritative entity."),
                        expected=(authority.value),
                        observed=text,
                    )
                )

        elif authority.answer_type == "entities":
            assert isinstance(
                authority.value,
                tuple,
            )

            missing_entities = tuple(
                entity
                for entity in authority.value
                if not _contains_normalized_text(
                    text=text,
                    expected=entity,
                )
            )

            if missing_entities:
                violations.append(
                    GenerationViolation(
                        code=("authority_entity_violation"),
                        detail=("Generated text omitted one or more authoritative entities."),
                        expected=" | ".join(authority.value),
                        observed=text,
                    )
                )

        elif authority.answer_type == "number":
            if isinstance(
                authority.value,
                bool,
            ) or not isinstance(
                authority.value,
                (
                    int,
                    float,
                ),
            ):
                raise AssertionError("Invalid numeric authority reached fidelity assessment.")

            expected_number = str(authority.value)

            # Strict policy: the authoritative literal itself must
            # appear. Mathematical rescaling such as "735 million"
            # is not accepted as equivalent to "735000000".
            if expected_number not in text:
                violations.append(
                    GenerationViolation(
                        code=("authority_numeric_violation"),
                        detail=(
                            "Generated text did not "
                            "preserve the exact "
                            "authoritative numeric "
                            "literal."
                        ),
                        expected=(expected_number),
                        observed=text,
                    )
                )

        elif authority.answer_type == "boolean":
            assert isinstance(
                authority.value,
                bool,
            )

            expected_boolean = "true" if authority.value else "false"

            if (
                re.search(
                    rf"\b{expected_boolean}\b",
                    text,
                    flags=re.IGNORECASE,
                )
                is None
            ):
                violations.append(
                    GenerationViolation(
                        code=("authority_boolean_violation"),
                        detail=(
                            "Generated text did not preserve the authoritative boolean literal."
                        ),
                        expected=(expected_boolean),
                        observed=text,
                    )
                )

        else:
            raise AssertionError("Unsupported answer type reached fidelity assessment.")

        if authority.unit is not None and not _contains_normalized_text(
            text=text,
            expected=authority.unit,
        ):
            violations.append(
                GenerationViolation(
                    code=("authority_unit_violation"),
                    detail=("Generated text did not preserve the authoritative unit."),
                    expected=(authority.unit),
                    observed=text,
                )
            )

    # -----------------------------------------------------
    # Reject new digit-based numeric claims that were not
    # available in authorized generation inputs.
    # -----------------------------------------------------

    allowed_numbers = _allowed_numeric_literals(request)

    observed_numbers = set(_numeric_literals(text))

    unauthorized_numbers = tuple(sorted(observed_numbers - allowed_numbers))

    if unauthorized_numbers:
        violations.append(
            GenerationViolation(
                code=("unauthorized_numeric_claim"),
                detail=(
                    "Generated text introduced "
                    "numeric literals that were "
                    "not present in the authorized "
                    "question, authority, or "
                    "selected evidence."
                ),
                expected=(" | ".join(sorted(allowed_numbers)) or "no numeric literals"),
                observed=" | ".join(unauthorized_numbers),
            )
        )

    # -----------------------------------------------------
    # Reject citation-like execution/evidence identifiers
    # outside the frozen request allowlist.
    # -----------------------------------------------------

    citations = set(_citation_ids(text))

    unauthorized_citations = tuple(sorted(citations - set(request.allowed_citation_ids)))

    if unauthorized_citations:
        violations.append(
            GenerationViolation(
                code=("unauthorized_citation"),
                detail=("Generated text introduced citation IDs outside the request allowlist."),
                expected=(" | ".join(request.allowed_citation_ids) or "no citation IDs"),
                observed=" | ".join(unauthorized_citations),
            )
        )

    ordered = _sorted_violations(violations)

    return GenerationFidelityAssessment(
        request=request,
        raw_generation=raw_generation,
        status=("rejected" if ordered else "accepted"),
        violations=ordered,
    )
