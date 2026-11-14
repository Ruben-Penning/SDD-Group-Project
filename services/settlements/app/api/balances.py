"""Balances route: the ledger from expenses-service minus recorded payments."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.clients import ledger
from app.db import payments_repo
from app.db.session import get_session
from app.domain.balances import current_balances

router = APIRouter(tags=["balances"])

SessionDep = Annotated[Session, Depends(get_session)]


class MemberBalance(BaseModel):
    member_id: int
    balance_cents: int


class BalancesOut(BaseModel):
    group_id: int
    balances: list[MemberBalance]


@router.get("/groups/{group_id}/balances", response_model=BalancesOut)
def get_balances(group_id: int, session: SessionDep) -> BalancesOut:
    # Raises ExpensesUnavailableError (503) or GroupNotFoundError (404); see app/main.py.
    net = ledger.fetch_ledger(group_id)
    payments = [
        (p.from_member_id, p.to_member_id, p.amount_cents)
        for p in payments_repo.list_payments(session, group_id)
    ]
    balances = current_balances(net, payments)
    return BalancesOut(
        group_id=group_id,
        balances=[MemberBalance(member_id=m, balance_cents=b) for m, b in sorted(balances.items())],
    )
