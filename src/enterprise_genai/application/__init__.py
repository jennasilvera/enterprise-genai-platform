"""Application-level service contracts."""

from enterprise_genai.application.answering import (
    AbstainedServiceResult,
    AnsweredServiceResult,
    AnsweringServiceProtocol,
    AnswerPayload,
    AnswerRequest,
    AnswerServiceResult,
    BooleanAnswerPayload,
    EntitiesAnswerPayload,
    EntityAnswerPayload,
    GenerationFidelityDisposition,
    NumberAnswerPayload,
    PresentationSource,
    TextAnswerPayload,
)

__all__ = [
    "AbstainedServiceResult",
    "AnsweredServiceResult",
    "AnsweringServiceProtocol",
    "AnswerPayload",
    "AnswerRequest",
    "AnswerServiceResult",
    "BooleanAnswerPayload",
    "EntitiesAnswerPayload",
    "EntityAnswerPayload",
    "GenerationFidelityDisposition",
    "NumberAnswerPayload",
    "PresentationSource",
    "TextAnswerPayload",
]
