from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from types import SimpleNamespace

import grpc
from fastapi.testclient import TestClient

from enterprise_genai.core.config import Settings
from enterprise_genai.rpc.retrieval.v1.readiness import (
    RETRIEVAL_GRPC_READINESS_VERSION,
)

GRPC_DEPENDENCY_READINESS_CONFIRMATION_VERSION = (
    "northstar-grpc-dependency-readiness-confirmation-v1"
)

LOCALHOST_HOST = "127.0.0.1"

READY_STARTUP_TIMEOUT_SECONDS = 2.0
UNAVAILABLE_STARTUP_TIMEOUT_SECONDS = 0.20


@dataclass(slots=True)
class LocalGrpcServer:
    server: grpc.Server
    workers: ThreadPoolExecutor
    target: str
    _stopped: bool = False

    def stop(self) -> None:
        if self._stopped:
            return

        self.server.stop(0).wait()
        self._stopped = True

    def close(self) -> None:
        self.stop()

        self.workers.shutdown(
            wait=True,
            cancel_futures=True,
        )


def _start_transport_only_server() -> LocalGrpcServer:
    """
    Start a genuine localhost gRPC transport endpoint.

    No RetrievalService implementation is registered intentionally.
    Phase 11E2 verifies startup transport reachability, not semantic
    RetrievalService health.
    """

    workers = ThreadPoolExecutor(max_workers=1)

    server = grpc.server(workers)

    port = server.add_insecure_port(f"{LOCALHOST_HOST}:0")

    if port <= 0:
        workers.shutdown(
            wait=True,
            cancel_futures=True,
        )

        raise RuntimeError("failed to bind localhost gRPC readiness server")

    target = f"{LOCALHOST_HOST}:{port}"

    server.start()

    probe_channel = grpc.insecure_channel(target)

    try:
        grpc.channel_ready_future(probe_channel).result(timeout=5.0)

    except grpc.FutureTimeoutError:
        probe_channel.close()

        server.stop(0).wait()

        workers.shutdown(
            wait=True,
            cancel_futures=True,
        )

        raise RuntimeError("localhost gRPC readiness server did not become ready") from None

    probe_channel.close()

    return LocalGrpcServer(
        server=server,
        workers=workers,
        target=target,
    )


def _lifecycle_cleanup_verified(
    main,
) -> bool:
    return (
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
        and not hasattr(
            main.app.state,
            "operational_metrics",
        )
    )


def _run_reachable_case() -> dict[str, object]:
    from enterprise_genai.api import main

    boundary = _start_transport_only_server()

    previous_settings = main.settings
    previous_builder = main.build_serving_assembly
    previous_check_database = main.check_database

    build_calls = 0

    def build_without_models(
        *,
        engine,
        metrics_registry,
        retrieval_executor,
    ):
        nonlocal build_calls

        del engine
        del metrics_registry

        build_calls += 1

        return SimpleNamespace(
            service=object(),
            retrieval_executor=retrieval_executor,
        )

    main.settings = Settings(
        _env_file=None,
        answering_enabled=True,
        retrieval_mode="grpc",
        retrieval_grpc_target=boundary.target,
        retrieval_grpc_deadline_seconds=1.0,
        retrieval_grpc_startup_timeout_seconds=(READY_STARTUP_TIMEOUT_SECONDS),
        database_url=previous_settings.database_url,
    )

    main.build_serving_assembly = build_without_models
    main.check_database = lambda: None

    try:
        with TestClient(
            main.app,
            raise_server_exceptions=True,
        ) as client:
            readiness = client.get("/health/ready")

            readiness_status_code = readiness.status_code

            readiness_payload = readiness.json()

            answering_status = main.app.state.answering_status

            service_installed = hasattr(
                main.app.state,
                "answering_service",
            )

            assembly = main.app.state.answering_assembly

            executor_type = type(assembly.retrieval_executor).__name__

        cleanup_verified = _lifecycle_cleanup_verified(main)

    finally:
        main.settings = previous_settings
        main.build_serving_assembly = previous_builder
        main.check_database = previous_check_database

        boundary.close()

    expected_readiness = {
        "status": "ready",
        "database": "ok",
        "answering": "ready",
    }

    if readiness_status_code != 200:
        raise RuntimeError("reachable gRPC dependency did not produce HTTP 200 readiness")

    if readiness_payload != expected_readiness:
        raise RuntimeError("reachable gRPC dependency did not match the readiness contract")

    if answering_status != "ready":
        raise RuntimeError("reachable gRPC dependency did not mark answering ready")

    if not service_installed:
        raise RuntimeError("reachable gRPC dependency did not install answering service")

    if build_calls != 1:
        raise RuntimeError("reachable readiness case expected exactly one assembly build")

    if executor_type != "GrpcRetrievalExecutor":
        raise RuntimeError("reachable readiness case did not install GrpcRetrievalExecutor")

    if not cleanup_verified:
        raise RuntimeError("reachable readiness case did not clean FastAPI lifecycle state")

    return {
        "case_id": "reachable_at_startup",
        "transport": ("grpc-insecure-localhost-tcp"),
        "endpoint": ("127.0.0.1:ephemeral"),
        "server_listening_during_startup": True,
        "startup_timeout_seconds": (READY_STARTUP_TIMEOUT_SECONDS),
        "semantic_rpc_invoked": False,
        "http": {
            "health_ready_status": (readiness_status_code),
            "health_ready": (readiness_payload),
        },
        "application": {
            "answering_status": (answering_status),
            "answering_service_installed": (service_installed),
            "retrieval_executor": (executor_type),
            "assembly_build_calls": (build_calls),
        },
        "lifecycle": {
            "cleanup_verified": (cleanup_verified),
        },
        "passed": True,
    }


