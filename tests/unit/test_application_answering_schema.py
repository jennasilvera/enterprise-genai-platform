from __future__ import annotations

import json

from fastapi import FastAPI
from pydantic import TypeAdapter

from enterprise_genai.application import (
    AnswerRequest,
    AnswerServiceResult,
)


def test_answer_request_schema_is_closed_and_nonempty() -> None:
    schema = AnswerRequest.model_json_schema()

    assert schema["additionalProperties"] is False

    assert schema["required"] == ["question"]

    question = schema["properties"]["question"]

    assert question["type"] == "string"

    assert question["minLength"] == 1


def test_answer_result_uses_status_discriminator_and_oneof() -> None:
    schema = TypeAdapter(AnswerServiceResult).json_schema()

    discriminator = schema["discriminator"]

    assert discriminator["propertyName"] == "status"

    assert set(discriminator["mapping"]) == {
        "answered",
        "abstained",
    }

    assert len(schema["oneOf"]) == 2


def test_answer_payload_uses_answer_type_discriminator() -> None:
    schema = TypeAdapter(AnswerServiceResult).json_schema()

    payload = schema["$defs"]["AnsweredServiceResult"]["properties"]["payload"]

    assert payload["discriminator"]["propertyName"] == "answer_type"

    assert set(payload["discriminator"]["mapping"]) == {
        "text",
        "entity",
        "entities",
        "number",
        "boolean",
    }

    assert len(payload["oneOf"]) == 5


def test_public_schema_has_no_raw_generation_surface() -> None:
    schema = TypeAdapter(AnswerServiceResult).json_schema()

    serialized = json.dumps(
        schema,
        sort_keys=True,
    ).casefold()

    for forbidden in (
        "raw_generation",
        "rawgeneration",
        "raw_model_output",
        "provider_prompt",
        "generation_prompt",
    ):
        assert forbidden not in serialized


def test_fastapi_openapi_preserves_answer_discriminator() -> None:
    app = FastAPI(title="phase-11a-schema-test")

    @app.post(
        "/answer",
        response_model=(AnswerServiceResult),
    )
    def answer_probe(
        request: AnswerRequest,
    ) -> AnswerServiceResult:
        raise RuntimeError(f"schema-only endpoint: {request.question}")

    operation = app.openapi()["paths"]["/answer"]["post"]

    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert response_schema["discriminator"]["propertyName"] == "status"

    assert set(response_schema["discriminator"]["mapping"]) == {
        "answered",
        "abstained",
    }

    assert len(response_schema["oneOf"]) == 2
