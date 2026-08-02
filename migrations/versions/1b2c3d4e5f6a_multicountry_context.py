"""multi-country practice context

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
"""
from alembic import op
import sqlalchemy as sa
revision="1b2c3d4e5f6a"
down_revision="0a1b2c3d4e5f"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("facility", sa.Column("country_code", sa.String(length=3), nullable=False, server_default="TZ"))
    op.create_index("ix_facility_country_code", "facility", ["country_code"])
    op.add_column("patient", sa.Column("country_code", sa.String(length=3), nullable=False, server_default="TZ"))
    op.create_index("ix_patient_country_code", "patient", ["country_code"])
def downgrade():
    op.drop_index("ix_patient_country_code", table_name="patient")
    op.drop_column("patient", "country_code")
    op.drop_index("ix_facility_country_code", table_name="facility")
    op.drop_column("facility", "country_code")
