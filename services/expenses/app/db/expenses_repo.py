"""Database access for expenses and their shares. No business rules here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Expense, ExpenseShare


def list_expenses(session: Session, group_id: int) -> list[Expense]:
    stmt = select(Expense).where(Expense.group_id == group_id).order_by(Expense.id)
    return list(session.scalars(stmt))


def create_expense(
    session: Session,
    group_id: int,
    description: str,
    amount_cents: int,
    paid_by_member_id: int,
    shares: dict[int, int],
) -> Expense:
    """Save the expense and one share row per member in a single commit."""
    expense = Expense(
        group_id=group_id,
        description=description,
        amount_cents=amount_cents,
        paid_by_member_id=paid_by_member_id,
        shares=[
            ExpenseShare(member_id=member_id, share_cents=share_cents)
            for member_id, share_cents in shares.items()
        ],
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def get_expense(session: Session, expense_id: int) -> Expense | None:
    return session.get(Expense, expense_id)


def update_expense(
    session: Session,
    expense: Expense,
    description: str,
    amount_cents: int,
    paid_by_member_id: int,
    shares: dict[int, int],
) -> Expense:
    """Overwrite the expense and replace all of its shares in a single commit."""
    expense.description = description
    expense.amount_cents = amount_cents
    expense.paid_by_member_id = paid_by_member_id
    # Clear first and flush, so the old share rows are deleted before the new ones are
    # inserted (a member can be in both, and (expense_id, member_id) is the primary key).
    expense.shares.clear()
    session.flush()
    expense.shares.extend(
        ExpenseShare(member_id=member_id, share_cents=share_cents)
        for member_id, share_cents in shares.items()
    )
    session.commit()
    session.refresh(expense)
    return expense


def delete_expense(session: Session, expense: Expense) -> None:
    """Delete the expense; its shares go with it."""
    session.delete(expense)
    session.commit()
