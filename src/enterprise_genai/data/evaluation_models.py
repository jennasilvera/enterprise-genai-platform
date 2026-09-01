from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

QueryType = Literal[
    "lexical",
    "semantic",
    "hybrid",
    "sql",
    "graph",
    "multi_source",
    "mixed_tool",
    "insufficient_evidence",
]

RequiredTool = Literal[
    "lexical_retrieval",
    "dense_retrieval",
    "hybrid_retrieval",
    "sql",
    "graph",
]

Difficulty = Literal[
    "easy",
    "medium",
    "hard",
]

EvaluationSplit = Literal[
    "development",
    "test",
]

AnswerType = Literal[
    "text",
    "entity",
    "entities",
    "number",
    "boolean",
    "abstain",
]


class ExpectedAnswer(BaseModel):
    answer_type: AnswerType
    value: str | float | bool | list[str] | None
    unit: str | None = None
    tolerance: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_answer(self) -> Self:
        if self.answer_type == "abstain":
            if self.value is not None:
                raise ValueError("Abstention answers must have value=None.")
            return self

        if self.value is None:
            raise ValueError("Non-abstention answers require a value.")

        if self.answer_type == "number":
            if isinstance(self.value, bool) or not isinstance(
                self.value,
                (int, float),
            ):
                raise ValueError("Numeric answers require an int or float value.")
        elif self.tolerance is not None:
            raise ValueError("Tolerance is only valid for numeric answers.")

        if self.answer_type == "entities" and not isinstance(self.value, list):
            raise ValueError("Entity-list answers require list[str].")

        return self


class RelevanceJudgment(BaseModel):
    document_id: str
    evidence_id: str
    relevance_grade: int = Field(ge=0, le=3)
    rationale: str = Field(min_length=1)


class EvaluationCase(BaseModel):
    query_id: str
    question: str = Field(min_length=1)
    query_type: QueryType
    split: EvaluationSplit
    difficulty: Difficulty
    answerable: bool
    expected_answer: ExpectedAnswer
    required_tools: list[RequiredTool]
    relevance_judgments: list[RelevanceJudgment]

    @model_validator(mode="after")
    def validate_case(self) -> Self:
        judgment_keys = [
            (judgment.document_id, judgment.evidence_id) for judgment in self.relevance_judgments
        ]

        if len(judgment_keys) != len(set(judgment_keys)):
            raise ValueError(f"Duplicate relevance judgment in {self.query_id}.")

        grades = [judgment.relevance_grade for judgment in self.relevance_judgments]

        if self.answerable:
            if self.expected_answer.answer_type == "abstain":
                raise ValueError("Answerable cases cannot expect abstention.")

            if 3 not in grades:
                raise ValueError(
                    "Answerable cases require at least one grade-3 canonical evidence judgment."
                )
        else:
            if self.expected_answer.answer_type != "abstain":
                raise ValueError("Unanswerable cases must expect abstention.")

            if 3 in grades:
                raise ValueError("Unanswerable cases cannot contain grade-3 answer evidence.")

        return self


class EvaluationSet(BaseModel):
    dataset_version: str
    evaluation_version: str
    cases: list[EvaluationCase]

    @model_validator(mode="after")
    def validate_query_ids(self) -> Self:
        query_ids = [case.query_id for case in self.cases]

        if len(query_ids) != len(set(query_ids)):
            raise ValueError("Duplicate query_id detected.")

        return self
