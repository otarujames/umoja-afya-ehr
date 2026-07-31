from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


class EncounterStatus(str, enum.Enum):
    PRE_REGISTERED = "PRE_REGISTERED"
    ARRIVED = "ARRIVED"
    WAITING_REGISTRATION = "WAITING_REGISTRATION"
    REGISTERED = "REGISTERED"
    WAITING_TRIAGE = "WAITING_TRIAGE"
    TRIAGED = "TRIAGED"
    READY_FOR_PROVIDER = "READY_FOR_PROVIDER"
    ROOMED = "ROOMED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_RESULTS = "WAITING_RESULTS"
    READY_FOR_DISCHARGE = "READY_FOR_DISCHARGE"
    DISCHARGED = "DISCHARGED"
    TRANSFERRED = "TRANSFERRED"
    LEFT_WITHOUT_BEING_SEEN = "LEFT_WITHOUT_BEING_SEEN"


class FlowSheetStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class Facility(Base):
    __tablename__ = "facility"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    facility_type: Mapped[str] = mapped_column(String(120))
    relation: Mapped[str] = mapped_column(String(160))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    hfr_code: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    council: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    ownership_category: Mapped[str] = mapped_column(String(80), default="Public", index=True)
    ownership_authority: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    hierarchy_level: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    parent_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    source_system: Mapped[str] = mapped_column(String(80), default="Umoja Afya")
    country_code: Mapped[str] = mapped_column(String(3), default="TZ", index=True)

    encounters: Mapped[list["Encounter"]] = relationship(back_populates="facility")


class Patient(Base):
    __tablename__ = "patient"

    id: Mapped[int] = mapped_column(primary_key=True)
    mpi_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    mrn: Mapped[str] = mapped_column(String(80), index=True)
    first_name: Mapped[str] = mapped_column(String(120))
    middle_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str] = mapped_column(String(120))
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str] = mapped_column(String(40))
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    nida_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    next_of_kin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    member_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    allergies: Mapped[str] = mapped_column(Text, default="No known allergies")
    problems: Mapped[str] = mapped_column(Text, default="Not yet assessed")
    medications: Mapped[str] = mapped_column(Text, default="Medication reconciliation pending")
    consent_status: Mapped[str] = mapped_column(String(80), default="OBTAINED")
    identity_status: Mapped[str] = mapped_column(String(80), default="VERIFIED")
    record_status: Mapped[str] = mapped_column(String(40), default="ACTIVE", index=True)
    deceased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deceased_location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    deceased_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    death_certificate_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expired_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    country_code: Mapped[str] = mapped_column(String(3), default="TZ", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    encounters: Mapped[list["Encounter"]] = relationship(back_populates="patient")
    flowsheets: Mapped[list["FlowSheet"]] = relationship(back_populates="patient")

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)


class Encounter(Base):
    __tablename__ = "encounter"

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: new_id("ENC"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facility.id"), index=True)
    encounter_type: Mapped[str] = mapped_column(String(80), default="OUTPATIENT")
    service: Mapped[str] = mapped_column(String(160), default="General Medicine")
    status: Mapped[EncounterStatus] = mapped_column(Enum(EncounterStatus), default=EncounterStatus.ARRIVED, index=True)
    acuity: Mapped[str] = mapped_column(String(40), default="Not assigned")
    location: Mapped[str] = mapped_column(String(160), default="Arrival Desk")
    room: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reason_for_visit: Mapped[str | None] = mapped_column(Text, nullable=True)
    arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    triage_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discharge_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discharge_disposition: Mapped[str | None] = mapped_column(String(160), nullable=True)
    discharge_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="encounters")
    facility: Mapped[Facility] = relationship(back_populates="encounters")
    orders: Mapped[list["Order"]] = relationship(back_populates="encounter")


class FlowSheet(Base):
    __tablename__ = "flowsheet"

    id: Mapped[int] = mapped_column(primary_key=True)
    flowsheet_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: new_id("FS"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(180))
    template_code: Mapped[str] = mapped_column(String(120), default="GENERAL")
    status: Mapped[FlowSheetStatus] = mapped_column(Enum(FlowSheetStatus), default=FlowSheetStatus.DRAFT)
    cadence_minutes: Mapped[int] = mapped_column(Integer, default=15)
    parameters_json: Mapped[str] = mapped_column(Text, default="[]")
    elapsed_seconds: Mapped[int] = mapped_column(Integer, default=0)
    active_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="flowsheets")
    events: Mapped[list["FlowSheetEvent"]] = relationship(back_populates="flowsheet", cascade="all, delete-orphan")
    observations: Mapped[list["FlowSheetObservation"]] = relationship(back_populates="flowsheet", cascade="all, delete-orphan")


class FlowSheetEvent(Base):
    __tablename__ = "flowsheet_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    flowsheet_id: Mapped[int] = mapped_column(ForeignKey("flowsheet.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(160), default="demo-user")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    flowsheet: Mapped[FlowSheet] = relationship(back_populates="events")


class FlowSheetObservation(Base):
    __tablename__ = "flowsheet_observation"

    id: Mapped[int] = mapped_column(primary_key=True)
    flowsheet_id: Mapped[int] = mapped_column(ForeignKey("flowsheet.id"), index=True)
    parameter: Mapped[str] = mapped_column(String(160))
    value: Mapped[str] = mapped_column(String(160))
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="MANUAL")
    recorded_by: Mapped[str] = mapped_column(String(160), default="demo-user")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    flowsheet: Mapped[FlowSheet] = relationship(back_populates="observations")


class Order(Base):
    __tablename__ = "clinical_order"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: new_id("ORD"))
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounter.id"), index=True)
    order_type: Mapped[str] = mapped_column(String(80))
    order_name: Mapped[str] = mapped_column(String(255))
    priority: Mapped[str] = mapped_column(String(40), default="ROUTINE")
    status: Mapped[str] = mapped_column(String(80), default="SIGNED")
    indication: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordered_by: Mapped[str] = mapped_column(String(160), default="demo-provider")
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    encounter: Mapped[Encounter] = relationship(back_populates="orders")
    results: Mapped[list["Result"]] = relationship(back_populates="order")


class OrderStatusEvent(Base):
    __tablename__ = "order_status_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: new_id("ORDEVT"))
    order_id: Mapped[int] = mapped_column(ForeignKey("clinical_order.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    status_before: Mapped[str] = mapped_column(String(80))
    status_after: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(160))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)



class Result(Base):
    __tablename__ = "diagnostic_result"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: new_id("RES"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("clinical_order.id"), nullable=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    test_name: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(String(180))
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    flag: Mapped[str] = mapped_column(String(40), default="NORMAL")
    status: Mapped[str] = mapped_column(String(80), default="FINAL")
    source: Mapped[str] = mapped_column(String(160), default="MNH Core Laboratory")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order | None] = relationship(back_populates="results")


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, default=lambda: new_id("AUD"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(160), default="demo-user")
    role: Mapped[str] = mapped_column(String(120), default="demo")
    action: Mapped[str] = mapped_column(String(160))
    resource_type: Mapped[str] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    patient_mpi_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    facility_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    outcome: Mapped[str] = mapped_column(String(40), default="SUCCESS")
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
