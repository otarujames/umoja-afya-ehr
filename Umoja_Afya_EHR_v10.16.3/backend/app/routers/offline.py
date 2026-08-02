from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import get_settings
from ..database import get_db
from ..enterprise_models import UserAccount
from ..offline_models import OfflineDevice
from ..security import require_user
from ..version import __version__

router = APIRouter(prefix="/offline", tags=["Offline and Device Sync"])

OFFLINE_MAX_PENDING = 5000


class DeviceEnrollmentIn(BaseModel):
    device_id: str = Field(min_length=16, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")
    device_name: str = Field(min_length=2, max_length=160)
    platform: str | None = Field(default=None, max_length=160)
    app_version: str = Field(default=__version__, max_length=40)


class DeviceHeartbeatIn(BaseModel):
    outcome: Literal["SYNCED", "NO_CHANGES", "NEEDS_REVIEW"] = "SYNCED"
    pending_count: int = Field(default=0, ge=0, le=OFFLINE_MAX_PENDING)


def _device_out(item: OfflineDevice) -> dict:
    return {
        "device_id": item.device_id,
        "device_name": item.device_name,
        "platform": item.platform,
        "app_version": item.app_version,
        "enrolled_at": item.enrolled_at,
        "last_seen_at": item.last_seen_at,
        "last_sync_at": item.last_sync_at,
        "active": item.revoked_at is None,
    }


@router.get("/policy")
def offline_policy(user: UserAccount = Depends(require_user)):
    settings = get_settings()
    return {
        "enabled": settings.offline_access_enabled,
        "encryption_required": True,
        "offline_pin_required": True,
        "lease_hours": settings.offline_lease_hours,
        "maximum_pending_operations": settings.offline_max_pending,
        "background_sync_requires_unlocked_app": True,
        "user_id": user.user_id,
        "facility_code": user.facility_code,
        "release": __version__,
        "queueable_workflows": [
            "patient registration",
            "scheduled arrival",
            "walk-in arrival",
            "triage and record activities",
            "draft notes",
            "flowsheet observations",
            "payments and financial counseling",
        ],
        "online_only_workflows": [
            "note signature and addenda",
            "medication administration and verification",
            "new clinical orders and result acknowledgement",
            "patient death recording",
            "discharge and claim submission",
            "user administration and break-glass access",
        ],
    }


@router.get("/devices")
def offline_devices(user: UserAccount = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(OfflineDevice).where(OfflineDevice.user_account_id == user.id).order_by(OfflineDevice.last_seen_at.desc())).all()
    return [_device_out(row) for row in rows]


@router.post("/devices", status_code=201)
def enroll_device(payload: DeviceEnrollmentIn, user: UserAccount = Depends(require_user), db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.offline_access_enabled:
        raise HTTPException(status_code=403, detail="Offline access is disabled by deployment policy")
    item = db.scalar(select(OfflineDevice).where(OfflineDevice.user_account_id == user.id, OfflineDevice.device_id == payload.device_id))
    current = datetime.now(timezone.utc)
    if item is None:
        item = OfflineDevice(
            device_id=payload.device_id,
            user_account_id=user.id,
            device_name=payload.device_name.strip(),
            platform=payload.platform,
            app_version=payload.app_version,
            enrolled_at=current,
            last_seen_at=current,
        )
        db.add(item)
    else:
        item.device_name = payload.device_name.strip()
        item.platform = payload.platform
        item.app_version = payload.app_version
        item.last_seen_at = current
        item.revoked_at = None
    write_audit(
        db,
        action="OFFLINE_DEVICE_ENROLLED",
        resource_type="OfflineDevice",
        resource_id=payload.device_id,
        actor=user.display_name,
        role=user.role_code,
        facility_code=user.facility_code,
        details=f"device={payload.device_name}; platform={payload.platform or 'unknown'}; release={payload.app_version}",
    )
    db.commit()
    db.refresh(item)
    return {**_device_out(item), "lease_hours": settings.offline_lease_hours}


@router.post("/devices/{device_id}/heartbeat")
def sync_heartbeat(device_id: str, payload: DeviceHeartbeatIn, user: UserAccount = Depends(require_user), db: Session = Depends(get_db)):
    if payload.pending_count > get_settings().offline_max_pending:
        raise HTTPException(status_code=422, detail="Pending operation count exceeds deployment policy")
    item = db.scalar(select(OfflineDevice).where(OfflineDevice.user_account_id == user.id, OfflineDevice.device_id == device_id))
    if item is None or item.revoked_at is not None:
        raise HTTPException(status_code=403, detail="This offline device is not enrolled or has been revoked")
    current = datetime.now(timezone.utc)
    item.last_seen_at = current
    item.last_sync_at = current
    write_audit(
        db,
        action="OFFLINE_SYNC_COMPLETED",
        resource_type="OfflineDevice",
        resource_id=device_id,
        actor=user.display_name,
        role=user.role_code,
        facility_code=user.facility_code,
        outcome="SUCCESS" if payload.outcome != "NEEDS_REVIEW" else "REVIEW",
        details=f"outcome={payload.outcome}; pending={payload.pending_count}",
    )
    db.commit()
    return {"synced_at": current, "outcome": payload.outcome, "pending_count": payload.pending_count}


@router.delete("/devices/{device_id}")
def revoke_device(device_id: str, user: UserAccount = Depends(require_user), db: Session = Depends(get_db)):
    item = db.scalar(select(OfflineDevice).where(OfflineDevice.user_account_id == user.id, OfflineDevice.device_id == device_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Offline device not found")
    item.revoked_at = datetime.now(timezone.utc)
    write_audit(
        db,
        action="OFFLINE_DEVICE_REVOKED",
        resource_type="OfflineDevice",
        resource_id=device_id,
        actor=user.display_name,
        role=user.role_code,
        facility_code=user.facility_code,
    )
    db.commit()
    return {"revoked": True, "device_id": device_id}
