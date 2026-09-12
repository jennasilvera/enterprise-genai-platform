from __future__ import annotations

import json
from pathlib import Path

import pytest

from enterprise_genai.evaluation.serving_latency_benchmark import (
    FROZEN_PROTOCOL_SHA256,
    ClientMeasurement,
    CorrelatedMeasurement,
    assert_server_port_available,
    build_result_payload,
    build_uvicorn_command,
    correlate_server_timing,
    parse_structured_server_events,
    validate_answer_payload,
    verify_frozen_protocol,
)
from enterprise_genai.evaluation.serving_latency_protocol import (
    CONTROL_CASES,
    MEASUREMENT_ROUNDS,
)


def test_uvicorn_command_matches_frozen_protocol() -> None:
    assert build_uvicorn_command() == (
        "uv",
        "run",
        "uvicorn",
        "enterprise_genai.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8011",
        "--workers",
        "1",
        "--loop",
        "asyncio",
        "--http",
        "h11",
        "--lifespan",
        "on",
        "--no-access-log",
        "--no-proxy-headers",
        "--no-server-header",
        "--no-date-header",
        "--log-level",
        "info",
    )


def test_frozen_protocol_artifact_matches_expected_hash() -> None:
    assert verify_frozen_protocol() == FROZEN_PROTOCOL_SHA256


def test_answer_validation_enforces_frozen_outcome() -> None:
    case = CONTROL_CASES[0]

    observed = validate_answer_payload(
        case,
        {
            "status": "answered",
            "presentation_source": ("deterministic_fallback"),
            "generation_fidelity": ("rejected"),
        },
    )

    assert observed == (
        "answered",
        "deterministic_fallback",
        "rejected",
    )

    with pytest.raises(
        RuntimeError,
        match="outcome mismatch",
    ):
        validate_answer_payload(
            case,
            {
                "status": "answered",
                "presentation_source": ("model_generation"),
                "generation_fidelity": ("accepted"),
            },
        )


def test_structured_log_parser_ignores_non_json_noise() -> None:
    events = parse_structured_server_events(
        (
            "plain uvicorn output",
            json.dumps(
                {
                    "request_id": "REQ-1",
                    "event": ("http_request_completed"),
                    "duration_ms": 10.0,
                }
            ),
            "not json",
            json.dumps(
                {
                    "request_id": "REQ-1",
                    "event": ("answer_service_completed"),
                    "total_duration_ms": 8.0,
                    "tool_durations_ms": {},
                }
            ),
        )
    )

    assert list(events) == [
        "REQ-1",
    ]

    assert len(events["REQ-1"]) == 2


def test_correlates_generated_request_timings() -> None:
    measurement = ClientMeasurement(
        round_number=1,
        query_id="Q-0001",
        request_id="REQ-1",
        client_observed_ms=12.0,
        status="answered",
        presentation_source=("deterministic_fallback"),
        generation_fidelity="rejected",
    )

    events = {
        "REQ-1": [
            {
                "event": ("http_request_completed"),
                "duration_ms": 11.0,
            },
            {
                "event": ("answer_service_completed"),
                "total_duration_ms": 10.0,
                "tool_durations_ms": {
                    "retrieval": 2.0,
                },
            },
            {
                "event": ("answer_generation_completed"),
                "generation_duration_ms": 7.0,
            },
        ],
    }

    result = correlate_server_timing(
        measurement,
        events,
    )

    assert result.server_http_ms == 11.0
    assert result.answer_service_ms == 10.0
    assert result.generation_ms == 7.0

    assert result.tool_duration_ms == (
        (
            "retrieval",
            2.0,
        ),
    )


def test_correlates_generation_skipped_request() -> None:
    measurement = ClientMeasurement(
        round_number=1,
        query_id="Q-0024",
        request_id="REQ-2",
        client_observed_ms=3.0,
        status="abstained",
        presentation_source="deterministic",
        generation_fidelity=("not_applicable"),
    )

    events = {
        "REQ-2": [
            {
                "event": ("http_request_completed"),
                "duration_ms": 2.5,
            },
            {
                "event": ("answer_service_completed"),
                "total_duration_ms": 2.0,
                "tool_durations_ms": {},
            },
        ],
    }

    result = correlate_server_timing(
        measurement,
        events,
    )

    assert result.generation_ms is None
    assert result.tool_duration_ms == ()


