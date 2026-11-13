"""ORM models for expenses-db. Schema changes go through Alembic migrations."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Group(Base):
    """A group of people sharing expenses ("Lisbon trip")."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )


class Member(Base):
    """A person in a group. Names are unique within a group."""

    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_members_group_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class Expense(Base):
    """Something one member paid for the group ("Ana paid 60 EUR for dinner")."""

    __tablename__ = "expenses"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="ck_expenses_amount_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    paid_by_member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    # Python-side link only (no schema change): saving an expense saves its shares.
    shares: Mapped[list["ExpenseShare"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ExpenseShare.member_id"
    )


class ExpenseShare(Base):
    """How much of one expense a member owes. One row per member per expense.

    Deleting an expense deletes its shares. This is the only cascade: SQL Server
    rejects schemas with more than one cascade path to the same table.
    """

    __tablename__ = "expense_shares"
    __table_args__ = (CheckConstraint("share_cents >= 0", name="ck_expense_shares_non_negative"),)

    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True
    )
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), primary_key=True)
    share_cents: Mapped[int] = mapped_column(Integer, nullable=False)
