from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from enterprise_genai.answering.contracts import (
    EvidenceRecord,
    FrozenAnsweringModel,
    NonEmptyStr,
    SufficiencyReason,
)
from enterprise_genai.answering.outcomes import (
    AbstentionOutcome,
    AnswerOutcome,
    GroundedAnswer,
    GroundedAnswerType,
)
from enterprise_genai.answering.sufficiency import (
    EvidenceRequirement,
)
from enterprise_genai.answering.synthesis import (
    SynthesisMode,
)
from enterprise_genai.data.evaluation_models import (
    AnswerType,
    EvaluationCase,
    EvaluationSet,
)
from enterprise_genai.execution.contracts import (
    RetrievalQuery,
    StructuredQuery,
    ToolExecutionPlan,
)

ANSWERING_EVALUATION_PROTOCOL_VERSION = "northstar-answering-evaluation-v1"

PHASE9C4_QUERY_IDS = (
    "Q-0001",
    "Q-0010",
    "Q-0011",
    "Q-0023",
    "Q-0024",
)

EvaluationExecutionKind = Literal[
    "orchestration",
    "unsupported_request",
]

ComparisonMode = Literal[
    "canonical_retrieval_evidence",
    "exact_entity",
    "numeric_tolerance",
    "abstention",
]


class AnsweringCaseProtocol(FrozenAnsweringModel):
    """Non-oracular execution and answering specification.

    Expected benchmark values and answer-source fact IDs deliberately
    do not live in this contract. They are joined only during scoring.
    """

    query_id: NonEmptyStr

    execution_kind: EvaluationExecutionKind

    execution_plan: ToolExecutionPlan | None = None

    requirements: tuple[
        EvidenceRequirement,
        ...,
    ] = ()

    synthesis_mode: SynthesisMode | None = None

    synthesis_answer_type: GroundedAnswerType | None = None

    comparison_mode: ComparisonMode

    expected_abstention_reason: SufficiencyReason | None = None

    unsupported_detail: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_protocol(
        self,
    ) -> AnsweringCaseProtocol:
        if self.execution_kind == "orchestration":
            if self.execution_plan is None:
                raise ValueError("Orchestration evaluation requires an execution plan.")

            if self.unsupported_detail is not None:
                raise ValueError("Orchestration evaluation cannot define unsupported_detail.")

            if not self.requirements:
                raise ValueError(
                    "Orchestration evaluation requires explicit evidence requirements."
                )

        else:
            if self.execution_plan is not None:
                raise ValueError(
                    "Unsupported-request evaluation must not define an execution plan."
                )

            if self.requirements:
                raise ValueError(
                    "Unsupported-request evaluation must not define evidence requirements."
                )

            if self.unsupported_detail is None:
                raise ValueError("Unsupported-request evaluation requires unsupported_detail.")

        if self.comparison_mode == "abstention":
            if self.synthesis_mode is not None or self.synthesis_answer_type is not None:
                raise ValueError("Abstention protocol must not define answer synthesis.")

            if self.expected_abstention_reason is None:
                raise ValueError("Abstention protocol requires an expected typed reason.")

        else:
            if self.synthesis_mode is None or self.synthesis_answer_type is None:
                raise ValueError("Answer protocol requires bounded synthesis metadata.")

            if self.expected_abstention_reason is not None:
                raise ValueError("Answer protocol cannot define an abstention reason.")

        if self.comparison_mode == "canonical_retrieval_evidence" and (
            self.synthesis_mode != "retrieval_text" or self.synthesis_answer_type != "text"
        ):
            raise ValueError("Canonical retrieval comparison requires retrieval_text synthesis.")

        if self.comparison_mode == "exact_entity" and self.synthesis_answer_type != "entity":
            raise ValueError("Exact entity comparison requires an entity answer.")

        if self.comparison_mode == "numeric_tolerance" and self.synthesis_answer_type != "number":
            raise ValueError("Numeric comparison requires a number answer.")

        return self