def _synthetic_measurements() -> tuple[
    CorrelatedMeasurement,
    ...,
]:
    measurements: list[CorrelatedMeasurement] = []

    for round_number in range(
        1,
        MEASUREMENT_ROUNDS + 1,
    ):
        for index, case in enumerate(
            CONTROL_CASES,
            start=1,
        ):
            generation = (
                None
                if (case.expected_generation_fidelity == "not_applicable")
                else (5.0 + round_number)
            )

            tool = ()

            if case.query_id in {
                "Q-0001",
                "Q-0023",
            }:
                tool = (
                    (
                        "retrieval",
                        float(index),
                    ),
                )

            elif case.query_id in {
                "Q-0010",
                "Q-0011",
            }:
                tool = (
                    (
                        "sql",
                        float(index),
                    ),
                )

            measurements.append(
                CorrelatedMeasurement(
                    round_number=(round_number),
                    query_id=(case.query_id),
                    request_id=(f"REQ-{round_number}-{index}"),
                    client_observed_ms=(100.0 + round_number + index),
                    server_http_ms=(90.0 + round_number + index),
                    answer_service_ms=(80.0 + round_number + index),
                    generation_ms=(generation),
                    tool_duration_ms=(tool),
                    status=(case.expected_status),
                    presentation_source=(case.expected_presentation_source),
                    generation_fidelity=(case.expected_generation_fidelity),
                )
            )

    return tuple(measurements)


def test_result_payload_has_frozen_shape_and_privacy() -> None:
    payload = build_result_payload(
        protocol_sha256=(FROZEN_PROTOCOL_SHA256),
        startup_ready_ms=1234.5,
        measurements=(_synthetic_measurements()),
        environment={
            "cpu": "synthetic",
        },
    )

    assert payload["measurement"]["total_requests"] == 25

    assert len(payload["samples"]) == 25

    assert payload["summaries"]["client_observed_ms"]["overall"]["n"] == 25

    serialized = json.dumps(
        payload,
        sort_keys=True,
    )

    for case in CONTROL_CASES:
        assert case.question not in serialized

    assert "request_id" not in payload["samples"][0]

    assert payload["privacy"]["stores_question_text"] is False


def test_result_payload_rejects_incomplete_measurement_set() -> None:
    with pytest.raises(
        RuntimeError,
        match="exactly 25",
    ):
        build_result_payload(
            protocol_sha256=(FROZEN_PROTOCOL_SHA256),
            startup_ready_ms=1.0,
            measurements=(_synthetic_measurements()[:-1]),
            environment={},
        )


def test_protocol_hash_guard_rejects_drift(
    tmp_path: Path,
) -> None:
    path = tmp_path / "protocol.json"

    path.write_text(
        '{"version":"tampered"}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="hash mismatch",
    ):
        verify_frozen_protocol(path)


def test_port_preflight_accepts_unused_port(
    monkeypatch,
) -> None:
    import enterprise_genai.evaluation.serving_latency_benchmark as benchmark

    class FakeSocket:
        def __enter__(
            self,
        ):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            traceback,
        ) -> None:
            return None

        def settimeout(
            self,
            timeout,
        ) -> None:
            assert timeout == 0.25

        def connect_ex(
            self,
            address,
        ) -> int:
            assert address == (
                "127.0.0.1",
                8011,
            )

            return 111

    monkeypatch.setattr(
        benchmark.socket,
        "socket",
        lambda *args, **kwargs: FakeSocket(),
    )

    assert_server_port_available()


def test_port_preflight_rejects_occupied_port(
    monkeypatch,
) -> None:
    import enterprise_genai.evaluation.serving_latency_benchmark as benchmark

    class FakeSocket:
        def __enter__(
            self,
        ):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            traceback,
        ) -> None:
            return None

        def settimeout(
            self,
            timeout,
        ) -> None:
            pass

        def connect_ex(
            self,
            address,
        ) -> int:
            return 0

    monkeypatch.setattr(
        benchmark.socket,
        "socket",
        lambda *args, **kwargs: FakeSocket(),
    )

    with pytest.raises(
        RuntimeError,
        match="already occupied",
    ):
        assert_server_port_available()
