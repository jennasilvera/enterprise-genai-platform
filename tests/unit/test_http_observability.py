from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import (
    TestClient,
)

from enterprise_genai.api.main import app
from enterprise_genai.observability import (
    HTTP_REQUEST_TRACE_VERSION,
    REQUEST_ID_HEADER,
    RequestObservabilityMiddleware,
)
from enterprise_genai.observability import (
    http as http_observability,
)


class FakeLogger:
    def __init__(
        self,
    ) -> None:
        self.events: list[
            tuple[
                str,
                str,
                dict[
                    str,
                    object,
                ],
            ]
        ] = []

    def info(
        self,
        event: str,
        **kwargs,
    ) -> None:
        self.events.append(
            (
                "info",
                event,
                kwargs,
            )
        )

    def error(
        self,
        event: str,
        **kwargs,
    ) -> None:
        self.events.append(
            (
                "error",
                event,
                kwargs,
            )
        )


def test_http_trace_version_is_frozen() -> None:
    assert HTTP_REQUEST_TRACE_VERSION == "northstar-http-request-trace-v1"

    assert REQUEST_ID_HEADER == "X-Request-ID"


def test_http_response_contains_unique_server_request_id() -> None:
    with TestClient(app) as client:
        first = client.get("/health/live")

        second = client.get("/health/live")

    assert first.status_code == 200

    assert second.status_code == 200

    first_id = first.headers[REQUEST_ID_HEADER]

    second_id = second.headers[REQUEST_ID_HEADER]

    UUID(first_id)

    UUID(second_id)

    assert first_id != second_id


def test_http_events_do_not_log_question_or_query_string(
    monkeypatch,
) -> None:
    fake = FakeLogger()

    monkeypatch.setattr(
        http_observability,
        "logger",
        fake,
    )

    secret_question = "PRIVATE-QUESTION-DO-NOT-LOG"

    secret_query = "PRIVATE-QUERY-DO-NOT-LOG"

    with TestClient(app) as client:
        response = client.post(
            (f"/answer?debug={secret_query}"),
            json={"question": (secret_question)},
        )

    assert response.status_code == 503

    assert len(fake.events) == 2

    (
        start_level,
        start_event,
        start_fields,
    ) = fake.events[0]

    (
        end_level,
        end_event,
        end_fields,
    ) = fake.events[1]

    assert start_level == "info"

    assert start_event == "http_request_started"

    assert end_level == "info"

    assert end_event == "http_request_completed"

    assert start_fields["request_id"] == end_fields["request_id"]

    assert response.headers[REQUEST_ID_HEADER] == start_fields["request_id"]

    assert start_fields["path"] == "/answer"

    assert end_fields["path"] == "/answer"

    assert end_fields["status_code"] == 503

    assert end_fields["duration_ms"] >= 0.0

    serialized = repr(fake.events)

    assert secret_question not in serialized

    assert secret_query not in serialized


def test_unhandled_failure_logs_only_exception_type(
    monkeypatch,
) -> None:
    fake = FakeLogger()

    monkeypatch.setattr(
        http_observability,
        "logger",
        fake,
    )

    broken = FastAPI()

    broken.add_middleware(RequestObservabilityMiddleware)

    sensitive_message = "PRIVATE-EXCEPTION-DO-NOT-LOG"

    @broken.get("/boom")
    def boom():
        raise RuntimeError(sensitive_message)

    with TestClient(
        broken,
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/boom")

    assert response.status_code == 500

    assert len(fake.events) == 2

    level, event, fields = fake.events[1]

    assert level == "error"

    assert event == "http_request_failed"

    assert fields["error_type"] == "RuntimeError"

    assert fields["path"] == "/boom"

    assert fields["duration_ms"] >= 0.0

    assert sensitive_message not in repr(fake.events)
