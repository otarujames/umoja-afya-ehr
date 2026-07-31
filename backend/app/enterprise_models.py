from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def public_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


class UserAccount(Base):
    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("USR"))
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(180))
    role_code: Mapped[str] = mapped_column(String(80), index=True)
    facility_code: Mapped[str] = mapped_column(String(80), default="MNH-UPANGA")
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_mfa: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)


class UserAccessGrant(Base):
    __tablename__ = "user_access_grant"
    __table_args__ = (UniqueConstraint("user_account_id", "scope_type", "scope_code", name="uq_user_access_grant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    grant_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("GRANT"))
    user_account_id: Mapped[int] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    scope_type: Mapped[str] = mapped_column(String(40), index=True)
    scope_code: Mapped[str] = mapped_column(String(160), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_by: Mapped[str] = mapped_column(String(180), default="System Administrator")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)



class Appointment(Base):
    __tablename__ = "appointment"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("APT"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facility.id"), index=True)
    service: Mapped[str] = mapped_column(String(160), index=True)
    provider: Mapped[str | None] = mapped_column(String(160), nullable=True)
    appointment_type: Mapped[str] = mapped_column(String(80), default="OFFICE_VISIT")
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(80), default="SCHEDULED", index=True)
    arrival_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    referral_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(160), default="scheduler")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AppointmentStatusEvent(Base):
    __tablename__ = "appointment_status_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("APTEVT"))
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointment.id", ondelete="CASCADE"), index=True)
    status_before: Mapped[str] = mapped_column(String(80))
    status_after: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(160))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)



class Referral(Base):
    __tablename__ = "referral"

    id: Mapped[int] = mapped_column(primary_key=True)
    referral_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("REF"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    source_facility_code: Mapped[str] = mapped_column(String(80))
    destination_facility_code: Mapped[str] = mapped_column(String(80))
    service: Mapped[str] = mapped_column(String(160))
    priority: Mapped[str] = mapped_column(String(40), default="ROUTINE")
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="NEW", index=True)
    requested_by: Mapped[str] = mapped_column(String(160))
    accepted_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    appointment_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    closure_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Bed(Base):
    __tablename__ = "bed"

    id: Mapped[int] = mapped_column(primary_key=True)
    bed_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("BED"))
    facility_id: Mapped[int] = mapped_column(ForeignKey("facility.id"), index=True)
    unit: Mapped[str] = mapped_column(String(120), index=True)
    room: Mapped[str] = mapped_column(String(80))
    bed_label: Mapped[str] = mapped_column(String(80))
    bed_type: Mapped[str] = mapped_column(String(80), default="GENERAL")
    status: Mapped[str] = mapped_column(String(80), default="AVAILABLE", index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True, index=True)
    isolation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ClinicalNote(Base):
    __tablename__ = "clinical_note"

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("NOTE"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounter.id"), index=True)
    note_type: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(80), default="DRAFT", index=True)
    author: Mapped[str] = mapped_column(String(160))
    service: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    cosign_required: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_audio_session_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)


