from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..collaboration_models import ActivityAccessRequest, PatientActivityLock, WorkflowInstance
from ..database import get_db
from ..enterprise_models import UserAccount
from ..models import Encounter, Patient
from ..security import require_user

router = APIRouter(prefix="/collaboration", tags=["collaboration"])
LOCK_MINUTES = 5


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class LockIn(BaseModel):
    patient_mpi_id: str
    activity_code: str = Field(min_length=2, max_length=120)
    encounter_id: str | None = None


class RequestIn(BaseModel):
    reason: str = Field(default="Please release the record so I can continue the patient workflow.", min_length=3, max_length=1000)


class ResponseIn(BaseModel):
    decision: str
    reason: str | None = None
    timeframe_minutes: int | None = Field(default=None, ge=1, le=240)


class WorkflowIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str | None = None
    workflow_code: str = Field(min_length=2, max_length=120)
    metadata: dict = Field(default_factory=dict)


def patient_and_encounter(db: Session, mpi: str, encounter_public_id: str | None):
    patient = db.scalar(select(Patient).where(Patient.mpi_id == mpi))
    if not patient:
        raise HTTPException(404, "Patient not found")
    encounter = None
    if encounter_public_id:
        encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == encounter_public_id, Encounter.patient_id == patient.id))
        if not encounter:
            raise HTTPException(404, "Encounter not found for patient")
    return patient, encounter


def serialize_lock(lock: PatientActivityLock | None, user: UserAccount, request: ActivityAccessRequest | None = None):
    if not lock:
        return {"status": "AVAILABLE", "owned_by_me": False}
    return {
        "status": "OWNED" if lock.holder_user_id == user.id else "LOCKED",
        "lock_id": lock.lock_id,
        "activity_code": lock.activity_code,
        "owned_by_me": lock.holder_user_id == user.id,
        "holder": {"username": lock.holder_username, "display_name": lock.holder_display_name},
        "acquired_at": lock.acquired_at,
        "expires_at": lock.expires_at,
        "request": None if not request else {
            "request_id": request.request_id,
            "status": request.status,
            "reason": request.reason,
            "denial_reason": request.denial_reason,
            "retry_after": request.retry_after,
            "requested_at": request.requested_at,
        },
    }


def auto_transfer_if_expired(db: Session, lock: PatientActivityLock) -> PatientActivityLock | None:
    if aware(lock.expires_at) > now():
        return lock
    pending = db.scalar(
        select(ActivityAccessRequest)
        .where(ActivityAccessRequest.lock_id == lock.id, ActivityAccessRequest.status == "PENDING")
        .order_by(ActivityAccessRequest.requested_at.asc())
    )
    if pending:
        requester = db.get(UserAccount, pending.requester_user_id)
        if requester and requester.active:
            old_holder = lock.holder_display_name
            lock.holder_user_id = requester.id
            lock.holder_username = requester.username
            lock.holder_display_name = requester.display_name
            lock.acquired_at = now()
            lock.heartbeat_at = now()
            lock.expires_at = now() + timedelta(minutes=LOCK_MINUTES)
            pending.status = "AUTO_GRANTED"
            pending.responded_at = now()
            pending.transferred_at = now()
            for other in db.scalars(select(ActivityAccessRequest).where(ActivityAccessRequest.lock_id == lock.id, ActivityAccessRequest.status == "PENDING")).all():
                if other.id != pending.id:
                    other.status = "EXPIRED"
                    other.responded_at = now()
            write_audit(db, action="PATIENT_ACTIVITY_AUTO_TRANSFER", resource_type="PatientActivityLock", resource_id=lock.lock_id, actor=requester.username, patient_mpi_id=None, details=f"Auto-transferred from {old_holder} after five-minute timeout")
            return lock
    lock.released_at = now()
    lock.release_reason = "Expired after five minutes without heartbeat"
    db.delete(lock)
    db.flush()
    return None


