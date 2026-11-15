"""GET /groups/{group_id}/settle-up with a fake ledger and in-memory SQLite, never Azure."""

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


def _settle_up(client, group_id=1):
    return client.get(f"/groups/{group_id}/settle-up", headers=KEY)


def test_lists_the_fewest_transfers(client, monkeypatch):
    # Ana (1) paid 30.00 for Ana, Ben (2), Cleo (3): +2000, -1000, -1000.
    _fake_ledger(monkeypatch, {1: 2000, 2: -1000, 3: -1000})
    r = _settle_up(client)
    assert r.status_code == 200
    body = r.json()
    assert body["group_id"] == 1
    assert sorted(
        (t["from_member_id"], t["to_member_id"], t["amount_cents"]) for t in body["transfers"]
    ) == [
        (2, 1, 1000),
        (3, 1, 1000),
    ]


def test_recorded_payment_shrinks_settle_up(client, monkeypatch):
    _fake_ledger(monkeypatch, {1: 2000, 2: -1000, 3: -1000})
    _pay(client, from_id=2, to_id=1, amount=1000)
    assert _settle_up(client).json()["transfers"] == [
        {"from_member_id": 3, "to_member_id": 1, "amount_cents": 1000}
    ]


def test_everyone_settled_returns_no_transfers(client, monkeypatch):
    _fake_ledger(monkeypatch, {1: 500, 2: -500})
    _pay(client, from_id=2, to_id=1, amount=500)
    assert _settle_up(client).json() == {"group_id": 1, "transfers": []}


def test_ledger_not_summing_to_zero_returns_502(client, monkeypatch):
    _fake_ledger(monkeypatch, {1: 500, 2: -400})
    r = _settle_up(client)
    assert r.status_code == 502
    assert "do not add up" in r.json()["detail"]


def test_expenses_down_returns_503_with_message(client, monkeypatch):
    _fake_ledger(monkeypatch, ExpensesUnavailableError(UNAVAILABLE_MESSAGE))
    r = _settle_up(client)
    assert r.status_code == 503
    assert r.json() == {"error": UNAVAILABLE_MESSAGE}


def test_unknown_group_returns_404(client, monkeypatch):
    _fake_ledger(monkeypatch, GroupNotFoundError("Group 1 not found"))
    assert _settle_up(client).status_code == 404


def test_settle_up_requires_api_key(client, monkeypatch):
    _fake_ledger(monkeypatch, {})
    assert client.get("/groups/1/settle-up").status_code == 401
