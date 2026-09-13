from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import grpc
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from enterprise_genai.core.config import Settings
from enterprise_genai.execution.contracts import RetrievalQuery, ToolExecutionResult
from enterprise_genai.execution.frozen_retrieval import FrozenHybridRetrievalExecutor
from enterprise_genai.rpc.retrieval.v1 import retrieval_pb2_grpc
from enterprise_genai.rpc.retrieval.v1.client import GrpcRetrievalExecutor
from enterprise_genai.rpc.retrieval.v1.servicer import RetrievalGrpcServicer

GRPC_SERVING_INTEGRATION_CONFIRMATION_VERSION = "northstar-grpc-serving-integration-confirmation-v1"

DATASET_VERSION = "northstar-v1"

CONFIRMATION_QUESTION = "What defect affected ORBIS-IDX-7?"

RPC_DEADLINE_SECONDS = 30.0

LOCALHOST_HOST = "127.0.0.1"


class RecordingRetrievalExecutor:
    """Record real RPC retrieval calls while delegating to frozen retrieval."""

    def __init__(
        self,
        delegate: FrozenHybridRetrievalExecutor,
    ) -> None:
        self._delegate = delegate
        self._queries: list[RetrievalQuery] = []
        self._lock = Lock()

    @property
    def queries(
        self,
    ) -> tuple[RetrievalQuery, ...]:
        with self._lock:
            return tuple(self._queries)

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        with self._lock:
            self._queries.append(query)

        return self._delegate.execute(query)


def stable_answer_snapshot(
    payload: dict[str, object],
) -> dict[str, object]:
    """
    Preserve stable answer metadata while excluding generated answer text
    and timing-dependent values.
    """

    status = payload.get("status")

    if not isinstance(
        status,
        str,
    ):
        raise TypeError("answer response is missing a string status")

    citations = payload.get("citations")

    citation_count = (
        len(citations)
        if isinstance(
            citations,
            list,
        )
        else 0
    )

    return {
        "status": status,
        "presentation_source": payload.get("presentation_source"),
        "generation_fidelity": payload.get("generation_fidelity"),
        "citation_count": citation_count,
    }


def run_grpc_serving_integration_confirmation(
    *,
    engine: Engine,
) -> dict[str, object]:
    """
    Execute the existing FastAPI answering path with retrieval supplied
    through a genuine localhost gRPC boundary.
    """

    with Session(engine) as session:
        persisted = FrozenHybridRetrievalExecutor.from_persisted_corpus(
            session,
            DATASET_VERSION,
        )

    recording = RecordingRetrievalExecutor(persisted)

    workers = ThreadPoolExecutor(max_workers=2)

    server = grpc.server(workers)

    retrieval_pb2_grpc.add_RetrievalServiceServicer_to_server(
        RetrievalGrpcServicer(recording),
        server,
    )

    port = server.add_insecure_port(f"{LOCALHOST_HOST}:0")

    if port <= 0:
        workers.shutdown(
            wait=True,
            cancel_futures=True,
        )

        raise RuntimeError("failed to bind localhost gRPC retrieval service")

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

        raise RuntimeError("localhost retrieval service did not become ready") from None

    probe_channel.close()

    from enterprise_genai.api import main

    previous_settings = main.settings

    main.settings = Settings(
        _env_file=None,
        answering_enabled=True,
        retrieval_mode="grpc",
        retrieval_grpc_target=target,
        retrieval_grpc_deadline_seconds=(RPC_DEADLINE_SECONDS),
        database_url=(previous_settings.database_url),
    )

    readiness_payload: dict[
        str,
        object,
    ]

    answer_payload: dict[
        str,
        object,
    ]

    answer_status_code: int

    executor_type: str

    try:
        with TestClient(main.app) as client:
            readiness = client.get("/health/ready")

            if readiness.status_code != 200:
                raise RuntimeError("FastAPI serving application was not ready")

            readiness_payload = readiness.json()

            assembly = main.app.state.answering_assembly

            if not isinstance(
                assembly.retrieval_executor,
                GrpcRetrievalExecutor,
            ):
                raise RuntimeError("serving assembly did not install GrpcRetrievalExecutor")

            executor_type = type(assembly.retrieval_executor).__name__

            answer = client.post(
                "/answer",
                json={"question": (CONFIRMATION_QUESTION)},
            )

            answer_status_code = answer.status_code

            if answer_status_code != 200:
                raise RuntimeError(
                    f"gRPC-backed /answer request failed with HTTP {answer_status_code}"
                )

            answer_payload = answer.json()

            if answer_payload.get("status") != "answered":
                raise RuntimeError(
                    "gRPC-backed retrieval case did not produce an answered application result"
                )

        lifecycle_cleanup_verified = (
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

        server.stop(0).wait()

        workers.shutdown(
            wait=True,
            cancel_futures=True,
        )

    queries = recording.queries

    if len(queries) != 1:
        raise RuntimeError(
            f"expected exactly one remote retrieval execution; observed {len(queries)}"
        )

    observed_query = queries[0]

    if observed_query.question != CONFIRMATION_QUESTION:
        raise RuntimeError("remote retrieval question did not match the HTTP request")

    if observed_query.dataset_version != DATASET_VERSION:
        raise RuntimeError("remote retrieval dataset version did not match Northstar v1")

    if not lifecycle_cleanup_verified:
        raise RuntimeError("FastAPI lifespan did not clean the installed answering resources")

    return {
        "confirmation_version": (GRPC_SERVING_INTEGRATION_CONFIRMATION_VERSION),
        "dataset_version": (DATASET_VERSION),
        "transport_path": ("fastapi-testclient-asgi->grpc-insecure-localhost-tcp"),
        "retrieval_endpoint": ("127.0.0.1:ephemeral"),
        "configuration": {
            "answering_enabled": True,
            "retrieval_mode": "grpc",
            "retrieval_grpc_deadline_seconds": (RPC_DEADLINE_SECONDS),
        },
        "readiness": (readiness_payload),
        "http": {
            "path": "/answer",
            "status_code": (answer_status_code),
            "question": (CONFIRMATION_QUESTION),
            "answer": (stable_answer_snapshot(answer_payload)),
        },
        "retrieval": {
            "executor_type": (executor_type),
            "remote_call_count": (len(queries)),
            "observed_query": {
                "dataset_version": (observed_query.dataset_version),
                "question": (observed_query.question),
                "top_k": (observed_query.top_k),
            },
        },
        "lifecycle": {
            "cleanup_verified": (lifecycle_cleanup_verified),
        },
        "summary": {
            "fastapi_path_verified": True,
            "grpc_retrieval_injected": True,
            "remote_retrieval_observed": True,
            "answer_completed": True,
            "lifecycle_cleanup_verified": True,
            "all_passed": True,
        },
    }