class AnswerComparison(FrozenAnsweringModel):
    """Stage-resolved comparison of one final answering outcome."""

    query_id: NonEmptyStr

    comparison_mode: ComparisonMode

    expected_answer_type: AnswerType

    observed_outcome: Literal[
        "answer",
        "abstain",
    ]

    observed_answer_type: AnswerType

    answer_type_correct: bool

    answer_value_correct: bool | None = None

    unit_correct: bool | None = None

    canonical_text_evidence_correct: bool | None = None

    abstention_reason_correct: bool | None = None

    supporting_record_ids_valid: bool

    source_fact_ids_valid: bool | None = None

    answer_source_provenance_correct: bool | None = None

    case_passed: bool


def _case_by_id(
    evaluation: EvaluationSet,
    query_id: str,
) -> EvaluationCase:
    matches = tuple(case for case in evaluation.cases if case.query_id == query_id)

    if len(matches) != 1:
        raise ValueError(
            f"Evaluation protocol requires exactly one {query_id!r} case; observed {len(matches)}."
        )

    return matches[0]


def build_phase9c4_protocol(
    evaluation: EvaluationSet,
) -> tuple[
    AnsweringCaseProtocol,
    ...,
]:
    """Build the frozen five-case answering integration protocol.

    Plans, evidence requirements, and synthesis modes are authored from
    question semantics and bounded production contracts.

    Benchmark expected values, relevance judgments, and answer-source
    fact IDs are not consulted here.
    """

    if evaluation.dataset_version != ("northstar-v1"):
        raise ValueError("Phase 9C4A requires dataset_version='northstar-v1'.")

    q1 = _case_by_id(
        evaluation,
        "Q-0001",
    )
    _case_by_id(
        evaluation,
        "Q-0010",
    )
    _case_by_id(
        evaluation,
        "Q-0011",
    )
    q23 = _case_by_id(
        evaluation,
        "Q-0023",
    )
    _case_by_id(
        evaluation,
        "Q-0024",
    )

    return (
        AnsweringCaseProtocol(
            query_id="Q-0001",
            execution_kind="orchestration",
            execution_plan=ToolExecutionPlan(
                route_label="retrieval",
                retrieval=RetrievalQuery(
                    dataset_version=(evaluation.dataset_version),
                    question=q1.question,
                    top_k=10,
                ),
            ),
            requirements=(
                EvidenceRequirement(
                    requirement_id=("q0001-orbis-identifier"),
                    description=("Evidence explicitly describing ORBIS-IDX-7."),
                    allowed_tools=("retrieval",),
                    allowed_kinds=("retrieval_hit",),
                    all_terms=("ORBIS-IDX-7",),
                ),
            ),
            synthesis_mode="retrieval_text",
            synthesis_answer_type="text",
            comparison_mode=("canonical_retrieval_evidence"),
        ),
        AnsweringCaseProtocol(
            query_id="Q-0010",
            execution_kind="orchestration",
            execution_plan=ToolExecutionPlan(
                route_label="sql",
                sql=StructuredQuery(
                    dataset_version=(evaluation.dataset_version),
                    period="2026Q2",
                    comparison_period="2025Q2",
                    operation=("portfolio_growth_rank"),
                    metric="revenue_usd",
                    rank_order="highest",
                    result_limit=1,
                ),
            ),
            requirements=(
                EvidenceRequirement(
                    requirement_id=("q0010-growth-entity"),
                    description=("Structured entity returned by the portfolio growth ranking."),
                    allowed_tools=("sql",),
                    allowed_kinds=("structured_entity",),
                ),
            ),
            synthesis_mode="entity_name",
            synthesis_answer_type="entity",
            comparison_mode="exact_entity",
        ),
        AnsweringCaseProtocol(
            query_id="Q-0011",
            execution_kind="orchestration",
            execution_plan=ToolExecutionPlan(
                route_label="sql",
                sql=StructuredQuery(
                    dataset_version=(evaluation.dataset_version),
                    period="2026Q2",
                    operation=("portfolio_metric_sum"),
                    metric="revenue_usd",
                ),
            ),
            requirements=(
                EvidenceRequirement(
                    requirement_id=("q0011-revenue-value"),
                    description=("Structured portfolio revenue scalar."),
                    allowed_tools=("sql",),
                    allowed_kinds=("structured_value",),
                ),
            ),
            synthesis_mode="structured_value",
            synthesis_answer_type="number",
            comparison_mode=("numeric_tolerance"),
        ),
        AnsweringCaseProtocol(
            query_id="Q-0023",
            execution_kind="orchestration",
            execution_plan=ToolExecutionPlan(
                route_label="retrieval",
                retrieval=RetrievalQuery(
                    dataset_version=(evaluation.dataset_version),
                    question=q23.question,
                    top_k=10,
                ),
            ),
            requirements=(
                EvidenceRequirement(
                    requirement_id=("q0023-exit-valuation"),
                    description=(
                        "Evidence explicitly stating "
                        "Northstar's expected 2030 "
                        "exit valuation for Meridian "
                        "Health Systems."
                    ),
                    allowed_tools=("retrieval",),
                    allowed_kinds=("retrieval_hit",),
                    all_terms=("2030 exit valuation",),
                ),
            ),
            comparison_mode="abstention",
            expected_abstention_reason=("missing_required_information"),
        ),
        AnsweringCaseProtocol(
            query_id="Q-0024",
            execution_kind=("unsupported_request"),
            comparison_mode="abstention",
            expected_abstention_reason=("unsupported_request"),
            unsupported_detail=(
                "customer_churn_rate is outside the bounded StructuredQuery metric set."
            ),
        ),
    )


