"""Migrations run against a throwaway SQLite file, never Azure."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.models import Base

SERVICE_ROOT = Path(__file__).resolve().parents[1]
TABLES = {"groups", "members", "expenses", "expense_shares"}


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

    # SQLite only enforces foreign keys when asked to (SQL Server always does).
    @event.listens_for(eng, "connect")
    def _enable_foreign_keys(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    yield eng
    eng.dispose()


@pytest.fixture
def migrated(alembic_cfg, engine):
    command.upgrade(alembic_cfg, "head")
    return engine


def _seed(conn):
    """One group with two members, Ana and Ben."""
    conn.execute(text("INSERT INTO groups (id, name) VALUES (1, 'Trip')"))
    conn.execute(
        text("INSERT INTO members (id, group_id, name) VALUES (1, 1, 'Ana'), (2, 1, 'Ben')")
    )


def _add_expense(conn, amount_cents=6000):
    conn.execute(
        text(
            "INSERT INTO expenses (id, group_id, paid_by_member_id, description, amount_cents) "
            "VALUES (1, 1, 1, 'Dinner', :a)"
        ),
        {"a": amount_cents},
    )


def test_upgrade_creates_all_tables(migrated):
    assert TABLES <= set(inspect(migrated).get_table_names())


def test_migration_matches_orm_model(migrated):
    inspector = inspect(migrated)
    for table in TABLES:
        migrated_cols = {c["name"] for c in inspector.get_columns(table)}
        modelled_cols = set(Base.metadata.tables[table].columns.keys())
        assert migrated_cols == modelled_cols, table


def test_downgrade_removes_all_tables(alembic_cfg, migrated):
    command.downgrade(alembic_cfg, "base")
    assert not TABLES & set(inspect(migrated).get_table_names())


def test_valid_expense_with_shares(migrated):
    with migrated.begin() as conn:
        _seed(conn)
        _add_expense(conn)
        conn.execute(
            text(
                "INSERT INTO expense_shares (expense_id, member_id, share_cents) "
                "VALUES (1, 1, 3000), (1, 2, 3000)"
            )
        )
        created = conn.execute(text("SELECT created_at FROM expenses")).scalar_one()
        total = conn.execute(text("SELECT SUM(share_cents) FROM expense_shares")).scalar_one()
    assert created is not None
    assert total == 6000


def test_deleting_expense_deletes_its_shares(migrated):
    with migrated.begin() as conn:
        _seed(conn)
        _add_expense(conn)
        conn.execute(
            text(
                "INSERT INTO expense_shares (expense_id, member_id, share_cents) "
                "VALUES (1, 2, 6000)"
            )
        )
        conn.execute(text("DELETE FROM expenses WHERE id = 1"))
        remaining = conn.execute(text("SELECT COUNT(*) FROM expense_shares")).scalar_one()
    assert remaining == 0


@pytest.mark.parametrize("amount", [0, -500], ids=["zero-amount", "negative-amount"])
def test_expense_amount_must_be_positive(migrated, amount):
    with pytest.raises(IntegrityError), migrated.begin() as conn:
        _seed(conn)
        _add_expense(conn, amount_cents=amount)


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO members (group_id, name) VALUES (1, 'Ana')",
        "INSERT INTO members (group_id, name) VALUES (99, 'Cleo')",
        "INSERT INTO expense_shares (expense_id, member_id, share_cents) VALUES (1, 2, -1)",
        "INSERT INTO expense_shares (expense_id, member_id, share_cents) VALUES (1, 99, 100)",
        "INSERT INTO expense_shares (expense_id, member_id, share_cents) "
        "VALUES (1, 2, 100), (1, 2, 200)",
    ],
    ids=[
        "duplicate-member-name",
        "member-of-unknown-group",
        "negative-share",
        "share-for-unknown-member",
        "two-shares-same-member",
    ],
)
def test_invalid_rows_rejected(migrated, sql):
    with pytest.raises(IntegrityError), migrated.begin() as conn:
        _seed(conn)
        _add_expense(conn)
        conn.execute(text(sql))
