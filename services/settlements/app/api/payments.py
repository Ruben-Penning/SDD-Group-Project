"""Payments routes: record, list and undo a settle-up payment."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import payments_repo
from app.db.session import get_session
from app.domain.payments import InvalidPaymentError, validate_payment

router = APIRouter(tags=["payments"])

SessionDep = Annotated[Session, Depends(get_session)]


class PaymentIn(BaseModel):
    from_member_id: int
    to_member_id: int
    amount_cents: int


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    from_member_id: int
    to_member_id: int
    amount_cents: int
    created_at: datetime


@router.post(
    "/groups/{group_id}/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED
)
def record_payment(group_id: int, body: PaymentIn, session: SessionDep) -> PaymentOut:
    try:
        validate_payment(body.from_member_id, body.to_member_id, body.amount_cents)
    except InvalidPaymentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    payment = payments_repo.create_payment(
        session, group_id, body.from_member_id, body.to_member_id, body.amount_cents
    )
    return PaymentOut.model_validate(payment)


@router.get("/groups/{group_id}/payments", response_model=list[PaymentOut])
def list_payments(group_id: int, session: SessionDep) -> list[PaymentOut]:
    return [PaymentOut.model_validate(p) for p in payments_repo.list_payments(session, group_id)]


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def undo_payment(payment_id: int, session: SessionDep) -> Response:
    if not payments_repo.delete_payment(session, payment_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
