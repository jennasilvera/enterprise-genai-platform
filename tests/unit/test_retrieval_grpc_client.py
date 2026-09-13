from __future__ import annotations

from collections.abc import Iterator

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
from enterprise_genai.rpc.retrieval.v1.client import (
    RETRIEVAL_GRPC_CLIENT_VERSION,
    GrpcRetrievalExecutor,
)
from enterprise_genai.rpc.retrieval.v1.codec import (
    retrieval_result_to_proto,
)


class SequenceClock:
    def __init__(
        self,
        *values: float,
    ) -> None:
        self._values: Iterator[float] = iter(values)

    def __call__(
        self,
    ) -> float:
        return next(self._values)


class FakeRpcError(grpc.RpcError):
    def __init__(
        self,
        code: grpc.StatusCode | None,
        *,
        details: str = "",
    ) -> None:
        super().__init__()

        self._code = code
        self._details = details

    def code(
        self,
    ) -> grpc.StatusCode | None:
        return self._code

    def details(
        self,
    ) -> str:
        return self._details


class RecordingRetrieveRpc:
    def __init__(
        self,
        *,
        response: (retrieval_pb2.RetrievalResponse | object | None) = None,
        rpc_error: (grpc.RpcError | None) = None,
    ) -> None:
        self._response = response
        self._rpc_error = rpc_error

        self.requests: list[retrieval_pb2.RetrievalRequest] = []

        self.timeouts: list[float] = []

    def __call__(
        self,
        request: retrieval_pb2.RetrievalRequest,
        *,
        timeout: float,
    ) -> retrieval_pb2.RetrievalResponse:
        self.requests.append(request)

        self.timeouts.append(timeout)

        if self._rpc_error is not None:
            raise self._rpc_error

        if self._response is None:
            raise AssertionError("fake RPC has no response")

        return self._response  # type: ignore[return-value]


class FakeStub:
    def __init__(
        self,
        rpc: RecordingRetrieveRpc,
    ) -> None:
        self.Retrieve = rpc


