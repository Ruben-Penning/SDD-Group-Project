"""Payments API against an in-memory SQLite database, never Azure."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


def _pay(client, group_id=1, from_id=1, to_id=2, amount=2000):
    return client.post(
        f"/groups/{group_id}/payments",
        json={"from_member_id": from_id, "to_member_id": to_id, "amount_cents": amount},
        headers=KEY,
    )


def test_record_payment_returns_201_with_body(client):
    r = _pay(client)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] > 0
    assert body["group_id"] == 1
    assert body["from_member_id"] == 1
    assert body["to_member_id"] == 2
    assert body["amount_cents"] == 2000
    assert body["created_at"]


def test_list_returns_only_that_groups_payments_in_order(client):
    _pay(client, group_id=1, amount=100)
    _pay(client, group_id=2, amount=999)
    _pay(client, group_id=1, amount=300)
    r = client.get("/groups/1/payments", headers=KEY)
    assert r.status_code == 200
    assert [p["amount_cents"] for p in r.json()] == [100, 300]


def test_list_empty_group_returns_empty_list(client):
    assert client.get("/groups/42/payments", headers=KEY).json() == []


@pytest.mark.parametrize(
    "from_id,to_id,amount",
    [(1, 2, 0), (1, 2, -5), (3, 3, 100)],
    ids=["zero-amount", "negative-amount", "pay-yourself"],
)
def test_invalid_payment_returns_400_and_saves_nothing(client, from_id, to_id, amount):
    r = _pay(client, from_id=from_id, to_id=to_id, amount=amount)
    assert r.status_code == 400
    assert "detail" in r.json()
    assert client.get("/groups/1/payments", headers=KEY).json() == []


def test_non_integer_amount_returns_422(client):
    r = client.post(
        "/groups/1/payments",
        json={"from_member_id": 1, "to_member_id": 2, "amount_cents": 20.5},
        headers=KEY,
    )
    assert r.status_code == 422


def test_delete_removes_payment(client):
    payment_id = _pay(client).json()["id"]
    r = client.delete(f"/payments/{payment_id}", headers=KEY)
    assert r.status_code == 204
    assert client.get("/groups/1/payments", headers=KEY).json() == []


def test_delete_unknown_payment_returns_404(client):
    assert client.delete("/payments/999", headers=KEY).status_code == 404


def test_payments_routes_require_api_key(client):
    assert client.get("/groups/1/payments").status_code == 401
    r = client.post(
        "/groups/1/payments",
        json={"from_member_id": 1, "to_member_id": 2, "amount_cents": 100},
    )
    assert r.status_code == 401
    assert client.delete("/payments/1").status_code == 401