"""Groups and members API against an in-memory SQLite database, never Azure."""

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


def _group(client, name="Lisbon trip"):
    return client.post("/groups", json={"name": name}, headers=KEY)


def _member(client, group_id, name):
    return client.post(f"/groups/{group_id}/members", json={"name": name}, headers=KEY)


def test_create_group_returns_201_with_id(client):
    r = _group(client)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] > 0
    assert body["name"] == "Lisbon trip"
    assert body["created_at"]


def test_list_groups_is_a_plain_list_in_creation_order(client):
    assert client.get("/groups", headers=KEY).json() == []
    _group(client, "A")
    _group(client, "B")
    names = [g["name"] for g in client.get("/groups", headers=KEY).json()]
    assert names == ["A", "B"]


def test_get_group_by_id(client):
    group_id = _group(client).json()["id"]
    r = client.get(f"/groups/{group_id}", headers=KEY)
    assert r.status_code == 200
    assert r.json()["name"] == "Lisbon trip"


def test_unknown_group_is_404(client):
    assert client.get("/groups/99", headers=KEY).status_code == 404
    assert client.get("/groups/99/members", headers=KEY).status_code == 404
    assert _member(client, 99, "Ana").status_code == 404


def test_blank_group_name_is_400_with_detail(client):
    r = _group(client, "   ")
    assert r.status_code == 400
    assert r.json() == {"detail": "group name must not be empty"}


def test_add_member_returns_201_and_lists_members(client):
    group_id = _group(client).json()["id"]
    r = _member(client, group_id, " Ana ")
    assert r.status_code == 201
    assert r.json()["name"] == "Ana"
    assert r.json()["group_id"] == group_id
    _member(client, group_id, "Ben")
    members = client.get(f"/groups/{group_id}/members", headers=KEY).json()
    assert [m["name"] for m in members] == ["Ana", "Ben"]


def test_duplicate_member_name_is_400_with_detail(client):
    group_id = _group(client).json()["id"]
    _member(client, group_id, "Ana")
    r = _member(client, group_id, "ana")
    assert r.status_code == 400
    assert r.json() == {"detail": "a member named 'ana' already exists in this group"}


def test_same_member_name_in_two_groups_is_fine(client):
    first = _group(client, "A").json()["id"]
    second = _group(client, "B").json()["id"]
    assert _member(client, first, "Ana").status_code == 201
    assert _member(client, second, "Ana").status_code == 201


def test_requires_api_key(client):
    assert client.get("/groups").status_code == 401
