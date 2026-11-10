"""Migrations run against a throwaway SQLite file, never Azure."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.models import Base

SERVICE_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def db_url(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)  # migrations/env.py reads it via get_settings()
    return url


@pytest.fixture
def alembic_cfg():
    cfg = Config(str(SERVICE_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVICE_ROOT / "migrations"))
    return cfg


@pytest.fixture
def engine(db_url):
    eng = create_engine(db_url)
    yield eng
    eng.dispose()


def _insert(conn, from_id, to_id, amount):
    conn.execute(
        text(
            "INSERT INTO payments (group_id, from_member_id, to_member_id, amount_cents) "
            "VALUES (1, :f, :t, :a)"
        ),
        {"f": from_id, "t": to_id, "a": amount},
    )


def test_upgrade_creates_payments_table(alembic_cfg, engine):
    command.upgrade(alembic_cfg, "head")
    cols = {c["name"] for c in inspect(engine).get_columns("payments")}
    assert cols == {
        "id",
        "group_id",
        "from_member_id",
        "to_member_id",
        "amount_cents",
        "created_at",
    }


def test_migration_matches_orm_model(alembic_cfg, engine):
    command.upgrade(alembic_cfg, "head")
    migrated = {c["name"] for c in inspect(engine).get_columns("payments")}
    modelled = set(Base.metadata.tables["payments"].columns.keys())
    assert migrated == modelled


def test_downgrade_removes_payments_table(alembic_cfg, engine):
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    assert "payments" not in inspect(engine).get_table_names()


def test_valid_payment_gets_created_at(alembic_cfg, engine):
    command.upgrade(alembic_cfg, "head")
    with engine.begin() as conn:
        _insert(conn, 1, 2, 2000)
        created = conn.execute(text("SELECT created_at FROM payments")).scalar_one()
    assert created is not None


@pytest.mark.parametrize(
    "from_id,to_id,amount",
    [(1, 2, 0), (1, 2, -500), (3, 3, 100)],
    ids=["zero-amount", "negative-amount", "pay-yourself"],
)
def test_invalid_payment_rejected(alembic_cfg, engine, from_id, to_id, amount):
    command.upgrade(alembic_cfg, "head")
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _insert(conn, from_id, to_id, amount)
