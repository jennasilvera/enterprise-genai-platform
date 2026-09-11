from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from statistics import median
from typing import Literal

SERVING_LATENCY_PROTOCOL_VERSION = "northstar-localhost-serving-latency-protocol-v1"

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8011
SERVER_APP = "enterprise_genai.api.main:app"

READINESS_PATH = "/health/ready"
ANSWER_PATH = "/answer"

STARTUP_TIMEOUT_S = 120.0
READINESS_POLL_INTERVAL_S = 0.1
REQUEST_TIMEOUT_S = 120.0

WARMUP_ROUNDS = 1
MEASUREMENT_ROUNDS = 5

P95_QUANTILE = 0.95
PERCENTILE_METHOD = "nearest-rank"


type AnswerStatus = Literal[
    "answered",
    "abstained",
]

type PresentationSource = Literal[
    "deterministic",
    "model_generation",
    "deterministic_fallback",
]

type GenerationFidelity = Literal[
    "not_applicable",
    "accepted",
    "rejected",
]


@dataclass(
    frozen=True,
    slots=True,
)
class LatencyControlCase:
    query_id: str
    question: str
    expected_status: AnswerStatus
    expected_presentation_source: PresentationSource
    expected_generation_fidelity: GenerationFidelity


CONTROL_CASES = (
    LatencyControlCase(
        query_id="Q-0001",
        question=("What defect affected ORBIS-IDX-7?"),
        expected_status="answered",
        expected_presentation_source=("deterministic_fallback"),
        expected_generation_fidelity="rejected",
    ),
    LatencyControlCase(
        query_id="Q-0010",
        question=(
            "Which portfolio company had the highest year-over-year revenue growth in 2026 Q2?"
        ),
        expected_status="answered",
        expected_presentation_source=("model_generation"),
        expected_generation_fidelity="accepted",
    ),
    LatencyControlCase(
        query_id="Q-0011",
        question=("What was total portfolio revenue in 2026 Q2?"),
        expected_status="answered",
        expected_presentation_source=("deterministic_fallback"),
        expected_generation_fidelity="rejected",
    ),
    LatencyControlCase(
        query_id="Q-0023",
        question=("What is Northstar's expected 2030 exit valuation for Meridian Health Systems?"),
        expected_status="abstained",
        expected_presentation_source="deterministic",
        expected_generation_fidelity="not_applicable",
    ),
    LatencyControlCase(
        query_id="Q-0024",
        question=("What was Alder Manufacturing's exact customer churn rate in 2026 Q2?"),
        expected_status="abstained",
        expected_presentation_source="deterministic",
        expected_generation_fidelity="not_applicable",
    ),
)

CONTROL_CASE_IDS = tuple(case.query_id for case in CONTROL_CASES)

MEASUREMENT_SAMPLE_COUNT = MEASUREMENT_ROUNDS * len(CONTROL_CASES)


def nearest_rank_percentile(
    values: tuple[
        float,
        ...,
    ],
    quantile: float,
) -> float:
    """Return the nearest-rank percentile for non-empty samples."""

    if not values:
        raise ValueError("Percentile requires at least one sample.")

    if not (0.0 < quantile <= 1.0):
        raise ValueError("Quantile must be in (0, 1].")

    if any(not isfinite(value) or value < 0.0 for value in values):
        raise ValueError("Latency samples must be finite and non-negative.")

    ordered = sorted(values)

    rank = ceil(quantile * len(ordered))

    return ordered[rank - 1]


def summarize_latency_samples(
    values: tuple[
        float,
        ...,
    ],
) -> dict[
    str,
    float | int,
]:
    """Return the frozen descriptive latency summary."""

    if not values:
        raise ValueError("Latency summary requires at least one sample.")

    if any(not isfinite(value) or value < 0.0 for value in values):
        raise ValueError("Latency samples must be finite and non-negative.")

    return {
        "n": len(values),
        "min_ms": min(values),
        "median_ms": median(values),
        "p95_ms": nearest_rank_percentile(
            values,
            P95_QUANTILE,
        ),
        "max_ms": max(values),
    }


