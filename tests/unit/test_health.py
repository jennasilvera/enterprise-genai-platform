from fastapi.testclient import TestClient

from enterprise_genai.api import main
from enterprise_genai.api.main import app


def test_live_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "enterprise-genai-platform",
        "environment": "dev",
    }


def test_ready_health_when_database_is_available(monkeypatch) -> None:
    monkeypatch.setattr(main, "check_database", lambda: None)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "answering": "disabled",
    }


def test_ready_health_when_database_is_unavailable(monkeypatch) -> None:
    def unavailable_database() -> None:
        raise RuntimeError("simulated database outage")

    monkeypatch.setattr(main, "check_database", unavailable_database)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "unavailable",
        "answering": "disabled",
    }
