"""Database access for payments. The API layer calls these; no business rules here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Payment


def create_payment(
    session: Session, group_id: int, from_member_id: int, to_member_id: int, amount_cents: int
) -> Payment:
    payment = Payment(
        group_id=group_id,
        from_member_id=from_member_id,
        to_member_id=to_member_id,
        amount_cents=amount_cents,
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


def list_payments(session: Session, group_id: int) -> list[Payment]:
    stmt = select(Payment).where(Payment.group_id == group_id).order_by(Payment.id)
    return list(session.scalars(stmt))


def delete_payment(session: Session, payment_id: int) -> bool:
    payment = session.get(Payment, payment_id)
    if payment is None:
        return False
    session.delete(payment)
    session.commit()
    return True
