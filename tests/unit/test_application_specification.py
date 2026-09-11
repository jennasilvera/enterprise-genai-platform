from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.answering.sufficiency import (
    EvidenceRequirement,
)
from enterprise_genai.application import (
    AnswerRequest,
    AnswerSpecificationProviderProtocol,
    AnswerSynthesisSpecification,
    ExecutableAnswerSpecification,
    UnsupportedAnswerSpecification,
)
from enterprise_genai.execution.contracts import (
    RetrievalQuery,
    ToolExecutionPlan,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
)


def _retrieval_plan(
    question: str,
) -> BoundedOrchestrationPlan:
    return BoundedOrchestrationPlan(
        question=question,
        execution_plan=(
            ToolExecutionPlan(
                route_label="retrieval",
                retrieval=RetrievalQuery(
                    question=question,
                ),
            )
        ),
    )


def _requirement() -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="risk-evidence",
        description=("Evidence describing the requested operational risk."),
        allowed_tools=("retrieval",),
        allowed_kinds=("retrieval_hit",),
    )


def test_executable_specification_is_fully_bounded() -> None:
    question = "What defect affected ORBIS-IDX-7?"

    spec = ExecutableAnswerSpecification(
        question=question,
        orchestration_plan=(_retrieval_plan(question)),
        requirements=(_requirement(),),
        synthesis=(
            AnswerSynthesisSpecification(
                mode="retrieval_text",
                answer_type="text",
            )
        ),
    )

    assert spec.kind == "executable"

    assert spec.orchestration_plan.question == question

    assert spec.synthesis is not None


def test_specification_rejects_question_plan_mismatch() -> None:
    with pytest.raises(
        ValidationError,
        match="exactly match",
    ):
        ExecutableAnswerSpecification(
            question="Question A?",
            orchestration_plan=(_retrieval_plan("Question B?")),
            requirements=(_requirement(),),
        )


def test_specification_requires_explicit_requirements() -> None:
    with pytest.raises(
        ValidationError,
    ):
        ExecutableAnswerSpecification(
            question="Question?",
            orchestration_plan=(_retrieval_plan("Question?")),
            requirements=(),
        )


def test_specification_rejects_duplicate_requirement_ids() -> None:
    requirement = _requirement()

    with pytest.raises(
        ValidationError,
        match="requirement IDs must be unique",
    ):
        ExecutableAnswerSpecification(
            question="Question?",
            orchestration_plan=(_retrieval_plan("Question?")),
            requirements=(
                requirement,
                requirement,
            ),
        )


def test_unsupported_specification_is_explicit() -> None:
    spec = UnsupportedAnswerSpecification(
        question=("What was Alder Manufacturing's exact customer churn rate?"),
        detail=("customer_churn_rate is outside the bounded structured metric set"),
    )

    assert spec.kind == "unsupported"


def test_specification_provider_protocol_is_structural() -> None:
    class FakeProvider:
        def prepare(
            self,
            request: AnswerRequest,
        ):
            return UnsupportedAnswerSpecification(
                question=request.question,
                detail="unsupported in test",
            )

    provider = FakeProvider()

    assert isinstance(
        provider,
        AnswerSpecificationProviderProtocol,
    )

    result = provider.prepare(AnswerRequest(question="Question?"))

    assert result.kind == "unsupported"
