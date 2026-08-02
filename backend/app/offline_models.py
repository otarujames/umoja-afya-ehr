from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OfflineDevice(Base):
    """A browser installation authorized to retain an encrypted offline vault."""

    __tablename__ = "offline_device"
    __table_args__ = (UniqueConstraint("user_account_id", "device_id", name="uq_offline_device_user_device"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(80), index=True)
    user_account_id: Mapped[int] = mapped_column(ForeignKey("user_account.id", ondelete="CASCADE"), index=True)
    device_name: Mapped[str] = mapped_column(String(160))
    platform: Mapped[str | None] = mapped_column(String(160), nullable=True)
    app_version: Mapped[str] = mapped_column(String(40))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IdempotencyReceipt(Base):
    """Durable replay receipt for a browser outbox mutation."""

    __tablename__ = "idempotency_receipt"
    __table_args__ = (UniqueConstraint("actor_user_id", "idempotency_key", name="uq_idempotency_actor_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[str] = mapped_column(String(80), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), index=True)
    request_method: Mapped[str] = mapped_column(String(12))
    request_path: Mapped[str] = mapped_column(String(500))
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="PROCESSING", index=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_content_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    offline_created_at: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