@router.post("/locks/acquire")
def acquire(payload: LockIn, db: Session = Depends(get_db), user: UserAccount = Depends(require_user)):
    patient, encounter = patient_and_encounter(db, payload.patient_mpi_id, payload.encounter_id)
    lock = db.scalar(select(PatientActivityLock).where(PatientActivityLock.patient_id == patient.id, PatientActivityLock.activity_code == payload.activity_code))
    if lock:
        lock = auto_transfer_if_expired(db, lock)
    if lock and lock.holder_user_id != user.id:
        req = db.scalar(select(ActivityAccessRequest).where(ActivityAccessRequest.lock_id == lock.id, ActivityAccessRequest.requester_user_id == user.id, ActivityAccessRequest.status.in_(["PENDING", "DENIED"])).order_by(ActivityAccessRequest.requested_at.desc()))
        db.commit()
        return serialize_lock(lock, user, req)
    if not lock:
        lock = PatientActivityLock(
            patient_id=patient.id, encounter_id=encounter.id if encounter else None, activity_code=payload.activity_code,
            holder_user_id=user.id, holder_username=user.username, holder_display_name=user.display_name,
            acquired_at=now(), heartbeat_at=now(), expires_at=now() + timedelta(minutes=LOCK_MINUTES),
        )
        db.add(lock)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            lock = db.scalar(select(PatientActivityLock).where(PatientActivityLock.patient_id == patient.id, PatientActivityLock.activity_code == payload.activity_code))
            return serialize_lock(lock, user)
        write_audit(db, action="PATIENT_ACTIVITY_LOCK_ACQUIRED", resource_type="PatientActivityLock", resource_id=lock.lock_id, actor=user.username, patient_mpi_id=patient.mpi_id, details=payload.activity_code)
    else:
        lock.heartbeat_at = now(); lock.expires_at = now() + timedelta(minutes=LOCK_MINUTES)
    db.commit(); db.refresh(lock)
    return serialize_lock(lock, user)


@router.post("/locks/{lock_id}/heartbeat")
def heartbeat(lock_id: str, db: Session = Depends(get_db), user: UserAccount = Depends(require_user)):
    lock = db.scalar(select(PatientActivityLock).where(PatientActivityLock.lock_id == lock_id))
    if not lock or lock.holder_user_id != user.id:
        raise HTTPException(409, "The patient activity is no longer locked by this user")
    lock.heartbeat_at = now(); lock.expires_at = now() + timedelta(minutes=LOCK_MINUTES)
    db.commit()
    return {"status": "RENEWED", "expires_at": lock.expires_at}


@router.post("/locks/{lock_id}/request")
def request_access(lock_id: str, payload: RequestIn, db: Session = Depends(get_db), user: UserAccount = Depends(require_user)):
    lock = db.scalar(select(PatientActivityLock).where(PatientActivityLock.lock_id == lock_id))
    if not lock:
        raise HTTPException(404, "Activity lock no longer exists")
    lock = auto_transfer_if_expired(db, lock)
    if not lock:
        db.commit(); return {"status": "RETRY_ACQUIRE"}
    if lock.holder_user_id == user.id:
        return {"status": "ALREADY_OWNER"}
    existing = db.scalar(select(ActivityAccessRequest).where(ActivityAccessRequest.lock_id == lock.id, ActivityAccessRequest.requester_user_id == user.id, ActivityAccessRequest.status == "PENDING"))
    if existing:
        return {"status": existing.status, "request_id": existing.request_id}
    req = ActivityAccessRequest(lock_id=lock.id, patient_id=lock.patient_id, activity_code=lock.activity_code, requester_user_id=user.id, requester_username=user.username, requester_display_name=user.display_name, reason=payload.reason)
    db.add(req)
    write_audit(db, action="PATIENT_ACTIVITY_ACCESS_REQUESTED", resource_type="ActivityAccessRequest", resource_id=req.request_id, actor=user.username, details=payload.reason)
    db.commit(); db.refresh(req)
    return {"status": "PENDING", "request_id": req.request_id, "auto_release_at": lock.expires_at}


@router.get("/locks/requests/incoming")
def incoming(db: Session = Depends(get_db), user: UserAccount = Depends(require_user)):
    rows = db.execute(
        select(ActivityAccessRequest, PatientActivityLock, Patient)
        .join(PatientActivityLock, ActivityAccessRequest.lock_id == PatientActivityLock.id)
        .join(Patient, ActivityAccessRequest.patient_id == Patient.id)
        .where(PatientActivityLock.holder_user_id == user.id, ActivityAccessRequest.status == "PENDING")
        .order_by(ActivityAccessRequest.requested_at.asc())
    ).all()
    return {"items": [{
        "request_id": r.request_id, "lock_id": l.lock_id, "requester": r.requester_display_name,
        "reason": r.reason, "patient_mpi_id": p.mpi_id, "patient_name": p.full_name,
        "activity_code": r.activity_code, "requested_at": r.requested_at, "auto_release_at": l.expires_at,
    } for r,l,p in rows]}


