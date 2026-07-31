"""add per-user function department and facility access matrix

Revision ID: f1a2b3c4d5e6
Revises: ec1dda2c4a2a
Create Date: 2026-07-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "ec1dda2c4a2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_access_grant",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grant_id", sa.String(length=80), nullable=False),
        sa.Column("user_account_id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("scope_code", sa.String(length=160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("granted_by", sa.String(length=180), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_account_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grant_id"),
        sa.UniqueConstraint("user_account_id", "scope_type", "scope_code", name="uq_user_access_grant"),
    )
    op.create_index(op.f("ix_user_access_grant_grant_id"), "user_access_grant", ["grant_id"], unique=True)
    op.create_index(op.f("ix_user_access_grant_scope_code"), "user_access_grant", ["scope_code"], unique=False)
    op.create_index(op.f("ix_user_access_grant_scope_type"), "user_access_grant", ["scope_type"], unique=False)
    op.create_index(op.f("ix_user_access_grant_user_account_id"), "user_access_grant", ["user_account_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_access_grant_user_account_id"), table_name="user_access_grant")
    op.drop_index(op.f("ix_user_access_grant_scope_type"), table_name="user_access_grant")
    op.drop_index(op.f("ix_user_access_grant_scope_code"), table_name="user_access_grant")
    op.drop_index(op.f("ix_user_access_grant_grant_id"), table_name="user_access_grant")
    op.drop_table("user_access_grant")
