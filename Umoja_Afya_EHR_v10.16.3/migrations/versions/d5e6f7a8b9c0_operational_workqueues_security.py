"""Add operational workqueues, walk-ins, duty rosters and session controls.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_account") as batch:
        batch.add_column(sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "service_point",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_point_id", sa.String(80), nullable=False),
        sa.Column("facility_id", sa.Integer(), sa.ForeignKey("facility.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("department", sa.String(120), nullable=False),
        sa.Column("clinic", sa.String(160), nullable=False),
        sa.Column("room", sa.String(80), nullable=True),
        sa.Column("scheduling_model", sa.String(80), nullable=False, server_default="PUBLIC_DUTY_ROSTER"),
        sa.Column("queue_capacity", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("facility_id", "code", name="uq_service_point_facility_code"),
        sa.UniqueConstraint("service_point_id"),
    )
    op.create_index("ix_service_point_service_point_id", "service_point", ["service_point_id"])
    op.create_index("ix_service_point_facility_id", "service_point", ["facility_id"])
    op.create_index("ix_service_point_code", "service_point", ["code"])
    op.create_index("ix_service_point_department", "service_point", ["department"])
    op.create_index("ix_service_point_clinic", "service_point", ["clinic"])

    op.create_table(
        "duty_roster",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("roster_id", sa.String(80), nullable=False),
        sa.Column("service_point_id", sa.Integer(), sa.ForeignKey("service_point.id", ondelete="CASCADE"), nullable=False),
        sa.Column("roster_date", sa.Date(), nullable=False),
        sa.Column("shift_start", sa.Time(), nullable=False),
        sa.Column("shift_end", sa.Time(), nullable=False),
        sa.Column("team_name", sa.String(160), nullable=False),
        sa.Column("lead_provider", sa.String(160), nullable=True),
        sa.Column("staff_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(40), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("service_point_id", "roster_date", "shift_start", name="uq_duty_roster_shift"),
        sa.UniqueConstraint("roster_id"),
    )
    op.create_index("ix_duty_roster_roster_id", "duty_roster", ["roster_id"])
    op.create_index("ix_duty_roster_service_point_id", "duty_roster", ["service_point_id"])
    op.create_index("ix_duty_roster_roster_date", "duty_roster", ["roster_date"])
    op.create_index("ix_duty_roster_status", "duty_roster", ["status"])

    op.create_table(
        "walk_in_episode",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("walkin_id", sa.String(80), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=True),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounter.id"), nullable=True),
        sa.Column("facility_id", sa.Integer(), sa.ForeignKey("facility.id"), nullable=False),
        sa.Column("service_point_id", sa.Integer(), sa.ForeignKey("service_point.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(80), nullable=False, server_default="SEARCH_OR_CREATE"),
        sa.Column("coverage_route", sa.String(80), nullable=True),
        sa.Column("queue_name", sa.String(160), nullable=True),
        sa.Column("created_by", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("walkin_id"),
    )
    for column in ["walkin_id", "patient_id", "encounter_id", "facility_id", "service_point_id", "status", "created_at"]:
        op.create_index(f"ix_walk_in_episode_{column}", "walk_in_episode", [column])

    op.create_table(
        "work_queue_definition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("queue_id", sa.String(80), nullable=False),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("service_area", sa.String(120), nullable=False),
        sa.Column("owner_team", sa.String(160), nullable=False),
        sa.Column("facility_code", sa.String(80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("routing_rule_json", sa.Text(), nullable=True),
        sa.Column("sla_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("queue_id"),
        sa.UniqueConstraint("code"),
    )
    for column in ["queue_id", "code", "category", "service_area", "owner_team", "facility_code", "active"]:
        op.create_index(f"ix_work_queue_definition_{column}", "work_queue_definition", [column])

    op.create_table(
        "work_queue_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.String(80), nullable=False),
        sa.Column("queue_definition_id", sa.Integer(), sa.ForeignKey("work_queue_definition.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=True),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounter.id"), nullable=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointment.id"), nullable=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(40), nullable=False, server_default="ROUTINE"),
        sa.Column("status", sa.String(40), nullable=False, server_default="ACTIVE"),
        sa.Column("assigned_to", sa.String(160), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deferred_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(160), nullable=False, server_default="Workflow Engine"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("item_id"),
    )
    for column in ["item_id", "queue_definition_id", "patient_id", "encounter_id", "appointment_id", "priority", "status", "assigned_to", "due_at", "created_at"]:
        op.create_index(f"ix_work_queue_item_{column}", "work_queue_item", [column])

    op.create_table(
        "work_queue_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(80), nullable=False),
        sa.Column("work_queue_item_id", sa.Integer(), sa.ForeignKey("work_queue_item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("status_before", sa.String(40), nullable=True),
        sa.Column("status_after", sa.String(40), nullable=True),
        sa.Column("actor", sa.String(160), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id"),
    )
    for column in ["event_id", "work_queue_item_id", "action", "occurred_at"]:
        op.create_index(f"ix_work_queue_event_{column}", "work_queue_event", [column])

    op.create_table(
        "workflow_notification",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notification_id", sa.String(80), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("facility_code", sa.String(80), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=True),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounter.id"), nullable=True),
        sa.Column("audience", sa.String(160), nullable=False, server_default="CLINICAL_WORKFLOW"),
        sa.Column("message_en", sa.String(400), nullable=False),
        sa.Column("message_sw", sa.String(400), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("notification_id"),
    )
    for column in ["notification_id", "event_type", "facility_code", "patient_id", "encounter_id", "created_at"]:
        op.create_index(f"ix_workflow_notification_{column}", "workflow_notification", [column])

    op.create_table(
        "user_session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(80), nullable=False),
        sa.Column("user_account_id", sa.Integer(), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_jti", sa.String(96), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_ip", sa.String(80), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.UniqueConstraint("session_id"),
        sa.UniqueConstraint("token_jti"),
    )
    for column in ["session_id", "user_account_id", "token_jti", "expires_at"]:
        op.create_index(f"ix_user_session_{column}", "user_session", [column])

    op.create_table(
        "break_glass_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("access_id", sa.String(80), nullable=False),
        sa.Column("user_account_id", sa.Integer(), sa.ForeignKey("user_account.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounter.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("emergency_type", sa.String(80), nullable=False, server_default="PATIENT_SAFETY"),
        sa.Column("status", sa.String(40), nullable=False, server_default="ACTIVE"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("access_id"),
    )
    for column in ["access_id", "user_account_id", "patient_id", "encounter_id", "status", "expires_at"]:
        op.create_index(f"ix_break_glass_access_{column}", "break_glass_access", [column])


def downgrade() -> None:
    for table in ["break_glass_access", "user_session", "workflow_notification", "work_queue_event", "work_queue_item", "work_queue_definition", "walk_in_episode", "duty_roster", "service_point"]:
        op.drop_table(table)
    with op.batch_alter_table("user_account") as batch:
        batch.drop_column("must_change_password")
        batch.drop_column("password_changed_at")
        batch.drop_column("locked_until")
        batch.drop_column("failed_login_count")
