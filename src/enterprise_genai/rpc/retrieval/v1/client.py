from __future__ import annotations

from collections.abc import Callable
from math import isfinite
from time import perf_counter
from typing import Protocol

import grpc
from pydantic import ValidationError

from enterprise_genai.execution.contracts import (
    RetrievalQuery,
    ToolExecutionResult,
)

from . import retrieval_pb2
from .codec import (
    retrieval_query_to_proto,
    retrieval_result_from_proto,
)

RETRIEVAL_GRPC_CLIENT_VERSION = "northstar-retrieval-grpc-client-v1"


class RetrievalRpcCallable(Protocol):
    """Unary retrieval RPC callable exposed by the generated stub."""

    def __call__(
        self,
        request: retrieval_pb2.RetrievalRequest,
        *,
        timeout: float,
    ) -> retrieval_pb2.RetrievalResponse: ...


class RetrievalStubProtocol(Protocol):
    """Structural subset of RetrievalServiceStub used by the client."""

    Retrieve: RetrievalRpcCallable


class GrpcRetrievalExecutor:
    """Adapt a gRPC retrieval stub to the existing executor contract."""

    def __init__(
        self,
        stub: RetrievalStubProtocol,
        *,
        deadline_seconds: float,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        if not isfinite(deadline_seconds) or deadline_seconds <= 0.0:
            raise ValueError("retrieval RPC deadline must be finite and greater than zero")

        self._stub = stub
        self._deadline_seconds = deadline_seconds
        self._clock = clock

    @property
    def deadline_seconds(
        self,
    ) -> float:
        return self._deadline_seconds

    def _duration_ms(
        self,
        started_at: float,
    ) -> float:
        return max(
            0.0,
            (self._clock() - started_at) * 1000.0,
        )

    @staticmethod
    def _transport_error_message(
        code: grpc.StatusCode | None,
    ) -> str:
        if code is grpc.StatusCode.DEADLINE_EXCEEDED:
            return "retrieval rpc deadline exceeded"

        if code is grpc.StatusCode.UNAVAILABLE:
            return "retrieval rpc unavailable"

        code_name = getattr(
            code,
            "name",
            "unknown",
        ).lower()

        return f"retrieval rpc failed: {code_name}"

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        started_at = self._clock()

        request = retrieval_query_to_proto(query)

        try:
            response = self._stub.Retrieve(
                request,
                timeout=(self._deadline_seconds),
            )

        except grpc.RpcError as exc:
            return ToolExecutionResult(
                tool="retrieval",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=(self._transport_error_message(exc.code())),
            )

        if not isinstance(
            response,
            retrieval_pb2.RetrievalResponse,
        ):
            return ToolExecutionResult(
                tool="retrieval",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=("retrieval rpc response invalid"),
            )

        try:
            return retrieval_result_from_proto(response)

        except (
            ValueError,
            ValidationError,
        ):
            return ToolExecutionResult(
                tool="retrieval",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=("retrieval rpc response invalid"),
            )
