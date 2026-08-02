"""store ISO currency on charges, claims and payments

Revision ID: 3d4e5f6a7b8c
Revises: 2c3d4e5f6a7b
"""
from alembic import op
import sqlalchemy as sa


revision = "3d4e5f6a7b8c"
down_revision = "2c3d4e5f6a7b"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("charge", "claim", "payment"):
        op.add_column(table, sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="TZS"))
        op.execute(sa.text(f"""
            UPDATE {table}
               SET currency_code = CASE COALESCE(
                    (SELECT country_code FROM patient WHERE patient.id = {table}.patient_id), 'TZ')
                    WHEN 'KE' THEN 'KES'
                    WHEN 'NG' THEN 'NGN'
                    ELSE 'TZS'
               END
        """))


def downgrade():
    for table in ("payment", "claim", "charge"):
        op.drop_column(table, "currency_code")
