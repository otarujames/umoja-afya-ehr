"""defer patient portal from provider EHR release

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("portal_message")


def downgrade() -> None:
    op.create_table(
        "portal_message",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.String(length=80), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("direction", sa.String(length=40), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("sender", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_portal_message_message_id", "portal_message", ["message_id"], unique=True)
    op.create_index("ix_portal_message_patient_id", "portal_message", ["patient_id"], unique=False)
