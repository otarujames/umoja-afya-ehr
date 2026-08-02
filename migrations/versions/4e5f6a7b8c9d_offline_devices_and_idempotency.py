"""offline devices and idempotent browser outbox receipts

Revision ID: 4e5f6a7b8c9d
Revises: 3d4e5f6a7b8c
"""
from alembic import op
import sqlalchemy as sa


revision = "4e5f6a7b8c9d"
down_revision = "3d4e5f6a7b8c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "offline_device",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=80), nullable=False),
        sa.Column("user_account_id", sa.Integer(), nullable=False),
        sa.Column("device_name", sa.String(length=160), nullable=False),
        sa.Column("platform", sa.String(length=160), nullable=True),
        sa.Column("app_version", sa.String(length=40), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_account_id"], ["user_account.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_account_id", "device_id", name="uq_offline_device_user_device"),
    )
    op.create_index("ix_offline_device_device_id", "offline_device", ["device_id"])
    op.create_index("ix_offline_device_user_account_id", "offline_device", ["user_account_id"])

    op.create_table(
        "idempotency_receipt",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("request_method", sa.String(length=12), nullable=False),
        sa.Column("request_path", sa.String(length=500), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_content_type", sa.String(length=160), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("device_id", sa.String(length=80), nullable=True),
        sa.Column("offline_created_at", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actor_user_id", "idempotency_key", name="uq_idempotency_actor_key"),
    )
    op.create_index("ix_idempotency_receipt_actor_user_id", "idempotency_receipt", ["actor_user_id"])
    op.create_index("ix_idempotency_receipt_idempotency_key", "idempotency_receipt", ["idempotency_key"])
    op.create_index("ix_idempotency_receipt_status", "idempotency_receipt", ["status"])
    op.create_index("ix_idempotency_receipt_device_id", "idempotency_receipt", ["device_id"])


def downgrade():
    op.drop_index("ix_idempotency_receipt_device_id", table_name="idempotency_receipt")
    op.drop_index("ix_idempotency_receipt_status", table_name="idempotency_receipt")
    op.drop_index("ix_idempotency_receipt_idempotency_key", table_name="idempotency_receipt")
    op.drop_index("ix_idempotency_receipt_actor_user_id", table_name="idempotency_receipt")
    op.drop_table("idempotency_receipt")
    op.drop_index("ix_offline_device_user_account_id", table_name="offline_device")
    op.drop_index("ix_offline_device_device_id", table_name="offline_device")
    op.drop_table("offline_device")
