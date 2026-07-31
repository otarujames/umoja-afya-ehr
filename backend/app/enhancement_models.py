from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def public_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


class OrderCatalogItem(Base):
    __tablename__ = "order_catalog_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    orderable_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    clinical: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    specimen: Mapped[str | None] = mapped_column(String(120), nullable=True)
    default_priority: Mapped[str] = mapped_column(String(40), default="ROUTINE")
    default_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    synonyms: Mapped[str | None] = mapped_column(Text, nullable=True)
    units: Mapped[str | None] = mapped_column(String(120), nullable=True)
    route: Mapped[str | None] = mapped_column(String(80), nullable=True)
    requires_reason: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_cosign: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class UserMessage(Base):
    __tablename__ = "user_message"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("MSG"))
    thread_id: Mapped[str] = mapped_column(String(80), index=True, default=lambda: public_id("THREAD"))
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patient.id"), nullable=True, index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(40), default="ROUTINE", index=True)
    status: Mapped[str] = mapped_column(String(40), default="UNREAD", index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ManagedEvent(Base):
    __tablename__ = "managed_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("EVT"))
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(120), index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patient.id"), nullable=True, index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    status_before: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status_after: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor: Mapped[str] = mapped_column(String(160))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reversed_by_event_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class DeviceEndpoint(Base):
    __tablename__ = "device_endpoint"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("DEV"))
    facility_code: Mapped[str] = mapped_column(String(80), index=True)
    unit: Mapped[str] = mapped_column(String(120), index=True)
    room: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bed_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    name: Mapped[str] = mapped_column(String(180))
    device_type: Mapped[str] = mapped_column(String(100), index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    protocol: Mapped[str] = mapped_column(String(80), default="FHIR_OBSERVATION")
    status: Mapped[str] = mapped_column(String(40), default="ONLINE", index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class DeviceReading(Base):
    __tablename__ = "device_reading"

    id: Mapped[int] = mapped_column(primary_key=True)
    reading_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("READ"))
    device_endpoint_id: Mapped[int] = mapped_column(ForeignKey("device_endpoint.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id"), index=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounter.id"), index=True)
    flowsheet_id: Mapped[int | None] = mapped_column(ForeignKey("flowsheet.id"), nullable=True, index=True)
    parameter_code: Mapped[str] = mapped_column(String(100), index=True)
    parameter_name: Mapped[str] = mapped_column(String(180))
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quality: Mapped[str] = mapped_column(String(40), default="VALID")
    source_message_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
