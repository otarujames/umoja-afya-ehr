"""record context, order catalog, messages, event reversal and devices

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column in [
        sa.Column("hfr_code", sa.String(length=80), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("council", sa.String(length=120), nullable=True),
        sa.Column("ownership_category", sa.String(length=80), nullable=False, server_default="Public"),
        sa.Column("ownership_authority", sa.String(length=120), nullable=True),
        sa.Column("hierarchy_level", sa.String(length=80), nullable=True),
        sa.Column("parent_code", sa.String(length=80), nullable=True),
        sa.Column("source_system", sa.String(length=80), nullable=False, server_default="Umoja Afya"),
    ]:
        op.add_column("facility", column)
    op.create_index("ix_facility_hfr_code", "facility", ["hfr_code"], unique=True)
    op.create_index("ix_facility_region", "facility", ["region"])
    op.create_index("ix_facility_council", "facility", ["council"])
    op.create_index("ix_facility_ownership_category", "facility", ["ownership_category"])
    op.create_index("ix_facility_ownership_authority", "facility", ["ownership_authority"])
    op.create_index("ix_facility_hierarchy_level", "facility", ["hierarchy_level"])
    op.create_index("ix_facility_parent_code", "facility", ["parent_code"])

    op.add_column("patient", sa.Column("record_status", sa.String(length=40), nullable=False, server_default="ACTIVE"))
    op.add_column("patient", sa.Column("deceased_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("patient", sa.Column("deceased_location", sa.String(length=160), nullable=True))
    op.add_column("patient", sa.Column("deceased_cause", sa.Text(), nullable=True))
    op.add_column("patient", sa.Column("death_certificate_number", sa.String(length=120), nullable=True))
    op.add_column("patient", sa.Column("expired_by", sa.String(length=160), nullable=True))
    op.create_index("ix_patient_record_status", "patient", ["record_status"])

    op.create_table(
        "order_catalog_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("orderable_code", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("subcategory", sa.String(120), nullable=True),
        sa.Column("clinical", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("department", sa.String(120), nullable=True),
        sa.Column("specimen", sa.String(120), nullable=True),
        sa.Column("default_priority", sa.String(40), nullable=False, server_default="ROUTINE"),
        sa.Column("default_instructions", sa.Text(), nullable=True),
        sa.Column("synonyms", sa.Text(), nullable=True),
        sa.Column("units", sa.String(120), nullable=True),
        sa.Column("route", sa.String(80), nullable=True),
        sa.Column("requires_reason", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_cosign", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, cols, unique in [
        ("ix_order_catalog_item_orderable_code", ["orderable_code"], True),
        ("ix_order_catalog_item_display_name", ["display_name"], False),
        ("ix_order_catalog_item_category", ["category"], False),
        ("ix_order_catalog_item_subcategory", ["subcategory"], False),
        ("ix_order_catalog_item_clinical", ["clinical"], False),
        ("ix_order_catalog_item_department", ["department"], False),
        ("ix_order_catalog_item_active", ["active"], False),
    ]: op.create_index(name, "order_catalog_item", cols, unique=unique)

    op.create_table(
        "user_message",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.String(80), nullable=False),
        sa.Column("thread_id", sa.String(80), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=True),
        sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounter.id"), nullable=True),
        sa.Column("subject", sa.String(240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(40), nullable=False, server_default="ROUTINE"),
        sa.Column("status", sa.String(40), nullable=False, server_default="UNREAD"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    for name, cols, unique in [
        ("ix_user_message_message_id", ["message_id"], True), ("ix_user_message_thread_id", ["thread_id"], False),
        ("ix_user_message_sender_user_id", ["sender_user_id"], False), ("ix_user_message_recipient_user_id", ["recipient_user_id"], False),
        ("ix_user_message_patient_id", ["patient_id"], False), ("ix_user_message_encounter_id", ["encounter_id"], False),
        ("ix_user_message_priority", ["priority"], False), ("ix_user_message_status", ["status"], False), ("ix_user_message_sent_at", ["sent_at"], False),
    ]: op.create_index(name, "user_message", cols, unique=unique)

    op.create_table(
        "managed_event",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_id", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False), sa.Column("entity_id", sa.String(120), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=True), sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounter.id"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False), sa.Column("status_before", sa.String(120), nullable=True), sa.Column("status_after", sa.String(120), nullable=True),
        sa.Column("actor", sa.String(160), nullable=False), sa.Column("reason", sa.Text(), nullable=True), sa.Column("reversible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reversed_by_event_id", sa.String(80), nullable=True), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("metadata_json", sa.Text(), nullable=True),
    )
    for name, cols, unique in [
        ("ix_managed_event_event_id", ["event_id"], True), ("ix_managed_event_entity_type", ["entity_type"], False), ("ix_managed_event_entity_id", ["entity_id"], False),
        ("ix_managed_event_patient_id", ["patient_id"], False), ("ix_managed_event_encounter_id", ["encounter_id"], False), ("ix_managed_event_action", ["action"], False),
        ("ix_managed_event_reversible", ["reversible"], False), ("ix_managed_event_reversed_by_event_id", ["reversed_by_event_id"], False), ("ix_managed_event_occurred_at", ["occurred_at"], False),
    ]: op.create_index(name, "managed_event", cols, unique=unique)

    op.create_table(
        "device_endpoint",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("device_id", sa.String(80), nullable=False), sa.Column("facility_code", sa.String(80), nullable=False),
        sa.Column("unit", sa.String(120), nullable=False), sa.Column("room", sa.String(80), nullable=True), sa.Column("bed_label", sa.String(80), nullable=True),
        sa.Column("name", sa.String(180), nullable=False), sa.Column("device_type", sa.String(100), nullable=False), sa.Column("manufacturer", sa.String(120), nullable=True),
        sa.Column("model", sa.String(120), nullable=True), sa.Column("protocol", sa.String(80), nullable=False, server_default="FHIR_OBSERVATION"),
        sa.Column("status", sa.String(40), nullable=False, server_default="ONLINE"), sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    for name, cols, unique in [
        ("ix_device_endpoint_device_id", ["device_id"], True), ("ix_device_endpoint_facility_code", ["facility_code"], False), ("ix_device_endpoint_unit", ["unit"], False),
        ("ix_device_endpoint_device_type", ["device_type"], False), ("ix_device_endpoint_status", ["status"], False), ("ix_device_endpoint_active", ["active"], False),
    ]: op.create_index(name, "device_endpoint", cols, unique=unique)

    op.create_table(
        "device_reading",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("reading_id", sa.String(80), nullable=False),
        sa.Column("device_endpoint_id", sa.Integer(), sa.ForeignKey("device_endpoint.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patient.id"), nullable=False), sa.Column("encounter_id", sa.Integer(), sa.ForeignKey("encounter.id"), nullable=False),
        sa.Column("flowsheet_id", sa.Integer(), sa.ForeignKey("flowsheet.id"), nullable=True), sa.Column("parameter_code", sa.String(100), nullable=False),
        sa.Column("parameter_name", sa.String(180), nullable=False), sa.Column("numeric_value", sa.Float(), nullable=True), sa.Column("text_value", sa.String(255), nullable=True),
        sa.Column("unit", sa.String(80), nullable=True), sa.Column("quality", sa.String(40), nullable=False, server_default="VALID"),
        sa.Column("source_message_id", sa.String(160), nullable=True), sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False), sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, cols, unique in [
        ("ix_device_reading_reading_id", ["reading_id"], True), ("ix_device_reading_device_endpoint_id", ["device_endpoint_id"], False),
        ("ix_device_reading_patient_id", ["patient_id"], False), ("ix_device_reading_encounter_id", ["encounter_id"], False),
        ("ix_device_reading_flowsheet_id", ["flowsheet_id"], False), ("ix_device_reading_parameter_code", ["parameter_code"], False),
        ("ix_device_reading_source_message_id", ["source_message_id"], False), ("ix_device_reading_recorded_at", ["recorded_at"], False),
    ]: op.create_index(name, "device_reading", cols, unique=unique)


def downgrade() -> None:
    op.drop_table("device_reading")
    op.drop_table("device_endpoint")
    op.drop_table("managed_event")
    op.drop_table("user_message")
    op.drop_table("order_catalog_item")
    op.drop_index("ix_patient_record_status", table_name="patient")
    for col in ["expired_by", "death_certificate_number", "deceased_cause", "deceased_location", "deceased_at", "record_status"]:
        op.drop_column("patient", col)
    for name in ["ix_facility_parent_code", "ix_facility_hierarchy_level", "ix_facility_ownership_authority", "ix_facility_ownership_category", "ix_facility_council", "ix_facility_region", "ix_facility_hfr_code"]:
        op.drop_index(name, table_name="facility")
    for col in ["source_system", "parent_code", "hierarchy_level", "ownership_authority", "ownership_category", "council", "region", "hfr_code"]:
        op.drop_column("facility", col)
