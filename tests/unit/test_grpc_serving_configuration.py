from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from enterprise_genai.api import main
from enterprise_genai.core.config import Settings
from enterprise_genai.rpc.retrieval.v1.client import (
    GrpcRetrievalExecutor,
)


class FakeChannel:
    def __init__(
        self,
    ) -> None:
        self.close_calls = 0

    def close(
        self,
    ) -> None:
        self.close_calls += 1


class FakeStub:
    pass


@pytest.fixture(autouse=True)
def clean_app_state():
    attributes = (
        "answering_service",
        "answering_assembly",
        "answering_status",
        "operational_metrics",
    )

    for attribute in attributes:
        if hasattr(
            main.app.state,
            attribute,
        ):
            delattr(
                main.app.state,
                attribute,
            )

    yield

    for attribute in attributes:
        if hasattr(
            main.app.state,
            attribute,
        ):
            delattr(
                main.app.state,
                attribute,
            )


def test_retrieval_mode_defaults_to_local() -> None:
    settings = Settings(_env_file=None)

    assert settings.retrieval_mode == "local"

    assert settings.retrieval_grpc_target is None


def test_grpc_mode_requires_target() -> None:
    with pytest.raises(
        ValueError,
        match=("retrieval_grpc_target"),
    ):
        Settings(
            _env_file=None,
            retrieval_mode="grpc",
        )


@pytest.mark.parametrize(
    "deadline",
    (
        0.0,
        -1.0,
        float("inf"),
        float("-inf"),
        float("nan"),
    ),
)
def test_settings_reject_invalid_grpc_deadline(
    deadline: float,
) -> None:
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            retrieval_grpc_deadline_seconds=(deadline),
        )


def test_grpc_lifespan_injects_client_and_closes_channel(
    monkeypatch,
) -> None:
    channel = FakeChannel()

    stub = FakeStub()

    observed: dict[
        str,
        object,
    ] = {}

    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            _env_file=None,
            answering_enabled=True,
            retrieval_mode="grpc",
            retrieval_grpc_target=("127.0.0.1:50051"),
            retrieval_grpc_deadline_seconds=(1.25),
        ),
    )

    def fake_insecure_channel(
        target: str,
    ):
        observed["target"] = target

        return channel

    monkeypatch.setattr(
        main.grpc,
        "insecure_channel",
        fake_insecure_channel,
    )

    def fake_stub_builder(
        supplied_channel,
    ):
        assert supplied_channel is channel

        return stub

    monkeypatch.setattr(
        main.retrieval_pb2_grpc,
        "RetrievalServiceStub",
        fake_stub_builder,
    )

    service = SimpleNamespace()

    def fake_build(
        *,
        engine,
        metrics_registry,
        retrieval_executor,
    ):
        observed["engine"] = engine

        observed["metrics_registry"] = metrics_registry

        observed["retrieval_executor"] = retrieval_executor

        return SimpleNamespace(service=service)

    monkeypatch.setattr(
        main,
        "build_serving_assembly",
        fake_build,
    )

    monkeypatch.setattr(
        main,
        "check_database",
        lambda: None,
    )

    with TestClient(main.app) as client:
        ready = client.get("/health/ready")

        assert ready.status_code == 200

        assert main.app.state.answering_service is service

        executor = observed["retrieval_executor"]

        assert isinstance(
            executor,
            GrpcRetrievalExecutor,
        )

        assert executor.deadline_seconds == 1.25

        assert observed["target"] == "127.0.0.1:50051"

        assert channel.close_calls == 0

    assert channel.close_calls == 1


def test_failed_grpc_serving_initialization_closes_channel(
    monkeypatch,
) -> None:
    channel = FakeChannel()

    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            _env_file=None,
            answering_enabled=True,
            retrieval_mode="grpc",
            retrieval_grpc_target=("127.0.0.1:50051"),
        ),
    )

    monkeypatch.setattr(
        main.grpc,
        "insecure_channel",
        lambda target: channel,
    )

    monkeypatch.setattr(
        main.retrieval_pb2_grpc,
        "RetrievalServiceStub",
        lambda supplied_channel: FakeStub(),
    )

    def fail_build(
        **kwargs,
    ):
        del kwargs

        raise RuntimeError("simulated assembly failure")

    monkeypatch.setattr(
        main,
        "build_serving_assembly",
        fail_build,
    )

    monkeypatch.setattr(
        main,
        "check_database",
        lambda: None,
    )

    with TestClient(main.app) as client:
        ready = client.get("/health/ready")

        assert ready.status_code == 503

    assert channel.close_calls == 1