class MedicationOrder(Base):
    __tablename__ = "medication_order"

    id: Mapped[int] = mapped_column(primary_key=True)
    medication_order_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("MED"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounter.id"), index=True)
    medication_name: Mapped[str] = mapped_column(String(255))
    dose: Mapped[str] = mapped_column(String(80))
    route: Mapped[str] = mapped_column(String(80))
    frequency: Mapped[str] = mapped_column(String(80))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="ACTIVE", index=True)
    indication: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_by: Mapped[str] = mapped_column(String(160))
    verified_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MedicationAdministration(Base):
    __tablename__ = "medication_administration"

    id: Mapped[int] = mapped_column(primary_key=True)
    administration_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("MAR"))
    medication_order_id: Mapped[int] = mapped_column(ForeignKey("medication_order.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    action: Mapped[str] = mapped_column(String(80), default="GIVEN")
    dose_given: Mapped[str | None] = mapped_column(String(80), nullable=True)
    administered_by: Mapped[str] = mapped_column(String(160))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    barcode_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    administered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkItem(Base):
    __tablename__ = "work_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_item_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("TASK"))
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patient.id"), nullable=True, index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True, index=True)
    queue: Mapped[str] = mapped_column(String(120), index=True)
    task_type: Mapped[str] = mapped_column(String(120))
    subject: Mapped[str] = mapped_column(String(255))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(40), default="ROUTINE")
    status: Mapped[str] = mapped_column(String(80), default="OPEN", index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(160), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Charge(Base):
    __tablename__ = "charge"

    id: Mapped[int] = mapped_column(primary_key=True)
    charge_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("CHG"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounter.id"), index=True)
    service_code: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(80), default="POSTED")
    payer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    posted_by: Mapped[str] = mapped_column(String(160))
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Claim(Base):
    __tablename__ = "claim"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("CLM"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounter.id"), index=True)
    payer: Mapped[str] = mapped_column(String(120), index=True)
    member_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(80), default="DRAFT", index=True)
    authorization_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    denial_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("PAY"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    method: Mapped[str] = mapped_column(String(80))
    reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    received_by: Mapped[str] = mapped_column(String(160))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InventoryItem(Base):
    __tablename__ = "inventory_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("ITEM"))
    facility_id: Mapped[int] = mapped_column(ForeignKey("facility.id"), index=True)
    item_code: Mapped[str] = mapped_column(String(80), index=True)
    item_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(120), index=True)
    unit: Mapped[str] = mapped_column(String(80))
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    batch_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expiry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str] = mapped_column(String(160))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class InventoryTransaction(Base):
    __tablename__ = "inventory_transaction"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("STK"))
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_item.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    actor: Mapped[str] = mapped_column(String(160))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class QualityIncident(Base):
    __tablename__ = "quality_incident"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("QSI"))
    facility_id: Mapped[int] = mapped_column(ForeignKey("facility.id"), index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patient.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(80), default="OPEN", index=True)
    owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reported_by: Mapped[str] = mapped_column(String(160))
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PublicHealthEvent(Base):
    __tablename__ = "public_health_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("PHE"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    condition_code: Mapped[str] = mapped_column(String(80), index=True)
    condition_name: Mapped[str] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(String(80), default="NOTIFIABLE_CONDITION")
    status: Mapped[str] = mapped_column(String(80), default="PENDING_VERIFICATION", index=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reported_to: Mapped[str] = mapped_column(String(120), default="eIDSR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationEvent(Base):
    __tablename__ = "integration_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("INT"))
    system: Mapped[str] = mapped_column(String(120), index=True)
    event_type: Mapped[str] = mapped_column(String(120))
    resource_type: Mapped[str] = mapped_column(String(120))
    resource_id: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(80), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AudioNoteSession(Base):
    __tablename__ = "audio_note_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("AUDNOTE"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    note_type: Mapped[str] = mapped_column(String(80), default="PROGRESS_NOTE")
    transcript: Mapped[str] = mapped_column(Text)
    draft_note: Mapped[str] = mapped_column(Text)
    engine: Mapped[str] = mapped_column(String(120), default="local-safe-draft-v1")
    engine_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default="MANUAL_TRANSCRIPT")
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    audio_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    audio_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    raw_audio_retained: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT_REQUIRES_REVIEW")
    created_by: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PracticeAdvisoryEvent(Base):
    __tablename__ = "practice_advisory_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("ADV"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True, index=True)
    advisory_key: Mapped[str] = mapped_column(String(160), index=True)
    action: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(160))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)



class TelehealthSession(Base):
    __tablename__ = "telehealth_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("TEL"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facility.id"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointment.id"), nullable=True, index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True, index=True)
    service: Mapped[str] = mapped_column(String(160), index=True)
    provider: Mapped[str] = mapped_column(String(160))
    modality: Mapped[str] = mapped_column(String(40), default="VIDEO")
    status: Mapped[str] = mapped_column(String(80), default="SCHEDULED", index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    join_code: Mapped[str] = mapped_column(String(80), unique=True, default=lambda: public_id("JOIN"))
    created_by: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ModuleActivity(Base):
    __tablename__ = "module_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("ACT"))
    module_code: Mapped[str] = mapped_column(String(80), index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patient.id"), nullable=True, index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True, index=True)
    activity_type: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(80), default="NEW", index=True)
    priority: Mapped[str] = mapped_column(String(40), default="ROUTINE")
    assigned_to: Mapped[str | None] = mapped_column(String(160), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
