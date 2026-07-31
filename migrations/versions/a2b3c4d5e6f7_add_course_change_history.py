"""add order and appointment course change history

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-28
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_status_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=80), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("status_before", sa.String(length=80), nullable=False),
        sa.Column("status_after", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["clinical_order.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_order_status_event_event_id"), "order_status_event", ["event_id"], unique=True)
    op.create_index(op.f("ix_order_status_event_order_id"), "order_status_event", ["order_id"], unique=False)
    op.create_table(
        "appointment_status_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(length=80), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("status_before", sa.String(length=80), nullable=False),
        sa.Column("status_after", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointment.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_appointment_status_event_appointment_id"), "appointment_status_event", ["appointment_id"], unique=False)
    op.create_index(op.f("ix_appointment_status_event_event_id"), "appointment_status_event", ["event_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_appointment_status_event_event_id"), table_name="appointment_status_event")
    op.drop_index(op.f("ix_appointment_status_event_appointment_id"), table_name="appointment_status_event")
    op.drop_table("appointment_status_event")
    op.drop_index(op.f("ix_order_status_event_order_id"), table_name="order_status_event")
    op.drop_index(op.f("ix_order_status_event_event_id"), table_name="order_status_event")
    op.drop_table("order_status_event")
