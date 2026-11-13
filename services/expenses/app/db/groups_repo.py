"""Database access for groups and members. The API layer calls these; no business rules here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Group, Member


def create_group(session: Session, name: str) -> Group:
    group = Group(name=name)
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


def list_groups(session: Session) -> list[Group]:
    return list(session.scalars(select(Group).order_by(Group.id)))


def get_group(session: Session, group_id: int) -> Group | None:
    return session.get(Group, group_id)


def list_members(session: Session, group_id: int) -> list[Member]:
    stmt = select(Member).where(Member.group_id == group_id).order_by(Member.id)
    return list(session.scalars(stmt))


def add_member(session: Session, group_id: int, name: str) -> Member:
    member = Member(group_id=group_id, name=name)
    session.add(member)
    session.commit()
    session.refresh(member)
    return member
