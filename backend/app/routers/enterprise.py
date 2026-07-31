from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..config import get_settings
from ..database import get_db
from ..event_management import record_managed_event
from ..enhancement_models import ManagedEvent
from ..enterprise_models import (
    Appointment,
    AudioNoteSession,
    AppointmentStatusEvent,
    Bed,
    Charge,
    Claim,
    ClinicalNote,
    IntegrationEvent,
    InventoryItem,
    InventoryTransaction,
    MedicationAdministration,
    MedicationOrder,
    ModuleActivity,
    Payment,
    PracticeAdvisoryEvent,
    PublicHealthEvent,
    QualityIncident,
    Referral,
    TelehealthSession,
    UserAccessGrant,
    UserAccount,
    WorkItem,
)
from ..models import Encounter, EncounterStatus, Facility, Patient, Result
from ..security import hash_password, optional_user, password_is_strong
from ..clinical_assist import generate_note_draft
from ..transcription import TranscriptionRejected, TranscriptionUnavailable, transcribe_audio, transcription_service_status
from ..access_control import (
    DEPARTMENT_CATALOG,
    DEPARTMENT_CODES,
    FUNCTION_CATALOG,
    FUNCTION_CODES,
    ROLE_TEMPLATES,
    get_user_access,
    replace_user_access,
    template_access,
)

router = APIRouter(tags=["Enterprise EHR Workflows"], dependencies=[Depends(optional_user)])


def now() -> datetime:
    return datetime.now(timezone.utc)


def money(value) -> float:
    return float(value or 0)


def get_patient(db: Session, mpi_id: str) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.mpi_id == mpi_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def get_encounter(db: Session, encounter_id: str) -> Encounter:
    encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == encounter_id))
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter


def get_facility(db: Session, code: str) -> Facility:
    facility = db.scalar(select(Facility).where(Facility.code == code))
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


def patient_brief(db: Session, patient_id: int) -> dict:
    patient = db.get(Patient, patient_id)
    return {
        "mpi_id": patient.mpi_id,
        "mrn": patient.mrn,
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth,
        "sex": patient.sex,
        "payer": patient.payer,
        "member_number": patient.member_number,
    }


def encounter_brief(db: Session, encounter_id: int | None) -> dict | None:
    if not encounter_id:
        return None
    encounter = db.get(Encounter, encounter_id)
    if not encounter:
        return None
    return {
        "encounter_id": encounter.encounter_id,
        "service": encounter.service,
        "status": encounter.status.value,
        "location": encounter.location,
        "room": encounter.room,
    }


class ModuleActivityIn(BaseModel):
    module_code: str
    activity_type: str
    title: str
    patient_mpi_id: str | None = None
    encounter_id: str | None = None
    priority: str = "ROUTINE"
    assigned_to: str | None = None
    details: str | None = None
    payload: dict = Field(default_factory=dict)
    created_by: str = "demo-user"


class ModuleActivityUpdateIn(BaseModel):
    status: Literal["NEW", "IN_PROGRESS", "WAITING", "COMPLETED", "CANCELLED"]
    actor: str
    assigned_to: str | None = None
    note: str | None = None


class AppointmentIn(BaseModel):
    patient_mpi_id: str
    facility_code: str
    service: str
    provider: str | None = None
    appointment_type: str = "OFFICE_VISIT"
    scheduled_start: datetime
    duration_minutes: int = Field(default=30, ge=5, le=720)
    notes: str | None = None
    created_by: str = "scheduler"


class StatusIn(BaseModel):
    status: str
    actor: str = "demo-user"
    note: str | None = None


class ReferralIn(BaseModel):
    patient_mpi_id: str
    source_facility_code: str
    destination_facility_code: str
    service: str
    priority: str = "ROUTINE"
    reason: str
    requested_by: str = "demo-provider"


class BedActionIn(BaseModel):
    action: Literal["ASSIGN", "OCCUPY", "MARK_DIRTY", "START_CLEANING", "MARK_AVAILABLE", "BLOCK", "UNBLOCK"]
    encounter_id: str | None = None
    actor: str = "operations-user"
    reason: str | None = None


class NoteIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str
    note_type: str
    title: str
    body: str
    author: str
    service: str
    cosign_required: bool = False
    source_audio_session_id: str | None = None


class NoteSignIn(BaseModel):
    signer: str
    attestation: str | None = None


class NoteUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=100000)
    note_type: str | None = Field(default=None, min_length=1, max_length=120)
    service: str | None = Field(default=None, min_length=1, max_length=160)
    cosign_required: bool | None = None
    source_audio_session_id: str | None = None
    actor: str = "demo-provider"


class NoteAddendumIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    author: str = Field(min_length=1, max_length=160)
    reason: str = Field(default="Clarification or additional clinical information", min_length=1, max_length=500)


class MedicationIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str
    medication_name: str
    dose: str
    route: str
    frequency: str
    indication: str | None = None
    ordered_by: str


class MedicationVerifyIn(BaseModel):
    pharmacist: str


class AdministrationIn(BaseModel):
    action: Literal["GIVEN", "HELD", "REFUSED", "NOT_GIVEN"]
    dose_given: str | None = None
    administered_by: str
    reason: str | None = None
    barcode_verified: bool = False


class WorkItemIn(BaseModel):
    queue: str
    task_type: str
    subject: str
    details: str | None = None
    patient_mpi_id: str | None = None
    encounter_id: str | None = None
    priority: str = "ROUTINE"
    assigned_to: str | None = None
    due_at: datetime | None = None
    created_by: str = "system"


class WorkItemUpdateIn(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
    actor: str
    assigned_to: str | None = None
    note: str | None = None


class ChargeIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str
    service_code: str
    description: str
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(ge=0)
    payer: str | None = None
    posted_by: str


class ClaimIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str
    payer: str
    member_number: str | None = None
    amount: float = Field(ge=0)
    authorization_number: str | None = None


class ClaimStatusIn(BaseModel):
    status: Literal["DRAFT", "READY", "SUBMITTED", "ACCEPTED", "DENIED", "PAID", "VOID"]
    actor: str
    denial_code: str | None = None
    denial_reason: str | None = None


class PaymentIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str | None = None
    amount: float = Field(gt=0)
    method: str
    reference: str | None = None
    received_by: str


class InventoryTransactionIn(BaseModel):
    transaction_type: Literal["RECEIPT", "ISSUE", "ADJUSTMENT_IN", "ADJUSTMENT_OUT", "TRANSFER_IN", "TRANSFER_OUT", "WASTE"]
    quantity: int = Field(gt=0)
    reason: str
    reference: str | None = None
    actor: str


class QualityIncidentIn(BaseModel):
    facility_code: str
    patient_mpi_id: str | None = None
    category: str
    severity: str
    description: str
    reported_by: str
    owner: str | None = None


class PublicHealthEventIn(BaseModel):
    patient_mpi_id: str
    condition_code: str
    condition_name: str
    event_type: str = "NOTIFIABLE_CONDITION"
    reported_to: str = "eIDSR"


class TelehealthSessionIn(BaseModel):
    patient_mpi_id: str
    facility_code: str
    service: str
    provider: str
    modality: Literal["VIDEO", "AUDIO", "STORE_AND_FORWARD"] = "VIDEO"
    scheduled_start: datetime
    reason: str | None = None
    created_by: str


class TelehealthActionIn(BaseModel):
    action: Literal["START", "PAUSE", "RESUME", "COMPLETE", "CANCEL"]
    actor: str
    note: str | None = None


class UserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=2, max_length=180)
    role_code: str = Field(default="custom", min_length=2, max_length=80)
    facility_code: str = "MNH-UPANGA"
    password: str = Field(min_length=12, max_length=256)
    requires_mfa: bool = True
    function_codes: list[str] = Field(default_factory=list)
    department_codes: list[str] = Field(default_factory=list)
    facility_codes: list[str] = Field(default_factory=list)
    country_codes: list[str] = Field(default_factory=list)
    access_reason: str | None = None
    actor: str = "System Administrator"


class UserUpdateIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=180)
    role_code: str | None = Field(default=None, min_length=2, max_length=80)
    facility_code: str | None = None
    active: bool | None = None
    requires_mfa: bool | None = None
    function_codes: list[str] | None = None
    department_codes: list[str] | None = None
    facility_codes: list[str] | None = None
    country_codes: list[str] | None = None
    access_reason: str | None = None
    actor: str = "System Administrator"


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=12, max_length=256)
    actor: str = "System Administrator"


class AudioNoteIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str | None = None
    language: Literal["en", "sw"] = "en"
    note_type: str = "PROGRESS_NOTE"
    transcript: str = Field(min_length=3, max_length=50000)
    created_by: str = Field(min_length=2, max_length=160)


class AdvisoryActionIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str | None = None
    advisory_key: str
    action: Literal["ACKNOWLEDGE", "DISMISS", "OVERRIDE"]
    reason: str | None = None
    actor: str = Field(min_length=2, max_length=160)


ALLOWED_CLINICAL_AUDIO_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/aac",
    "audio/flac",
    "video/webm",  # MediaRecorder may label an audio-only WebM stream this way.
}


def audio_session_payload(item: AudioNoteSession) -> dict:
    metadata = {}
    try:
        metadata = json.loads(item.metadata_json or "{}")
    except (TypeError, ValueError):
        metadata = {}
    return {
        "session_id": item.session_id,
        "language": item.language,
        "note_type": item.note_type,
        "transcript": item.transcript,
        "draft_note": item.draft_note,
        "engine": item.engine,
        "engine_model": item.engine_model,
        "source_type": item.source_type,
        "original_filename": item.original_filename,
        "mime_type": item.mime_type,
        "audio_sha256": item.audio_sha256,
        "audio_size_bytes": item.audio_size_bytes,
        "duration_seconds": item.duration_seconds,
        "confidence": (item.confidence_percent / 100.0) if item.confidence_percent is not None else None,
        "confidence_percent": item.confidence_percent,
        "raw_audio_retained": item.raw_audio_retained,
        "metadata": metadata,
        "status": item.status,
        "created_by": item.created_by,
        "created_at": item.created_at,
    }


