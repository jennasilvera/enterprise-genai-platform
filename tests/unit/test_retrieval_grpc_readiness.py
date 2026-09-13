from __future__ import annotations

import grpc
import pytest

from enterprise_genai.rpc.retrieval.v1 import (
    readiness,
)
from enterprise_genai.rpc.retrieval.v1.readiness import (
    RETRIEVAL_GRPC_READINESS_VERSION,
    grpc_channel_is_ready,
)


class ReadyFuture:
    def __init__(
        self,
    ) -> None:
        self.timeouts: list[float] = []

        self.cancel_calls = 0

    def result(
        self,
        *,
        timeout: float,
    ) -> None:
        self.timeouts.append(timeout)

    def cancel(
        self,
    ) -> bool:
        self.cancel_calls += 1

        return True


class TimeoutFuture:
    def __init__(
        self,
    ) -> None:
        self.timeouts: list[float] = []

        self.cancel_calls = 0

    def result(
        self,
        *,
        timeout: float,
    ) -> None:
        self.timeouts.append(timeout)

        raise grpc.FutureTimeoutError()

    def cancel(
        self,
    ) -> bool:
        self.cancel_calls += 1

        return True


def test_readiness_version_identifier() -> None:
    assert RETRIEVAL_GRPC_READINESS_VERSION == ("northstar-retrieval-grpc-readiness-v1")


def test_ready_channel_returns_true(
    monkeypatch,
) -> None:
    future = ReadyFuture()

    channel = object()

    monkeypatch.setattr(
        readiness.grpc,
        "channel_ready_future",
        lambda supplied_channel: future,
    )

    observed = grpc_channel_is_ready(
        channel,  # type: ignore[arg-type]
        timeout_seconds=0.25,
    )

    assert observed is True

    assert future.timeouts == [0.25]

    assert future.cancel_calls == 0


def test_timeout_returns_false_and_cancels_future(
    monkeypatch,
) -> None:
    future = TimeoutFuture()

    channel = object()

    monkeypatch.setattr(
        readiness.grpc,
        "channel_ready_future",
        lambda supplied_channel: future,
    )

    observed = grpc_channel_is_ready(
        channel,  # type: ignore[arg-type]
        timeout_seconds=0.125,
    )

    assert observed is False

    assert future.timeouts == [0.125]

    assert future.cancel_calls == 1


@pytest.mark.parametrize(
    "timeout",
    (
        0.0,
        -1.0,
        float("inf"),
        float("-inf"),
        float("nan"),
    ),
)
def test_invalid_timeout_is_rejected(
    timeout: float,
) -> None:
    with pytest.raises(
        ValueError,
        match=("readiness timeout"),
    ):
        grpc_channel_is_ready(
            object(),  # type: ignore[arg-type]
            timeout_seconds=timeout,
        )