def latency_protocol_payload() -> dict[
    str,
    object,
]:
    """Return the deterministic pre-measurement protocol payload."""

    return {
        "version": (SERVING_LATENCY_PROTOCOL_VERSION),
        "purpose": (
            "Measure descriptive warm localhost serving latency "
            "through a real single-worker Uvicorn TCP boundary."
        ),
        "server": {
            "app": SERVER_APP,
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "workers": 1,
            "loop": "asyncio",
            "http": "h11",
            "lifespan": "on",
            "access_log": False,
            "proxy_headers": False,
            "server_header": False,
            "date_header": False,
            "answering_enabled": True,
        },
        "startup": {
            "measurement": (
                "elapsed monotonic time from immediately before "
                "server-process launch until the first HTTP 200 "
                "response from /health/ready"
            ),
            "timeout_s": STARTUP_TIMEOUT_S,
            "poll_interval_s": (READINESS_POLL_INTERVAL_S),
            "observations": 1,
            "included_in_warm_latency_summary": False,
        },
        "client": {
            "process_boundary": ("separate client process from Uvicorn"),
            "transport": "HTTP/1.1 over localhost TCP",
            "connection_policy": (
                "one persistent connection for readiness, warm-up, and measurement"
            ),
            "concurrency": 1,
            "request_timeout_s": REQUEST_TIMEOUT_S,
            "client_clock": "time.perf_counter_ns",
        },
        "warmup": {
            "rounds": WARMUP_ROUNDS,
            "case_order": list(CONTROL_CASE_IDS),
            "included_in_summary": False,
        },
        "measurement": {
            "rounds": MEASUREMENT_ROUNDS,
            "case_order_per_round": list(CONTROL_CASE_IDS),
            "total_requests": (MEASUREMENT_SAMPLE_COUNT),
            "sequential": True,
            "expected_http_status": 200,
            "validate_answer_outcomes": True,
        },
        "control_cases": [
            {
                "query_id": (case.query_id),
                "expected_status": (case.expected_status),
                "expected_presentation_source": (case.expected_presentation_source),
                "expected_generation_fidelity": (case.expected_generation_fidelity),
            }
            for case in CONTROL_CASES
        ],
        "latency_channels": {
            "client_observed_ms": ("client-side POST /answer elapsed time"),
            "server_http_ms": (
                "http_request_completed.duration_ms correlated through X-Request-ID"
            ),
            "answer_service_ms": (
                "answer_service_completed.total_duration_ms correlated through X-Request-ID"
            ),
            "generation_ms": (
                "answer_generation_completed.generation_duration_ms when generation was invoked"
            ),
            "tool_duration_ms": ("per-tool duration values from answer_service_completed"),
        },
        "server_log_correlation": {
            "response_header": "X-Request-ID",
            "required_events": [
                "http_request_completed",
                "answer_service_completed",
            ],
            "optional_generation_event": ("answer_generation_completed"),
        },
        "statistics": {
            "scopes": [
                "overall",
                "per_case",
            ],
            "fields": [
                "n",
                "min_ms",
                "median_ms",
                "p95_ms",
                "max_ms",
            ],
            "median_method": ("statistics.median"),
            "p95_quantile": P95_QUANTILE,
            "p95_method": (PERCENTILE_METHOD),
            "nearest_rank_definition": ("sorted_values[ceil(p*n)-1]"),
        },
        "environment_capture": [
            "uname",
            "WSL/kernel identity",
            "CPU model",
            "physical/logical CPU counts",
            "PyTorch version",
            "CUDA availability",
            "PyTorch intra-op thread count",
            "PyTorch inter-op thread count",
            "Uvicorn version",
            "FastAPI version",
            "Python version",
        ],
        "result_artifact_policy": {
            "store_per_sample_latency": True,
            "store_question_text": False,
            "store_answer_text": False,
            "store_evidence_text": False,
            "store_prompt_text": False,
            "store_raw_model_output": False,
            "store_query_id": True,
            "store_round_number": True,
            "store_validated_outcome_taxonomy": True,
        },
        "claim_boundary": [
            "localhost only",
            "single Uvicorn worker",
            "sequential requests",
            "CPU-only target environment",
            "descriptive latency rather than throughput",
            "not a concurrency scalability test",
            "not a production SLO",
            "not internet or WAN latency",
            "not multi-worker performance",
        ],
        "methodology_note": (
            "Incidental latency observations existed before this "
            "protocol. The exact Phase 11C4 benchmark methodology "
            "is frozen before Phase 11C4 benchmark execution and "
            "summary computation."
        ),
    }
