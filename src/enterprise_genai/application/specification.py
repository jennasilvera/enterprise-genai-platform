from __future__ import annotations

from typing import (
    Literal,
    Protocol,
    runtime_checkable,
)

from pydantic import (
    Field,
    model_validator,
)

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
)
from enterprise_genai.answering.outcomes import (
    GroundedAnswerType,
)
from enterprise_genai.answering.sufficiency import (
    EvidenceRequirement,
)
from enterprise_genai.answering.synthesis import (
    SynthesisMode,
)
from enterprise_genai.application.answering import (
    AnswerRequest,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
)


class AnswerSynthesisSpecification(FrozenAnsweringModel):
    """Bounded deterministic synthesis metadata."""

    mode: SynthesisMode

    answer_type: GroundedAnswerType


class ExecutableAnswerSpecification(FrozenAnsweringModel):
    """Fully prepared executable answering request."""

    kind: Literal["executable"] = "executable"

    question: NonEmptyStr

    orchestration_plan: BoundedOrchestrationPlan

    requirements: tuple[
        EvidenceRequirement,
        ...,
    ] = Field(min_length=1)

    synthesis: AnswerSynthesisSpecification | None = None

    @model_validator(mode="after")
    def validate_executable_specification(
        self,
    ) -> ExecutableAnswerSpecification:
        if self.orchestration_plan.question != self.question:
            raise ValueError(
                "answer specification question must exactly match the orchestration-plan question"
            )

        requirement_ids = tuple(requirement.requirement_id for requirement in self.requirements)

        if len(set(requirement_ids)) != len(requirement_ids):
            raise ValueError("answer specification requirement IDs must be unique")

        return self


class UnsupportedAnswerSpecification(FrozenAnsweringModel):
    """Explicitly unsupported bounded request."""

    kind: Literal["unsupported"] = "unsupported"

    question: NonEmptyStr

    detail: NonEmptyStr


AnswerExecutionSpecification = ExecutableAnswerSpecification | UnsupportedAnswerSpecification


@runtime_checkable
class AnswerSpecificationProviderProtocol(Protocol):
    """Prepare a bounded answer specification.

    This protocol makes no claim about how the
    specification is produced. Implementations
    must be evaluated independently.
    """

    def prepare(
        self,
        request: AnswerRequest,
    ) -> AnswerExecutionSpecification: ...
