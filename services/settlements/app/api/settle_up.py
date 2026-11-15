"""Settle-up route: the fewest transfers that clear a group's current balances."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.balances import load_balances
from app.db.session import get_session
from app.domain.settle_up import settle_up

router = APIRouter(tags=["settle-up"])

SessionDep = Annotated[Session, Depends(get_session)]


class TransferOut(BaseModel):
    from_member_id: int
    to_member_id: int
    amount_cents: int


class SettleUpOut(BaseModel):
    group_id: int
    transfers: list[TransferOut]


@router.get("/groups/{group_id}/settle-up", response_model=SettleUpOut)
def get_settle_up(group_id: int, session: SessionDep) -> SettleUpOut:
    balances = load_balances(group_id, session)
    try:
        transfers = settle_up(balances)
    except ValueError as exc:
        # Only possible if the ledger from expenses-service does not sum to zero.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Balances from expenses-service do not add up; cannot settle up",
        ) from exc
    return SettleUpOut(
        group_id=group_id,
        transfers=[
            TransferOut(from_member_id=f, to_member_id=t, amount_cents=c) for f, t, c in transfers
        ],
    )
