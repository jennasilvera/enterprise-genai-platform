from __future__ import annotations

from typing import Protocol

import grpc
from pydantic import ValidationError

from enterprise_genai.execution.contracts import (
    RetrievalQuery,
    ToolExecutionResult,
)

from . import (
    retrieval_pb2,
    retrieval_pb2_grpc,
)
from .codec import (
    retrieval_query_from_proto,
    retrieval_result_to_proto,
)

RETRIEVAL_GRPC_SERVICER_VERSION = "northstar-retrieval-grpc-servicer-v1"


class RetrievalExecutorProtocol(Protocol):
    """Structural retrieval executor consumed by the RPC adapter."""

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult: ...


class RetrievalGrpcServicer(retrieval_pb2_grpc.RetrievalServiceServicer):
    """Adapt the versioned retrieval RPC to the typed domain executor."""

    def __init__(
        self,
        executor: RetrievalExecutorProtocol,
    ) -> None:
        self._executor = executor

    def Retrieve(
        self,
        request: retrieval_pb2.RetrievalRequest,
        context: grpc.ServicerContext,
    ) -> retrieval_pb2.RetrievalResponse:
        try:
            query = retrieval_query_from_proto(request)

        except ValidationError:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "invalid retrieval request",
            )

            raise AssertionError("gRPC abort returned unexpectedly") from None

        try:
            result = self._executor.execute(query)

        except Exception:
            context.abort(
                grpc.StatusCode.INTERNAL,
                "retrieval executor failure",
            )

            raise AssertionError("gRPC abort returned unexpectedly") from None

        try:
            return retrieval_result_to_proto(result)

        except Exception:
            context.abort(
                grpc.StatusCode.INTERNAL,
                "invalid retrieval executor result",
            )

            raise AssertionError("gRPC abort returned unexpectedly") from None
