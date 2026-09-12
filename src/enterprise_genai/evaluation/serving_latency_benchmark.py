from __future__ import annotations

import hashlib
import http.client
import json
import math
import os
import platform
import socket
import subprocess
import tempfile
import time
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns
from typing import Any

import torch

from enterprise_genai.evaluation.serving_latency_protocol import (
    ANSWER_PATH,
    CONTROL_CASES,
    MEASUREMENT_ROUNDS,
    MEASUREMENT_SAMPLE_COUNT,
    READINESS_PATH,
    READINESS_POLL_INTERVAL_S,
    REQUEST_TIMEOUT_S,
    SERVER_APP,
    SERVER_HOST,
    SERVER_PORT,
    SERVING_LATENCY_PROTOCOL_VERSION,
    STARTUP_TIMEOUT_S,
    LatencyControlCase,
    summarize_latency_samples,
)

SERVING_LATENCY_RESULT_VERSION = "northstar-localhost-serving-latency-result-v1"

FROZEN_PROTOCOL_SHA256 = "c39f2c19135efd8959bd0490a6666acb3e7eda45ba016d76f4267634c8a2e432"

DEFAULT_PROTOCOL_PATH = Path("artifacts/evaluation/phase11c4a/latency-protocol.json")

DEFAULT_RESULT_PATH = Path("artifacts/evaluation/phase11c4c/localhost-latency-results.json")


@dataclass(
    frozen=True,
    slots=True,
)
class ClientMeasurement:
    round_number: int
    query_id: str
    request_id: str
    client_observed_ms: float
    status: str
    presentation_source: str
    generation_fidelity: str


@dataclass(
    frozen=True,
    slots=True,
)
class CorrelatedMeasurement:
    round_number: int
    query_id: str
    request_id: str
    client_observed_ms: float
    server_http_ms: float
    answer_service_ms: float
    generation_ms: float | None
    tool_duration_ms: tuple[
        tuple[
            str,
            float,
        ],
        ...,
    ]
    status: str
    presentation_source: str
    generation_fidelity: str


def assert_server_port_available() -> None:
    """Fail closed if the frozen benchmark port is already occupied."""

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as probe:
        probe.settimeout(0.25)

        result = probe.connect_ex(
            (
                SERVER_HOST,
                SERVER_PORT,
            )
        )

    if result == 0:
        raise RuntimeError(
            f"Frozen latency benchmark port is already occupied: {SERVER_HOST}:{SERVER_PORT}."
        )