def validate_audio_note_context(
    db: Session,
    *,
    patient: Patient,
    encounter: Encounter | None,
    source_audio_session_id: str | None,
) -> AudioNoteSession | None:
    if not source_audio_session_id:
        return None
    session = db.scalar(select(AudioNoteSession).where(AudioNoteSession.session_id == source_audio_session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Audio annotation session not found")
    if session.patient_id != patient.id:
        raise HTTPException(status_code=409, detail="Audio annotation belongs to a different patient")
    if encounter and session.encounter_id and session.encounter_id != encounter.id:
        raise HTTPException(status_code=409, detail="Audio annotation belongs to a different encounter")
    return session


@router.get("/notes/audio-capabilities")
def audio_capabilities():
    settings = get_settings()
    service_status = transcription_service_status()
    return {
        "server_transcription_configured": bool(settings.transcription_endpoint),
        "server_transcription_available": service_status.get("available", False),
        "server_transcription_detail": service_status.get("detail"),
        "server_transcription_model": service_status.get("model"),
        "server_transcription_required": settings.transcription_required,
        "accepted_mime_types": sorted(ALLOWED_CLINICAL_AUDIO_TYPES),
        "max_audio_bytes": settings.transcription_max_audio_bytes,
        "minimum_confidence": settings.transcription_min_confidence,
        "raw_audio_retained": settings.retain_raw_clinical_audio,
        "languages": [
            {"code": "en", "label": "English", "locale": "en-TZ"},
            {"code": "sw", "label": "Kiswahili", "locale": "sw-TZ"},
        ],
        "clinical_guardrail": "Transcription and draft text remain unsigned until reviewed and signed by a clinician.",
    }


@router.get("/notes/audio-sessions")
def audio_sessions(patient_mpi_id: str, encounter_id: str | None = None, limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    patient = get_patient(db, patient_mpi_id)
    query = select(AudioNoteSession).where(AudioNoteSession.patient_id == patient.id)
    if encounter_id:
        encounter = get_encounter(db, encounter_id)
        if encounter.patient_id != patient.id:
            raise HTTPException(status_code=409, detail="Encounter does not belong to the selected patient")
        query = query.where(AudioNoteSession.encounter_id == encounter.id)
    items = list(db.scalars(query.order_by(AudioNoteSession.created_at.desc()).limit(limit)).all())
    return [audio_session_payload(item) for item in items]


@router.post("/notes/audio-annotations", status_code=201)
def create_audio_note(payload: AudioNoteIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    encounter = get_encounter(db, payload.encounter_id) if payload.encounter_id else None
    if encounter and encounter.patient_id != patient.id:
        raise HTTPException(status_code=409, detail="Encounter does not belong to the selected patient")
    try:
        draft = generate_note_draft(payload.transcript, payload.language, payload.note_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    item = AudioNoteSession(
        patient_id=patient.id,
        encounter_id=encounter.id if encounter else None,
        language=payload.language,
        note_type=payload.note_type,
        transcript=payload.transcript.strip(),
        draft_note=draft,
        engine="manual-transcript-structured-draft-v2",
        source_type="MANUAL_TRANSCRIPT",
        metadata_json=json.dumps({"transcript_source": "typed_or_browser_dictation"}, separators=(",", ":")),
        raw_audio_retained=False,
        created_by=payload.created_by,
    )
    db.add(item)
    db.flush()
    write_audit(db, action="CREATE_AUDIO_NOTE_DRAFT", resource_type="AudioNoteSession", resource_id=item.session_id, actor=payload.created_by, role="audio_notes.use", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code if encounter else None, details="Manual/browser transcript; clinician review required before signature")
    db.commit()
    return audio_session_payload(item)


@router.post("/notes/audio-transcriptions", status_code=201)
async def transcribe_audio_note(
    patient_mpi_id: str = Form(...),
    encounter_id: str | None = Form(default=None),
    language: Literal["en", "sw"] = Form(default="en"),
    note_type: str = Form(default="PROGRESS_NOTE"),
    created_by: str = Form(..., min_length=2, max_length=160),
    consent_confirmed: bool = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    patient = get_patient(db, patient_mpi_id)
    encounter = get_encounter(db, encounter_id) if encounter_id else None
    if encounter and encounter.patient_id != patient.id:
        raise HTTPException(status_code=409, detail="Encounter does not belong to the selected patient")
    if not consent_confirmed:
        raise HTTPException(status_code=422, detail="Confirm that clinical audio capture is permitted for this encounter")

    mime_type = (file.content_type or "application/octet-stream").lower().split(";")[0]
    if mime_type not in ALLOWED_CLINICAL_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported clinical audio type: {mime_type}")
    audio = await file.read(settings.transcription_max_audio_bytes + 1)
    await file.close()
    if not audio:
        raise HTTPException(status_code=422, detail="The submitted audio file is empty")
    if len(audio) > settings.transcription_max_audio_bytes:
        raise HTTPException(status_code=413, detail="Clinical audio exceeds the configured size limit")

    safe_filename = (file.filename or "clinical-audio.webm").replace("/", "_").replace("\\", "_")[:255]
    digest = hashlib.sha256(audio).hexdigest()
    try:
        result = transcribe_audio(
            audio=audio,
            filename=safe_filename,
            content_type=mime_type,
            language=language,
        )
    except TranscriptionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TranscriptionRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    draft = generate_note_draft(result.transcript, language, note_type)
    confidence_percent = None if result.confidence is None else max(0, min(100, round(result.confidence * 100)))
    status = "DRAFT_REQUIRES_REVIEW"
    if result.confidence is not None and result.confidence < settings.transcription_min_confidence:
        status = "LOW_CONFIDENCE_REQUIRES_REVIEW"
    metadata = {
        "segments": result.segments[:250],
        "consent_confirmed": True,
        "audio_disposition": "discarded_after_transcription" if not settings.retain_raw_clinical_audio else "retention_connector_required",
        "minimum_confidence": settings.transcription_min_confidence,
    }
    item = AudioNoteSession(
        patient_id=patient.id,
        encounter_id=encounter.id if encounter else None,
        language=language,
        note_type=note_type,
        transcript=result.transcript,
        draft_note=draft,
        engine=result.engine,
        engine_model=result.model,
        source_type="RECORDED_AUDIO",
        original_filename=safe_filename,
        mime_type=mime_type,
        audio_sha256=digest,
        audio_size_bytes=len(audio),
        duration_seconds=round(result.duration_seconds) if result.duration_seconds is not None else None,
        confidence_percent=confidence_percent,
        metadata_json=json.dumps(metadata, separators=(",", ":"), default=str),
        raw_audio_retained=False,
        status=status,
        created_by=created_by,
    )
    db.add(item)
    db.flush()
    write_audit(
        db,
        action="TRANSCRIBE_CLINICAL_AUDIO",
        resource_type="AudioNoteSession",
        resource_id=item.session_id,
        actor=created_by,
        role="audio_notes.use",
        patient_mpi_id=patient.mpi_id,
        facility_code=encounter.facility.code if encounter else None,
        details=f"{result.engine}; confidence={confidence_percent}; raw audio retained=false; clinician review required",
    )
    db.commit()
    return audio_session_payload(item)


@router.get("/practice-advisories")
def practice_advisories(patient_mpi_id: str, encounter_id: str | None = None, language: Literal["en", "sw"] = "en", db: Session = Depends(get_db)):
    patient = get_patient(db, patient_mpi_id)
    encounter = get_encounter(db, encounter_id) if encounter_id else None
    advisories: list[dict] = []
    allergies = (patient.allergies or "").strip()
    if allergies and allergies.lower() not in {"none", "no known drug allergies", "nkda"}:
        advisories.append({"key": "ALLERGY_REVIEW", "severity": "HIGH", "title": "Pitia mzio kabla ya kuagiza dawa" if language == "sw" else "Review allergies before ordering", "message": allergies, "source": "Patient allergy record"})
    unacknowledged = list(db.execute(select(Result).where(Result.patient_id == patient.id, Result.flag == "CRITICAL", Result.acknowledged.is_(False)).order_by(Result.issued_at.desc())).scalars().all())
    for result in unacknowledged:
        advisories.append({"key": f"CRITICAL_RESULT_{result.result_id}", "severity": "CRITICAL", "title": "Jibu muhimu halijathibitishwa" if language == "sw" else "Critical result is unacknowledged", "message": f"{result.test_name}: {result.value} {result.unit or ''}".strip(), "source": result.source})
    problem_text = (patient.problems or "").lower()
    if "hypertension" in problem_text:
        advisories.append({"key": "HYPERTENSION_FOLLOWUP", "severity": "MEDIUM", "title": "Tathmini shinikizo la damu na ufuatiliaji" if language == "sw" else "Assess blood pressure and follow-up", "message": "Thibitisha usomaji wa sasa, matumizi ya dawa, vipimo vinavyohitajika na mpango wa ufuatiliaji." if language == "sw" else "Confirm the current reading, medication adherence, indicated investigations and follow-up plan.", "source": "Problem list rule"})
    acted = {row.advisory_key: row.action for row in db.scalars(select(PracticeAdvisoryEvent).where(PracticeAdvisoryEvent.patient_id == patient.id).order_by(PracticeAdvisoryEvent.occurred_at.desc())).all()}
    for advisory in advisories:
        advisory["latest_action"] = acted.get(advisory["key"])
    return {"patient_mpi_id": patient.mpi_id, "encounter_id": encounter.encounter_id if encounter else None, "language": language, "advisories": advisories}


@router.post("/practice-advisories/actions", status_code=201)
def practice_advisory_action(payload: AdvisoryActionIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    encounter = get_encounter(db, payload.encounter_id) if payload.encounter_id else None
    if payload.action in {"DISMISS", "OVERRIDE"} and not (payload.reason or "").strip():
        raise HTTPException(status_code=422, detail="A reason is required to dismiss or override a practice advisory")
    item = PracticeAdvisoryEvent(patient_id=patient.id, encounter_id=encounter.id if encounter else None, advisory_key=payload.advisory_key, action=payload.action, reason=payload.reason, actor=payload.actor)
    db.add(item)
    db.flush()
    write_audit(db, action=f"ADVISORY_{payload.action}", resource_type="PracticeAdvisory", resource_id=item.event_id, actor=payload.actor, role="advisories.view", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code if encounter else None, details=payload.reason or payload.advisory_key)
    db.commit()
    return {"event_id": item.event_id, "advisory_key": item.advisory_key, "action": item.action, "occurred_at": item.occurred_at}


@router.get("/telehealth-sessions")
def telehealth_sessions(status: str | None = None, patient_mpi_id: str | None = None, db: Session = Depends(get_db)):
    query = select(TelehealthSession)
    if status:
        query = query.where(TelehealthSession.status == status.upper())
    if patient_mpi_id:
        query = query.where(TelehealthSession.patient_id == get_patient(db, patient_mpi_id).id)
    items = list(db.scalars(query.order_by(TelehealthSession.scheduled_start.desc())).all())
    return [{
        "session_id": x.session_id,
        "patient": patient_brief(db, x.patient_id),
        "facility": {
            "code": db.get(Facility, x.facility_id).code,
            "name": db.get(Facility, x.facility_id).name,
        },
        "appointment_id": db.get(Appointment, x.appointment_id).appointment_id if x.appointment_id and db.get(Appointment, x.appointment_id) else None,
        "encounter": encounter_brief(db, x.encounter_id),
        "service": x.service,
        "provider": x.provider,
        "modality": x.modality,
        "status": x.status,
        "reason": x.reason,
        "scheduled_start": x.scheduled_start,
        "started_at": x.started_at,
        "paused_at": x.paused_at,
        "ended_at": x.ended_at,
        "join_code": x.join_code,
        "created_by": x.created_by,
    } for x in items]


@router.post("/telehealth-sessions", status_code=201)
def create_telehealth_session(payload: TelehealthSessionIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    facility = get_facility(db, payload.facility_code)
    appointment = Appointment(
        patient_id=patient.id, facility_id=facility.id, service=payload.service, provider=payload.provider,
        appointment_type="TELEHEALTH", scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_start + timedelta(minutes=30), status="CONFIRMED",
        notes=payload.reason, created_by=payload.created_by,
    )
    db.add(appointment)
    db.flush()
    item = TelehealthSession(
        patient_id=patient.id, facility_id=facility.id, appointment_id=appointment.id,
        service=payload.service, provider=payload.provider, modality=payload.modality,
        scheduled_start=payload.scheduled_start, reason=payload.reason, created_by=payload.created_by,
    )
    db.add(item)
    db.flush()
    db.add(WorkItem(
        queue="TELEHEALTH", task_type="VIRTUAL_VISIT_READINESS", subject=f"Prepare {payload.service} telehealth visit",
        patient_id=patient.id, priority="ROUTINE", assigned_to=payload.provider,
        due_at=payload.scheduled_start - timedelta(minutes=30), created_by=payload.created_by,
    ))
    db.add(IntegrationEvent(
        system="Workflow Notification Service", event_type="TELEHEALTH_SCHEDULED", resource_type="TelehealthSession",
        resource_id=item.session_id, payload_json=json.dumps({"patient": patient.mpi_id, "appointment": appointment.appointment_id}),
    ))
    write_audit(db, action="CREATE_TELEHEALTH_SESSION", resource_type="TelehealthSession", resource_id=item.session_id, actor=payload.created_by, role="Telehealth", patient_mpi_id=patient.mpi_id, facility_code=facility.code)
    db.commit()
    return {"session_id": item.session_id, "appointment_id": appointment.appointment_id, "status": item.status, "join_code": item.join_code}


@router.post("/telehealth-sessions/{session_id}/actions")
def telehealth_action(session_id: str, payload: TelehealthActionIn, db: Session = Depends(get_db)):
    item = db.scalar(select(TelehealthSession).where(TelehealthSession.session_id == session_id))
    if not item:
        raise HTTPException(status_code=404, detail="Telehealth session not found")
    action = payload.action
    allowed = {
        "SCHEDULED": {"START", "CANCEL"},
        "READY": {"START", "CANCEL"},
        "IN_PROGRESS": {"PAUSE", "COMPLETE", "CANCEL"},
        "PAUSED": {"RESUME", "COMPLETE", "CANCEL"},
        "COMPLETED": set(),
        "CANCELLED": set(),
    }
    if action not in allowed.get(item.status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot {action.lower()} a session in {item.status} status")
    if action == "START":
        item.status = "IN_PROGRESS"
        item.started_at = item.started_at or now()
        item.paused_at = None
    elif action == "PAUSE":
        item.status = "PAUSED"
        item.paused_at = now()
    elif action == "RESUME":
        item.status = "IN_PROGRESS"
        item.paused_at = None
    elif action == "COMPLETE":
        item.status = "COMPLETED"
        item.ended_at = now()
    elif action == "CANCEL":
        item.status = "CANCELLED"
        item.ended_at = now()
    patient = db.get(Patient, item.patient_id)
    facility = db.get(Facility, item.facility_id)
    db.add(IntegrationEvent(
        system="Workflow Notification Service", event_type=f"TELEHEALTH_{action}", resource_type="TelehealthSession",
        resource_id=item.session_id, payload_json=json.dumps({"status": item.status, "note": payload.note}),
    ))
    write_audit(db, action=f"TELEHEALTH_{action}", resource_type="TelehealthSession", resource_id=item.session_id, actor=payload.actor, role="Telehealth", patient_mpi_id=patient.mpi_id, facility_code=facility.code, details=payload.note)
    db.commit()
    return {"session_id": item.session_id, "status": item.status, "started_at": item.started_at, "ended_at": item.ended_at}


@router.get("/module-activities")
def module_activities(module_code: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    query = select(ModuleActivity)
    if module_code:
        query = query.where(ModuleActivity.module_code == module_code.upper())
    if status:
        query = query.where(ModuleActivity.status == status.upper())
    items = list(db.scalars(query.order_by(ModuleActivity.created_at.desc())).all())
    return [{
        "activity_id": x.activity_id,
        "module_code": x.module_code,
        "activity_type": x.activity_type,
        "title": x.title,
        "status": x.status,
        "priority": x.priority,
        "assigned_to": x.assigned_to,
        "details": x.details,
        "payload": json.loads(x.payload_json or "{}"),
        "patient": patient_brief(db, x.patient_id) if x.patient_id else None,
        "encounter": encounter_brief(db, x.encounter_id),
        "created_by": x.created_by,
        "created_at": x.created_at,
        "updated_at": x.updated_at,
    } for x in items]


@router.post("/module-activities", status_code=201)
def create_module_activity(payload: ModuleActivityIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id) if payload.patient_mpi_id else None
    encounter = get_encounter(db, payload.encounter_id) if payload.encounter_id else None
    item = ModuleActivity(
        module_code=payload.module_code.upper(),
        activity_type=payload.activity_type,
        title=payload.title,
        patient_id=patient.id if patient else None,
        encounter_id=encounter.id if encounter else None,
        priority=payload.priority,
        assigned_to=payload.assigned_to,
        details=payload.details,
        payload_json=json.dumps(payload.payload),
        created_by=payload.created_by,
    )
    db.add(item)
    db.flush()
    write_audit(db, action="CREATE_MODULE_ACTIVITY", resource_type=payload.module_code.upper(), resource_id=item.activity_id, actor=payload.created_by, role=payload.module_code.upper(), patient_mpi_id=patient.mpi_id if patient else None, facility_code=encounter.facility.code if encounter else None, details=payload.title)
    db.commit()
    return {"activity_id": item.activity_id, "status": item.status}


@router.patch("/module-activities/{activity_id}")
def update_module_activity(activity_id: str, payload: ModuleActivityUpdateIn, db: Session = Depends(get_db)):
    item = db.scalar(select(ModuleActivity).where(ModuleActivity.activity_id == activity_id))
    if not item:
        raise HTTPException(status_code=404, detail="Module activity not found")
    item.status = payload.status
    if payload.assigned_to is not None:
        item.assigned_to = payload.assigned_to
    if payload.status == "COMPLETED":
        item.completed_at = now()
    patient = db.get(Patient, item.patient_id) if item.patient_id else None
    encounter = db.get(Encounter, item.encounter_id) if item.encounter_id else None
    write_audit(db, action="UPDATE_MODULE_ACTIVITY", resource_type=item.module_code, resource_id=item.activity_id, actor=payload.actor, role=item.module_code, patient_mpi_id=patient.mpi_id if patient else None, facility_code=encounter.facility.code if encounter else None, details=payload.note or payload.status)
    db.commit()
    return {"activity_id": item.activity_id, "status": item.status}


@router.get("/enterprise/summary")
def enterprise_summary(facility_code: str | None = None, db: Session = Depends(get_db)):
    facility = None
    if facility_code and facility_code != "ALL":
        facility = get_facility(db, facility_code)
    encounter_query = select(func.count(Encounter.id))
    if facility:
        encounter_query = encounter_query.where(Encounter.facility_id == facility.id)
    active_encounters = db.scalar(encounter_query.where(Encounter.discharge_at.is_(None))) or 0
    appointment_query = select(func.count(Appointment.id)).where(Appointment.scheduled_start >= now() - timedelta(hours=12), Appointment.scheduled_start <= now() + timedelta(hours=24))
    if facility:
        appointment_query = appointment_query.where(Appointment.facility_id == facility.id)
    bed_query = select(Bed)
    if facility:
        bed_query = bed_query.where(Bed.facility_id == facility.id)
    beds = list(db.scalars(bed_query).all())
    return {
        "active_encounters": active_encounters,
        "appointments_36h": db.scalar(appointment_query) or 0,
        "open_referrals": db.scalar(select(func.count(Referral.id)).where(Referral.status.not_in(["CLOSED", "DECLINED"]))) or 0,
        "open_work_items": db.scalar(select(func.count(WorkItem.id)).where(WorkItem.status.in_(["OPEN", "IN_PROGRESS"]))) or 0,
        "unsigned_notes": db.scalar(select(func.count(ClinicalNote.id)).where(ClinicalNote.status == "DRAFT")) or 0,
        "medications_unverified": db.scalar(select(func.count(MedicationOrder.id)).where(MedicationOrder.status == "ACTIVE", MedicationOrder.verified_at.is_(None))) or 0,
        "claim_denials": db.scalar(select(func.count(Claim.id)).where(Claim.status == "DENIED")) or 0,
        "claim_value": money(db.scalar(select(func.sum(Claim.amount)).where(Claim.status.in_(["READY", "SUBMITTED", "ACCEPTED", "DENIED"])))),
        "stockout_risks": db.scalar(select(func.count(InventoryItem.id)).where(InventoryItem.on_hand <= InventoryItem.reorder_level)) or 0,
        "open_telehealth_sessions": db.scalar(select(func.count(TelehealthSession.id)).where(TelehealthSession.status.in_(["SCHEDULED", "READY", "IN_PROGRESS", "PAUSED"]))) or 0,
        "beds": {
            "total": len(beds),
            "available": sum(1 for b in beds if b.status == "AVAILABLE"),
            "occupied": sum(1 for b in beds if b.status == "OCCUPIED"),
            "dirty": sum(1 for b in beds if b.status in {"DIRTY", "CLEANING"}),
            "blocked": sum(1 for b in beds if b.status == "BLOCKED"),
        },
    }


@router.get("/analytics/summary")
def analytics_summary(facility_code: str | None = None, db: Session = Depends(get_db)):
    return enterprise_summary(facility_code=facility_code, db=db)


@router.get("/appointments")
def appointments(
    facility_code: str | None = None,
    status: str | None = None,
    from_hours: int = Query(default=-12, ge=-720, le=720),
    to_hours: int = Query(default=168, ge=1, le=2160),
    db: Session = Depends(get_db),
):
    query = select(Appointment).where(
        Appointment.scheduled_start >= now() + timedelta(hours=from_hours),
        Appointment.scheduled_start <= now() + timedelta(hours=to_hours),
    )
    if facility_code and facility_code != "ALL":
        query = query.where(Appointment.facility_id == get_facility(db, facility_code).id)
    if status:
        query = query.where(Appointment.status == status)
    items = list(db.scalars(query.order_by(Appointment.scheduled_start)).all())
    output = []
    for item in items:
        facility = db.get(Facility, item.facility_id)
        output.append({
            "appointment_id": item.appointment_id,
            "patient": patient_brief(db, item.patient_id),
            "facility": {"code": facility.code, "name": facility.name},
            "service": item.service,
            "provider": item.provider,
            "appointment_type": item.appointment_type,
            "scheduled_start": item.scheduled_start,
            "scheduled_end": item.scheduled_end,
            "status": item.status,
            "notes": item.notes,
            "history": [{"event_id": event.event_id, "status_before": event.status_before, "status_after": event.status_after, "reason": event.reason, "actor": event.actor, "occurred_at": event.occurred_at} for event in db.scalars(select(AppointmentStatusEvent).where(AppointmentStatusEvent.appointment_id == item.id).order_by(AppointmentStatusEvent.occurred_at.desc())).all()],
        })
    return output


@router.post("/appointments", status_code=201)
def create_appointment(payload: AppointmentIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    if payload.appointment_type.upper() == "PRIVATE_NAMED_PROVIDER" and not (payload.provider or "").strip():
        raise HTTPException(status_code=422, detail="A named provider is required for private-provider scheduling")
    if payload.appointment_type.upper() == "PUBLIC_DUTY_ROSTER" and not (payload.provider or "").strip():
        payload.provider = "Duty roster / next available clinician"
    facility = get_facility(db, payload.facility_code)
    item = Appointment(
        patient_id=patient.id,
        facility_id=facility.id,
        service=payload.service,
        provider=payload.provider,
        appointment_type=payload.appointment_type,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_start + timedelta(minutes=payload.duration_minutes),
        notes=payload.notes,
        created_by=payload.created_by,
    )
    db.add(item)
    db.flush()
    record_managed_event(db, entity_type="APPOINTMENT", entity_id=item.appointment_id, action="CREATE", actor=payload.created_by, status_before="NONE", status_after=item.status, patient_id=patient.id, reason=payload.notes, reversible=True, metadata={"facility_code": facility.code, "service": item.service, "scheduled_start": item.scheduled_start})
    db.add(WorkItem(queue="SCHEDULING", task_type="APPOINTMENT_CONFIRMATION", subject=f"Confirm {payload.service} appointment", patient_id=patient.id, priority="ROUTINE", assigned_to="Scheduling Pool", due_at=payload.scheduled_start - timedelta(hours=24), created_by=payload.created_by))
    db.add(IntegrationEvent(system="Workflow Notification Service", event_type="APPOINTMENT_CREATED", resource_type="Appointment", resource_id=item.appointment_id, payload_json=json.dumps({"patient": patient.mpi_id, "start": payload.scheduled_start.isoformat()})))
    write_audit(db, action="CREATE_APPOINTMENT", resource_type="Appointment", resource_id=item.appointment_id, actor=payload.created_by, role="Scheduling", patient_mpi_id=patient.mpi_id, facility_code=facility.code)
    db.commit()
    return {"appointment_id": item.appointment_id, "status": item.status}


@router.patch("/appointments/{appointment_id}")
def update_appointment(appointment_id: str, payload: StatusIn, db: Session = Depends(get_db)):
    item = db.scalar(select(Appointment).where(Appointment.appointment_id == appointment_id))
    if not item:
        raise HTTPException(status_code=404, detail="Appointment not found")
    requested = payload.status.upper().strip()
    current = item.status.upper()
    transitions = {
        "SCHEDULED": {"CONFIRMED", "ARRIVED", "CANCELLED", "NO_SHOW"},
        "CONFIRMED": {"ARRIVED", "CANCELLED", "NO_SHOW"},
        "CANCELLED": {"REINSTATED"},
        "NO_SHOW": {"REINSTATED"},
        "ARRIVED": set(),
    }
    if requested not in transitions.get(current, set()):
        raise HTTPException(status_code=409, detail=f"Cannot change appointment from {current} to {requested}")
    if requested in {"CANCELLED", "REINSTATED"} and not (payload.note or "").strip():
        raise HTTPException(status_code=422, detail="A reason is required to cancel or reinstate an appointment")
    next_status = "SCHEDULED" if requested == "REINSTATED" else requested
    item.status = next_status
    patient = db.get(Patient, item.patient_id)
    facility = db.get(Facility, item.facility_id)
    event = AppointmentStatusEvent(appointment_id=item.id, status_before=current, status_after=next_status, reason=(payload.note or requested).strip(), actor=payload.actor)
    db.add(event)
    encounter_public_id = None
    notification = None
    if requested == "ARRIVED":
        encounter = db.scalar(select(Encounter).where(Encounter.patient_id == item.patient_id, Encounter.facility_id == item.facility_id, Encounter.service == item.service, Encounter.discharge_at.is_(None)).order_by(Encounter.arrival_at.desc()))
        if not encounter:
            encounter = Encounter(patient_id=item.patient_id, facility_id=item.facility_id, encounter_type="OUTPATIENT", service=item.service, status=EncounterStatus.ARRIVED, acuity="Not assigned", location="Arrival Desk", provider=item.provider, reason_for_visit=item.notes or f"Scheduled {item.service} visit", arrival_at=now())
            db.add(encounter)
            db.flush()
        encounter_public_id = encounter.encounter_id
        notification = {
            "type": "PATIENT_ARRIVED",
            "duration_ms": 1000,
            "title": "Patient arrived",
            "message": f"{patient.full_name} arrived for {item.service}",
            "patient_mpi_id": patient.mpi_id,
            "encounter_id": encounter.encounter_id,
        }
        db.add(IntegrationEvent(system="WORKFLOW", event_type="PATIENT_ARRIVED", resource_type="Encounter", resource_id=encounter.encounter_id, payload_json=json.dumps(notification)))
    record_managed_event(db, entity_type="APPOINTMENT", entity_id=item.appointment_id, action=requested, actor=payload.actor, status_before=current, status_after=next_status, patient_id=patient.id, encounter_id=encounter.id if requested == "ARRIVED" and encounter_public_id else None, reason=payload.note, reversible=True, metadata={"notification": notification})
    write_audit(db, action=f"APPOINTMENT_{requested}", resource_type="Appointment", resource_id=item.appointment_id, actor=payload.actor, role="Scheduling", patient_mpi_id=patient.mpi_id, facility_code=facility.code, details=payload.note or next_status)
    db.commit()
    return {"appointment_id": item.appointment_id, "status": item.status, "encounter_id": encounter_public_id, "notification": notification}


@router.get("/referrals")
def referrals(status: str | None = None, facility_code: str | None = None, db: Session = Depends(get_db)):
    query = select(Referral)
    if status:
        query = query.where(Referral.status == status)
    if facility_code and facility_code != "ALL":
        query = query.where((Referral.destination_facility_code == facility_code) | (Referral.source_facility_code == facility_code))
    items = list(db.scalars(query.order_by(Referral.requested_at.desc())).all())
    return [{
        "referral_id": x.referral_id,
        "patient": patient_brief(db, x.patient_id),
        "source_facility_code": x.source_facility_code,
        "destination_facility_code": x.destination_facility_code,
        "service": x.service,
        "priority": x.priority,
        "reason": x.reason,
        "status": x.status,
        "requested_by": x.requested_by,
        "accepted_by": x.accepted_by,
        "appointment_id": x.appointment_id,
        "closure_summary": x.closure_summary,
        "requested_at": x.requested_at,
    } for x in items]


@router.post("/referrals", status_code=201)
def create_referral(payload: ReferralIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    get_facility(db, payload.source_facility_code)
    get_facility(db, payload.destination_facility_code)
    item = Referral(patient_id=patient.id, **payload.model_dump(exclude={"patient_mpi_id"}))
    db.add(item)
    db.flush()
    db.add(WorkItem(queue=f"REFERRAL-{payload.destination_facility_code}", task_type="REFERRAL_REVIEW", subject=f"{payload.priority} referral to {payload.service}", details=payload.reason, patient_id=patient.id, priority=payload.priority, assigned_to="Referral Intake Pool", created_by=payload.requested_by))
    db.add(IntegrationEvent(system="National HIE", event_type="REFERRAL_CREATED", resource_type="ServiceRequest", resource_id=item.referral_id, payload_json=json.dumps({"patient": patient.mpi_id, "destination": payload.destination_facility_code})))
    write_audit(db, action="CREATE_REFERRAL", resource_type="Referral", resource_id=item.referral_id, actor=payload.requested_by, role="Provider", patient_mpi_id=patient.mpi_id, facility_code=payload.source_facility_code)
    db.commit()
    return {"referral_id": item.referral_id, "status": item.status}


@router.patch("/referrals/{referral_id}")
def update_referral(referral_id: str, payload: StatusIn, db: Session = Depends(get_db)):
    item = db.scalar(select(Referral).where(Referral.referral_id == referral_id))
    if not item:
        raise HTTPException(status_code=404, detail="Referral not found")
    item.status = payload.status.upper()
    if item.status == "ACCEPTED":
        item.accepted_by = payload.actor
    if item.status == "CLOSED":
        item.closure_summary = payload.note
    patient = db.get(Patient, item.patient_id)
    write_audit(db, action="UPDATE_REFERRAL", resource_type="Referral", resource_id=item.referral_id, actor=payload.actor, role="Referral", patient_mpi_id=patient.mpi_id, facility_code=item.destination_facility_code, details=payload.note or item.status)
    db.commit()
    return {"referral_id": item.referral_id, "status": item.status}


@router.get("/beds")
def beds(facility_code: str | None = None, unit: str | None = None, db: Session = Depends(get_db)):
    query = select(Bed)
    if facility_code and facility_code != "ALL":
        query = query.where(Bed.facility_id == get_facility(db, facility_code).id)
    if unit:
        query = query.where(Bed.unit == unit)
    items = list(db.scalars(query.order_by(Bed.unit, Bed.room, Bed.bed_label)).all())
    output = []
    for item in items:
        facility = db.get(Facility, item.facility_id)
        encounter = encounter_brief(db, item.encounter_id)
        patient = None
        if item.encounter_id:
            enc = db.get(Encounter, item.encounter_id)
            patient = patient_brief(db, enc.patient_id) if enc else None
        output.append({
            "bed_id": item.bed_id,
            "facility": {"code": facility.code, "name": facility.name},
            "unit": item.unit,
            "room": item.room,
            "bed_label": item.bed_label,
            "bed_type": item.bed_type,
            "status": item.status,
            "isolation": item.isolation,
            "encounter": encounter,
            "patient": patient,
        })
    return output


@router.post("/beds/{bed_id}/actions")
def bed_action(bed_id: str, payload: BedActionIn, db: Session = Depends(get_db)):
    bed = db.scalar(select(Bed).where(Bed.bed_id == bed_id))
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    facility = db.get(Facility, bed.facility_id)
    encounter = get_encounter(db, payload.encounter_id) if payload.encounter_id else None
    if payload.action in {"ASSIGN", "OCCUPY"}:
        if not encounter:
            raise HTTPException(status_code=400, detail="Encounter ID required")
        if bed.status not in {"AVAILABLE", "ASSIGNED"} and bed.encounter_id != encounter.id:
            raise HTTPException(status_code=409, detail="Bed is not available")
        bed.encounter_id = encounter.id
        bed.status = "OCCUPIED" if payload.action == "OCCUPY" else "ASSIGNED"
        bed.assigned_at = now()
        encounter.location = bed.unit
        encounter.room = f"{bed.room} / {bed.bed_label}"
    elif payload.action == "MARK_DIRTY":
        bed.status = "DIRTY"
        bed.encounter_id = None
    elif payload.action == "START_CLEANING":
        bed.status = "CLEANING"
    elif payload.action in {"MARK_AVAILABLE", "UNBLOCK"}:
        bed.status = "AVAILABLE"
        bed.encounter_id = None
        bed.isolation = None
    elif payload.action == "BLOCK":
        bed.status = "BLOCKED"
        bed.isolation = payload.reason or "Operational block"
    write_audit(db, action=f"BED_{payload.action}", resource_type="Bed", resource_id=bed.bed_id, actor=payload.actor, role="Hospital Operations", patient_mpi_id=(encounter.patient.mpi_id if encounter else None), facility_code=facility.code, details=payload.reason)
    db.commit()
    return {"bed_id": bed.bed_id, "status": bed.status, "encounter_id": encounter.encounter_id if encounter else None}


NOTE_TEMPLATES = [
    {
        "code": "PROGRESS_NOTE",
        "name": "Progress Note",
        "group": "General Clinical",
        "title": "Progress Note",
        "body": "Subjective:\n\nObjective:\n- Vitals:\n- Examination:\n- Relevant results:\n\nAssessment:\n\nPlan:\n1. ",
    },
    {
        "code": "HISTORY_AND_PHYSICAL",
        "name": "History and Physical",
        "group": "Admission",
        "title": "Admission History and Physical",
        "body": "Chief complaint:\n\nHistory of present illness:\n\nPast medical and surgical history:\n\nMedications and allergies:\n\nSocial and family history:\n\nReview of systems:\n\nExamination:\n\nAssessment and differential diagnosis:\n\nPlan:\n",
    },
    {
        "code": "ED_PROVIDER_NOTE",
        "name": "Emergency Provider Note",
        "group": "Emergency",
        "title": "Emergency Department Provider Note",
        "body": "Arrival / triage summary:\n\nPresenting complaint and onset:\n\nPrimary survey / immediate threats:\n\nFocused history and examination:\n\nInvestigations reviewed:\n\nInterventions and response:\n\nClinical impression:\n\nDisposition and handoff:\n",
    },
    {
        "code": "NURSING_SHIFT_NOTE",
        "name": "Nursing Shift Note",
        "group": "Nursing",
        "title": "Nursing Shift Note",
        "body": "Shift assessment:\n\nSafety / fall precautions:\n\nMobility, hygiene and skin care:\n\nIntake and output:\n\nPain and symptom management:\n\nLines, drains, wounds and devices:\n\nEducation / family communication:\n\nEscalations and handoff:\n",
    },
    {
        "code": "PROCEDURE_NOTE",
        "name": "Procedure Note",
        "group": "Procedures",
        "title": "Procedure Note",
        "body": "Procedure:\n\nIndication:\n\nConsent / emergency basis:\n\nTime-out and site verification:\n\nTechnique and findings:\n\nSpecimens / devices:\n\nComplications:\n\nEstimated blood loss:\n\nPost-procedure plan:\n",
    },
    {
        "code": "CONSULT_NOTE",
        "name": "Consultation Note",
        "group": "Consults",
        "title": "Specialist Consultation",
        "body": "Reason for consultation:\n\nClinical summary:\n\nKey findings:\n\nAssessment:\n\nRecommendations:\n\nCommunication with requesting team:\n",
    },
    {
        "code": "DISCHARGE_SUMMARY",
        "name": "Discharge Summary",
        "group": "Transitions of Care",
        "title": "Discharge Summary",
        "body": "Admission diagnosis:\n\nDischarge diagnosis:\n\nHospital course:\n\nProcedures and significant results:\n\nCondition at discharge:\n\nDischarge medications:\n\nFollow-up and pending results:\n\nPatient / family instructions and warning signs:\n",
    },
    {
        "code": "DEATH_PRONOUNCEMENT",
        "name": "Death Pronouncement Note",
        "group": "Patient Status",
        "title": "Death Pronouncement Note",
        "body": "Date and time assessed:\n\nClinical circumstances:\n\nExamination confirming death:\n\nTime of death:\n\nPersons notified:\n\nMedical certification / mortuary disposition:\n",
    },
]

SMART_PHRASES = [
    {"code": ".NORMALGEN", "label": "Normal general examination", "text": "Patient is alert, oriented and in no acute distress. Airway is patent, breathing is unlaboured, and perfusion is clinically adequate."},
    {"code": ".SAFETY", "label": "Safety and identity check", "text": "Patient identity, active encounter, allergies and current medication list were reviewed before proceeding."},
    {"code": ".HANDOFF", "label": "Structured handoff", "text": "Situation, background, assessment and recommended next actions were communicated to the receiving team; questions were answered."},
    {"code": ".EDRETURN", "label": "Emergency return precautions", "text": "Return immediately for worsening symptoms, breathing difficulty, chest pain, altered consciousness, uncontrolled bleeding, persistent vomiting or any new concerning change."},
    {"code": ".INTERPRETER", "label": "Language support", "text": "The encounter was conducted in the patient's preferred language with language assistance as required; understanding was confirmed using teach-back."},
]


@router.get("/notes/templates")
def note_templates():
    return {"templates": NOTE_TEMPLATES, "smart_phrases": SMART_PHRASES}


@router.get("/notes")
def notes(patient_mpi_id: str | None = None, encounter_id: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    query = select(ClinicalNote)
    if patient_mpi_id:
        query = query.where(ClinicalNote.patient_id == get_patient(db, patient_mpi_id).id)
    if encounter_id:
        query = query.where(ClinicalNote.encounter_id == get_encounter(db, encounter_id).id)
    if status:
        query = query.where(ClinicalNote.status == status)
    items = list(db.scalars(query.order_by(ClinicalNote.created_at.desc())).all())
    return [{
        "note_id": x.note_id,
        "patient": patient_brief(db, x.patient_id),
        "encounter": encounter_brief(db, x.encounter_id),
        "note_type": x.note_type,
        "title": x.title,
        "status": x.status,
        "author": x.author,
        "service": x.service,
        "body": x.body,
        "cosign_required": x.cosign_required,
        "signed_by": x.signed_by,
        "created_at": x.created_at,
        "signed_at": x.signed_at,
        "amended_at": x.amended_at,
        "source_audio_session_id": x.source_audio_session_id,
    } for x in items]


@router.post("/notes", status_code=201)
def create_note(payload: NoteIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    encounter = get_encounter(db, payload.encounter_id)
    if encounter.patient_id != patient.id:
        raise HTTPException(status_code=409, detail="Encounter does not belong to patient")
    validate_audio_note_context(
        db,
        patient=patient,
        encounter=encounter,
        source_audio_session_id=payload.source_audio_session_id,
    )
    note = ClinicalNote(patient_id=patient.id, encounter_id=encounter.id, **payload.model_dump(exclude={"patient_mpi_id", "encounter_id"}))
    db.add(note)
    db.flush()
    if note.cosign_required:
        db.add(WorkItem(queue="COSIGN", task_type="NOTE_COSIGN", subject=f"Cosign {note.note_type}: {note.title}", patient_id=patient.id, encounter_id=encounter.id, priority="ROUTINE", assigned_to="Supervising Provider Pool", created_by=note.author))
    record_managed_event(db, entity_type="CLINICAL_NOTE", entity_id=note.note_id, action="CREATE_DRAFT", actor=note.author, status_before="NONE", status_after=note.status, patient_id=patient.id, encounter_id=encounter.id, reason=note.title, reversible=True, metadata={"note_type": note.note_type, "service": note.service})
    write_audit(db, action="CREATE_NOTE", resource_type="ClinicalNote", resource_id=note.note_id, actor=note.author, role="Provider", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code)
    db.commit()
    return {"note_id": note.note_id, "status": note.status}


@router.patch("/notes/{note_id}")
def update_note(note_id: str, payload: NoteUpdateIn, db: Session = Depends(get_db)):
    note = db.scalar(select(ClinicalNote).where(ClinicalNote.note_id == note_id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Signed or finalized notes cannot be edited; create an addendum")
    before = {"title": note.title, "body": note.body, "note_type": note.note_type, "service": note.service, "cosign_required": note.cosign_required, "source_audio_session_id": note.source_audio_session_id}
    changes = payload.model_dump(exclude={"actor"}, exclude_none=True)
    patient = db.get(Patient, note.patient_id)
    encounter = db.get(Encounter, note.encounter_id)
    if "source_audio_session_id" in changes:
        validate_audio_note_context(
            db,
            patient=patient,
            encounter=encounter,
            source_audio_session_id=changes["source_audio_session_id"],
        )
    for field, value in changes.items():
        setattr(note, field, value)
    record_managed_event(db, entity_type="CLINICAL_NOTE", entity_id=note.note_id, action="EDIT_DRAFT", actor=payload.actor, status_before=note.status, status_after=note.status, patient_id=patient.id, encounter_id=encounter.id, reason="Draft note updated", reversible=True, metadata={"before": before, "after": changes})
    write_audit(db, action="UPDATE_NOTE_DRAFT", resource_type="ClinicalNote", resource_id=note.note_id, actor=payload.actor, role="Provider", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code, details="Draft note updated")
    db.commit()
    return {"note_id": note.note_id, "status": note.status, "updated": list(changes)}


@router.post("/notes/{note_id}/addendum")
def add_note_addendum(note_id: str, payload: NoteAddendumIn, db: Session = Depends(get_db)):
    note = db.scalar(select(ClinicalNote).where(ClinicalNote.note_id == note_id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.status != "SIGNED":
        raise HTTPException(status_code=409, detail="Addenda are only permitted for signed notes")
    previous_body = note.body
    timestamp = now().strftime("%Y-%m-%d %H:%M UTC")
    note.body = f"{note.body}\n\n--- ADDENDUM {timestamp} by {payload.author} ---\n{payload.text}"
    note.amended_at = now()
    patient = db.get(Patient, note.patient_id)
    encounter = db.get(Encounter, note.encounter_id)
    record_managed_event(db, entity_type="CLINICAL_NOTE", entity_id=note.note_id, action="ADDENDUM", actor=payload.author, status_before="SIGNED", status_after="SIGNED", patient_id=patient.id, encounter_id=encounter.id, reason=payload.reason, reversible=False, metadata={"previous_body": previous_body, "addendum": payload.text})
    write_audit(db, action="ADD_NOTE_ADDENDUM", resource_type="ClinicalNote", resource_id=note.note_id, actor=payload.author, role="Provider", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code, details=payload.reason)
    db.commit()
    return {"note_id": note.note_id, "status": note.status, "amended_at": note.amended_at}


@router.get("/notes/{note_id}/history")
def note_history(note_id: str, db: Session = Depends(get_db)):
    note = db.scalar(select(ClinicalNote).where(ClinicalNote.note_id == note_id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    events = list(db.scalars(select(ManagedEvent).where(ManagedEvent.entity_type == "CLINICAL_NOTE", ManagedEvent.entity_id == note_id).order_by(ManagedEvent.occurred_at.desc())).all())
    return [{"event_id": e.event_id, "action": e.action, "actor": e.actor, "status_before": e.status_before, "status_after": e.status_after, "reason": e.reason, "occurred_at": e.occurred_at, "metadata": json.loads(e.metadata_json or "{}") if isinstance(e.metadata_json, str) else (e.metadata_json or {})} for e in events]


@router.post("/notes/{note_id}/sign")
def sign_note(note_id: str, payload: NoteSignIn, db: Session = Depends(get_db)):
    note = db.scalar(select(ClinicalNote).where(ClinicalNote.note_id == note_id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.status == "SIGNED":
        raise HTTPException(status_code=409, detail="Note is already signed")
    note.status = "SIGNED"
    note.signed_by = payload.signer
    note.signed_at = now()
    patient = db.get(Patient, note.patient_id)
    encounter = db.get(Encounter, note.encounter_id)
    record_managed_event(db, entity_type="CLINICAL_NOTE", entity_id=note.note_id, action="SIGN", actor=payload.signer, status_before="DRAFT", status_after="SIGNED", patient_id=patient.id, encounter_id=encounter.id, reason=payload.attestation or "Electronic signature", reversible=False, metadata={"cosign_required": note.cosign_required})
    write_audit(db, action="SIGN_NOTE", resource_type="ClinicalNote", resource_id=note.note_id, actor=payload.signer, role="Provider", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code, details=payload.attestation)
    db.commit()
    return {"note_id": note.note_id, "status": note.status, "signed_at": note.signed_at}


@router.get("/medications")
def medications(patient_mpi_id: str | None = None, encounter_id: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    query = select(MedicationOrder)
    if patient_mpi_id:
        query = query.where(MedicationOrder.patient_id == get_patient(db, patient_mpi_id).id)
    if encounter_id:
        query = query.where(MedicationOrder.encounter_id == get_encounter(db, encounter_id).id)
    if status:
        query = query.where(MedicationOrder.status == status)
    items = list(db.scalars(query.order_by(MedicationOrder.created_at.desc())).all())
    output = []
    for x in items:
        administrations = list(db.scalars(select(MedicationAdministration).where(MedicationAdministration.medication_order_id == x.id).order_by(MedicationAdministration.administered_at.desc())).all())
        output.append({
            "medication_order_id": x.medication_order_id,
            "patient": patient_brief(db, x.patient_id),
            "encounter": encounter_brief(db, x.encounter_id),
            "medication_name": x.medication_name,
            "dose": x.dose,
            "route": x.route,
            "frequency": x.frequency,
            "status": x.status,
            "indication": x.indication,
            "ordered_by": x.ordered_by,
            "verified_by": x.verified_by,
            "verified_at": x.verified_at,
            "administrations": [{
                "administration_id": a.administration_id,
                "action": a.action,
                "dose_given": a.dose_given,
                "administered_by": a.administered_by,
                "reason": a.reason,
                "barcode_verified": a.barcode_verified,
                "administered_at": a.administered_at,
            } for a in administrations[:10]],
        })
    return output


@router.post("/medications", status_code=201)
def create_medication(payload: MedicationIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    encounter = get_encounter(db, payload.encounter_id)
    if encounter.patient_id != patient.id:
        raise HTTPException(status_code=409, detail="Encounter does not belong to patient")
    item = MedicationOrder(patient_id=patient.id, encounter_id=encounter.id, **payload.model_dump(exclude={"patient_mpi_id", "encounter_id"}))
    db.add(item)
    db.flush()
    db.add(WorkItem(queue="PHARMACY-VERIFY", task_type="MEDICATION_VERIFICATION", subject=f"Verify {item.medication_name} {item.dose}", patient_id=patient.id, encounter_id=encounter.id, priority="ROUTINE", assigned_to="Pharmacy Verification Pool", created_by=payload.ordered_by))
    write_audit(db, action="ORDER_MEDICATION", resource_type="MedicationOrder", resource_id=item.medication_order_id, actor=payload.ordered_by, role="Provider", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code)
    db.commit()
    return {"medication_order_id": item.medication_order_id, "status": item.status}


@router.post("/medications/{medication_order_id}/verify")
def verify_medication(medication_order_id: str, payload: MedicationVerifyIn, db: Session = Depends(get_db)):
    item = db.scalar(select(MedicationOrder).where(MedicationOrder.medication_order_id == medication_order_id))
    if not item:
        raise HTTPException(status_code=404, detail="Medication order not found")
    item.verified_by = payload.pharmacist
    item.verified_at = now()
    patient = db.get(Patient, item.patient_id)
    encounter = db.get(Encounter, item.encounter_id)
    write_audit(db, action="VERIFY_MEDICATION", resource_type="MedicationOrder", resource_id=item.medication_order_id, actor=payload.pharmacist, role="Pharmacy", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code)
    db.commit()
    return {"medication_order_id": item.medication_order_id, "verified_at": item.verified_at}


@router.post("/medications/{medication_order_id}/administrations", status_code=201)
def administer_medication(medication_order_id: str, payload: AdministrationIn, db: Session = Depends(get_db)):
    item = db.scalar(select(MedicationOrder).where(MedicationOrder.medication_order_id == medication_order_id))
    if not item:
        raise HTTPException(status_code=404, detail="Medication order not found")
    if payload.action == "GIVEN" and not item.verified_at:
        raise HTTPException(status_code=409, detail="Medication must be pharmacist-verified before administration")
    administration = MedicationAdministration(medication_order_id=item.id, **payload.model_dump())
    db.add(administration)
    db.flush()
    patient = db.get(Patient, item.patient_id)
    encounter = db.get(Encounter, item.encounter_id)
    write_audit(db, action=f"MAR_{payload.action}", resource_type="MedicationAdministration", resource_id=administration.administration_id, actor=payload.administered_by, role="Nursing", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code, details=payload.reason)
    db.commit()
    return {"administration_id": administration.administration_id, "action": administration.action, "administered_at": administration.administered_at}


@router.get("/work-items")
def work_items(queue: str | None = None, status: str | None = None, patient_mpi_id: str | None = None, db: Session = Depends(get_db)):
    query = select(WorkItem)
    if queue:
        query = query.where(WorkItem.queue == queue)
    if status:
        query = query.where(WorkItem.status == status)
    if patient_mpi_id:
        query = query.where(WorkItem.patient_id == get_patient(db, patient_mpi_id).id)
    items = list(db.scalars(query.order_by(WorkItem.due_at.is_(None), WorkItem.due_at, WorkItem.created_at.desc())).all())
    return [{
        "work_item_id": x.work_item_id,
        "queue": x.queue,
        "task_type": x.task_type,
        "subject": x.subject,
        "details": x.details,
        "priority": x.priority,
        "status": x.status,
        "assigned_to": x.assigned_to,
        "due_at": x.due_at,
        "patient": patient_brief(db, x.patient_id) if x.patient_id else None,
        "encounter": encounter_brief(db, x.encounter_id),
        "created_by": x.created_by,
        "created_at": x.created_at,
    } for x in items]


@router.post("/work-items", status_code=201)
def create_work_item(payload: WorkItemIn, db: Session = Depends(get_db)):
    patient_id = get_patient(db, payload.patient_mpi_id).id if payload.patient_mpi_id else None
    encounter_id = get_encounter(db, payload.encounter_id).id if payload.encounter_id else None
    item = WorkItem(patient_id=patient_id, encounter_id=encounter_id, **payload.model_dump(exclude={"patient_mpi_id", "encounter_id"}))
    db.add(item)
    db.commit()
    return {"work_item_id": item.work_item_id, "status": item.status}


@router.patch("/work-items/{work_item_id}")
def update_work_item(work_item_id: str, payload: WorkItemUpdateIn, db: Session = Depends(get_db)):
    item = db.scalar(select(WorkItem).where(WorkItem.work_item_id == work_item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Work item not found")
    item.status = payload.status
    if payload.assigned_to is not None:
        item.assigned_to = payload.assigned_to
    if payload.status == "COMPLETED":
        item.completed_at = now()
    patient = db.get(Patient, item.patient_id) if item.patient_id else None
    write_audit(db, action="UPDATE_WORK_ITEM", resource_type="WorkItem", resource_id=item.work_item_id, actor=payload.actor, role="Work Queue", patient_mpi_id=patient.mpi_id if patient else None, details=payload.note or payload.status)
    db.commit()
    return {"work_item_id": item.work_item_id, "status": item.status}


@router.get("/charges")
def charges(patient_mpi_id: str | None = None, encounter_id: str | None = None, db: Session = Depends(get_db)):
    query = select(Charge)
    if patient_mpi_id:
        query = query.where(Charge.patient_id == get_patient(db, patient_mpi_id).id)
    if encounter_id:
        query = query.where(Charge.encounter_id == get_encounter(db, encounter_id).id)
    items = list(db.scalars(query.order_by(Charge.posted_at.desc())).all())
    return [{
        "charge_id": x.charge_id,
        "patient": patient_brief(db, x.patient_id),
        "encounter": encounter_brief(db, x.encounter_id),
        "service_code": x.service_code,
        "description": x.description,
        "quantity": x.quantity,
        "unit_price": money(x.unit_price),
        "total": money(x.unit_price) * x.quantity,
        "status": x.status,
        "payer": x.payer,
        "posted_by": x.posted_by,
        "posted_at": x.posted_at,
    } for x in items]


@router.post("/charges", status_code=201)
def create_charge(payload: ChargeIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    encounter = get_encounter(db, payload.encounter_id)
    item = Charge(patient_id=patient.id, encounter_id=encounter.id, **payload.model_dump(exclude={"patient_mpi_id", "encounter_id"}))
    db.add(item)
    write_audit(db, action="POST_CHARGE", resource_type="Charge", resource_id=item.charge_id, actor=payload.posted_by, role="Revenue Cycle", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code, details=payload.description)
    db.commit()
    return {"charge_id": item.charge_id, "total": payload.quantity * payload.unit_price}


@router.get("/claims")
def claims(status: str | None = None, payer: str | None = None, db: Session = Depends(get_db)):
    query = select(Claim)
    if status:
        query = query.where(Claim.status == status)
    if payer:
        query = query.where(Claim.payer == payer)
    items = list(db.scalars(query.order_by(Claim.updated_at.desc())).all())
    return [{
        "claim_id": x.claim_id,
        "patient": patient_brief(db, x.patient_id),
        "encounter": encounter_brief(db, x.encounter_id),
        "payer": x.payer,
        "member_number": x.member_number,
        "amount": money(x.amount),
        "status": x.status,
        "authorization_number": x.authorization_number,
        "denial_code": x.denial_code,
        "denial_reason": x.denial_reason,
        "submitted_at": x.submitted_at,
        "updated_at": x.updated_at,
    } for x in items]


@router.post("/claims", status_code=201)
def create_claim(payload: ClaimIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    encounter = get_encounter(db, payload.encounter_id)
    item = Claim(patient_id=patient.id, encounter_id=encounter.id, **payload.model_dump(exclude={"patient_mpi_id", "encounter_id"}))
    db.add(item)
    db.commit()
    return {"claim_id": item.claim_id, "status": item.status}


@router.patch("/claims/{claim_id}")
def update_claim(claim_id: str, payload: ClaimStatusIn, db: Session = Depends(get_db)):
    item = db.scalar(select(Claim).where(Claim.claim_id == claim_id))
    if not item:
        raise HTTPException(status_code=404, detail="Claim not found")
    item.status = payload.status
    item.denial_code = payload.denial_code
    item.denial_reason = payload.denial_reason
    if payload.status == "SUBMITTED":
        item.submitted_at = now()
        db.add(IntegrationEvent(system=item.payer, event_type="CLAIM_SUBMITTED", resource_type="Claim", resource_id=item.claim_id, payload_json=json.dumps({"amount": money(item.amount)})))
    patient = db.get(Patient, item.patient_id)
    encounter = db.get(Encounter, item.encounter_id)
    write_audit(db, action="UPDATE_CLAIM", resource_type="Claim", resource_id=item.claim_id, actor=payload.actor, role="Revenue Cycle", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code, details=payload.denial_reason or payload.status)
    db.commit()
    return {"claim_id": item.claim_id, "status": item.status}


@router.post("/payments", status_code=201)
def create_payment(payload: PaymentIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    encounter = get_encounter(db, payload.encounter_id) if payload.encounter_id else None
    item = Payment(patient_id=patient.id, encounter_id=encounter.id if encounter else None, **payload.model_dump(exclude={"patient_mpi_id", "encounter_id"}))
    db.add(item)
    db.add(IntegrationEvent(system="GePG", event_type="PAYMENT_RECEIVED", resource_type="Payment", resource_id=item.payment_id, payload_json=json.dumps({"amount": payload.amount, "method": payload.method})))
    write_audit(db, action="RECEIVE_PAYMENT", resource_type="Payment", resource_id=item.payment_id, actor=payload.received_by, role="Cashier", patient_mpi_id=patient.mpi_id, facility_code=encounter.facility.code if encounter else None, details=payload.method)
    db.commit()
    return {"payment_id": item.payment_id, "amount": payload.amount}


@router.get("/inventory")
def inventory(facility_code: str | None = None, category: str | None = None, risk_only: bool = False, db: Session = Depends(get_db)):
    query = select(InventoryItem)
    if facility_code and facility_code != "ALL":
        query = query.where(InventoryItem.facility_id == get_facility(db, facility_code).id)
    if category:
        query = query.where(InventoryItem.category == category)
    if risk_only:
        query = query.where(InventoryItem.on_hand <= InventoryItem.reorder_level)
    items = list(db.scalars(query.order_by(InventoryItem.category, InventoryItem.item_name)).all())
    return [{
        "item_id": x.item_id,
        "facility": db.get(Facility, x.facility_id).code,
        "item_code": x.item_code,
        "item_name": x.item_name,
        "category": x.category,
        "unit": x.unit,
        "on_hand": x.on_hand,
        "reorder_level": x.reorder_level,
        "stock_status": "CRITICAL" if x.on_hand <= max(1, x.reorder_level // 2) else ("LOW" if x.on_hand <= x.reorder_level else "OK"),
        "batch_number": x.batch_number,
        "expiry_at": x.expiry_at,
        "location": x.location,
    } for x in items]


@router.post("/inventory/{item_id}/transactions", status_code=201)
def inventory_transaction(item_id: str, payload: InventoryTransactionIn, db: Session = Depends(get_db)):
    item = db.scalar(select(InventoryItem).where(InventoryItem.item_id == item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    direction = 1 if payload.transaction_type in {"RECEIPT", "ADJUSTMENT_IN", "TRANSFER_IN"} else -1
    next_on_hand = item.on_hand + direction * payload.quantity
    if next_on_hand < 0:
        raise HTTPException(status_code=409, detail="Insufficient stock")
    item.on_hand = next_on_hand
    transaction = InventoryTransaction(inventory_item_id=item.id, **payload.model_dump())
    db.add(transaction)
    facility = db.get(Facility, item.facility_id)
    write_audit(db, action=f"INVENTORY_{payload.transaction_type}", resource_type="InventoryItem", resource_id=item.item_id, actor=payload.actor, role="Supply Chain", facility_code=facility.code, details=f"{payload.quantity} {item.unit}: {payload.reason}")
    db.commit()
    return {"transaction_id": transaction.transaction_id, "on_hand": item.on_hand}


@router.get("/quality-incidents")
def quality_incidents(status: str | None = None, db: Session = Depends(get_db)):
    query = select(QualityIncident)
    if status:
        query = query.where(QualityIncident.status == status)
    items = list(db.scalars(query.order_by(QualityIncident.reported_at.desc())).all())
    return [{
        "incident_id": x.incident_id,
        "facility": db.get(Facility, x.facility_id).code,
        "patient": patient_brief(db, x.patient_id) if x.patient_id else None,
        "category": x.category,
        "severity": x.severity,
        "description": x.description,
        "status": x.status,
        "owner": x.owner,
        "reported_by": x.reported_by,
        "reported_at": x.reported_at,
    } for x in items]


@router.post("/quality-incidents", status_code=201)
def create_quality_incident(payload: QualityIncidentIn, db: Session = Depends(get_db)):
    facility = get_facility(db, payload.facility_code)
    patient = get_patient(db, payload.patient_mpi_id) if payload.patient_mpi_id else None
    item = QualityIncident(facility_id=facility.id, patient_id=patient.id if patient else None, **payload.model_dump(exclude={"facility_code", "patient_mpi_id"}))
    db.add(item)
    db.add(WorkItem(queue="QUALITY-SAFETY", task_type="INCIDENT_REVIEW", subject=f"{payload.severity} {payload.category} incident", details=payload.description, patient_id=patient.id if patient else None, priority=payload.severity, assigned_to=payload.owner or "Quality and Safety Pool", created_by=payload.reported_by))
    write_audit(db, action="REPORT_QUALITY_INCIDENT", resource_type="QualityIncident", resource_id=item.incident_id, actor=payload.reported_by, role="Quality", patient_mpi_id=patient.mpi_id if patient else None, facility_code=facility.code)
    db.commit()
    return {"incident_id": item.incident_id, "status": item.status}


@router.get("/public-health-events")
def public_health_events(status: str | None = None, db: Session = Depends(get_db)):
    query = select(PublicHealthEvent)
    if status:
        query = query.where(PublicHealthEvent.status == status)
    items = list(db.scalars(query.order_by(PublicHealthEvent.created_at.desc())).all())
    return [{
        "event_id": x.event_id,
        "patient": patient_brief(db, x.patient_id),
        "condition_code": x.condition_code,
        "condition_name": x.condition_name,
        "event_type": x.event_type,
        "status": x.status,
        "district": x.district,
        "region": x.region,
        "reported_to": x.reported_to,
        "created_at": x.created_at,
        "reported_at": x.reported_at,
    } for x in items]


@router.post("/public-health-events", status_code=201)
def create_public_health_event(payload: PublicHealthEventIn, db: Session = Depends(get_db)):
    patient = get_patient(db, payload.patient_mpi_id)
    item = PublicHealthEvent(patient_id=patient.id, district=patient.district, region=patient.region, **payload.model_dump(exclude={"patient_mpi_id"}))
    db.add(item)
    db.flush()
    db.add(IntegrationEvent(system=payload.reported_to, event_type="NOTIFIABLE_EVENT", resource_type="PublicHealthEvent", resource_id=item.event_id, payload_json=json.dumps({"patient": patient.mpi_id, "condition": payload.condition_code})))
    db.commit()
    return {"event_id": item.event_id, "status": item.status}


@router.get("/integration-events")
def integration_events(system: str | None = None, status: str | None = None, limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    query = select(IntegrationEvent)
    if system:
        query = query.where(IntegrationEvent.system == system)
    if status:
        query = query.where(IntegrationEvent.status == status)
    items = list(db.scalars(query.order_by(IntegrationEvent.created_at.desc()).limit(limit)).all())
    return [{
        "integration_event_id": x.integration_event_id,
        "system": x.system,
        "event_type": x.event_type,
        "resource_type": x.resource_type,
        "resource_id": x.resource_id,
        "status": x.status,
        "attempts": x.attempts,
        "error": x.error,
        "created_at": x.created_at,
        "processed_at": x.processed_at,
    } for x in items]


@router.get("/admin/access-catalog")
def access_catalog(db: Session = Depends(get_db)):
    facilities = list(db.scalars(select(Facility).where(Facility.active.is_(True)).order_by(Facility.name)).all())
    return {
        "functions": [item.__dict__ for item in FUNCTION_CATALOG],
        "departments": [item.__dict__ for item in DEPARTMENT_CATALOG],
        "facilities": [{"code": item.code, "label": item.name, "group": item.country_code, "description": f"{item.facility_type} · {item.region or item.relation}"} for item in facilities],
        "countries": [{"code":"TZ","label":"Tanzania","group":"Country Context","description":"United Republic of Tanzania"},{"code":"KE","label":"Kenya","group":"Country Context","description":"Republic of Kenya"},{"code":"NG","label":"Nigeria","group":"Country Context","description":"Federal Republic of Nigeria"}],
        "templates": {
            code: {
                "label": code.replace("_", " ").title(),
                "functions": value["functions"],
                "departments": value["departments"],
            }
            for code, value in ROLE_TEMPLATES.items()
        },
    }


def _user_payload(db: Session, item: UserAccount) -> dict:
    return {
        "user_id": item.user_id,
        "username": item.username,
        "display_name": item.display_name,
        "role_code": item.role_code,
        "facility_code": item.facility_code,
        "active": item.active,
        "requires_mfa": item.requires_mfa,
        "last_login_at": item.last_login_at,
        "created_at": item.created_at,
        "failed_login_count": item.failed_login_count,
        "locked_until": item.locked_until,
        "must_change_password": item.must_change_password,
        "password_changed_at": item.password_changed_at,
        **get_user_access(db, item),
    }


@router.get("/admin/users")
def users(db: Session = Depends(get_db)):
    items = list(db.scalars(select(UserAccount).order_by(UserAccount.display_name)).all())
    return [_user_payload(db, item) for item in items]


@router.get("/admin/users/{user_id}")
def user_detail(user_id: str, db: Session = Depends(get_db)):
    item = db.scalar(select(UserAccount).where(UserAccount.user_id == user_id))
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_payload(db, item)


@router.post("/admin/users", status_code=201)
def create_user(payload: UserCreateIn, db: Session = Depends(get_db)):
    username = payload.username.lower().strip()
    display_name = payload.display_name.strip()
    if db.scalar(select(UserAccount).where(func.lower(UserAccount.username) == username)):
        raise HTTPException(status_code=409, detail="Username already exists")
    if not password_is_strong(payload.password):
        raise HTTPException(status_code=422, detail="Password must contain at least 12 characters, upper and lower case letters, a number and a symbol")
    role_code = payload.role_code.lower().strip() or "custom"
    requested_facilities = payload.facility_codes or [payload.facility_code]
    requested_countries = payload.country_codes or sorted({get_facility(db, code).country_code for code in requested_facilities})
    for code in requested_facilities:
        get_facility(db, code)
    defaults = template_access(role_code, requested_facilities[0])
    functions = payload.function_codes or defaults["functions"]
    departments = payload.department_codes if payload.department_codes else defaults["departments"]
    invalid_functions = sorted(set(functions) - FUNCTION_CODES)
    invalid_departments = sorted(set(departments) - DEPARTMENT_CODES)
    if invalid_functions:
        raise HTTPException(status_code=422, detail=f"Unknown function code(s): {', '.join(invalid_functions)}")
    if invalid_departments:
        raise HTTPException(status_code=422, detail=f"Unknown department code(s): {', '.join(invalid_departments)}")
    item = UserAccount(
        username=username,
        display_name=display_name,
        role_code=role_code,
        facility_code=requested_facilities[0],
        password_hash=hash_password(payload.password),
        active=True,
        requires_mfa=payload.requires_mfa,
        must_change_password=True,
        password_changed_at=now(),
    )
    db.add(item)
    db.flush()
    try:
        access = replace_user_access(
            db,
            item,
            functions=functions,
            departments=departments,
            facilities=requested_facilities,
            countries=requested_countries,
            actor=payload.actor,
            reason=payload.access_reason or "Initial user provisioning",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    write_audit(
        db,
        action="CREATE_USER",
        resource_type="UserAccount",
        resource_id=item.user_id,
        actor=payload.actor,
        role="system.users.manage",
        facility_code=item.facility_code,
        details=f"Created {username}; functions={len(access['functions'])}; departments={len(access['departments'])}; facilities={len(access['facilities'])}",
    )
    db.commit()
    db.refresh(item)
    return _user_payload(db, item)


@router.patch("/admin/users/{user_id}")
def update_user(user_id: str, payload: UserUpdateIn, db: Session = Depends(get_db)):
    item = db.scalar(select(UserAccount).where(UserAccount.user_id == user_id))
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    before = _user_payload(db, item)
    if payload.display_name is not None:
        item.display_name = payload.display_name.strip()
    if payload.role_code is not None:
        item.role_code = payload.role_code.lower().strip()
    if payload.active is not None:
        item.active = payload.active
    if payload.requires_mfa is not None:
        item.requires_mfa = payload.requires_mfa
    access_changed = any(value is not None for value in (payload.function_codes, payload.department_codes, payload.facility_codes, payload.country_codes))
    if access_changed:
        current = get_user_access(db, item)
        functions = payload.function_codes if payload.function_codes is not None else current["functions"]
        departments = payload.department_codes if payload.department_codes is not None else current["departments"]
        facilities = payload.facility_codes if payload.facility_codes is not None else current["facilities"]
        countries = payload.country_codes if payload.country_codes is not None else current.get("countries", [])
        for code in facilities:
            get_facility(db, code)
        invalid_functions = sorted(set(functions) - FUNCTION_CODES)
        invalid_departments = sorted(set(departments) - DEPARTMENT_CODES)
        if invalid_functions:
            raise HTTPException(status_code=422, detail=f"Unknown function code(s): {', '.join(invalid_functions)}")
        if invalid_departments:
            raise HTTPException(status_code=422, detail=f"Unknown department code(s): {', '.join(invalid_departments)}")
        try:
            replace_user_access(
                db,
                item,
                functions=functions,
                departments=departments,
                facilities=facilities,
                countries=countries,
                actor=payload.actor,
                reason=payload.access_reason or "Access matrix update",
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    elif payload.facility_code is not None:
        get_facility(db, payload.facility_code)
        current = get_user_access(db, item)
        facilities = [payload.facility_code, *[x for x in current["facilities"] if x != payload.facility_code]]
        replace_user_access(db, item, functions=current["functions"], departments=current["departments"], facilities=facilities, actor=payload.actor, reason=payload.access_reason or "Primary facility update")
    after = _user_payload(db, item)
    write_audit(
        db,
        action="UPDATE_USER",
        resource_type="UserAccount",
        resource_id=item.user_id,
        actor=payload.actor,
        role="system.users.manage",
        facility_code=item.facility_code,
        details=json.dumps({"before": before, "after": after}, default=str),
    )
    db.commit()
    return _user_payload(db, item)


@router.post("/admin/users/{user_id}/reset-password")
def reset_user_password(user_id: str, payload: PasswordResetIn, db: Session = Depends(get_db)):
    item = db.scalar(select(UserAccount).where(UserAccount.user_id == user_id))
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    if not password_is_strong(payload.password):
        raise HTTPException(status_code=422, detail="Password must contain at least 12 characters, upper and lower case letters, a number and a symbol")
    item.password_hash = hash_password(payload.password)
    item.password_changed_at = now()
    item.must_change_password = True
    item.failed_login_count = 0
    item.locked_until = None
    write_audit(db, action="RESET_PASSWORD", resource_type="UserAccount", resource_id=item.user_id, actor=payload.actor, role="system.users.manage", facility_code=item.facility_code)
    db.commit()
    return {"user_id": item.user_id, "password_reset": True}


@router.post("/admin/users/{user_id}/unlock")
def unlock_user(user_id: str, payload: UserUpdateIn, db: Session = Depends(get_db)):
    item = db.scalar(select(UserAccount).where(UserAccount.user_id == user_id))
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    item.active = True
    write_audit(db, action="UNLOCK_USER", resource_type="UserAccount", resource_id=item.user_id, actor=payload.actor, role="system.users.manage", facility_code=item.facility_code)
    db.commit()
    return _user_payload(db, item)
