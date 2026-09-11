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
from enterprise_genai.application.service import (
    GROUNDED_ANSWERING_SERVICE_VERSION,
    AnswerExecutionRuntimeProtocol,
    GroundedAnsweringService,
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

from enterprise_genai.application.specification import (
    AnswerExecutionSpecification,
    AnswerSpecificationProviderProtocol,
    AnswerSynthesisSpecification,
    ExecutableAnswerSpecification,
    UnsupportedAnswerSpecification,
)

__all__ += [
    "AnswerExecutionSpecification",
    "AnswerSpecificationProviderProtocol",
    "AnswerSynthesisSpecification",
    "ExecutableAnswerSpecification",
    "UnsupportedAnswerSpecification",
]

__all__ += [
    "GROUNDED_ANSWERING_SERVICE_VERSION",
    "AnswerExecutionRuntimeProtocol",
    "GroundedAnsweringService",
]
