import pytest

from enterprise_genai.data.evaluation_models import (
    EvaluationCase,
    EvaluationSet,
    ExpectedAnswer,
)
from enterprise_genai.data.evaluation_validation import (
    validate_evaluation_ground_truth,
)
from enterprise_genai.data.universe import build_universe


def _sql_case(
    source_fact_ids: list[str],
) -> EvaluationCase:
    return EvaluationCase(
        query_id="Q-SQL-TEST",
        question=("Which company had the highest year-over-year revenue growth in 2026 Q2?"),
        query_type="sql",
        split="development",
        difficulty="medium",
        answerable=True,
        expected_answer=ExpectedAnswer(
            answer_type="entity",
            value="HelioGrid Energy",
        ),
        answer_source_fact_ids=source_fact_ids,
        required_tools=["sql"],
        relevance_judgments=[],
    )


def test_sql_case_does_not_require_document_qrels() -> None:
    case = _sql_case(
        [
            "FIN-PC-004-2025Q2",
            "FIN-PC-004-2026Q2",
        ]
    )

    assert case.relevance_judgments == []


def test_sql_case_requires_canonical_answer_sources() -> None:
    with pytest.raises(
        ValueError,
        match="canonical answer source facts",
    ):
        _sql_case([])


def test_valid_answer_source_facts_pass() -> None:
    evaluation_set = EvaluationSet(
        dataset_version="northstar-v1",
        evaluation_version="northstar-eval-test",
        cases=[
            _sql_case(
                [
                    "FIN-PC-004-2025Q2",
                    "FIN-PC-004-2026Q2",
                ]
            )
        ],
    )

    validate_evaluation_ground_truth(
        evaluation_set,
        build_universe(),
    )


def test_unknown_answer_source_fact_is_rejected() -> None:
    evaluation_set = EvaluationSet(
        dataset_version="northstar-v1",
        evaluation_version="northstar-eval-test",
        cases=[
            _sql_case(
                [
                    "FIN-PC-999-2026Q2",
                ]
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="FIN-PC-999-2026Q2",
    ):
        validate_evaluation_ground_truth(
            evaluation_set,
            build_universe(),
        )


def test_unanswerable_case_rejects_answer_sources() -> None:
    with pytest.raises(
        ValueError,
        match="cannot define answer source facts",
    ):
        EvaluationCase(
            query_id="Q-ABSTAIN-TEST",
            question="What is the unsupported forecast?",
            query_type="insufficient_evidence",
            split="test",
            difficulty="medium",
            answerable=False,
            expected_answer=ExpectedAnswer(
                answer_type="abstain",
                value=None,
            ),
            answer_source_fact_ids=[
                "PC-001",
            ],
            required_tools=["hybrid_retrieval"],
            relevance_judgments=[],
        )
