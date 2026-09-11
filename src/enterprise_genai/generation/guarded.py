from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
)
from enterprise_genai.generation.contracts import (
    GenerationAuthority,
    GroundedGenerationRequest,
)
from enterprise_genai.generation.validation import (
    GenerationFidelityAssessment,
)

SAFE_GENERATION_POLICY_VERSION = "northstar-safe-generation-presentation-v1"


SafeGenerationSource = Literal[
    "model_generation",
    "deterministic_fallback",
]


def render_deterministic_authority(
    authority: GenerationAuthority,
) -> str:
    """Render deterministic authority without probabilistic inference."""

    if authority.outcome == "answer":
        answer_type = authority.answer_type

        value = authority.value

        assert answer_type is not None
        assert value is not None

        if answer_type in {
            "text",
            "entity",
        }:
            assert isinstance(
                value,
                str,
            )

            return value

        if answer_type == "entities":
            assert isinstance(
                value,
                tuple,
            )

            return ", ".join(value)

        if answer_type == "number":
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
                raise AssertionError("Invalid numeric authority reached deterministic renderer.")

            rendered = str(value)

            if authority.unit is not None:
                rendered += " " + authority.unit

            return rendered

        if answer_type == "boolean":
            assert isinstance(
                value,
                bool,
            )

            return "true" if value else "false"

        raise AssertionError("Unsupported answer type reached deterministic renderer.")

    reason = authority.reason

    assert reason is not None

    missing = authority.missing_information

    if reason == "missing_required_information":
        text = "The available evidence is insufficient to answer this question."

        if missing:
            text += " Missing required information: " + "; ".join(missing)

        return text

    if reason == "unsupported_request":
        text = "This request is outside the supported query capabilities."

        if missing:
            text += " Detail: " + "; ".join(missing)

        return text

    text = f"A deterministic answer could not be produced. Reason: {reason}."

    if missing:
        text += " Detail: " + "; ".join(missing)

    return text


class SafeGenerationResult(FrozenAnsweringModel):
    """Presentation result that cannot expose rejected model text."""

    request: GroundedGenerationRequest

    fidelity: GenerationFidelityAssessment

    source: SafeGenerationSource

    text: NonEmptyStr

    citation_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    policy_version: NonEmptyStr = SAFE_GENERATION_POLICY_VERSION

    @model_validator(mode="after")
    def validate_result(
        self,
    ) -> SafeGenerationResult:
        if self.policy_version != SAFE_GENERATION_POLICY_VERSION:
            raise ValueError(
                "Safe generation result requires the frozen presentation policy version."
            )

        if self.fidelity.request != self.request:
            raise ValueError(
                "Safe generation request must match the fidelity assessment request exactly."
            )

        if self.citation_ids != self.request.allowed_citation_ids:
            raise ValueError(
                "Safe generation citation IDs must match the frozen request allowlist exactly."
            )

        if self.source == "model_generation":
            if self.fidelity.status != "accepted":
                raise ValueError(
                    "Model generation can be presented only after an accepted fidelity assessment."
                )

            if self.fidelity.safe_text != self.text:
                raise ValueError(
                    "Model presentation text must equal the fidelity-approved safe text exactly."
                )

            return self

        if self.fidelity.status != "rejected":
            raise ValueError("Deterministic fallback requires a rejected fidelity assessment.")

        expected = render_deterministic_authority(self.request.authority)

        if self.text != expected:
            raise ValueError(
                "Deterministic fallback text "
                "must equal the authoritative "
                "deterministic rendering exactly."
            )

        return self


def resolve_safe_generation(
    fidelity: GenerationFidelityAssessment,
) -> SafeGenerationResult:
    """Return approved model text or deterministic authority fallback."""

    request = fidelity.request

    if fidelity.status == "accepted":
        safe_text = fidelity.safe_text

        assert safe_text is not None

        return SafeGenerationResult(
            request=request,
            fidelity=fidelity,
            source="model_generation",
            text=safe_text,
            citation_ids=(request.allowed_citation_ids),
        )

    return SafeGenerationResult(
        request=request,
        fidelity=fidelity,
        source="deterministic_fallback",
        text=(render_deterministic_authority(request.authority)),
        citation_ids=(request.allowed_citation_ids),
    )