def _hit_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="retrieval",
        status="ok",
        payload=RetrievalPayload(
            hits=(
                RetrievalHit(
                    rank=1,
                    chunk_id="CHUNK-001",
                    evidence_id="EVIDENCE-001",
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


def _empty_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="retrieval",
        status="empty",
        payload=RetrievalPayload(hits=()),
        duration_ms=4.25,
    )


def _domain_error_result() -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="retrieval",
        status="error",
        duration_ms=2.5,
        error=("retrieval executor dataset version mismatch"),
    )


def _client_for_result(
    result: ToolExecutionResult,
    *,
    deadline_seconds: float = 2.5,
) -> tuple[
    GrpcRetrievalExecutor,
    RecordingRetrieveRpc,
]:
    rpc = RecordingRetrieveRpc(response=(retrieval_result_to_proto(result)))

    client = GrpcRetrievalExecutor(
        FakeStub(rpc),
        deadline_seconds=(deadline_seconds),
    )

    return (
        client,
        rpc,
    )


def test_client_version_is_frozen() -> None:
    assert RETRIEVAL_GRPC_CLIENT_VERSION == ("northstar-retrieval-grpc-client-v1")


@pytest.mark.parametrize(
    "deadline_seconds",
    (
        0.0,
        -1.0,
        float("inf"),
        float("-inf"),
        float("nan"),
    ),
)
def test_client_rejects_invalid_deadline(
    deadline_seconds: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="deadline",
    ):
        GrpcRetrievalExecutor(
            FakeStub(RecordingRetrieveRpc()),
            deadline_seconds=(deadline_seconds),
        )


def test_success_preserves_query_deadline_and_result() -> None:
    expected = _hit_result()

    client, rpc = _client_for_result(
        expected,
        deadline_seconds=3.75,
    )

    query = RetrievalQuery(
        dataset_version="northstar-v1",
        question=("What defect affected ORBIS-IDX-7?"),
        top_k=7,
    )

    result = client.execute(query)

    assert result == expected

    assert rpc.timeouts == [3.75]

    assert len(rpc.requests) == 1

    sent = rpc.requests[0]

    assert sent.question == (query.question)

    assert sent.dataset_version == query.dataset_version

    assert sent.top_k == (query.top_k)


def test_empty_result_is_preserved() -> None:
    expected = _empty_result()

    client, _ = _client_for_result(expected)

    assert client.execute(RetrievalQuery(question="Question?")) == expected


def test_typed_domain_error_is_preserved() -> None:
    expected = _domain_error_result()

    client, _ = _client_for_result(expected)

    assert client.execute(RetrievalQuery(question="Question?")) == expected


def test_deadline_exceeded_maps_to_bounded_error() -> None:
    rpc = RecordingRetrieveRpc(
        rpc_error=FakeRpcError(
            grpc.StatusCode.DEADLINE_EXCEEDED,
            details=("SECRET DEADLINE DETAILS"),
        )
    )

    client = GrpcRetrievalExecutor(
        FakeStub(rpc),
        deadline_seconds=1.25,
        clock=SequenceClock(
            10.0,
            10.125,
        ),
    )

    result = client.execute(RetrievalQuery(question="PRIVATE QUESTION"))

    assert result.tool == "retrieval"
    assert result.status == "error"

    assert result.error == ("retrieval rpc deadline exceeded")

    assert result.duration_ms == (pytest.approx(125.0))

    assert rpc.timeouts == [1.25]

    assert "SECRET" not in result.error

    assert "PRIVATE QUESTION" not in result.error


def test_unavailable_maps_to_bounded_error() -> None:
    rpc = RecordingRetrieveRpc(
        rpc_error=FakeRpcError(
            grpc.StatusCode.UNAVAILABLE,
            details="SECRET BACKEND ADDRESS",
        )
    )

    client = GrpcRetrievalExecutor(
        FakeStub(rpc),
        deadline_seconds=2.0,
    )

    result = client.execute(RetrievalQuery(question="Question?"))

    assert result.status == "error"

    assert result.error == ("retrieval rpc unavailable")

    assert "SECRET" not in result.error


def test_other_rpc_status_maps_without_details() -> None:
    rpc = RecordingRetrieveRpc(
        rpc_error=FakeRpcError(
            grpc.StatusCode.INTERNAL,
            details=("SECRET SERVER TRACE"),
        )
    )

    client = GrpcRetrievalExecutor(
        FakeStub(rpc),
        deadline_seconds=2.0,
    )

    result = client.execute(RetrievalQuery(question="Question?"))

    assert result.status == "error"

    assert result.error == ("retrieval rpc failed: internal")

    assert "SECRET" not in result.error


def test_unknown_rpc_status_is_bounded() -> None:
    rpc = RecordingRetrieveRpc(
        rpc_error=FakeRpcError(
            None,
            details=("SECRET UNKNOWN FAILURE"),
        )
    )

    client = GrpcRetrievalExecutor(
        FakeStub(rpc),
        deadline_seconds=2.0,
    )

    result = client.execute(RetrievalQuery(question="Question?"))

    assert result.status == "error"

    assert result.error == ("retrieval rpc failed: unknown")


def test_malformed_response_maps_to_typed_error() -> None:
    malformed = retrieval_pb2.RetrievalResponse(
        status=(retrieval_pb2.EXECUTION_STATUS_UNSPECIFIED),
        duration_ms=999.0,
    )

    rpc = RecordingRetrieveRpc(response=malformed)

    client = GrpcRetrievalExecutor(
        FakeStub(rpc),
        deadline_seconds=2.0,
        clock=SequenceClock(
            20.0,
            20.040,
        ),
    )

    result = client.execute(RetrievalQuery(question="Question?"))

    assert result.status == "error"

    assert result.error == ("retrieval rpc response invalid")

    assert result.duration_ms == (pytest.approx(40.0))


def test_wrong_response_type_maps_to_typed_error() -> None:
    rpc = RecordingRetrieveRpc(response=object())

    client = GrpcRetrievalExecutor(
        FakeStub(rpc),
        deadline_seconds=2.0,
        clock=SequenceClock(
            30.0,
            30.010,
        ),
    )

    result = client.execute(RetrievalQuery(question="Question?"))

    assert result.status == "error"

    assert result.error == ("retrieval rpc response invalid")

    assert result.duration_ms == (pytest.approx(10.0))


def test_valid_response_preserves_server_duration_not_client_elapsed() -> None:
    expected = _hit_result()

    rpc = RecordingRetrieveRpc(response=(retrieval_result_to_proto(expected)))

    client = GrpcRetrievalExecutor(
        FakeStub(rpc),
        deadline_seconds=2.0,
        clock=SequenceClock(
            100.0,
        ),
    )

    result = client.execute(RetrievalQuery(question="Question?"))

    assert result.duration_ms == (expected.duration_ms)
