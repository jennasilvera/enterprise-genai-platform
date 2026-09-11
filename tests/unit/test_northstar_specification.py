from __future__ import annotations

from enterprise_genai.application.answering import (
    AnswerRequest,
)
from enterprise_genai.application.northstar_specification import (
    NORTHSTAR_BOUNDED_SPECIFICATION_VERSION,
    NorthstarBoundedSpecificationProvider,
)
from enterprise_genai.application.specification import (
    ExecutableAnswerSpecification,
    UnsupportedAnswerSpecification,
)


def _provider() -> NorthstarBoundedSpecificationProvider:
    return NorthstarBoundedSpecificationProvider()


def test_serving_specification_version_is_frozen() -> None:
    assert NORTHSTAR_BOUNDED_SPECIFICATION_VERSION == "northstar-bounded-serving-specification-v1"


def test_defect_question_compiles_to_retrieval() -> None:
    question = "What defect affected ORBIS-IDX-7?"

    result = _provider().prepare(AnswerRequest(question=question))

    assert isinstance(
        result,
        ExecutableAnswerSpecification,
    )

    plan = result.orchestration_plan.execution_plan

    assert plan.route_label == "retrieval"

    assert plan.retrieval is not None

    assert result.requirements[0].all_terms == ("ORBIS-IDX-7",)

    assert result.synthesis is not None

    assert result.synthesis.mode == "retrieval_text"


def test_growth_question_compiles_to_bounded_sql() -> None:
    result = _provider().prepare(
        AnswerRequest(
            question=(
                "Which portfolio company had the highest year-over-year revenue growth in 2026 Q2?"
            )
        )
    )

    assert isinstance(
        result,
        ExecutableAnswerSpecification,
    )

    query = result.orchestration_plan.execution_plan.sql

    assert query is not None

    assert query.period == "2026Q2"

    assert query.comparison_period == "2025Q2"

    assert query.operation == "portfolio_growth_rank"

    assert query.metric == "revenue_usd"

    assert query.rank_order == "highest"

    assert query.result_limit == 1

    assert result.synthesis is not None

    assert result.synthesis.mode == "entity_name"


def test_lowest_growth_is_supported_explicitly() -> None:
    result = _provider().prepare(
        AnswerRequest(
            question=("Which company had the lowest year over year revenue growth in 2026 Q2?")
        )
    )

    assert isinstance(
        result,
        ExecutableAnswerSpecification,
    )

    query = result.orchestration_plan.execution_plan.sql

    assert query is not None
    assert query.rank_order == "lowest"


def test_total_revenue_compiles_to_portfolio_sum() -> None:
    result = _provider().prepare(
        AnswerRequest(question=("What was total portfolio revenue in 2026 Q2?"))
    )

    assert isinstance(
        result,
        ExecutableAnswerSpecification,
    )

    query = result.orchestration_plan.execution_plan.sql

    assert query is not None

    assert query.operation == "portfolio_metric_sum"

    assert query.period == "2026Q2"
    assert query.metric == "revenue_usd"

    assert result.synthesis is not None

    assert result.synthesis.mode == "structured_value"


def test_exit_valuation_compiles_to_retrieval_requirement() -> None:
    result = _provider().prepare(
        AnswerRequest(
            question=(
                "What is Northstar's expected 2030 exit valuation for Meridian Health Systems?"
            )
        )
    )

    assert isinstance(
        result,
        ExecutableAnswerSpecification,
    )

    requirement = result.requirements[0]

    assert requirement.all_terms == (
        "2030 exit valuation",
        "Meridian Health Systems",
    )

    assert result.synthesis is not None

    assert result.synthesis.mode == "retrieval_text"


def test_unrecognized_question_is_explicitly_unsupported() -> None:
    question = "What was Alder Manufacturing's exact customer churn rate in 2026 Q2?"

    result = _provider().prepare(AnswerRequest(question=question))

    assert isinstance(
        result,
        UnsupportedAnswerSpecification,
    )

    assert result.question == question

    assert "deterministic" in result.detail
