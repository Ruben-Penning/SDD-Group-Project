"""PUT and DELETE /expenses/{id} against an in-memory SQLite database, never Azure."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, ExpenseShare
from app.db.session import get_session
from app.main import create_app

KEY = {"X-API-Key": "test-key"}


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    # SQLite only enforces foreign keys when asked to (SQL Server always does).
    @event.listens_for(eng, "connect")
    def _enable_foreign_keys(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def client(monkeypatch, engine):
    monkeypatch.setenv("API_KEY", "test-key")
    session_factory = sessionmaker(bind=engine)

    def override_session():
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


@pytest.fixture
def expense(client):
    """Group with Ana, Ben, Cleo; Ana paid 6000 for Ana and Ben. Returns (expense, ids)."""
    group_id = client.post("/groups", json={"name": "Trip"}, headers=KEY).json()["id"]
    ids = [
        client.post(f"/groups/{group_id}/members", json={"name": n}, headers=KEY).json()["id"]
        for n in ("Ana", "Ben", "Cleo")
    ]
    created = client.post(
        f"/groups/{group_id}/expenses",
        json={
            "description": "Dinner",
            "amount_cents": 6000,
            "paid_by_member_id": ids[0],
            "member_ids": ids[:2],
        },
        headers=KEY,
    ).json()
    return created, ids


def _edit(client, expense_id, **body):
    return client.put(f"/expenses/{expense_id}", json=body, headers=KEY)


def test_put_replaces_the_expense_and_resplits(client, expense):
    created, (ana, ben, cleo) = expense
    r = _edit(
        client,
        created["id"],
        description=" Big dinner ",
        amount_cents=1000,
        paid_by_member_id=ben,
        member_ids=[ana, ben, cleo],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["id"]
    assert body["group_id"] == created["group_id"]
    assert body["description"] == "Big dinner"
    assert body["amount_cents"] == 1000
    assert body["paid_by_member_id"] == ben
    assert body["shares"] == [
        {"member_id": ana, "share_cents": 334},
        {"member_id": ben, "share_cents": 333},
        {"member_id": cleo, "share_cents": 333},
    ]
    listed = client.get(f"/groups/{created['group_id']}/expenses", headers=KEY).json()
    assert listed == [body]


def test_put_can_remove_a_member_from_the_split(client, expense, engine):
    created, (ana, _, _) = expense
    r = _edit(
        client,
        created["id"],
        description="Dinner",
        amount_cents=6000,
        paid_by_member_id=ana,
        member_ids=[ana],
    )
    assert r.json()["shares"] == [{"member_id": ana, "share_cents": 6000}]
    with engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(ExpenseShare)) == 1


def test_put_updates_the_ledger(client, expense):
    created, (ana, ben, _) = expense
    _edit(
        client,
        created["id"],
        description="Dinner",
        amount_cents=2000,
        paid_by_member_id=ana,
        member_ids=[ana, ben],
    )
    ledger = client.get(f"/groups/{created['group_id']}/ledger", headers=KEY).json()
    assert [b["net_cents"] for b in ledger["balances"]] == [1000, -1000, 0]


@pytest.mark.parametrize(
    "overrides,detail",
    [
        ({"amount_cents": 0}, "amount_cents must be greater than 0"),
        ({"amount_cents": 3_000_000_000}, "amount_cents must be at most 100000000 (1,000,000.00)"),
        ({"member_ids": []}, "member_ids must contain at least one member"),
        ({"paid_by_member_id": 999}, "paid_by_member_id is not a member of this group"),
    ],
)
def test_invalid_put_is_400_and_changes_nothing(client, expense, overrides, detail):
    created, (ana, ben, _) = expense
    body = {
        "description": "Changed",
        "amount_cents": 100,
        "paid_by_member_id": ana,
        "member_ids": [ana, ben],
        **overrides,
    }
    r = _edit(client, created["id"], **body)
    assert r.status_code == 400
    assert r.json() == {"detail": detail}
    listed = client.get(f"/groups/{created['group_id']}/expenses", headers=KEY).json()
    assert listed == [created]


def test_put_cannot_use_members_of_another_group(client, expense):
    created, (ana, _, _) = expense
    other = client.post("/groups", json={"name": "Other"}, headers=KEY).json()["id"]
    outsider = client.post(f"/groups/{other}/members", json={"name": "Dan"}, headers=KEY)
    r = _edit(
        client,
        created["id"],
        description="Dinner",
        amount_cents=6000,
        paid_by_member_id=ana,
        member_ids=[ana, outsider.json()["id"]],
    )
    assert r.status_code == 400


def test_delete_removes_the_expense_and_its_shares(client, expense, engine):
    created, _ = expense
    r = client.delete(f"/expenses/{created['id']}", headers=KEY)
    assert r.status_code == 204
    assert r.content == b""
    assert client.get(f"/groups/{created['group_id']}/expenses", headers=KEY).json() == []
    with engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(ExpenseShare)) == 0
    ledger = client.get(f"/groups/{created['group_id']}/ledger", headers=KEY).json()
    assert all(b["net_cents"] == 0 for b in ledger["balances"])


def test_unknown_expense_is_404(client):
    body = {"description": "x", "amount_cents": 1, "paid_by_member_id": 1, "member_ids": [1]}
    assert client.put("/expenses/99", json=body, headers=KEY).status_code == 404
    assert client.delete("/expenses/99", headers=KEY).status_code == 404


def test_deleting_twice_is_404(client, expense):
    created, _ = expense
    assert client.delete(f"/expenses/{created['id']}", headers=KEY).status_code == 204
    assert client.delete(f"/expenses/{created['id']}", headers=KEY).status_code == 404


def test_requires_api_key(client, expense):
    created, _ = expense
    assert client.delete(f"/expenses/{created['id']}").status_code == 401