def _normalize_string(
    value: str,
) -> str:
    return " ".join(value.casefold().split())


def _support_records(
    outcome: GroundedAnswer,
) -> tuple[
    EvidenceRecord,
    ...,
]:
    selected = set(outcome.supporting_record_ids)

    return tuple(
        record for record in outcome.assessment.bundle.records if record.record_id in selected
    )


def _supporting_ids_valid(
    outcome: GroundedAnswer,
) -> bool:
    available = {record.record_id for record in outcome.assessment.bundle.records}

    observed = set(outcome.supporting_record_ids)

    return (
        outcome.supporting_record_ids == outcome.assessment.supporting_record_ids
        and observed <= available
        and bool(observed)
    )


def _source_fact_ids_valid(
    outcome: GroundedAnswer,
) -> bool:
    expected: set[str] = set()

    for record in _support_records(outcome):
        expected.update(record.source_fact_ids)

    return outcome.source_fact_ids == tuple(sorted(expected))


def _answer_source_provenance_correct(
    *,
    case: EvaluationCase,
    outcome: GroundedAnswer,
) -> bool:
    expected = set(case.answer_source_fact_ids)

    observed = set(outcome.source_fact_ids)

    return bool(expected) and (expected <= observed)


def _canonical_text_evidence_correct(
    *,
    case: EvaluationCase,
    outcome: GroundedAnswer,
) -> bool:
    canonical = {
        (
            judgment.document_id,
            judgment.evidence_id,
        )
        for judgment in case.relevance_judgments
        if judgment.relevance_grade == 3
    }

    if not canonical:
        return False

    for record in _support_records(outcome):
        if record.tool != "retrieval":
            continue

        for (
            document_id,
            evidence_id,
        ) in canonical:
            if record.document_id == document_id and record.record_id.endswith(f":{evidence_id}"):
                return True

    return False


def _numeric_value_correct(
    *,
    expected: int | float,
    observed: object,
    tolerance: float,
) -> bool:
    if isinstance(
        observed,
        bool,
    ) or not isinstance(
        observed,
        (
            int,
            float,
        ),
    ):
        return False

    return abs(float(observed) - float(expected)) <= tolerance


