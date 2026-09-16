from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import (
    TestClient,
)

from enterprise_genai.api import main
from enterprise_genai.api.main import (
    app,
)
from enterprise_genai.application import (
    AbstainedServiceResult,
    AnswerRequest,
    AnswerServiceResult,
)
from enterprise_genai.core.config import (
    Settings,
)


class FakeAnsweringService:
    def __init__(
        self,
    ) -> None:
        self.requests: list[AnswerRequest] = []

    def answer(
        self,
        request: AnswerRequest,
    ) -> AnswerServiceResult:
        self.requests.append(request)

        return AbstainedServiceResult(
            presentation_source=("deterministic"),
            generation_fidelity=("not_applicable"),
            text=("This request is outside the supported query capabilities."),
            reason=("unsupported_request"),
            detail=("unsupported test request"),
        )


@pytest.fixture(autouse=True)
def clean_serving_state():
    attributes = (
        "answering_service",
        "reviewed_answering_service",
        "answering_assembly",
        "answering_status",
        "operational_metrics",
    )

    for attribute in attributes:
        if hasattr(
            app.state,
            attribute,
        ):
            delattr(
                app.state,
                attribute,
            )

    yield

    for attribute in attributes:
        if hasattr(
            app.state,
            attribute,
        ):
            delattr(
                app.state,
                attribute,
            )


def test_answering_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.answering_enabled is False


def test_disabled_answering_remains_ready(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            _env_file=None,
            answering_enabled=False,
        ),
    )

    monkeypatch.setattr(
        main,
        "check_database",
        lambda: None,
    )

    def forbidden_build(
        **kwargs,
    ):
        raise AssertionError("disabled answering must not build serving resources")

    monkeypatch.setattr(
        main,
        "build_serving_assembly",
        forbidden_build,
    )

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200

    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "answering": "disabled",
    }


def test_enabled_lifecycle_installs_service(
    monkeypatch,
) -> None:
    service = FakeAnsweringService()

    reviewed_service = object()

    assembly = SimpleNamespace(
        service=service,
        reviewed_service=reviewed_service,
    )

    calls = []

    def fake_build(
        *,
        engine,
        metrics_registry,
    ):
        calls.append(
            (
                engine,
                metrics_registry,
            )
        )

        return assembly

    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            _env_file=None,
            answering_enabled=True,
        ),
    )

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

    with TestClient(app) as client:
        ready = client.get("/health/ready")

        answer = client.post(
            "/answer",
            json={"question": ("An unsupported question?")},
        )

        assert hasattr(
            app.state,
            "answering_service",
        )

        assert app.state.answering_service is service

        assert app.state.reviewed_answering_service is reviewed_service

    assert len(calls) == 1

    assert ready.status_code == 200

    assert ready.json() == {
        "status": "ready",
        "database": "ok",
        "answering": "ready",
    }

    assert answer.status_code == 200

    assert answer.json()["status"] == "abstained"

    assert len(service.requests) == 1

    assert not hasattr(
        app.state,
        "answering_service",
    )

    assert not hasattr(
        app.state,
        "answering_assembly",
    )

    assert not hasattr(
        app.state,
        "reviewed_answering_service",
    )

    assert not hasattr(
        app.state,
        "answering_status",
    )


def test_failed_enabled_initialization_is_not_ready(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            _env_file=None,
            answering_enabled=True,
        ),
    )

    monkeypatch.setattr(
        main,
        "check_database",
        lambda: None,
    )

    def fail_build(
        *,
        engine,
    ):
        raise RuntimeError("simulated serving startup failure")

    monkeypatch.setattr(
        main,
        "build_serving_assembly",
        fail_build,
    )

    with TestClient(app) as client:
        ready = client.get("/health/ready")

        answer = client.post(
            "/answer",
            json={
                "question": "Question?",
            },
        )

    assert ready.status_code == 503

    assert ready.json() == {
        "status": "not_ready",
        "database": "ok",
        "answering": "unavailable",
    }

    assert answer.status_code == 503

    assert answer.json() == {"detail": ("answering service unavailable")}


def test_lifespan_owns_process_local_metrics_registry(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main,
        "settings",
        Settings(
            _env_file=None,
            answering_enabled=False,
        ),
    )

    with TestClient(app):
        assert hasattr(
            app.state,
            "operational_metrics",
        )

        metrics = app.state.operational_metrics

        snapshot = metrics.snapshot()

        assert snapshot.version == "northstar-operational-metrics-v1"

    assert not hasattr(
        app.state,
        "operational_metrics",
    )
