from __future__ import annotations

import pytest
from pydantic import (
    TypeAdapter,
    ValidationError,
)

from enterprise_genai.application import (
    AbstainedServiceResult,
    AnsweredServiceResult,
    AnsweringServiceProtocol,
    AnswerRequest,
    AnswerServiceResult,
    EntitiesAnswerPayload,
    EntityAnswerPayload,
    NumberAnswerPayload,
)


def test_answer_request_strips_outer_whitespace() -> None:
    request = AnswerRequest(question="  What happened to ORBIS-IDX-7?  ")

    assert request.question == "What happened to ORBIS-IDX-7?"


def test_answer_request_rejects_blank_question() -> None:
    with pytest.raises(
        ValidationError,
        match="non-whitespace",
    ):
        AnswerRequest(question="   ")


def test_number_payload_rejects_boolean() -> None:
    with pytest.raises(
        ValidationError,
        match="boolean",
    ):
        NumberAnswerPayload(value=True)


def test_number_payload_rejects_nonfinite_float() -> None:
    with pytest.raises(
        ValidationError,
        match="finite",
    ):
        NumberAnswerPayload(value=float("inf"))


def test_entities_payload_rejects_duplicates() -> None:
    with pytest.raises(
        ValidationError,
        match="unique",
    ):
        EntitiesAnswerPayload(
            value=(
                "Alder Manufacturing",
                "Alder Manufacturing",
            )
        )


def test_model_generation_requires_accepted_fidelity() -> None:
    result = AnsweredServiceResult(
        presentation_source="model_generation",
        generation_fidelity="accepted",
        text=("HelioGrid Energy had the highest year-over-year revenue growth."),
        payload=EntityAnswerPayload(value="HelioGrid Energy"),
        citation_ids=("SQL:ENTITY:PC-004",),
        provenance_fact_ids=(
            "FIN-PC004-2025-Q2",
            "FIN-PC004-2026-Q2",
        ),
    )

    assert result.presentation_source == "model_generation"

    assert result.generation_fidelity == "accepted"


def test_presentation_source_fidelity_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="disagree",
    ):
        AnsweredServiceResult(
            presentation_source=("model_generation"),
            generation_fidelity="rejected",
            text="HelioGrid Energy",
            payload=EntityAnswerPayload(value="HelioGrid Energy"),
        )


def test_duplicate_citation_ids_are_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="citation IDs must be unique",
    ):
        AnsweredServiceResult(
            presentation_source="deterministic",
            generation_fidelity=("not_applicable"),
            text="735000000 USD",
            payload=NumberAnswerPayload(
                value=735000000,
                unit="USD",
            ),
            citation_ids=(
                "SQL:VALUE:portfolio_metric_sum",
                "SQL:VALUE:portfolio_metric_sum",
            ),
        )


def test_deterministic_fallback_abstention_is_typed() -> None:
    result = AbstainedServiceResult(
        presentation_source=("deterministic_fallback"),
        generation_fidelity="rejected",
        text=("The available evidence is insufficient to answer this question."),
        reason=("missing_required_information"),
        detail=("Expected 2030 exit valuation was not supported."),
    )

    assert result.status == "abstained"

    assert result.reason == "missing_required_information"


def test_answer_service_result_discriminates_answered_result() -> None:
    adapter = TypeAdapter(AnswerServiceResult)

    result = adapter.validate_python(
        {
            "status": "answered",
            "presentation_source": ("deterministic"),
            "generation_fidelity": ("not_applicable"),
            "text": "735000000 USD",
            "payload": {
                "answer_type": "number",
                "value": 735000000,
                "unit": "USD",
            },
            "citation_ids": [],
            "provenance_fact_ids": [],
        }
    )

    assert isinstance(
        result,
        AnsweredServiceResult,
    )

    assert result.payload.answer_type == "number"


def test_answering_service_protocol_is_structural() -> None:
    class FakeService:
        def answer(
            self,
            request: AnswerRequest,
        ) -> AnswerServiceResult:
            return AbstainedServiceResult(
                presentation_source=("deterministic"),
                generation_fidelity=("not_applicable"),
                text=("The request cannot be answered."),
                reason="test_abstention",
            )

    service = FakeService()

    assert isinstance(
        service,
        AnsweringServiceProtocol,
    )

    result = service.answer(AnswerRequest(question="Question?"))

    assert result.status == "abstained"