@router.post("/requests/{request_id}/respond")
def respond(request_id: str, payload: ResponseIn, db: Session = Depends(get_db), user: UserAccount = Depends(require_user)):
    req = db.scalar(select(ActivityAccessRequest).where(ActivityAccessRequest.request_id == request_id))
    if not req:
        raise HTTPException(404, "Request not found")
    lock = db.get(PatientActivityLock, req.lock_id)
    if not lock or lock.holder_user_id != user.id:
        raise HTTPException(403, "Only the current activity holder may respond")
    decision = payload.decision.upper()
    if decision == "YES":
        requester = db.get(UserAccount, req.requester_user_id)
        if not requester or not requester.active:
            raise HTTPException(409, "Requester account is not active")
        lock.holder_user_id = requester.id; lock.holder_username = requester.username; lock.holder_display_name = requester.display_name
        lock.acquired_at = now(); lock.heartbeat_at = now(); lock.expires_at = now() + timedelta(minutes=LOCK_MINUTES)
        req.status = "GRANTED"; req.responded_at = now(); req.transferred_at = now()
        outcome = "GRANTED"
    elif decision == "NO":
        if not payload.reason or not payload.timeframe_minutes:
            raise HTTPException(422, "A denial reason and timeframe are required")
        req.status = "DENIED"; req.denial_reason = payload.reason; req.retry_after = now() + timedelta(minutes=payload.timeframe_minutes); req.responded_at = now()
        lock.expires_at = min(lock.expires_at, req.retry_after)
        outcome = "DENIED"
    else:
        raise HTTPException(422, "Decision must be YES or NO")
    write_audit(db, action=f"PATIENT_ACTIVITY_ACCESS_{outcome}", resource_type="ActivityAccessRequest", resource_id=req.request_id, actor=user.username, details=payload.reason)
    db.commit()
    return {"status": req.status, "retry_after": req.retry_after, "new_holder": lock.holder_display_name}


@router.post("/locks/{lock_id}/release")
def release(lock_id: str, db: Session = Depends(get_db), user: UserAccount = Depends(require_user)):
    lock = db.scalar(select(PatientActivityLock).where(PatientActivityLock.lock_id == lock_id))
    if not lock:
        return {"status": "ALREADY_RELEASED"}
    if lock.holder_user_id != user.id:
        raise HTTPException(403, "Only the lock holder may release this activity")
    pending = db.scalar(select(ActivityAccessRequest).where(ActivityAccessRequest.lock_id == lock.id, ActivityAccessRequest.status == "PENDING").order_by(ActivityAccessRequest.requested_at.asc()))
    if pending:
        requester = db.get(UserAccount, pending.requester_user_id)
        if requester and requester.active:
            lock.holder_user_id=requester.id; lock.holder_username=requester.username; lock.holder_display_name=requester.display_name
            lock.acquired_at=now(); lock.heartbeat_at=now(); lock.expires_at=now()+timedelta(minutes=LOCK_MINUTES)
            pending.status="GRANTED"; pending.responded_at=now(); pending.transferred_at=now()
            db.commit(); return {"status":"TRANSFERRED", "new_holder":requester.display_name}
    write_audit(db, action="PATIENT_ACTIVITY_LOCK_RELEASED", resource_type="PatientActivityLock", resource_id=lock.lock_id, actor=user.username)
    db.delete(lock); db.commit()
    return {"status": "RELEASED"}


@router.post("/workflows/start")
def start_workflow(payload: WorkflowIn, db: Session = Depends(get_db), user: UserAccount = Depends(require_user)):
    patient, encounter = patient_and_encounter(db, payload.patient_mpi_id, payload.encounter_id)
    existing = db.scalar(select(WorkflowInstance).where(WorkflowInstance.patient_id == patient.id, WorkflowInstance.encounter_id == (encounter.id if encounter else None), WorkflowInstance.workflow_code == payload.workflow_code))
    if existing:
        raise HTTPException(409, detail={"message":"This workflow has already been initiated and cannot be repeated.","workflow_id":existing.workflow_id,"status":existing.status,"initiated_at":existing.initiated_at})
    item = WorkflowInstance(patient_id=patient.id, encounter_id=encounter.id if encounter else None, workflow_code=payload.workflow_code, initiated_by=user.display_name, metadata_json=json.dumps(payload.metadata))
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409, "This workflow has already been initiated and cannot be repeated") from exc
    write_audit(db, action="WORKFLOW_INITIATED", resource_type="WorkflowInstance", resource_id=item.workflow_id, actor=user.username, patient_mpi_id=patient.mpi_id, details=payload.workflow_code)
    db.commit(); db.refresh(item)
    return {"workflow_id":item.workflow_id,"status":item.status,"workflow_code":item.workflow_code,"initiated_at":item.initiated_at}


@router.get("/workflows/status")
def workflow_status(patient_mpi_id: str, encounter_id: str | None = None, db: Session = Depends(get_db), user: UserAccount = Depends(require_user)):
    patient, encounter = patient_and_encounter(db, patient_mpi_id, encounter_id)
    query = select(WorkflowInstance).where(WorkflowInstance.patient_id == patient.id)
    if encounter:
        query = query.where(WorkflowInstance.encounter_id == encounter.id)
    items = db.scalars(query.order_by(WorkflowInstance.initiated_at.desc())).all()
    return {"items":[{"workflow_id":x.workflow_id,"workflow_code":x.workflow_code,"status":x.status,"initiated_by":x.initiated_by,"initiated_at":x.initiated_at} for x in items]}
