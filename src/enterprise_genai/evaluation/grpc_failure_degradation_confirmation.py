from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from time import sleep

import grpc
from fastapi.testclient import TestClient

from enterprise_genai.application.serving import (
    build_serving_assembly as build_real_serving_assembly,
)
from enterprise_genai.core.config import Settings
from enterprise_genai.execution.contracts import (
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.generation.contracts import (
    GroundedGenerationRequest,
    RawGeneration,
)
from enterprise_genai.rpc.retrieval.v1 import retrieval_pb2_grpc
from enterprise_genai.rpc.retrieval.v1.servicer import (
    RetrievalGrpcServicer,
)

GRPC_FAILURE_DEGRADATION_CONFIRMATION_VERSION = "northstar-grpc-failure-degradation-confirmation-v1"

CONFIRMATION_QUESTION = "What defect affected ORBIS-IDX-7?"

LOCALHOST_HOST = "127.0.0.1"

DEADLINE_SECONDS = 0.05
SLOW_EXECUTION_SECONDS = 0.30

UNAVAILABLE_DEADLINE_SECONDS = 1.0


class UnusedGenerationProvider:
    """Fail if degradation handling incorrectly invokes generation."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(
        self,
        request: GroundedGenerationRequest,
    ) -> RawGeneration:
        del request

        self.calls += 1

        raise AssertionError("generation must not run for execution_failed abstention")


class SlowRetrievalExecutor:
    def __init__(
        self,
        *,
        delay_seconds: float,
    ) -> None:
        self._delay_seconds = delay_seconds

        self._lock = Lock()

        self._calls = 0

    @property
    def calls(
        self,
    ) -> int:
        with self._lock:
            return self._calls

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        del query

        with self._lock:
            self._calls += 1

        sleep(self._delay_seconds)

        return ToolExecutionResult(
            tool="retrieval",
            status="empty",
            payload=RetrievalPayload(hits=()),
            duration_ms=(self._delay_seconds * 1000.0),
        )


class EmptyRetrievalExecutor:
    def __init__(
        self,
    ) -> None:
        self._lock = Lock()

        self._calls = 0

    @property
    def calls(
        self,
    ) -> int:
        with self._lock:
            return self._calls

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        del query

        with self._lock:
            self._calls += 1

        return ToolExecutionResult(
            tool="retrieval",
            status="empty",
            payload=RetrievalPayload(hits=()),
            duration_ms=0.0,
        )


@dataclass(
    slots=True,
)
class LocalGrpcServer:
    server: grpc.Server
    workers: ThreadPoolExecutor
    target: str
    _stopped: bool = False

    def stop(
        self,
    ) -> None:
        if self._stopped:
            return

        self.server.stop(0).wait()

        self._stopped = True

    def close(
        self,
    ) -> None:
        self.stop()

        self.workers.shutdown(
            wait=True,
            cancel_futures=True,
        )


def _start_server(
    executor,
) -> LocalGrpcServer:
    workers = ThreadPoolExecutor(max_workers=2)

    server = grpc.server(workers)

    retrieval_pb2_grpc.add_RetrievalServiceServicer_to_server(
        RetrievalGrpcServicer(executor),
        server,
    )

    port = server.add_insecure_port(f"{LOCALHOST_HOST}:0")

    if port <= 0:
        workers.shutdown(
            wait=True,
            cancel_futures=True,
        )

        raise RuntimeError("failed to bind localhost gRPC degradation server")

    target = f"{LOCALHOST_HOST}:{port}"

    server.start()

    channel = grpc.insecure_channel(target)

    try:
        grpc.channel_ready_future(channel).result(timeout=5.0)

    except grpc.FutureTimeoutError:
        channel.close()

        server.stop(0).wait()

        workers.shutdown(
            wait=True,
            cancel_futures=True,
        )

        raise RuntimeError("localhost gRPC degradation server did not become ready") from None

    channel.close()

    return LocalGrpcServer(
        server=server,
        workers=workers,
        target=target,
    )


def stable_abstention_snapshot(
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "status": payload.get("status"),
        "presentation_source": payload.get("presentation_source"),
        "generation_fidelity": payload.get("generation_fidelity"),
        "reason": payload.get("reason"),
        "detail": payload.get("detail"),
        "citation_ids": payload.get(
            "citation_ids",
            [],
        ),
        "provenance_fact_ids": payload.get(
            "provenance_fact_ids",
            [],
        ),
    }


def _run_application_failure_case(
    *,
    target: str,
    deadline_seconds: float,
    expected_detail: str,
) -> dict[str, object]:
    from enterprise_genai.api import main

    previous_settings = main.settings

    previous_builder = main.build_serving_assembly

    generation = UnusedGenerationProvider()

    def build_with_unused_generation(
        *,
        engine,
        metrics_registry,
        retrieval_executor,
    ):
        return build_real_serving_assembly(
            engine=engine,
            metrics_registry=(metrics_registry),
            retrieval_executor=(retrieval_executor),
            generation_builder=(lambda: generation),
        )

    main.settings = Settings(
        _env_file=None,
        answering_enabled=True,
        retrieval_mode="grpc",
        retrieval_grpc_target=target,
        retrieval_grpc_deadline_seconds=(deadline_seconds),
    )

    main.build_serving_assembly = build_with_unused_generation

    try:
        with TestClient(
            main.app,
            raise_server_exceptions=True,
        ) as client:
            response = client.post(
                "/answer",
                json={"question": (CONFIRMATION_QUESTION)},
            )

            status_code = response.status_code

            payload = response.json()

            installed_executor_type = type(
                main.app.state.answering_assembly.retrieval_executor
            ).__name__

        cleanup_verified = (
            not hasattr(
                main.app.state,
                "answering_service",
            )
            and not hasattr(
                main.app.state,
                "answering_assembly",
            )
            and not hasattr(
                main.app.state,
                "answering_status",
            )
        )

    finally:
        main.settings = previous_settings

        main.build_serving_assembly = previous_builder

    if status_code != 200:
        raise RuntimeError(f"degraded /answer request returned HTTP {status_code}")

    snapshot = stable_abstention_snapshot(payload)

    expected_snapshot = {
        "status": "abstained",
        "presentation_source": ("deterministic"),
        "generation_fidelity": ("not_applicable"),
        "reason": ("execution_failed"),
        "detail": expected_detail,
        "citation_ids": [],
        "provenance_fact_ids": [],
    }

    if snapshot != expected_snapshot:
        raise RuntimeError(
            "degraded application response did not match the frozen fail-closed contract"
        )

    if installed_executor_type != "GrpcRetrievalExecutor":
        raise RuntimeError("degradation confirmation did not use GrpcRetrievalExecutor")

    if generation.calls != 0:
        raise RuntimeError("generation was invoked during execution_failed abstention")

    if not cleanup_verified:
        raise RuntimeError("FastAPI lifecycle cleanup failed after degradation case")

    return {
        "http_status": (status_code),
        "retrieval_executor": (installed_executor_type),
        "response": snapshot,
        "generation_calls": (generation.calls),
        "lifecycle_cleanup": (cleanup_verified),
    }


def _run_deadline_case() -> dict[
    str,
    object,
]:
    executor = SlowRetrievalExecutor(delay_seconds=(SLOW_EXECUTION_SECONDS))

    boundary = _start_server(executor)

    try:
        result = _run_application_failure_case(
            target=(boundary.target),
            deadline_seconds=(DEADLINE_SECONDS),
            expected_detail=("retrieval: retrieval rpc deadline exceeded"),
        )

    finally:
        boundary.close()

    if executor.calls != 1:
        raise RuntimeError("deadline confirmation expected exactly one server retrieval call")

    return {
        "case_id": ("real_grpc_deadline"),
        "transport": ("grpc-insecure-localhost-tcp"),
        "endpoint": ("127.0.0.1:ephemeral"),
        "client_deadline_seconds": (DEADLINE_SECONDS),
        "server_delay_seconds": (SLOW_EXECUTION_SECONDS),
        "server_retrieval_calls": (executor.calls),
        **result,
    }


def _run_unavailable_case() -> dict[
    str,
    object,
]:
    executor = EmptyRetrievalExecutor()

    boundary = _start_server(executor)

    target = boundary.target

    boundary.close()

    result = _run_application_failure_case(
        target=target,
        deadline_seconds=(UNAVAILABLE_DEADLINE_SECONDS),
        expected_detail=("retrieval: retrieval rpc unavailable"),
    )

    if executor.calls != 0:
        raise RuntimeError("stopped retrieval server unexpectedly executed a request")

    return {
        "case_id": ("real_grpc_unavailable"),
        "transport": ("grpc-insecure-localhost-tcp"),
        "endpoint": ("127.0.0.1:ephemeral"),
        "server_stopped_before_request": (True),
        "client_deadline_seconds": (UNAVAILABLE_DEADLINE_SECONDS),
        "server_retrieval_calls": (executor.calls),
        **result,
    }


def run_grpc_failure_degradation_confirmation() -> dict[
    str,
    object,
]:
    deadline = _run_deadline_case()

    unavailable = _run_unavailable_case()

    return {
        "confirmation_version": (GRPC_FAILURE_DEGRADATION_CONFIRMATION_VERSION),
        "question": (CONFIRMATION_QUESTION),
        "policy": {
            "required_tool_error": ("fail_closed"),
            "application_outcome": ("typed_deterministic_abstention"),
            "http_status": 200,
            "abstention_reason": ("execution_failed"),
            "generation_on_failure": (False),
        },
        "cases": [
            deadline,
            unavailable,
        ],
        "summary": {
            "deadline_fail_closed": True,
            "unavailable_fail_closed": (True),
            "typed_abstention_verified": (True),
            "generation_skipped": True,
            "lifecycle_cleanup_verified": (True),
            "all_passed": True,
        },
    }
