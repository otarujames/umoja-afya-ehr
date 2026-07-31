from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def public_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


class PatientActivityLock(Base):
    __tablename__ = "patient_activity_lock"
    __table_args__ = (UniqueConstraint("patient_id", "activity_code", name="uq_patient_activity_lock"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lock_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("LOCK"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id", ondelete="CASCADE"), index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id", ondelete="SET NULL"), nullable=True, index=True)
    activity_code: Mapped[str] = mapped_column(String(120), index=True)
    holder_user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    holder_username: Mapped[str] = mapped_column(String(120), index=True)
    holder_display_name: Mapped[str] = mapped_column(String(180))
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ActivityAccessRequest(Base):
    __tablename__ = "activity_access_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("LOCKREQ"))
    lock_id: Mapped[int] = mapped_column(ForeignKey("patient_activity_lock.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id", ondelete="CASCADE"), index=True)
    activity_code: Mapped[str] = mapped_column(String(120), index=True)
    requester_user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    requester_username: Mapped[str] = mapped_column(String(120), index=True)
    requester_display_name: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transferred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowInstance(Base):
    __tablename__ = "workflow_instance"
    __table_args__ = (UniqueConstraint("patient_id", "encounter_id", "workflow_code", name="uq_patient_encounter_workflow"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, default=lambda: public_id("WF"))
    patient_id: Mapped[int] = mapped_column(ForeignKey("patient.id", ondelete="CASCADE"), index=True)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounter.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_code: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default="STARTED", index=True)
    initiated_by: Mapped[str] = mapped_column(String(180))
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
