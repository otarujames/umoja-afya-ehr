"""add front desk print, coverage verification and travel screening workflows

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "print_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=80), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("facility_code", sa.String(length=80), nullable=False),
        sa.Column("template_code", sa.String(length=100), nullable=False),
        sa.Column("template_name", sa.String(length=200), nullable=False),
        sa.Column("copies", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("printer_name", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounter.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    for name, cols, unique in [
        ("ix_print_job_job_id", ["job_id"], True),
        ("ix_print_job_patient_id", ["patient_id"], False),
        ("ix_print_job_encounter_id", ["encounter_id"], False),
        ("ix_print_job_facility_code", ["facility_code"], False),
        ("ix_print_job_template_code", ["template_code"], False),
        ("ix_print_job_status", ["status"], False),
        ("ix_print_job_created_at", ["created_at"], False),
    ]:
        op.create_index(name, "print_job", cols, unique=unique)

    op.create_table(
        "coverage_verification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("verification_id", sa.String(length=80), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("payer", sa.String(length=160), nullable=False),
        sa.Column("member_number", sa.String(length=160), nullable=True),
        sa.Column("service", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("response_code", sa.String(length=80), nullable=True),
        sa.Column("response_message", sa.Text(), nullable=True),
        sa.Column("copay_amount", sa.String(length=80), nullable=True),
        sa.Column("requested_by", sa.String(length=160), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounter.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("verification_id"),
    )
    for name, cols, unique in [
        ("ix_coverage_verification_verification_id", ["verification_id"], True),
        ("ix_coverage_verification_patient_id", ["patient_id"], False),
        ("ix_coverage_verification_encounter_id", ["encounter_id"], False),
        ("ix_coverage_verification_payer", ["payer"], False),
        ("ix_coverage_verification_status", ["status"], False),
        ("ix_coverage_verification_requested_at", ["requested_at"], False),
    ]:
        op.create_index(name, "coverage_verification", cols, unique=unique)

    op.create_table(
        "travel_screening",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("screening_id", sa.String(length=80), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("screening_type", sa.String(length=80), nullable=False),
        sa.Column("responses_json", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=40), nullable=False),
        sa.Column("disposition", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("completed_by", sa.String(length=160), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounter.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("screening_id"),
    )
    for name, cols, unique in [
        ("ix_travel_screening_screening_id", ["screening_id"], True),
        ("ix_travel_screening_patient_id", ["patient_id"], False),
        ("ix_travel_screening_encounter_id", ["encounter_id"], False),
        ("ix_travel_screening_risk_level", ["risk_level"], False),
        ("ix_travel_screening_status", ["status"], False),
        ("ix_travel_screening_completed_at", ["completed_at"], False),
    ]:
        op.create_index(name, "travel_screening", cols, unique=unique)


def downgrade() -> None:
    for table in ["travel_screening", "coverage_verification", "print_job"]:
        op.drop_table(table)
