from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import sleep

import grpc
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from enterprise_genai.db.chunk_ingestion import (
    chunk_database_row_counts,
)
from enterprise_genai.db.document_ingestion import (
    document_database_row_counts,
)
from enterprise_genai.execution.contracts import (
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.execution.frozen_retrieval import (
    FrozenHybridRetrievalExecutor,
)
from enterprise_genai.retrieval.chunking import (
    EVIDENCE_BLOCK_STRATEGY,
)
from enterprise_genai.rpc.retrieval.v1 import (
    retrieval_pb2_grpc,
)
from enterprise_genai.rpc.retrieval.v1.client import (
    GrpcRetrievalExecutor,
)
from enterprise_genai.rpc.retrieval.v1.servicer import (
    RetrievalGrpcServicer,
)

GRPC_RETRIEVAL_CONFIRMATION_VERSION = "northstar-grpc-retrieval-confirmation-v1"

DATASET_VERSION = "northstar-v1"

LOCALHOST_HOST = "127.0.0.1"

NORMAL_RPC_DEADLINE_SECONDS = 30.0

DEADLINE_TEST_SECONDS = 0.02

DEADLINE_TEST_SLEEP_SECONDS = 0.25

UNAVAILABLE_TEST_DEADLINE_SECONDS = 1.0


CONFIRMATION_CASES = (
    (
        "orbis_lexical",
        RetrievalQuery(
            question=("What defect affected ORBIS-IDX-7?"),
            top_k=5,
        ),
    ),
    (
        "alder_supplier_risk",
        RetrievalQuery(
            question=("What supplier concentration risk affects Alder Manufacturing?"),
            top_k=5,
        ),
    ),
    (
        "vantage_renewal_risk",
        RetrievalQuery(
            question=("What renewal risk is described for Vantage Retail Analytics?"),
            top_k=5,
        ),
    ),
    (
        "dataset_version_error",
        RetrievalQuery(
            dataset_version="northstar-v2",
            question="supplier concentration",
            top_k=5,
        ),
    ),
)


@dataclass(
    slots=True,
)
class _LocalhostBoundary:
    server: grpc.Server
    channel: grpc.Channel
    workers: ThreadPoolExecutor
    client: GrpcRetrievalExecutor
    _stopped: bool = False

    def stop_server(
        self,
    ) -> None:
        if self._stopped:
            return

        self.server.stop(0).wait()

        self._stopped = True

    def close(
        self,
    ) -> None:
        self.channel.close()

        self.stop_server()

        self.workers.shutdown(
            wait=True,
            cancel_futures=True,
        )


class _EmptyRetrievalExecutor:
    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        del query

        return ToolExecutionResult(
            tool="retrieval",
            status="empty",
            payload=RetrievalPayload(hits=()),
            duration_ms=0.0,
        )


class _SlowRetrievalExecutor:
    def __init__(
        self,
        *,
        sleep_seconds: float,
    ) -> None:
        self._sleep_seconds = sleep_seconds

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        del query

        sleep(self._sleep_seconds)

        return ToolExecutionResult(
            tool="retrieval",
            status="empty",
            payload=RetrievalPayload(hits=()),
            duration_ms=(self._sleep_seconds * 1000.0),
        )


def semantic_retrieval_result(
    result: ToolExecutionResult,
) -> dict[str, object]:
    """
    Return deterministic retrieval semantics.

    duration_ms is intentionally excluded because direct and RPC
    executions have different timing contexts.
    """

    payload = result.payload

    if payload is None:
        return {
            "status": result.status,
            "error": result.error,
            "payload": None,
        }

    if not isinstance(
        payload,
        RetrievalPayload,
    ):
        raise TypeError("retrieval result contained a non-retrieval payload")

    hits = []

    for hit in payload.hits:
        hits.append(
            {
                "rank": hit.rank,
                "chunk_id": hit.chunk_id,
                "evidence_id": (hit.evidence_id),
                "document_id": (hit.document_id),
                "text": hit.text,
                "source_fact_ids": list(hit.source_fact_ids),
                "rrf_score": hit.rrf_score,
                "bm25_rank": hit.bm25_rank,
                "dense_rank": (hit.dense_rank),
            }
        )

    return {
        "status": result.status,
        "error": result.error,
        "payload": {
            "hits": hits,
        },
    }


def _start_localhost_boundary(
    executor,
    *,
    deadline_seconds: float,
) -> _LocalhostBoundary:
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

        raise RuntimeError("failed to bind localhost gRPC retrieval server")

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

        raise RuntimeError("localhost gRPC retrieval channel did not become ready") from None

    stub = retrieval_pb2_grpc.RetrievalServiceStub(channel)

    client = GrpcRetrievalExecutor(
        stub,
        deadline_seconds=(deadline_seconds),
    )

    return _LocalhostBoundary(
        server=server,
        channel=channel,
        workers=workers,
        client=client,
    )


def _assert_persisted_counts(
    *,
    document_counts: dict[str, int],
    chunk_counts: dict[str, int],
) -> None:
    expected_documents = 32
    expected_evidence_blocks = 80
    expected_chunks = 80
    expected_chunk_source_facts = 186

    if document_counts.get("documents") != expected_documents:
        raise RuntimeError("persisted document count does not match frozen corpus")

    if document_counts.get("evidence_blocks") != expected_evidence_blocks:
        raise RuntimeError("persisted evidence-block count does not match frozen corpus")

    if chunk_counts.get("chunks") != expected_chunks:
        raise RuntimeError("persisted chunk count does not match frozen corpus")

    if chunk_counts.get("chunk_source_facts") != expected_chunk_source_facts:
        raise RuntimeError("persisted chunk provenance count does not match frozen corpus")


def _run_parity_confirmation(
    retrieval: FrozenHybridRetrievalExecutor,
) -> list[dict[str, object]]:
    boundary = _start_localhost_boundary(
        retrieval,
        deadline_seconds=(NORMAL_RPC_DEADLINE_SECONDS),
    )

    observations: list[dict[str, object]] = []

    try:
        for (
            case_id,
            query,
        ) in CONFIRMATION_CASES:
            direct = retrieval.execute(query)

            remote = boundary.client.execute(query)

            direct_semantics = semantic_retrieval_result(direct)

            remote_semantics = semantic_retrieval_result(remote)

            if direct_semantics != remote_semantics:
                raise RuntimeError(f"localhost gRPC retrieval parity failed for {case_id}")

            observations.append(
                {
                    "case_id": case_id,
                    "dataset_version": (query.dataset_version),
                    "top_k": query.top_k,
                    "semantic_parity": True,
                    "result": (remote_semantics),
                }
            )

    finally:
        boundary.close()

    return observations


def _run_deadline_confirmation() -> dict[
    str,
    object,
]:
    boundary = _start_localhost_boundary(
        _SlowRetrievalExecutor(sleep_seconds=(DEADLINE_TEST_SLEEP_SECONDS)),
        deadline_seconds=(DEADLINE_TEST_SECONDS),
    )

    try:
        result = boundary.client.execute(
            RetrievalQuery(question=("controlled deadline confirmation"))
        )

    finally:
        boundary.close()

    if result.status != "error" or result.error != ("retrieval rpc deadline exceeded"):
        raise RuntimeError(
            "real localhost gRPC deadline did not map to the bounded retrieval error"
        )

    return {
        "verified": True,
        "expected_error": ("retrieval rpc deadline exceeded"),
        "client_deadline_seconds": (DEADLINE_TEST_SECONDS),
        "server_sleep_seconds": (DEADLINE_TEST_SLEEP_SECONDS),
    }


def _run_unavailable_confirmation() -> dict[
    str,
    object,
]:
    boundary = _start_localhost_boundary(
        _EmptyRetrievalExecutor(),
        deadline_seconds=(UNAVAILABLE_TEST_DEADLINE_SECONDS),
    )

    try:
        boundary.stop_server()

        result = boundary.client.execute(
            RetrievalQuery(question=("controlled unavailable confirmation"))
        )

    finally:
        boundary.close()

    if result.status != "error" or result.error != "retrieval rpc unavailable":
        raise RuntimeError(
            "stopped localhost gRPC server did not map to the bounded unavailable retrieval error"
        )

    return {
        "verified": True,
        "expected_error": ("retrieval rpc unavailable"),
        "client_deadline_seconds": (UNAVAILABLE_TEST_DEADLINE_SECONDS),
    }


def run_grpc_retrieval_confirmation(
    *,
    engine: Engine,
) -> dict[str, object]:
    with Session(engine) as session:
        document_counts = document_database_row_counts(
            session,
            DATASET_VERSION,
        )

        chunk_counts = chunk_database_row_counts(
            session,
            DATASET_VERSION,
            EVIDENCE_BLOCK_STRATEGY,
        )

        _assert_persisted_counts(
            document_counts=(document_counts),
            chunk_counts=(chunk_counts),
        )

        retrieval = FrozenHybridRetrievalExecutor.from_persisted_corpus(
            session,
            DATASET_VERSION,
        )

    parity_cases = _run_parity_confirmation(retrieval)

    deadline = _run_deadline_confirmation()

    unavailable = _run_unavailable_confirmation()

    metadata = dict(retrieval.metadata)

    return {
        "confirmation_version": (GRPC_RETRIEVAL_CONFIRMATION_VERSION),
        "dataset_version": (DATASET_VERSION),
        "transport": ("grpc-insecure-localhost-tcp"),
        "endpoint": ("127.0.0.1:ephemeral"),
        "retrieval_metadata": metadata,
        "persisted_counts": {
            "documents": (document_counts),
            "chunks": chunk_counts,
        },
        "parity": {
            "cases": parity_cases,
            "case_count": len(parity_cases),
            "all_semantically_equal": True,
            "excluded_fields": [
                "duration_ms",
            ],
        },
        "deadline": deadline,
        "unavailable": unavailable,
        "summary": {
            "persisted_corpus_verified": True,
            "localhost_rpc_verified": True,
            "semantic_parity_verified": True,
            "deadline_verified": True,
            "unavailable_verified": True,
            "all_passed": True,
        },
    }
