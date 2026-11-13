"""Expenses API against an in-memory SQLite database, never Azure."""

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


@pytest.fixture
def group(client):
    """A group with three members; returns (group_id, [ana_id, ben_id, cleo_id])."""
    group_id = client.post("/groups", json={"name": "Trip"}, headers=KEY).json()["id"]
    ids = [
        client.post(f"/groups/{group_id}/members", json={"name": n}, headers=KEY).json()["id"]
        for n in ("Ana", "Ben", "Cleo")
    ]
    return group_id, ids


def _expense(client, group_id, **overrides):
    body = {"description": "Dinner", "amount_cents": 6000, "paid_by_member_id": 1}
    body.update(overrides)
    return client.post(f"/groups/{group_id}/expenses", json=body, headers=KEY)


def test_add_expense_splits_equally(client, group):
    group_id, (ana, ben, cleo) = group
    r = _expense(client, group_id, paid_by_member_id=ana, member_ids=[ana, ben, cleo])
    assert r.status_code == 201
    body = r.json()
    assert body["id"] > 0
    assert body["description"] == "Dinner"
    assert body["amount_cents"] == 6000
    assert body["paid_by_member_id"] == ana
    assert body["created_at"]
    assert body["shares"] == [
        {"member_id": ana, "share_cents": 2000},
        {"member_id": ben, "share_cents": 2000},
        {"member_id": cleo, "share_cents": 2000},
    ]


def test_list_expenses_returns_that_groups_expenses_in_order(client, group):
    group_id, (ana, ben, _) = group
    other = client.post("/groups", json={"name": "Other"}, headers=KEY).json()["id"]
    _expense(client, group_id, description="Taxi", amount_cents=1000, member_ids=[ana, ben])
    _expense(client, group_id, description="Hotel", amount_cents=5001, member_ids=[ana, ben])
    expenses = client.get(f"/groups/{group_id}/expenses", headers=KEY).json()
    assert [e["description"] for e in expenses] == ["Taxi", "Hotel"]
    assert [s["share_cents"] for s in expenses[1]["shares"]] == [2501, 2500]
    assert client.get(f"/groups/{other}/expenses", headers=KEY).json() == []


def test_unknown_group_is_404(client):
    assert client.get("/groups/99/expenses", headers=KEY).status_code == 404
    assert _expense(client, 99, member_ids=[1]).status_code == 404


@pytest.mark.parametrize(
    "overrides,detail",
    [
        ({"amount_cents": 0}, "amount_cents must be greater than 0"),
        ({"member_ids": []}, "member_ids must contain at least one member"),
        ({"description": " "}, "description must not be empty"),
        ({"paid_by_member_id": 99}, "paid_by_member_id is not a member of this group"),
        ({"member_ids": [1, 99]}, "member_ids not in this group: [99]"),
    ],
)
def test_invalid_expense_is_400_with_detail(client, group, overrides, detail):
    group_id, (ana, ben, _) = group
    body = {"paid_by_member_id": ana, "member_ids": [ana, ben], **overrides}
    r = _expense(client, group_id, **body)
    assert r.status_code == 400
    assert r.json() == {"detail": detail}
    assert client.get(f"/groups/{group_id}/expenses", headers=KEY).json() == []


def test_member_of_another_group_cannot_share(client, group):
    group_id, (ana, _, _) = group
    other = client.post("/groups", json={"name": "Other"}, headers=KEY).json()["id"]
    outsider = client.post(f"/groups/{other}/members", json={"name": "Dan"}, headers=KEY).json()[
        "id"
    ]
    r = _expense(client, group_id, paid_by_member_id=ana, member_ids=[ana, outsider])
    assert r.status_code == 400
