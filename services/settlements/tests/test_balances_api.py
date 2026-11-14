"""GET /groups/{group_id}/balances with a fake ledger and in-memory SQLite, never Azure."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.clients import ledger
from app.clients.ledger import UNAVAILABLE_MESSAGE, ExpensesUnavailableError, GroupNotFoundError
from app.db.models import Base
from app.db.session import get_session
from app.main import create_app

KEY = {"X-API-Key": "test-key"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_session():
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    yield TestClient(app)
    engine.dispose()


def _fake_ledger(monkeypatch, result):
    """Replace the call to expenses-service. `result` is a dict, or an exception to raise."""

    def fake(group_id):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(ledger, "fetch_ledger", fake)


def _pay(client, from_id, to_id, amount, group_id=1):
    r = client.post(
        f"/groups/{group_id}/payments",
        json={"from_member_id": from_id, "to_member_id": to_id, "amount_cents": amount},
        headers=KEY,
    )
    assert r.status_code == 201


def _balances(client, group_id=1):
    return client.get(f"/groups/{group_id}/balances", headers=KEY)


def test_without_payments_balances_equal_ledger(client, monkeypatch):
    _fake_ledger(monkeypatch, {2: -1500, 1: 1500})
    r = _balances(client)
    assert r.status_code == 200
    assert r.json() == {
        "group_id": 1,
        "balances": [
            {"member_id": 1, "balance_cents": 1500},
            {"member_id": 2, "balance_cents": -1500},
        ],
    }


def test_recorded_payment_updates_balances(client, monkeypatch):
    # Hand-worked: Ana (1) paid 30.00 for Ana, Ben (2), Cleo (3) -> +2000, -1000, -1000.
    _fake_ledger(monkeypatch, {1: 2000, 2: -1000, 3: -1000})
    _pay(client, from_id=2, to_id=1, amount=1000)
    body = _balances(client).json()
    assert {b["member_id"]: b["balance_cents"] for b in body["balances"]} == {
        1: 1000,
        2: 0,
        3: -1000,
    }
    assert sum(b["balance_cents"] for b in body["balances"]) == 0


def test_other_groups_payments_are_ignored(client, monkeypatch):
    _fake_ledger(monkeypatch, {1: 500, 2: -500})
    _pay(client, from_id=2, to_id=1, amount=500, group_id=2)
    balances = _balances(client).json()["balances"]
    assert [b["balance_cents"] for b in balances] == [500, -500]


def test_empty_group_returns_empty_list(client, monkeypatch):
    _fake_ledger(monkeypatch, {})
    assert _balances(client).json() == {"group_id": 1, "balances": []}


def test_expenses_down_returns_503_with_message(client, monkeypatch):
    _fake_ledger(monkeypatch, ExpensesUnavailableError(UNAVAILABLE_MESSAGE))
    r = _balances(client)
    assert r.status_code == 503
    assert r.json() == {"error": UNAVAILABLE_MESSAGE}


def test_unknown_group_returns_404(client, monkeypatch):
    _fake_ledger(monkeypatch, GroupNotFoundError("Group 1 not found"))
    assert _balances(client).status_code == 404


def test_balances_require_api_key(client, monkeypatch):
    _fake_ledger(monkeypatch, {})
    assert client.get("/groups/1/balances").status_code == 401
