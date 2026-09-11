from __future__ import annotations

import re

from enterprise_genai.answering.sufficiency import (
    EvidenceRequirement,
)
from enterprise_genai.application.answering import (
    AnswerRequest,
)
from enterprise_genai.application.specification import (
    AnswerExecutionSpecification,
    AnswerSynthesisSpecification,
    ExecutableAnswerSpecification,
    UnsupportedAnswerSpecification,
)
from enterprise_genai.execution.contracts import (
    RetrievalQuery,
    StructuredQuery,
    ToolExecutionPlan,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
)

NORTHSTAR_BOUNDED_SPECIFICATION_VERSION = "northstar-bounded-serving-specification-v1"


_DEFECT_RE = re.compile(
    r"^what defect affected "
    r"(?P<identifier>[A-Za-z0-9][A-Za-z0-9._:-]*)"
    r"\??$",
    re.IGNORECASE,
)

_GROWTH_RE = re.compile(
    r"^which (?:portfolio )?company had the "
    r"(?P<rank>highest|lowest) "
    r"year[- ]over[- ]year revenue growth in "
    r"(?P<year>20\d{2})\s*Q(?P<quarter>[1-4])"
    r"\??$",
    re.IGNORECASE,
)

_TOTAL_REVENUE_RE = re.compile(
    r"^what was total portfolio revenue in "
    r"(?P<year>20\d{2})\s*Q(?P<quarter>[1-4])"
    r"\??$",
    re.IGNORECASE,
)

_EXIT_VALUATION_RE = re.compile(
    r"^what is northstar(?:'s|’s) expected "
    r"(?P<year>20\d{2}) exit valuation for "
    r"(?P<company>.+?)"
    r"\??$",
    re.IGNORECASE,
)


def _quarter(
    *,
    year: str,
    quarter: str,
) -> str:
    return f"{year}Q{quarter}"


def _previous_year(
    period: str,
) -> str:
    year = int(period[:4])

    return f"{year - 1}{period[4:]}"


def _retrieval_specification(
    *,
    question: str,
    requirement: EvidenceRequirement,
    synthesis: AnswerSynthesisSpecification,
) -> ExecutableAnswerSpecification:
    return ExecutableAnswerSpecification(
        question=question,
        orchestration_plan=(
            BoundedOrchestrationPlan(
                question=question,
                execution_plan=(
                    ToolExecutionPlan(
                        route_label="retrieval",
                        retrieval=(
                            RetrievalQuery(
                                question=question,
                                top_k=10,
                            )
                        ),
                    )
                ),
            )
        ),
        requirements=(requirement,),
        synthesis=synthesis,
    )


class NorthstarBoundedSpecificationProvider:
    """Compile only explicit deterministic Northstar query families.

    Version 1 intentionally does not perform arbitrary semantic
    planning. Requests outside the documented grammar are represented
    as unsupported rather than guessed into an execution plan.
    """

    @property
    def version(
        self,
    ) -> str:
        return NORTHSTAR_BOUNDED_SPECIFICATION_VERSION

    def prepare(
        self,
        request: AnswerRequest,
    ) -> AnswerExecutionSpecification:
        question = " ".join(request.question.split())

        defect = _DEFECT_RE.fullmatch(question)

        if defect is not None:
            identifier = defect.group("identifier")

            return _retrieval_specification(
                question=request.question,
                requirement=(
                    EvidenceRequirement(
                        requirement_id=("serve-defect-identifier"),
                        description=(f"Evidence explicitly describing {identifier}."),
                        allowed_tools=("retrieval",),
                        allowed_kinds=("retrieval_hit",),
                        all_terms=(identifier,),
                    )
                ),
                synthesis=(
                    AnswerSynthesisSpecification(
                        mode="retrieval_text",
                        answer_type="text",
                    )
                ),
            )

        growth = _GROWTH_RE.fullmatch(question)

        if growth is not None:
            period = _quarter(
                year=growth.group("year"),
                quarter=growth.group("quarter"),
            )

            rank = growth.group("rank").casefold()

            return ExecutableAnswerSpecification(
                question=request.question,
                orchestration_plan=(
                    BoundedOrchestrationPlan(
                        question=(request.question),
                        execution_plan=(
                            ToolExecutionPlan(
                                route_label="sql",
                                sql=StructuredQuery(
                                    period=period,
                                    comparison_period=(_previous_year(period)),
                                    operation=("portfolio_growth_rank"),
                                    metric=("revenue_usd"),
                                    rank_order=rank,
                                    result_limit=1,
                                ),
                            )
                        ),
                    )
                ),
                requirements=(
                    EvidenceRequirement(
                        requirement_id=("serve-growth-entity"),
                        description=(
                            "Structured evidence identifying the ranked portfolio company."
                        ),
                        allowed_tools=("sql",),
                        allowed_kinds=("structured_entity",),
                    ),
                ),
                synthesis=(
                    AnswerSynthesisSpecification(
                        mode="entity_name",
                        answer_type="entity",
                    )
                ),
            )

        total_revenue = _TOTAL_REVENUE_RE.fullmatch(question)

        if total_revenue is not None:
            period = _quarter(
                year=total_revenue.group("year"),
                quarter=total_revenue.group("quarter"),
            )

            return ExecutableAnswerSpecification(
                question=request.question,
                orchestration_plan=(
                    BoundedOrchestrationPlan(
                        question=(request.question),
                        execution_plan=(
                            ToolExecutionPlan(
                                route_label="sql",
                                sql=StructuredQuery(
                                    period=period,
                                    operation=("portfolio_metric_sum"),
                                    metric=("revenue_usd"),
                                ),
                            )
                        ),
                    )
                ),
                requirements=(
                    EvidenceRequirement(
                        requirement_id=("serve-portfolio-revenue"),
                        description=("Structured portfolio revenue evidence."),
                        allowed_tools=("sql",),
                        allowed_kinds=("structured_value",),
                    ),
                ),
                synthesis=(
                    AnswerSynthesisSpecification(
                        mode=("structured_value"),
                        answer_type="number",
                    )
                ),
            )

        exit_valuation = _EXIT_VALUATION_RE.fullmatch(question)

        if exit_valuation is not None:
            year = exit_valuation.group("year")

            company = exit_valuation.group("company").strip().rstrip("?").strip()

            return _retrieval_specification(
                question=request.question,
                requirement=(
                    EvidenceRequirement(
                        requirement_id=("serve-exit-valuation"),
                        description=(
                            "Evidence explicitly "
                            "stating Northstar's "
                            f"expected {year} exit "
                            f"valuation for {company}."
                        ),
                        allowed_tools=("retrieval",),
                        allowed_kinds=("retrieval_hit",),
                        all_terms=(
                            f"{year} exit valuation",
                            company,
                        ),
                    )
                ),
                synthesis=(
                    AnswerSynthesisSpecification(
                        mode="retrieval_text",
                        answer_type="text",
                    )
                ),
            )

        return UnsupportedAnswerSpecification(
            question=request.question,
            detail=("Question is outside the supported deterministic Northstar serving grammar."),
        )