def _run_unavailable_case() -> dict[str, object]:
    from enterprise_genai.api import main

    boundary = _start_transport_only_server()

    target = boundary.target

    boundary.close()

    previous_settings = main.settings
    previous_builder = main.build_serving_assembly
    previous_check_database = main.check_database

    build_calls = 0

    def forbidden_build(
        **kwargs,
    ):
        nonlocal build_calls

        del kwargs

        build_calls += 1

        raise AssertionError("serving assembly must not be built when startup readiness fails")

    main.settings = Settings(
        _env_file=None,
        answering_enabled=True,
        retrieval_mode="grpc",
        retrieval_grpc_target=target,
        retrieval_grpc_deadline_seconds=1.0,
        retrieval_grpc_startup_timeout_seconds=(UNAVAILABLE_STARTUP_TIMEOUT_SECONDS),
        database_url=previous_settings.database_url,
    )

    main.build_serving_assembly = forbidden_build
    main.check_database = lambda: None

    try:
        with TestClient(
            main.app,
            raise_server_exceptions=True,
        ) as client:
            readiness = client.get("/health/ready")

            answer = client.post(
                "/answer",
                json={
                    "question": ("What defect affected ORBIS-IDX-7?"),
                },
            )

            readiness_status_code = readiness.status_code

            readiness_payload = readiness.json()

            answer_status_code = answer.status_code

            answer_payload = answer.json()

            answering_status = main.app.state.answering_status

            service_installed = hasattr(
                main.app.state,
                "answering_service",
            )

        cleanup_verified = _lifecycle_cleanup_verified(main)

    finally:
        main.settings = previous_settings
        main.build_serving_assembly = previous_builder
        main.check_database = previous_check_database

    expected_readiness = {
        "status": "not_ready",
        "database": "ok",
        "answering": "unavailable",
    }

    expected_answer = {
        "detail": "answering service unavailable",
    }

    if readiness_status_code != 503:
        raise RuntimeError("unreachable gRPC dependency did not produce HTTP 503 readiness")

    if readiness_payload != expected_readiness:
        raise RuntimeError("unreachable gRPC dependency did not match the readiness contract")

    if answer_status_code != 503:
        raise RuntimeError("unreachable startup dependency did not block /answer")

    if answer_payload != expected_answer:
        raise RuntimeError("unreachable startup dependency returned an unexpected /answer payload")

    if answering_status != "unavailable":
        raise RuntimeError("unreachable gRPC dependency did not mark answering unavailable")

    if service_installed:
        raise RuntimeError("answering service was installed despite failed startup readiness")

    if build_calls != 0:
        raise RuntimeError("serving assembly was reached despite failed startup readiness")

    if not cleanup_verified:
        raise RuntimeError("unavailable readiness case did not clean FastAPI lifecycle state")

    return {
        "case_id": "unavailable_at_startup",
        "transport": ("grpc-insecure-localhost-tcp"),
        "endpoint": ("127.0.0.1:ephemeral"),
        "server_stopped_before_application_startup": (True),
        "startup_timeout_seconds": (UNAVAILABLE_STARTUP_TIMEOUT_SECONDS),
        "semantic_rpc_invoked": False,
        "http": {
            "health_ready_status": (readiness_status_code),
            "health_ready": (readiness_payload),
            "answer_status": (answer_status_code),
            "answer": (answer_payload),
        },
        "application": {
            "answering_status": (answering_status),
            "answering_service_installed": (service_installed),
            "assembly_build_calls": (build_calls),
        },
        "lifecycle": {
            "cleanup_verified": (cleanup_verified),
        },
        "passed": True,
    }


def run_grpc_dependency_readiness_confirmation() -> dict[str, object]:
    reachable = _run_reachable_case()

    unavailable = _run_unavailable_case()

    return {
        "confirmation_version": (GRPC_DEPENDENCY_READINESS_CONFIRMATION_VERSION),
        "readiness_primitive_version": (RETRIEVAL_GRPC_READINESS_VERSION),
        "scope": {
            "dependency": ("grpc_retrieval"),
            "phase": ("application_startup_only"),
            "transport_reachability": (True),
            "semantic_rpc_health": (False),
            "continuous_runtime_health": (False),
        },
        "configuration": {
            "startup_timeout_is_dedicated": (True),
            "ready_case_timeout_seconds": (READY_STARTUP_TIMEOUT_SECONDS),
            "unavailable_case_timeout_seconds": (UNAVAILABLE_STARTUP_TIMEOUT_SECONDS),
        },
        "cases": [
            reachable,
            unavailable,
        ],
        "summary": {
            "real_localhost_grpc_transport": (True),
            "reachable_dependency_allows_startup_readiness": (True),
            "unreachable_dependency_fails_closed": (True),
            "unavailable_dependency_blocks_answering": (True),
            "health_schema_preserved": (True),
            "model_loading_required": (False),
            "semantic_rpc_health_claimed": (False),
            "runtime_health_polling_claimed": (False),
            "all_passed": (True),
        },
    }