def compare_answer_outcome(
    *,
    case: EvaluationCase,
    protocol: AnsweringCaseProtocol,
    outcome: AnswerOutcome,
) -> AnswerComparison:
    """Score one final outcome without influencing answer construction."""

    if case.query_id != protocol.query_id:
        raise ValueError("Evaluation case and protocol query IDs must match.")

    expected = case.expected_answer

    if isinstance(
        outcome,
        AbstentionOutcome,
    ):
        answer_type_correct = expected.answer_type == "abstain"

        reason_correct = (
            protocol.expected_abstention_reason is not None
            and outcome.reason == protocol.expected_abstention_reason
        )

        passed = protocol.comparison_mode == "abstention" and answer_type_correct and reason_correct

        return AnswerComparison(
            query_id=case.query_id,
            comparison_mode=(protocol.comparison_mode),
            expected_answer_type=(expected.answer_type),
            observed_outcome="abstain",
            observed_answer_type="abstain",
            answer_type_correct=(answer_type_correct),
            abstention_reason_correct=(reason_correct),
            supporting_record_ids_valid=(
                outcome.supporting_record_ids == outcome.assessment.supporting_record_ids
            ),
            case_passed=passed,
        )

    answer_type_correct = outcome.answer_type == expected.answer_type

    supporting_valid = _supporting_ids_valid(outcome)

    source_facts_valid = _source_fact_ids_valid(outcome)

    provenance_correct = _answer_source_provenance_correct(
        case=case,
        outcome=outcome,
    )

    value_correct: bool | None = None
    unit_correct: bool | None = None
    canonical_text: bool | None = None

    if protocol.comparison_mode == "canonical_retrieval_evidence":
        canonical_text = _canonical_text_evidence_correct(
            case=case,
            outcome=outcome,
        )

        passed = all(
            (
                answer_type_correct,
                supporting_valid,
                source_facts_valid,
                provenance_correct,
                canonical_text,
            )
        )

    elif protocol.comparison_mode == "exact_entity":
        value_correct = (
            isinstance(
                expected.value,
                str,
            )
            and isinstance(
                outcome.value,
                str,
            )
            and _normalize_string(outcome.value) == _normalize_string(expected.value)
        )

        passed = all(
            (
                answer_type_correct,
                value_correct,
                supporting_valid,
                source_facts_valid,
                provenance_correct,
            )
        )

    elif protocol.comparison_mode == "numeric_tolerance":
        if isinstance(
            expected.value,
            bool,
        ) or not isinstance(
            expected.value,
            (
                int,
                float,
            ),
        ):
            raise ValueError("Numeric comparison requires a numeric benchmark value.")

        tolerance = expected.tolerance if expected.tolerance is not None else 0.0

        value_correct = _numeric_value_correct(
            expected=expected.value,
            observed=outcome.value,
            tolerance=tolerance,
        )

        unit_correct = outcome.unit == expected.unit

        passed = all(
            (
                answer_type_correct,
                value_correct,
                unit_correct,
                supporting_valid,
                source_facts_valid,
                provenance_correct,
            )
        )

    else:
        passed = False

    return AnswerComparison(
        query_id=case.query_id,
        comparison_mode=(protocol.comparison_mode),
        expected_answer_type=(expected.answer_type),
        observed_outcome="answer",
        observed_answer_type=(outcome.answer_type),
        answer_type_correct=(answer_type_correct),
        answer_value_correct=(value_correct),
        unit_correct=unit_correct,
        canonical_text_evidence_correct=(canonical_text),
        supporting_record_ids_valid=(supporting_valid),
        source_fact_ids_valid=(source_facts_valid),
        answer_source_provenance_correct=(provenance_correct),
        case_passed=passed,
    )
