"""Ledger route: net paid minus owed per member. Called by settlements-service over HTTP."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.groups import existing_group
from app.db import expenses_repo, groups_repo
from app.db.session import get_session
from app.domain.ledger import ExpenseLine, compute_ledger

router = APIRouter(tags=["ledger"])

SessionDep = Annotated[Session, Depends(get_session)]


class BalanceOut(BaseModel):
    member_id: int
    net_cents: int


class LedgerOut(BaseModel):
    group_id: int
    balances: list[BalanceOut]


@router.get("/groups/{group_id}/ledger", response_model=LedgerOut)
def get_ledger(group_id: int, session: SessionDep) -> LedgerOut:
    existing_group(session, group_id)
    member_ids = [m.id for m in groups_repo.list_members(session, group_id)]
    expenses = [
        ExpenseLine(
            paid_by_member_id=e.paid_by_member_id,
            amount_cents=e.amount_cents,
            shares={s.member_id: s.share_cents for s in e.shares},
        )
        for e in expenses_repo.list_expenses(session, group_id)
    ]
    net = compute_ledger(member_ids, expenses)
    return LedgerOut(
        group_id=group_id,
        balances=[BalanceOut(member_id=m, net_cents=cents) for m, cents in net.items()],
    )
