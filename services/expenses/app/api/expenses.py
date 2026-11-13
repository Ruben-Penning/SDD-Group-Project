"""Expenses routes: add an expense split equally, and list a group's expenses."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.groups import existing_group
from app.db import expenses_repo, groups_repo
from app.db.session import get_session
from app.domain.expenses import (
    InvalidExpenseError,
    check_members_in_group,
    clean_description,
    split_equally,
)

router = APIRouter(tags=["expenses"])

SessionDep = Annotated[Session, Depends(get_session)]


class ExpenseIn(BaseModel):
    description: str
    amount_cents: int
    paid_by_member_id: int
    member_ids: list[int]


class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    member_id: int
    share_cents: int


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    description: str
    amount_cents: int
    paid_by_member_id: int
    created_at: datetime
    shares: list[ShareOut]


@router.get("/groups/{group_id}/expenses", response_model=list[ExpenseOut])
def list_expenses(group_id: int, session: SessionDep) -> list[ExpenseOut]:
    existing_group(session, group_id)
    return [ExpenseOut.model_validate(e) for e in expenses_repo.list_expenses(session, group_id)]


@router.post(
    "/groups/{group_id}/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED
)
def add_expense(group_id: int, body: ExpenseIn, session: SessionDep) -> ExpenseOut:
    existing_group(session, group_id)
    group_member_ids = {m.id for m in groups_repo.list_members(session, group_id)}
    try:
        description = clean_description(body.description)
        check_members_in_group(body.paid_by_member_id, body.member_ids, group_member_ids)
        shares = split_equally(body.amount_cents, body.member_ids)
    except InvalidExpenseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    expense = expenses_repo.create_expense(
        session, group_id, description, body.amount_cents, body.paid_by_member_id, shares
    )
    return ExpenseOut.model_validate(expense)
