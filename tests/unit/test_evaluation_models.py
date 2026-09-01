import pytest
from pydantic import ValidationError

from enterprise_genai.data.evaluation_models import (
    EvaluationCase,
    EvaluationSet,
    ExpectedAnswer,
    RelevanceJudgment,
)


def _orbis_case() -> EvaluationCase:
    return EvaluationCase(
        query_id="Q-0001",
        question=("Which company reported an incident involving ORBIS-IDX-7?"),
        query_type="lexical",
        split="development",
        difficulty="easy",
        answerable=True,
        expected_answer=ExpectedAnswer(
            answer_type="entity",
            value="Orbis Cybersecurity",
        ),
        required_tools=["lexical_retrieval"],
        relevance_judgments=[
            RelevanceJudgment(
                document_id="DOC-PC006-INCIDENT-001",
                evidence_id="EVID-PC006-INCIDENT-001",
                relevance_grade=3,
                rationale=(
                    "The incident report explicitly names ORBIS-IDX-7 and describes the failure."
                ),
            )
        ],
    )


def test_answerable_case_requires_grade_three_evidence() -> None:
    case = _orbis_case()

    assert case.relevance_judgments[0].relevance_grade == 3


def test_answerable_case_without_grade_three_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EvaluationCase(
            query_id="Q-INVALID",
            question="What happened?",
            query_type="semantic",
            split="development",
            difficulty="medium",
            answerable=True,
            expected_answer=ExpectedAnswer(
                answer_type="text",
                value="An event occurred.",
            ),
            required_tools=["dense_retrieval"],
            relevance_judgments=[
                RelevanceJudgment(
                    document_id="DOC-PC006-INCIDENT-001",
                    evidence_id="EVID-PC006-INCIDENT-001",
                    relevance_grade=2,
                    rationale="Supporting but not canonical.",
                )
            ],
        )


def test_unanswerable_case_requires_abstention() -> None:
    case = EvaluationCase(
        query_id="Q-0002",
        question=("What is Northstar's expected 2030 exit valuation for Meridian?"),
        query_type="insufficient_evidence",
        split="test",
        difficulty="medium",
        answerable=False,
        expected_answer=ExpectedAnswer(
            answer_type="abstain",
            value=None,
        ),
        required_tools=["hybrid_retrieval"],
        relevance_judgments=[],
    )

    assert case.expected_answer.answer_type == "abstain"


def test_unanswerable_case_rejects_grade_three_evidence() -> None:
    with pytest.raises(ValidationError):
        EvaluationCase(
            query_id="Q-INVALID",
            question="Unsupported forecast?",
            query_type="insufficient_evidence",
            split="test",
            difficulty="medium",
            answerable=False,
            expected_answer=ExpectedAnswer(
                answer_type="abstain",
                value=None,
            ),
            required_tools=["hybrid_retrieval"],
            relevance_judgments=[
                RelevanceJudgment(
                    document_id="DOC-PC001-RISK-001",
                    evidence_id="EVID-PC001-CUSTOMER-001",
                    relevance_grade=3,
                    rationale="Invalid canonical answer evidence.",
                )
            ],
        )


def test_duplicate_query_ids_are_rejected() -> None:
    case = _orbis_case()

    with pytest.raises(ValidationError):
        EvaluationSet(
            dataset_version="northstar-v1",
            evaluation_version="northstar-eval-v1",
            cases=[
                case,
                case.model_copy(deep=True),
            ],
        )


def test_numeric_answer_can_define_tolerance() -> None:
    answer = ExpectedAnswer(
        answer_type="number",
        value=35.2941,
        unit="percent",
        tolerance=0.01,
    )

    assert answer.tolerance == 0.01
