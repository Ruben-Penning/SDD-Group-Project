"""Ledger client against a fake expenses-service (httpx.MockTransport), never the network."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.clients.ledger import (
    UNAVAILABLE_MESSAGE,
    ExpensesUnavailableError,
    GroupNotFoundError,
    fetch_ledger,
)
from app.main import create_app

LEDGER = {
    "group_id": 7,
    "balances": [
        {"member_id": 1, "net_cents": 1500},
        {"member_id": 2, "net_cents": -1000},
        {"member_id": 3, "net_cents": -500},
    ],
}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("EXPENSES_URL", "http://expenses.test")
    monkeypatch.setenv("API_KEY", "test-key")


def _fake(handler):
    return httpx.MockTransport(handler)


def test_returns_balances_by_member():
    def handler(request):
        return httpx.Response(200, json=LEDGER)

    assert fetch_ledger(7, transport=_fake(handler)) == {1: 1500, 2: -1000, 3: -500}


def test_calls_ledger_url_with_api_key_and_2s_timeout():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("X-API-Key")
        seen["timeout"] = request.extensions["timeout"]
        return httpx.Response(200, json=LEDGER)

    fetch_ledger(7, transport=_fake(handler))
    assert seen["url"] == "http://expenses.test/groups/7/ledger"
    assert seen["key"] == "test-key"
    assert set(seen["timeout"].values()) == {2.0}


def test_empty_group_returns_empty_dict():
    def handler(request):
        return httpx.Response(200, json={"group_id": 7, "balances": []})

    assert fetch_ledger(7, transport=_fake(handler)) == {}


def test_unknown_group_raises_not_found():
    def handler(request):
        return httpx.Response(404, json={"detail": "Group not found"})

    with pytest.raises(GroupNotFoundError):
        fetch_ledger(7, transport=_fake(handler))


@pytest.mark.parametrize(
    "error",
    [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError],
    ids=["read-timeout", "connect-timeout", "connection-refused"],
)
def test_network_failure_raises_unavailable(error):
    def handler(request):
        raise error("simulated", request=request)

    with pytest.raises(ExpensesUnavailableError, match="unavailable"):
        fetch_ledger(7, transport=_fake(handler))


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(503),
        httpx.Response(401, json={"detail": "Invalid API key"}),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"group_id": 7}),
        httpx.Response(200, json={"balances": [{"member_id": 1}]}),
    ],
    ids=["500", "503", "wrong-api-key", "not-json", "missing-balances", "missing-net-cents"],
)
def test_bad_response_raises_unavailable(response):
    with pytest.raises(ExpensesUnavailableError):
        fetch_ledger(7, transport=_fake(lambda request: response))


def _app_raising(exc):
    app = create_app()

    @app.get("/test-only/raise")
    def _raise():
        raise exc

    return TestClient(app)


def test_api_turns_unavailable_into_503_with_clear_message():
    r = _app_raising(ExpensesUnavailableError(UNAVAILABLE_MESSAGE)).get("/test-only/raise")
    assert r.status_code == 503
    assert r.json() == {"error": UNAVAILABLE_MESSAGE}


def test_api_turns_group_not_found_into_404():
    r = _app_raising(GroupNotFoundError("Group 7 not found")).get("/test-only/raise")
    assert r.status_code == 404
    assert r.json() == {"detail": "Group 7 not found"}