def build_uvicorn_command() -> tuple[
    str,
    ...,
]:
    return (
        "uv",
        "run",
        "uvicorn",
        SERVER_APP,
        "--host",
        SERVER_HOST,
        "--port",
        str(SERVER_PORT),
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


def sha256_file(
    path: Path,
) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_protocol(
    path: Path = DEFAULT_PROTOCOL_PATH,
) -> str:
    digest = sha256_file(path)

    if digest != FROZEN_PROTOCOL_SHA256:
        raise RuntimeError(f"Frozen latency protocol hash mismatch: {digest!r}.")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if payload.get("version") != SERVING_LATENCY_PROTOCOL_VERSION:
        raise RuntimeError("Frozen latency protocol version mismatch.")

    return digest


def _finite_non_negative(
    value: Any,
    *,
    field: str,
) -> float:
    if not isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        raise RuntimeError(f"{field} must be numeric.")

    observed = float(value)

    if not math.isfinite(observed) or observed < 0.0:
        raise RuntimeError(f"{field} must be finite and non-negative.")

    return observed


def validate_answer_payload(
    case: LatencyControlCase,
    payload: dict[
        str,
        Any,
    ],
) -> tuple[
    str,
    str,
    str,
]:
    status = payload.get("status")

    source = payload.get("presentation_source")

    fidelity = payload.get("generation_fidelity")

    expected = (
        case.expected_status,
        case.expected_presentation_source,
        case.expected_generation_fidelity,
    )

    observed = (
        status,
        source,
        fidelity,
    )

    if observed != expected:
        raise RuntimeError(
            "Frozen answering outcome mismatch "
            f"for {case.query_id}: "
            f"expected={expected!r}, "
            f"observed={observed!r}."
        )

    return (
        str(status),
        str(source),
        str(fidelity),
    )


def parse_structured_server_events(
    lines: Iterable[str],
) -> dict[
    str,
    list[
        dict[
            str,
            Any,
        ]
    ],
]:
    by_request: dict[
        str,
        list[
            dict[
                str,
                Any,
            ]
        ],
    ] = {}

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        if not isinstance(
            payload,
            dict,
        ):
            continue

        event = payload.get("event")

        request_id = payload.get("request_id")

        if not isinstance(
            event,
            str,
        ):
            continue

        if not isinstance(
            request_id,
            str,
        ):
            continue

        if not request_id.strip():
            continue

        by_request.setdefault(
            request_id,
            [],
        ).append(payload)

    return by_request


def _exact_event(
    events: list[
        dict[
            str,
            Any,
        ]
    ],
    event_name: str,
) -> dict[
    str,
    Any,
]:
    matched = [event for event in events if event.get("event") == event_name]

    if len(matched) != 1:
        raise RuntimeError(f"Expected exactly one {event_name!r} event; observed {len(matched)}.")

    return matched[0]


def correlate_server_timing(
    measurement: ClientMeasurement,
    events_by_request: dict[
        str,
        list[
            dict[
                str,
                Any,
            ]
        ],
    ],
) -> CorrelatedMeasurement:
    events = events_by_request.get(measurement.request_id)

    if events is None:
        raise RuntimeError(
            f"No structured server events for request_id={measurement.request_id!r}."
        )

    http_event = _exact_event(
        events,
        "http_request_completed",
    )

    service_event = _exact_event(
        events,
        "answer_service_completed",
    )

    server_http_ms = _finite_non_negative(
        http_event.get("duration_ms"),
        field="server_http_ms",
    )

    answer_service_ms = _finite_non_negative(
        service_event.get("total_duration_ms"),
        field="answer_service_ms",
    )

    raw_tools = service_event.get(
        "tool_durations_ms",
        {},
    )

    if not isinstance(
        raw_tools,
        dict,
    ):
        raise RuntimeError("tool_durations_ms must be an object.")

    tool_duration_ms = tuple(
        sorted(
            (
                str(tool),
                _finite_non_negative(
                    duration,
                    field=(f"tool_duration_ms[{tool!r}]"),
                ),
            )
            for (
                tool,
                duration,
            ) in raw_tools.items()
        )
    )

    generation_events = [
        event for event in events if event.get("event") == "answer_generation_completed"
    ]

    generation_expected = measurement.generation_fidelity != "not_applicable"

    if generation_expected:
        if len(generation_events) != 1:
            raise RuntimeError("Generation-invoked request requires exactly one generation event.")

        generation_ms: float | None = _finite_non_negative(
            generation_events[0].get("generation_duration_ms"),
            field="generation_ms",
        )

    else:
        if generation_events:
            raise RuntimeError("Generation-skipped request emitted an unexpected generation event.")

        generation_ms = None

    return CorrelatedMeasurement(
        round_number=(measurement.round_number),
        query_id=(measurement.query_id),
        request_id=(measurement.request_id),
        client_observed_ms=(measurement.client_observed_ms),
        server_http_ms=(server_http_ms),
        answer_service_ms=(answer_service_ms),
        generation_ms=(generation_ms),
        tool_duration_ms=(tool_duration_ms),
        status=(measurement.status),
        presentation_source=(measurement.presentation_source),
        generation_fidelity=(measurement.generation_fidelity),
    )


def _channel_summary(
    measurements: tuple[
        CorrelatedMeasurement,
        ...,
    ],
    *,
    extractor,
) -> dict[
    str,
    object,
]:
    overall_values = tuple(
        value for measurement in measurements if (value := extractor(measurement)) is not None
    )

    result: dict[
        str,
        object,
    ] = {
        "overall": (summarize_latency_samples(overall_values)),
        "per_case": {},
    }

    per_case: dict[
        str,
        object,
    ] = {}

    for case in CONTROL_CASES:
        values = tuple(
            value
            for measurement in measurements
            if (measurement.query_id == case.query_id)
            and (value := extractor(measurement)) is not None
        )

        if values:
            per_case[case.query_id] = summarize_latency_samples(values)

    result["per_case"] = per_case

    return result


def _tool_value(
    measurement: CorrelatedMeasurement,
    tool: str,
) -> float | None:
    values = dict(measurement.tool_duration_ms)

    return values.get(tool)


def _validate_measurement_set(
    measurements: tuple[
        CorrelatedMeasurement,
        ...,
    ],
) -> None:
    if len(measurements) != MEASUREMENT_SAMPLE_COUNT:
        raise RuntimeError(
            f"Latency result requires exactly {MEASUREMENT_SAMPLE_COUNT} measured requests."
        )

    observed_pairs = [
        (
            measurement.round_number,
            measurement.query_id,
        )
        for measurement in measurements
    ]

    expected_pairs = [
        (
            round_number,
            case.query_id,
        )
        for round_number in range(
            1,
            MEASUREMENT_ROUNDS + 1,
        )
        for case in CONTROL_CASES
    ]

    if observed_pairs != expected_pairs:
        raise RuntimeError("Measured request ordering does not match the frozen latency protocol.")


def build_result_payload(
    *,
    protocol_sha256: str,
    startup_ready_ms: float,
    measurements: tuple[
        CorrelatedMeasurement,
        ...,
    ],
    environment: dict[
        str,
        object,
    ],
) -> dict[
    str,
    object,
]:
    _validate_measurement_set(measurements)

    startup = _finite_non_negative(
        startup_ready_ms,
        field="startup_ready_ms",
    )

    for measurement in measurements:
        for field, value in (
            (
                "client_observed_ms",
                measurement.client_observed_ms,
            ),
            (
                "server_http_ms",
                measurement.server_http_ms,
            ),
            (
                "answer_service_ms",
                measurement.answer_service_ms,
            ),
        ):
            _finite_non_negative(
                value,
                field=field,
            )

    summaries = {
        "client_observed_ms": (
            _channel_summary(
                measurements,
                extractor=(lambda measurement: measurement.client_observed_ms),
            )
        ),
        "server_http_ms": (
            _channel_summary(
                measurements,
                extractor=(lambda measurement: measurement.server_http_ms),
            )
        ),
        "answer_service_ms": (
            _channel_summary(
                measurements,
                extractor=(lambda measurement: measurement.answer_service_ms),
            )
        ),
        "generation_ms": (
            _channel_summary(
                measurements,
                extractor=(lambda measurement: measurement.generation_ms),
            )
        ),
        "tool_duration_ms": {
            tool: _channel_summary(
                measurements,
                extractor=(
                    lambda measurement, tool=tool: _tool_value(
                        measurement,
                        tool,
                    )
                ),
            )
            for tool in (
                "retrieval",
                "sql",
                "graph",
            )
            if any(
                _tool_value(
                    measurement,
                    tool,
                )
                is not None
                for measurement in measurements
            )
        },
    }

    return {
        "version": (SERVING_LATENCY_RESULT_VERSION),
        "protocol": {
            "version": (SERVING_LATENCY_PROTOCOL_VERSION),
            "sha256": (protocol_sha256),
        },
        "startup": {
            "ready_ms": startup,
            "included_in_warm_summary": False,
        },
        "environment": environment,
        "measurement": {
            "rounds": (MEASUREMENT_ROUNDS),
            "total_requests": (MEASUREMENT_SAMPLE_COUNT),
            "sequential": True,
            "concurrency": 1,
        },
        "samples": [
            {
                "round": (measurement.round_number),
                "query_id": (measurement.query_id),
                "status": (measurement.status),
                "presentation_source": (measurement.presentation_source),
                "generation_fidelity": (measurement.generation_fidelity),
                "client_observed_ms": (measurement.client_observed_ms),
                "server_http_ms": (measurement.server_http_ms),
                "answer_service_ms": (measurement.answer_service_ms),
                "generation_ms": (measurement.generation_ms),
                "tool_duration_ms": dict(measurement.tool_duration_ms),
            }
            for measurement in measurements
        ],
        "summaries": summaries,
        "privacy": {
            "stores_question_text": False,
            "stores_answer_text": False,
            "stores_evidence_text": False,
            "stores_prompt_text": False,
            "stores_raw_model_output": False,
            "stores_request_id": False,
        },
        "claim_boundary": {
            "localhost_only": True,
            "single_worker": True,
            "sequential_requests": True,
            "production_latency": False,
            "production_throughput": False,
            "concurrency_scalability": False,
            "service_level_objective": False,
        },
    }


def capture_environment() -> dict[
    str,
    object,
]:
    uname = subprocess.run(
        [
            "uname",
            "-a",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    lscpu = subprocess.run(
        [
            "lscpu",
            "-J",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    lscpu_payload = json.loads(lscpu.stdout)

    fields = {
        str(
            item.get(
                "field",
                "",
            )
        ).rstrip(":"): str(
            item.get(
                "data",
                "",
            )
        )
        for item in lscpu_payload.get("lscpu", [])
    }

    proc_version = Path("/proc/version").read_text(encoding="utf-8").strip()

    return {
        "uname": uname,
        "platform": (platform.platform()),
        "machine": (platform.machine()),
        "python_version": (platform.python_version()),
        "wsl_detected": ("microsoft" in proc_version.lower()),
        "cpu_model": (fields.get("Model name")),
        "logical_cpu_count": (fields.get("CPU(s)")),
        "cores_per_socket": (fields.get("Core(s) per socket")),
        "sockets": (fields.get("Socket(s)")),
        "threads_per_core": (fields.get("Thread(s) per core")),
        "uvicorn_version": (version("uvicorn")),
        "fastapi_version": (version("fastapi")),
        "torch_version": (torch.__version__),
        "cuda_available": (torch.cuda.is_available()),
        "torch_num_threads": (torch.get_num_threads()),
        "torch_num_interop_threads": (torch.get_num_interop_threads()),
    }


def _request_json(
    connection: http.client.HTTPConnection,
    *,
    method: str,
    path: str,
    payload: dict[
        str,
        Any,
    ]
    | None = None,
) -> tuple[
    http.client.HTTPResponse,
    dict[
        str,
        Any,
    ],
]:
    body: bytes | None = None

    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        body = json.dumps(
            payload,
            separators=(
                ",",
                ":",
            ),
        ).encode("utf-8")

        headers["Content-Type"] = "application/json"

    connection.request(
        method,
        path,
        body=body,
        headers=headers,
    )

    response = connection.getresponse()

    raw = response.read()

    decoded = json.loads(raw.decode("utf-8"))

    if not isinstance(
        decoded,
        dict,
    ):
        raise RuntimeError("Expected JSON object response.")

    return (
        response,
        decoded,
    )


def _wait_until_ready(
    *,
    connection: http.client.HTTPConnection,
    process: subprocess.Popen,
    started_ns: int,
) -> float:
    deadline = time.monotonic() + STARTUP_TIMEOUT_S

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Uvicorn exited before readiness with code {process.returncode}.")

        try:
            response, payload = _request_json(
                connection,
                method="GET",
                path=READINESS_PATH,
            )

        except (
            ConnectionError,
            OSError,
            http.client.HTTPException,
        ):
            connection.close()

            time.sleep(READINESS_POLL_INTERVAL_S)

            continue

        if response.status == 200 and payload.get("status") == "ready":
            return (perf_counter_ns() - started_ns) / 1_000_000.0

        time.sleep(READINESS_POLL_INTERVAL_S)

    raise TimeoutError("Uvicorn readiness timed out.")


def _perform_answer_request(
    *,
    connection: http.client.HTTPConnection,
    case: LatencyControlCase,
    round_number: int,
) -> ClientMeasurement:
    started_ns = perf_counter_ns()

    response, payload = _request_json(
        connection,
        method="POST",
        path=ANSWER_PATH,
        payload={
            "question": (case.question),
        },
    )

    elapsed_ms = (perf_counter_ns() - started_ns) / 1_000_000.0

    if response.status != 200:
        raise RuntimeError(f"Latency control request returned HTTP {response.status}.")

    request_id = response.getheader("X-Request-ID")

    if request_id is None or not request_id.strip():
        raise RuntimeError("Latency response is missing X-Request-ID.")

    (
        status,
        source,
        fidelity,
    ) = validate_answer_payload(
        case,
        payload,
    )

    return ClientMeasurement(
        round_number=(round_number),
        query_id=(case.query_id),
        request_id=(request_id),
        client_observed_ms=(elapsed_ms),
        status=status,
        presentation_source=source,
        generation_fidelity=fidelity,
    )


def _terminate_process(
    process: subprocess.Popen,
) -> None:
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=30.0)

    except subprocess.TimeoutExpired:
        process.kill()

        process.wait(timeout=10.0)


def run_benchmark(
    *,
    protocol_path: Path = (DEFAULT_PROTOCOL_PATH),
    result_path: Path = (DEFAULT_RESULT_PATH),
) -> Path:
    """Execute the frozen Phase 11C4 localhost benchmark."""

    protocol_sha256 = verify_frozen_protocol(protocol_path)

    assert_server_port_available()

    environment = capture_environment()

    server_env = os.environ.copy()

    server_env["ANSWERING_ENABLED"] = "true"

    with tempfile.TemporaryDirectory(prefix=("phase11c4-")) as temporary_directory:
        server_log_path = Path(temporary_directory) / "server.log"

        with server_log_path.open(
            "w",
            encoding="utf-8",
            buffering=1,
        ) as server_log:
            started_ns = perf_counter_ns()

            process = subprocess.Popen(
                build_uvicorn_command(),
                stdout=server_log,
                stderr=(subprocess.STDOUT),
                text=True,
                env=server_env,
            )

            connection = http.client.HTTPConnection(
                SERVER_HOST,
                SERVER_PORT,
                timeout=(REQUEST_TIMEOUT_S),
            )

            measurements: list[ClientMeasurement] = []

            try:
                startup_ready_ms = _wait_until_ready(
                    connection=connection,
                    process=process,
                    started_ns=started_ns,
                )

                # Frozen warm-up round.
                for case in CONTROL_CASES:
                    _perform_answer_request(
                        connection=connection,
                        case=case,
                        round_number=0,
                    )

                # Frozen measurement rounds.
                for round_number in range(
                    1,
                    MEASUREMENT_ROUNDS + 1,
                ):
                    for case in CONTROL_CASES:
                        measurements.append(
                            _perform_answer_request(
                                connection=connection,
                                case=case,
                                round_number=round_number,
                            )
                        )

            finally:
                connection.close()

                _terminate_process(process)

        log_lines = server_log_path.read_text(encoding="utf-8").splitlines()

    events_by_request = parse_structured_server_events(log_lines)

    correlated = tuple(
        correlate_server_timing(
            measurement,
            events_by_request,
        )
        for measurement in measurements
    )

    payload = build_result_payload(
        protocol_sha256=(protocol_sha256),
        startup_ready_ms=(startup_ready_ms),
        measurements=(correlated),
        environment=(environment),
    )

    result_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return result_path
