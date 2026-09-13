from __future__ import annotations

from math import isfinite

import grpc

RETRIEVAL_GRPC_READINESS_VERSION = "northstar-retrieval-grpc-readiness-v1"


def grpc_channel_is_ready(
    channel: grpc.Channel,
    *,
    timeout_seconds: float,
) -> bool:
    """
    Return whether a gRPC channel reaches READY within a bounded timeout.

    This primitive is intended for startup reachability gating. It checks
    transport/channel readiness only; it does not execute a RetrievalService
    method or establish ongoing semantic or runtime dependency health.
    """

    if not isfinite(timeout_seconds) or timeout_seconds <= 0.0:
        raise ValueError("gRPC readiness timeout must be finite and greater than zero")

    future = grpc.channel_ready_future(channel)

    try:
        future.result(timeout=timeout_seconds)

    except grpc.FutureTimeoutError:
        future.cancel()

        return False

    return True
