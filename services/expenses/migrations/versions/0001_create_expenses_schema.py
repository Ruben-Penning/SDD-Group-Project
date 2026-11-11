"""create groups, members, expenses and expense_shares tables

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )

    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("group_id", "name", name="uq_members_group_name"),
    )
    op.create_index("ix_members_group_id", "members", ["group_id"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("paid_by_member_id", sa.Integer(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_expenses_amount_positive"),
    )
    op.create_index("ix_expenses_group_id", "expenses", ["group_id"])

    op.create_table(
        "expense_shares",
        sa.Column(
            "expense_id",
            sa.Integer(),
            sa.ForeignKey("expenses.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id"), primary_key=True),
        sa.Column("share_cents", sa.Integer(), nullable=False),
        sa.CheckConstraint("share_cents >= 0", name="ck_expense_shares_non_negative"),
    )


def downgrade() -> None:
    op.drop_table("expense_shares")
    op.drop_index("ix_expenses_group_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_members_group_id", table_name="members")
    op.drop_table("members")
    op.drop_table("groups")
