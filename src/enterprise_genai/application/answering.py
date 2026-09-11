from __future__ import annotations

from math import isfinite
from typing import (
    Annotated,
    Literal,
    Protocol,
    runtime_checkable,
)

from pydantic import (
    Field,
    field_validator,
    model_validator,
)

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
)

PresentationSource = Literal[
    "deterministic",
    "model_generation",
    "deterministic_fallback",
]

GenerationFidelityDisposition = Literal[
    "not_applicable",
    "accepted",
    "rejected",
]


class AnswerRequest(FrozenAnsweringModel):
    """Application-level request for one grounded answer."""

    question: NonEmptyStr

    @field_validator(
        "question",
        mode="before",
    )
    @classmethod
    def normalize_question(
        cls,
        value: object,
    ) -> object:
        if not isinstance(
            value,
            str,
        ):
            return value

        normalized = value.strip()

        if not normalized:
            raise ValueError("question must contain non-whitespace text")

        return normalized


class TextAnswerPayload(FrozenAnsweringModel):
    answer_type: Literal["text"] = "text"

    value: NonEmptyStr


class EntityAnswerPayload(FrozenAnsweringModel):
    answer_type: Literal["entity"] = "entity"

    value: NonEmptyStr


class EntitiesAnswerPayload(FrozenAnsweringModel):
    answer_type: Literal["entities"] = "entities"

    value: tuple[
        NonEmptyStr,
        ...,
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_entities(
        self,
    ) -> EntitiesAnswerPayload:
        if len(set(self.value)) != len(self.value):
            raise ValueError("entity values must be unique")

        return self


class NumberAnswerPayload(FrozenAnsweringModel):
    answer_type: Literal["number"] = "number"

    value: int | float
    unit: NonEmptyStr | None = None

    @field_validator(
        "value",
        mode="before",
    )
    @classmethod
    def reject_boolean_number(
        cls,
        value: object,
    ) -> object:
        if isinstance(
            value,
            bool,
        ):
            raise ValueError("boolean is not a numeric answer value")

        return value

    @field_validator(
        "value",
    )
    @classmethod
    def require_finite_number(
        cls,
        value: int | float,
    ) -> int | float:
        if isinstance(
            value,
            float,
        ) and not isfinite(value):
            raise ValueError("numeric answer must be finite")

        return value


class BooleanAnswerPayload(FrozenAnsweringModel):
    answer_type: Literal["boolean"] = "boolean"

    value: bool


AnswerPayload = Annotated[
    (
        TextAnswerPayload
        | EntityAnswerPayload
        | EntitiesAnswerPayload
        | NumberAnswerPayload
        | BooleanAnswerPayload
    ),
    Field(discriminator="answer_type"),
]


class PresentationResultBase(FrozenAnsweringModel):
    """Fields safe to cross the application presentation boundary."""

    presentation_source: PresentationSource
    generation_fidelity: GenerationFidelityDisposition

    text: NonEmptyStr

    citation_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    provenance_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    @field_validator(
        "text",
        mode="before",
    )
    @classmethod
    def reject_blank_text(
        cls,
        value: object,
    ) -> object:
        if (
            isinstance(
                value,
                str,
            )
            and not value.strip()
        ):
            raise ValueError("presentation text must contain non-whitespace content")

        return value

    @model_validator(mode="after")
    def validate_presentation_boundary(
        self,
    ) -> PresentationResultBase:
        expected_fidelity = {
            "deterministic": ("not_applicable"),
            "model_generation": ("accepted"),
            "deterministic_fallback": ("rejected"),
        }[self.presentation_source]

        if self.generation_fidelity != expected_fidelity:
            raise ValueError("presentation source and generation fidelity disagree")

        if len(set(self.citation_ids)) != len(self.citation_ids):
            raise ValueError("citation IDs must be unique")

        if len(set(self.provenance_fact_ids)) != len(self.provenance_fact_ids):
            raise ValueError("provenance fact IDs must be unique")

        return self


class AnsweredServiceResult(PresentationResultBase):
    status: Literal["answered"] = "answered"

    payload: AnswerPayload


class AbstainedServiceResult(PresentationResultBase):
    status: Literal["abstained"] = "abstained"

    reason: NonEmptyStr
    detail: str | None = None

    @field_validator(
        "detail",
    )
    @classmethod
    def reject_blank_detail(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("abstention detail cannot be blank")

        return value


AnswerServiceResult = Annotated[
    (AnsweredServiceResult | AbstainedServiceResult),
    Field(discriminator="status"),
]


@runtime_checkable
class AnsweringServiceProtocol(Protocol):
    """Application service consumed by the HTTP boundary."""

    def answer(
        self,
        request: AnswerRequest,
    ) -> AnswerServiceResult: ...
