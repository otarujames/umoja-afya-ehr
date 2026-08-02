"""admin-managed user profile photos

Revision ID: 5f6a7b8c9d0e
Revises: 4e5f6a7b8c9d
"""
from alembic import op
import sqlalchemy as sa


revision = "5f6a7b8c9d0e"
down_revision = "4e5f6a7b8c9d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_account", sa.Column("profile_photo_data", sa.LargeBinary(), nullable=True))
    op.add_column("user_account", sa.Column("profile_photo_mime", sa.String(length=50), nullable=True))
    op.add_column("user_account", sa.Column("profile_photo_sha256", sa.String(length=64), nullable=True))
    op.add_column("user_account", sa.Column("profile_photo_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_account", sa.Column("profile_photo_updated_by", sa.String(length=180), nullable=True))


def downgrade():
    op.drop_column("user_account", "profile_photo_updated_by")
    op.drop_column("user_account", "profile_photo_updated_at")
    op.drop_column("user_account", "profile_photo_sha256")
    op.drop_column("user_account", "profile_photo_mime")
    op.drop_column("user_account", "profile_photo_data")
