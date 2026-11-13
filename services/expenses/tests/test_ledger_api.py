"""Ledger API against an in-memory SQLite database, never Azure."""

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


def _setup_group(client):
    """Ana, Ben, Cleo. Ana pays 1000 for all three, Ben pays 500 for Ben and Cleo."""
    group_id = client.post("/groups", json={"name": "Trip"}, headers=KEY).json()["id"]
    ana, ben, cleo = (
        client.post(f"/groups/{group_id}/members", json={"name": n}, headers=KEY).json()["id"]
        for n in ("Ana", "Ben", "Cleo")
    )
    for payer, amount, members in ((ana, 1000, [ana, ben, cleo]), (ben, 500, [ben, cleo])):
        client.post(
            f"/groups/{group_id}/expenses",
            json={
                "description": "x",
                "amount_cents": amount,
                "paid_by_member_id": payer,
                "member_ids": members,
            },
            headers=KEY,
        )
    return group_id, (ana, ben, cleo)


def test_ledger_shape_agreed_with_settlements(client):
    group_id, (ana, ben, cleo) = _setup_group(client)
    r = client.get(f"/groups/{group_id}/ledger", headers=KEY)
    assert r.status_code == 200
    assert r.json() == {
        "group_id": group_id,
        "balances": [
            {"member_id": ana, "net_cents": 666},
            {"member_id": ben, "net_cents": -83},
            {"member_id": cleo, "net_cents": -583},
        ],
    }


def test_balances_sum_to_zero(client):
    group_id, _ = _setup_group(client)
    balances = client.get(f"/groups/{group_id}/ledger", headers=KEY).json()["balances"]
    assert sum(b["net_cents"] for b in balances) == 0


def test_group_without_expenses_lists_members_at_zero(client):
    group_id = client.post("/groups", json={"name": "Empty"}, headers=KEY).json()["id"]
    member = client.post(f"/groups/{group_id}/members", json={"name": "Ana"}, headers=KEY)
    r = client.get(f"/groups/{group_id}/ledger", headers=KEY)
    assert r.json() == {
        "group_id": group_id,
        "balances": [{"member_id": member.json()["id"], "net_cents": 0}],
    }


def test_unknown_group_is_404(client):
    assert client.get("/groups/99/ledger", headers=KEY).status_code == 404


def test_requires_api_key(client):
    assert client.get("/groups/1/ledger").status_code == 401
