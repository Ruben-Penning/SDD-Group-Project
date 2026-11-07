import json
import logging

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.security import require_api_key


def test_health_returns_ok():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_each_request_logs_one_json_line(caplog):
    client = TestClient(create_app())
    with caplog.at_level(logging.INFO, logger="request"):
        client.get("/health")
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "request"]
    assert len(lines) == 1
    assert lines[0]["method"] == "GET"
    assert lines[0]["path"] == "/health"
    assert lines[0]["status"] == 200
    assert "duration_ms" in lines[0]


def test_cors_allows_only_configured_origin(monkeypatch):
    monkeypatch.setenv("CORS_ORIGIN", "https://ui.example.com")
    client = TestClient(create_app())
    allowed = client.get("/health", headers={"Origin": "https://ui.example.com"})
    blocked = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert allowed.headers.get("access-control-allow-origin") == "https://ui.example.com"
    assert "access-control-allow-origin" not in blocked.headers


def _protected_client() -> TestClient:
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_api_key)])
    def protected() -> dict:
        return {"ok": True}

    return TestClient(app)


def test_api_key_required_when_configured(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    client = _protected_client()
    assert client.get("/protected").status_code == 401
    assert client.get("/protected", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/protected", headers={"X-API-Key": "test-key"}).status_code == 200


def test_api_key_skipped_when_not_configured(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    assert _protected_client().get("/protected").status_code == 200
