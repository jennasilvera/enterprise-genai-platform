from __future__ import annotations

from typing import NoReturn

import grpc
import pytest

from enterprise_genai.execution.contracts import (
    RetrievalHit,
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.rpc.retrieval.v1 import (
    retrieval_pb2,
)
from enterprise_genai.rpc.retrieval.v1.codec import (
    retrieval_result_from_proto,
)
from enterprise_genai.rpc.retrieval.v1.servicer import (
    RETRIEVAL_GRPC_SERVICER_VERSION,
    RetrievalGrpcServicer,
)


class RpcAbort(Exception):
    def __init__(
        self,
        *,
        code: grpc.StatusCode,
        details: str,
    ) -> None:
        super().__init__(f"{code.name}: {details}")

        self.code = code
        self.details = details


class FakeServicerContext:
    def abort(
        self,
        code: grpc.StatusCode,
        details: str,
    ) -> NoReturn:
        raise RpcAbort(
            code=code,
            details=details,
        )


class RecordingExecutor:
    def __init__(
        self,
        result: ToolExecutionResult,
    ) -> None:
        self.result = result
        self.queries: list[RetrievalQuery] = []

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        self.queries.append(query)

        return self.result


class RaisingExecutor:
    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        del query

        raise RuntimeError("SECRET EXECUTOR MESSAGE")


def _empty_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="retrieval",
        status="empty",
        payload=RetrievalPayload(hits=()),
        duration_ms=4.25,
    )


def _hit_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="retrieval",
        status="ok",
        payload=RetrievalPayload(
            hits=(
                RetrievalHit(
                    rank=1,
                    chunk_id="CHUNK-001",
                    evidence_id=("EVIDENCE-001"),
                    document_id="DOC-001",
                    text=("Synthetic retrieval evidence."),
                    source_fact_ids=(
                        "FACT-001",
                        "FACT-002",
                    ),
                    rrf_score=0.03125,
                    bm25_rank=1,
                    dense_rank=2,
                ),
            )
        ),
        duration_ms=8.5,
    )


def test_servicer_version_is_frozen() -> None:
    assert RETRIEVAL_GRPC_SERVICER_VERSION == ("northstar-retrieval-grpc-servicer-v1")


def test_valid_request_preserves_explicit_query_fields() -> None:
    result = _hit_result()

    executor = RecordingExecutor(result)

    servicer = RetrievalGrpcServicer(executor)

    request = retrieval_pb2.RetrievalRequest(
        question=("What defect affected ORBIS-IDX-7?"),
        dataset_version="northstar-v1",
        top_k=7,
    )

    response = servicer.Retrieve(
        request,
        FakeServicerContext(),
    )

    assert executor.queries == [
        RetrievalQuery(
            question=("What defect affected ORBIS-IDX-7?"),
            dataset_version=("northstar-v1"),
            top_k=7,
        )
    ]

    assert retrieval_result_from_proto(response) == result


def test_omitted_wire_fields_preserve_domain_defaults() -> None:
    executor = RecordingExecutor(_empty_result())

    servicer = RetrievalGrpcServicer(executor)

    response = servicer.Retrieve(
        retrieval_pb2.RetrievalRequest(question="Question?"),
        FakeServicerContext(),
    )

    assert executor.queries == [RetrievalQuery(question="Question?")]

    assert retrieval_result_from_proto(response) == _empty_result()


def test_empty_domain_result_remains_rpc_success_payload() -> None:
    result = _empty_result()

    servicer = RetrievalGrpcServicer(RecordingExecutor(result))

    response = servicer.Retrieve(
        retrieval_pb2.RetrievalRequest(question="Question?"),
        FakeServicerContext(),
    )

    assert response.status == (retrieval_pb2.EXECUTION_STATUS_EMPTY)

    assert response.HasField("payload")

    assert not response.HasField("error")


def test_typed_domain_error_remains_typed_rpc_response() -> None:
    result = ToolExecutionResult(
        tool="retrieval",
        status="error",
        duration_ms=2.0,
        error=("retrieval executor dataset version mismatch"),
    )

    servicer = RetrievalGrpcServicer(RecordingExecutor(result))

    response = servicer.Retrieve(
        retrieval_pb2.RetrievalRequest(question="Question?"),
        FakeServicerContext(),
    )

    assert response.status == (retrieval_pb2.EXECUTION_STATUS_ERROR)

    assert not response.HasField("payload")

    assert response.HasField("error")

    assert retrieval_result_from_proto(response) == result


@pytest.mark.parametrize(
    "rpc_request",
    (
        retrieval_pb2.RetrievalRequest(question=""),
        retrieval_pb2.RetrievalRequest(
            question="Question?",
            dataset_version="",
        ),
        retrieval_pb2.RetrievalRequest(
            question="Question?",
            top_k=0,
        ),
        retrieval_pb2.RetrievalRequest(
            question="Question?",
            top_k=51,
        ),
    ),
)
def test_invalid_wire_request_aborts_invalid_argument(
    rpc_request: retrieval_pb2.RetrievalRequest,
) -> None:
    executor = RecordingExecutor(_empty_result())

    servicer = RetrievalGrpcServicer(executor)

    with pytest.raises(RpcAbort) as observed:
        servicer.Retrieve(
            rpc_request,
            FakeServicerContext(),
        )

    assert observed.value.code is grpc.StatusCode.INVALID_ARGUMENT

    assert observed.value.details == "invalid retrieval request"

    assert executor.queries == []


def test_executor_exception_aborts_internal_without_message_leak() -> None:
    servicer = RetrievalGrpcServicer(RaisingExecutor())

    with pytest.raises(RpcAbort) as observed:
        servicer.Retrieve(
            retrieval_pb2.RetrievalRequest(question="Question?"),
            FakeServicerContext(),
        )

    assert observed.value.code is grpc.StatusCode.INTERNAL

    assert observed.value.details == "retrieval executor failure"

    assert "SECRET" not in observed.value.details


def test_invalid_executor_result_aborts_internal() -> None:
    invalid = ToolExecutionResult.model_construct(
        tool="sql",
        status="error",
        payload=None,
        duration_ms=0.0,
        error="synthetic",
    )

    servicer = RetrievalGrpcServicer(RecordingExecutor(invalid))

    with pytest.raises(RpcAbort) as observed:
        servicer.Retrieve(
            retrieval_pb2.RetrievalRequest(question="Question?"),
            FakeServicerContext(),
        )

    assert observed.value.code is grpc.StatusCode.INTERNAL

    assert observed.value.details == ("invalid retrieval executor result")


def test_executor_exception_does_not_echo_question() -> None:
    secret_question = "PRIVATE CUSTOMER QUESTION DO NOT LOG"

    servicer = RetrievalGrpcServicer(RaisingExecutor())

    with pytest.raises(RpcAbort) as observed:
        servicer.Retrieve(
            retrieval_pb2.RetrievalRequest(question=secret_question),
            FakeServicerContext(),
        )

    assert secret_question not in observed.value.details
