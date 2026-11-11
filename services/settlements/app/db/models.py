"""ORM models for settlements-db. Schema changes go through Alembic migrations."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Payment(Base):
    """A recorded settle-up ("Ana paid Ben 20 EUR").

    group_id and the member ids point to expenses-db logically only:
    no foreign keys across databases.
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_payments_amount_positive"),
        CheckConstraint("from_member_id <> to_member_id", name="ck_payments_distinct_members"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    from_member_id: Mapped[int] = mapped_column(Integer, nullable=False)
    to_member_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
