"""create payments table

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
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("from_member_id", sa.Integer(), nullable=False),
        sa.Column("to_member_id", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_payments_amount_positive"),
        sa.CheckConstraint("from_member_id <> to_member_id", name="ck_payments_distinct_members"),
    )
    op.create_index("ix_payments_group_id", "payments", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_group_id", table_name="payments")
    op.drop_table("payments")
