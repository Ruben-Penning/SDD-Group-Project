"""Groups and members routes: create and list groups, add and list members."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import groups_repo
from app.db.models import Group
from app.db.session import get_session
from app.domain.groups import InvalidGroupError, check_member_name_is_new, clean_name

router = APIRouter(tags=["groups"])

SessionDep = Annotated[Session, Depends(get_session)]


class NameIn(BaseModel):
    name: str


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    name: str


def existing_group(session: Session, group_id: int) -> Group:
    group = groups_repo.get_group(session, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


@router.get("/groups", response_model=list[GroupOut])
def list_groups(session: SessionDep) -> list[GroupOut]:
    return [GroupOut.model_validate(g) for g in groups_repo.list_groups(session)]


@router.post("/groups", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(body: NameIn, session: SessionDep) -> GroupOut:
    try:
        name = clean_name(body.name, "group")
    except InvalidGroupError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return GroupOut.model_validate(groups_repo.create_group(session, name))


@router.get("/groups/{group_id}", response_model=GroupOut)
def get_group(group_id: int, session: SessionDep) -> GroupOut:
    return GroupOut.model_validate(existing_group(session, group_id))


@router.get("/groups/{group_id}/members", response_model=list[MemberOut])
def list_members(group_id: int, session: SessionDep) -> list[MemberOut]:
    existing_group(session, group_id)
    return [MemberOut.model_validate(m) for m in groups_repo.list_members(session, group_id)]


@router.post(
    "/groups/{group_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED
)
def add_member(group_id: int, body: NameIn, session: SessionDep) -> MemberOut:
    existing_group(session, group_id)
    try:
        name = clean_name(body.name, "member")
        existing_names = [m.name for m in groups_repo.list_members(session, group_id)]
        check_member_name_is_new(name, existing_names)
        member = groups_repo.add_member(session, group_id, name)
    except InvalidGroupError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except IntegrityError as exc:
        # Two requests adding the same name at once: the unique constraint catches the second.
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"a member named {name!r} already exists in this group",
        ) from exc
    return MemberOut.model_validate(member)
