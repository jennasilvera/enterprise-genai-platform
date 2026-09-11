from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from enterprise_genai.api.main import app
from enterprise_genai.application import (
    AbstainedServiceResult,
    AnsweredServiceResult,
    AnswerRequest,
    AnswerServiceResult,
    NumberAnswerPayload,
)


class FakeAnsweringService:
    def __init__(
        self,
        result: AnswerServiceResult,
    ) -> None:
        self.result = result
        self.requests: list[AnswerRequest] = []

    def answer(
        self,
        request: AnswerRequest,
    ) -> AnswerServiceResult:
        self.requests.append(request)

        return self.result


def _answered_result() -> AnsweredServiceResult:
    return AnsweredServiceResult(
        presentation_source=("deterministic_fallback"),
        generation_fidelity="rejected",
        text="735000000 USD",
        payload=NumberAnswerPayload(
            value=735000000,
            unit="USD",
        ),
        citation_ids=("SQL:VALUE:portfolio_metric_sum",),
        provenance_fact_ids=(
            "FIN-PC-001-2026Q2",
            "FIN-PC-002-2026Q2",
        ),
    )


def _abstained_result() -> AbstainedServiceResult:
    return AbstainedServiceResult(
        presentation_source="deterministic",
        generation_fidelity=("not_applicable"),
        text=("The available evidence is insufficient to answer this question."),
        reason=("missing_required_information"),
        detail=("Expected exit valuation was not supported."),
    )


@pytest.fixture(autouse=True)
def clear_answering_service():
    if hasattr(
        app.state,
        "answering_service",
    ):
        delattr(
            app.state,
            "answering_service",
        )

    yield

    if hasattr(
        app.state,
        "answering_service",
    ):
        delattr(
            app.state,
            "answering_service",
        )


def test_answer_endpoint_requires_installed_service() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/answer",
            json={
                "question": "Question?",
            },
        )

    assert response.status_code == 503

    assert response.json() == {"detail": ("answering service unavailable")}


def test_answer_endpoint_serializes_answered_result() -> None:
    service = FakeAnsweringService(_answered_result())

    app.state.answering_service = service

    with TestClient(app) as client:
        response = client.post(
            "/answer",
            json={"question": ("What was total portfolio revenue in 2026 Q2?")},
        )

    assert response.status_code == 200

    assert response.json() == {
        "presentation_source": ("deterministic_fallback"),
        "generation_fidelity": ("rejected"),
        "text": "735000000 USD",
        "citation_ids": [
            "SQL:VALUE:portfolio_metric_sum",
        ],
        "provenance_fact_ids": [
            "FIN-PC-001-2026Q2",
            "FIN-PC-002-2026Q2",
        ],
        "status": "answered",
        "payload": {
            "answer_type": "number",
            "value": 735000000,
            "unit": "USD",
        },
    }

    assert len(service.requests) == 1


def test_answer_endpoint_serializes_abstention() -> None:
    service = FakeAnsweringService(_abstained_result())

    app.state.answering_service = service

    with TestClient(app) as client:
        response = client.post(
            "/answer",
            json={"question": ("What is the future exit valuation?")},
        )

    assert response.status_code == 200

    assert response.json() == {
        "presentation_source": ("deterministic"),
        "generation_fidelity": ("not_applicable"),
        "text": ("The available evidence is insufficient to answer this question."),
        "citation_ids": [],
        "provenance_fact_ids": [],
        "status": "abstained",
        "reason": ("missing_required_information"),
        "detail": ("Expected exit valuation was not supported."),
    }


def test_answer_endpoint_normalizes_question() -> None:
    service = FakeAnsweringService(_answered_result())

    app.state.answering_service = service

    with TestClient(app) as client:
        response = client.post(
            "/answer",
            json={"question": ("   What was revenue?   ")},
        )

    assert response.status_code == 200

    assert service.requests[0].question == "What was revenue?"


def test_answer_endpoint_rejects_blank_question() -> None:
    service = FakeAnsweringService(_answered_result())

    app.state.answering_service = service

    with TestClient(app) as client:
        response = client.post(
            "/answer",
            json={
                "question": "   ",
            },
        )

    assert response.status_code == 422

    assert service.requests == []


def test_answer_endpoint_rejects_unknown_request_fields() -> None:
    service = FakeAnsweringService(_answered_result())

    app.state.answering_service = service

    with TestClient(app) as client:
        response = client.post(
            "/answer",
            json={
                "question": "Question?",
                "raw_generation": ("do not accept this"),
            },
        )

    assert response.status_code == 422

    assert service.requests == []


def test_real_openapi_preserves_answer_discriminator() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    operation = schema["paths"]["/answer"]["post"]

    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert response_schema["discriminator"]["propertyName"] == "status"

    assert set(response_schema["discriminator"]["mapping"]) == {
        "answered",
        "abstained",
    }

    assert len(response_schema["oneOf"]) == 2
