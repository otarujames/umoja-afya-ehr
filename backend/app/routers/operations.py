from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..database import get_db
from ..enterprise_models import Appointment, AppointmentStatusEvent, UserAccount
from ..models import Encounter, EncounterStatus, Facility, Patient
from ..operational_models import (
    BreakGlassAccess,
    CoverageVerification,
    DutyRoster,
    PrintJob,
    ServicePoint,
    TravelScreening,
    WalkInEpisode,
    WorkflowNotification,
    WorkQueueDefinition,
    WorkQueueEvent,
    WorkQueueItem,
)
from ..security import optional_user

router = APIRouter(tags=["Operational Workflows"])


def now() -> datetime:
    return datetime.now(timezone.utc)


def facility_by_code(db: Session, code: str) -> Facility:
    facility = db.scalar(select(Facility).where(Facility.code == code))
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


def patient_by_mpi(db: Session, mpi_id: str) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.mpi_id == mpi_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient




def ensure_facility_review_operations(db: Session, facility: Facility, target: date) -> None:
    """Create a small operational review dataset for any selected facility/context.

    This keeps the Docker review functional after Change Context without pretending the
    synthetic rows are production data. The function is idempotent per facility/day.
    """
    points = list(db.scalars(select(ServicePoint).where(ServicePoint.facility_id == facility.id)).all())
    if not points:
        definitions = [
            ("OPD", "General OPD", "Outpatient", "General OPD Clinic", "OPD 1", 40),
            ("SURG", "Surgical OPD", "Surgery", "Surgical OPD", "Clinic 2", 25),
            ("PEDS", "Paediatric Clinic", "Paediatrics", "Paediatric Clinic", "Clinic 3", 25),
            ("MAT", "Maternity Clinic", "Maternity", "Antenatal / Maternity", "Clinic 4", 30),
            ("ED", "Emergency Reception", "Emergency", "Emergency Department", "ED", 50),
            ("IMG", "Imaging Reception", "Radiology", "Diagnostic Imaging", "Imaging", 20),
        ]
        for suffix, name, department, clinic, room, capacity in definitions:
            point = ServicePoint(
                facility_id=facility.id, code=f"{facility.code[:8]}-{suffix}",
                name=f"{name} Service Point", department=department, clinic=clinic,
                room=room, scheduling_model="PUBLIC_DUTY_ROSTER", queue_capacity=capacity, active=True,
            )
            db.add(point); db.flush(); points.append(point)
    roster_exists = db.scalar(select(DutyRoster.id).join(ServicePoint).where(ServicePoint.facility_id == facility.id, DutyRoster.roster_date == target).limit(1))
    if not roster_exists:
        leads = ["Dr. Asha Mrema", "Dr. Hamisi Kilonzo", "Dr. Amina Salehe", "Sr. Neema Kerefu", "Dr. Rehema Msuya", "Radiology Duty Team"]
        for idx, point in enumerate(points[:8]):
            db.add(DutyRoster(service_point_id=point.id, roster_date=target, shift_start=time(7,0), shift_end=time(15,0), team_name=f"{point.department} Duty Team", lead_provider=leads[idx % len(leads)], staff_count=3, status="ACTIVE", notes="Synthetic Docker review roster"))
    start = datetime.combine(target, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    count = int(db.scalar(select(func.count(Appointment.id)).where(Appointment.facility_id == facility.id, Appointment.scheduled_start >= start, Appointment.scheduled_start < end)) or 0)
    if count == 0:
        patients = list(db.scalars(select(Patient).order_by(Patient.id).limit(90)).all())
        statuses = ["SCHEDULED", "ARRIVED", "REGISTERED", "WAITING_TRIAGE", "TRIAGED", "READY_FOR_PROVIDER", "IN_PROGRESS", "DISCHARGED"]
        for idx, patient in enumerate(patients[:48]):
            point = points[idx % len(points)]
            status = statuses[idx % len(statuses)]
            scheduled = start + timedelta(hours=7, minutes=idx*12)
            apt = Appointment(appointment_id=f"APT-{facility.code[:8]}-{target.strftime('%Y%m%d')}-{idx+1:03d}", patient_id=patient.id, facility_id=facility.id, service=point.clinic, provider=f"{point.department} Duty Team", appointment_type="PUBLIC_DUTY_ROSTER", scheduled_start=scheduled, scheduled_end=scheduled+timedelta(minutes=30), status="SCHEDULED" if status=="SCHEDULED" else "ARRIVED", arrival_method="SCHEDULED" if status=="SCHEDULED" else "FRONT_DESK", notes=f"Synthetic review appointment for {point.name}", created_by="Docker Review Seeder")
            db.add(apt); db.flush()
            if status != "SCHEDULED":
                db.add(Encounter(patient_id=patient.id, facility_id=facility.id, encounter_type="OUTPATIENT", service=point.clinic, status=EncounterStatus(status), acuity=["Low","Medium","High"][idx%3], location=point.name, room=point.room, provider=f"{point.department} Duty Team", reason_for_visit="Synthetic review visit", arrival_at=scheduled+timedelta(minutes=5)))
    db.commit()

def patient_brief(patient: Patient | None) -> dict | None:
    if not patient:
        return None
    return {
        "mpi_id": patient.mpi_id,
        "mrn": patient.mrn,
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth,
        "sex": patient.sex,
        "phone": patient.phone,
        "payer": patient.payer,
        "member_number": patient.member_number,
    }


def appointment_state(db: Session, appointment: Appointment, patient: Patient) -> tuple[str, Encounter | None]:
    day_start = appointment.scheduled_start.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    encounter = db.scalar(
        select(Encounter)
        .where(
            Encounter.patient_id == patient.id,
            Encounter.facility_id == appointment.facility_id,
            Encounter.arrival_at >= day_start,
            Encounter.arrival_at < day_end,
        )
        .order_by(Encounter.arrival_at.desc())
    )
    if encounter:
        return encounter.status.value if hasattr(encounter.status, "value") else str(encounter.status), encounter
    return appointment.status, None


@router.get("/today-patients")
def today_patients(
    facility_code: str = Query(default="MNH-UPANGA"),
    service: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    day: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    facility = facility_by_code(db, facility_code)
    target = day or now().date()
    ensure_facility_review_operations(db, facility, target)
    start = datetime.combine(target, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    query = select(Appointment).where(
        Appointment.facility_id == facility.id,
        Appointment.scheduled_start >= start,
        Appointment.scheduled_start < end,
    )
    if service:
        query = query.where(Appointment.service == service)
    appointments = list(db.scalars(query.order_by(Appointment.scheduled_start).limit(1000)).all())
    rows: list[dict] = []
    counts = {
        "expected": len(appointments),
        "scheduled": 0,
        "arrived": 0,
        "checked_in": 0,
        "waiting": 0,
        "triaged": 0,
        "ready_for_provider": 0,
        "completed": 0,
    }
    for appointment in appointments:
        patient = db.get(Patient, appointment.patient_id)
        if not patient:
            continue
        current_status, encounter = appointment_state(db, appointment, patient)
        normalized = current_status.upper()
        bucket = {
            "SCHEDULED": "scheduled",
            "CONFIRMED": "scheduled",
            "ARRIVED": "arrived",
            "WAITING_REGISTRATION": "arrived",
            "REGISTERED": "checked_in",
            "WAITING_TRIAGE": "waiting",
            "TRIAGED": "triaged",
            "READY_FOR_PROVIDER": "ready_for_provider",
            "ROOMED": "ready_for_provider",
            "IN_PROGRESS": "ready_for_provider",
            "WAITING_RESULTS": "ready_for_provider",
            "READY_FOR_DISCHARGE": "ready_for_provider",
            "DISCHARGED": "completed",
            "COMPLETED": "completed",
        }.get(normalized, "scheduled")
        counts[bucket] += 1
        row = {
            "appointment_id": appointment.appointment_id,
            "patient": patient_brief(patient),
            "scheduled_start": appointment.scheduled_start,
            "service": appointment.service,
            "provider": appointment.provider,
            "appointment_type": appointment.appointment_type,
            "status": normalized,
            "queue": encounter.location if encounter else appointment.service,
            "on_duty_team": appointment.provider or "Duty roster / next available clinician",
            "encounter_id": encounter.encounter_id if encounter else None,
            "location": encounter.location if encounter else "Expected",
            "next_step": {
                "SCHEDULED": "ARRIVE",
                "CONFIRMED": "ARRIVE",
                "ARRIVED": "CHECK_IN",
                "WAITING_REGISTRATION": "COMPLETE_REGISTRATION",
                "REGISTERED": "SEND_TO_TRIAGE",
                "WAITING_TRIAGE": "TRIAGE",
                "TRIAGED": "READY_FOR_PROVIDER",
                "READY_FOR_PROVIDER": "ROOM_PATIENT",
                "ROOMED": "START_VISIT",
                "IN_PROGRESS": "CONTINUE_CARE",
                "WAITING_RESULTS": "REVIEW_RESULTS",
                "READY_FOR_DISCHARGE": "DISCHARGE",
                "DISCHARGED": "OPEN_CHART",
            }.get(normalized, "OPEN_RECORD"),
        }
        if search:
            needle = search.lower().strip()
            haystack = " ".join([patient.full_name, patient.mpi_id, patient.mrn, patient.phone or "", appointment.service]).lower()
            if needle not in haystack:
                continue
        if status and normalized != status.upper():
            continue
        rows.append(row)

    walkin_count = int(db.scalar(select(func.count(WalkInEpisode.id)).where(WalkInEpisode.facility_id == facility.id, WalkInEpisode.created_at >= start, WalkInEpisode.created_at < end, WalkInEpisode.status.not_in(["COMPLETED", "CANCELLED"]))) or 0)
    counts["walk_ins_waiting"] = walkin_count
    counts["total_visible"] = len(rows)
    return {
        "facility": {"code": facility.code, "name": facility.name},
        "day": target,
        "counts": counts,
        "rows": rows[offset : offset + limit],
        "offset": offset,
        "limit": limit,
        "total": len(rows),
    }


@router.get("/service-points")
def service_points(
    facility_code: str = Query(default="MNH-UPANGA"),
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    facility = facility_by_code(db, facility_code)
    ensure_facility_review_operations(db, facility, now().date())
    query = select(ServicePoint).where(ServicePoint.facility_id == facility.id)
    if active_only:
        query = query.where(ServicePoint.active.is_(True))
    items = list(db.scalars(query.order_by(ServicePoint.department, ServicePoint.name)).all())
    return [
        {
            "service_point_id": item.service_point_id,
            "code": item.code,
            "name": item.name,
            "department": item.department,
            "clinic": item.clinic,
            "room": item.room,
            "scheduling_model": item.scheduling_model,
            "queue_capacity": item.queue_capacity,
            "active": item.active,
        }
        for item in items
    ]


@router.get("/duty-rosters")
def duty_rosters(
    facility_code: str = Query(default="MNH-UPANGA"),
    day: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    facility = facility_by_code(db, facility_code)
    target = day or now().date()
    ensure_facility_review_operations(db, facility, target)
    rows = list(
        db.execute(
            select(DutyRoster, ServicePoint)
            .join(ServicePoint, DutyRoster.service_point_id == ServicePoint.id)
            .where(ServicePoint.facility_id == facility.id, DutyRoster.roster_date == target)
            .order_by(ServicePoint.name, DutyRoster.shift_start)
        ).all()
    )
    return [
        {
            "roster_id": roster.roster_id,
            "date": roster.roster_date,
            "shift_start": roster.shift_start,
            "shift_end": roster.shift_end,
            "team_name": roster.team_name,
            "lead_provider": roster.lead_provider,
            "staff_count": roster.staff_count,
            "status": roster.status,
            "service_point": {
                "service_point_id": point.service_point_id,
                "code": point.code,
                "name": point.name,
                "department": point.department,
                "clinic": point.clinic,
                "room": point.room,
                "queue_capacity": point.queue_capacity,
            },
        }
        for roster, point in rows
    ]


class WalkInCreateIn(BaseModel):
    patient_mpi_id: str
    facility_code: str = "MNH-UPANGA"
    service_point_id: str | None = None
    service: str | None = Field(default=None, min_length=2, max_length=240)
    reason: str = Field(min_length=2, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    coverage_route: str | None = None
    created_by: str = "Front Desk"


class WalkInActionIn(BaseModel):
    action: Literal[
        "ARRIVE",
        "ASSIGN_SERVICE",
        "SEND_TO_TRIAGE",
        "TRIAGE_COMPLETE",
        "READY_FOR_PROVIDER",
        "COMPLETE",
        "CANCEL",
    ]
    actor: str
    service_point_id: str | None = None
    queue_name: str | None = None
    note: str | None = None


@router.post("/walk-ins", status_code=201)
def create_walk_in(payload: WalkInCreateIn, db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, payload.patient_mpi_id)
    facility = facility_by_code(db, payload.facility_code)
    point = None
    if payload.service_point_id:
        point = db.scalar(select(ServicePoint).where(ServicePoint.service_point_id == payload.service_point_id, ServicePoint.facility_id == facility.id))
        if not point:
            raise HTTPException(status_code=404, detail="Service point not found")
    service = (payload.service or "").strip() or (point.clinic if point else "Walk-In Assessment")
    # Reuse a just-created registration encounter so the integrated wizard does not
    # create two encounters for one walk-in arrival. Existing patients receive a new
    # walk-in encounter as expected.
    recent_cutoff = now() - timedelta(minutes=30)
    encounter = db.scalar(
        select(Encounter).where(
            Encounter.patient_id == patient.id,
            Encounter.facility_id == facility.id,
            Encounter.arrival_at >= recent_cutoff,
            Encounter.status.in_([EncounterStatus.REGISTERED, EncounterStatus.PRE_REGISTERED]),
        ).order_by(Encounter.arrival_at.desc())
    )
    if encounter:
        encounter.encounter_type = "WALK_IN"
        encounter.service = service
        encounter.status = EncounterStatus.ARRIVED
        encounter.acuity = encounter.acuity or "Not assigned"
        encounter.location = point.name if point else "Walk-In Registration"
        encounter.room = point.room if point else None
        encounter.provider = "Duty roster / next available clinician"
        encounter.reason_for_visit = payload.reason
        encounter.arrival_at = now()
    else:
        encounter = Encounter(
            patient_id=patient.id,
            facility_id=facility.id,
            encounter_type="WALK_IN",
            service=service,
            status=EncounterStatus.ARRIVED,
            acuity="Not assigned",
            location=point.name if point else "Walk-In Registration",
            room=point.room if point else None,
            provider="Duty roster / next available clinician",
            reason_for_visit=payload.reason,
            arrival_at=now(),
        )
        db.add(encounter)
        db.flush()
    item = WalkInEpisode(
        patient_id=patient.id,
        encounter_id=encounter.id,
        facility_id=facility.id,
        service_point_id=point.id if point else None,
        reason=payload.reason,
        notes=payload.notes,
        status="ARRIVED",
        coverage_route=payload.coverage_route or patient.payer,
        queue_name=point.name if point else "Walk-In Registration Queue",
        created_by=payload.created_by,
        arrived_at=now(),
    )
    db.add(item)
    notification = WorkflowNotification(
        event_type="PATIENT_ARRIVED",
        facility_code=facility.code,
        patient_id=patient.id,
        encounter_id=encounter.id,
        message_en=f"{patient.full_name} arrived as a walk-in for {service}",
        message_sw=f"{patient.full_name} amewasili bila miadi kwa huduma ya {service}",
        payload_json=json.dumps({"duration_ms": 1000, "walkin_id": item.walkin_id, "encounter_id": encounter.encounter_id}),
        expires_at=now() + timedelta(minutes=10),
    )
    db.add(notification)
    queue = db.scalar(select(WorkQueueDefinition).where(WorkQueueDefinition.code == "WALKIN_REG_FOLLOWUP"))
    if queue:
        db.add(
            WorkQueueItem(
                queue_definition_id=queue.id,
                patient_id=patient.id,
                encounter_id=encounter.id,
                title="Complete walk-in registration and routing",
                reason=payload.reason,
                priority="HIGH" if payload.coverage_route == "EMERGENCY" else "ROUTINE",
                status="ACTIVE",
                assigned_to=queue.owner_team,
                due_at=now() + timedelta(hours=queue.sla_hours),
                created_by=payload.created_by,
            )
        )
    write_audit(db, action="CREATE_WALK_IN", resource_type="WalkInEpisode", resource_id=item.walkin_id, actor=payload.created_by, role="registration.manage", patient_mpi_id=patient.mpi_id, facility_code=facility.code, details=payload.reason)
    db.commit()
    return {
        "walkin_id": item.walkin_id,
        "encounter_id": encounter.encounter_id,
        "status": item.status,
        "notification": {"duration_ms": 1000, "message_en": notification.message_en, "message_sw": notification.message_sw},
    }


@router.get("/walk-ins")
def walk_ins(
    facility_code: str = Query(default="MNH-UPANGA"),
    status: str | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    facility = facility_by_code(db, facility_code)
    query = select(WalkInEpisode).where(WalkInEpisode.facility_id == facility.id, WalkInEpisode.created_at >= now() - timedelta(hours=hours))
    if status:
        query = query.where(WalkInEpisode.status == status.upper())
    items = list(db.scalars(query.order_by(WalkInEpisode.created_at.desc())).all())
    output = []
    for item in items:
        patient = db.get(Patient, item.patient_id) if item.patient_id else None
        encounter = db.get(Encounter, item.encounter_id) if item.encounter_id else None
        point = db.get(ServicePoint, item.service_point_id) if item.service_point_id else None
        output.append({
            "walkin_id": item.walkin_id,
            "patient": patient_brief(patient),
            "encounter_id": encounter.encounter_id if encounter else None,
            "service_point": point.name if point else None,
            "queue_name": item.queue_name,
            "reason": item.reason,
            "status": item.status,
            "coverage_route": item.coverage_route,
            "created_by": item.created_by,
            "created_at": item.created_at,
            "arrived_at": item.arrived_at,
        })
    return output


@router.patch("/walk-ins/{walkin_id}")
def update_walk_in(walkin_id: str, payload: WalkInActionIn, db: Session = Depends(get_db)):
    item = db.scalar(select(WalkInEpisode).where(WalkInEpisode.walkin_id == walkin_id))
    if not item:
        raise HTTPException(status_code=404, detail="Walk-in episode not found")
    encounter = db.get(Encounter, item.encounter_id) if item.encounter_id else None
    transitions = {
        "ARRIVED": {"ASSIGN_SERVICE", "SEND_TO_TRIAGE", "CANCEL"},
        "SERVICE_ASSIGNED": {"SEND_TO_TRIAGE", "CANCEL"},
        "WAITING_TRIAGE": {"TRIAGE_COMPLETE", "CANCEL"},
        "TRIAGED": {"READY_FOR_PROVIDER", "CANCEL"},
        "READY_FOR_PROVIDER": {"COMPLETE", "CANCEL"},
    }
    if payload.action not in transitions.get(item.status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid walk-in transition: {item.status} -> {payload.action}")
    before = item.status
    point = None
    if payload.service_point_id:
        point = db.scalar(select(ServicePoint).where(ServicePoint.service_point_id == payload.service_point_id))
        if not point:
            raise HTTPException(status_code=404, detail="Service point not found")
        item.service_point_id = point.id
        item.queue_name = payload.queue_name or point.name
        if encounter:
            encounter.service = point.clinic
            encounter.location = point.name
            encounter.room = point.room
    mapping = {
        "ASSIGN_SERVICE": ("SERVICE_ASSIGNED", EncounterStatus.REGISTERED),
        "SEND_TO_TRIAGE": ("WAITING_TRIAGE", EncounterStatus.WAITING_TRIAGE),
        "TRIAGE_COMPLETE": ("TRIAGED", EncounterStatus.TRIAGED),
        "READY_FOR_PROVIDER": ("READY_FOR_PROVIDER", EncounterStatus.READY_FOR_PROVIDER),
        "COMPLETE": ("COMPLETED", EncounterStatus.READY_FOR_DISCHARGE),
        "CANCEL": ("CANCELLED", EncounterStatus.LEFT_WITHOUT_BEING_SEEN),
    }
    new_status, encounter_status = mapping[payload.action]
    item.status = new_status
    if new_status in {"COMPLETED", "CANCELLED"}:
        item.completed_at = now()
    if encounter:
        encounter.status = encounter_status
        if encounter_status == EncounterStatus.TRIAGED:
            encounter.triage_at = now()
    patient = db.get(Patient, item.patient_id) if item.patient_id else None
    facility = db.get(Facility, item.facility_id)
    write_audit(db, action=f"WALK_IN_{payload.action}", resource_type="WalkInEpisode", resource_id=item.walkin_id, actor=payload.actor, role="registration.manage", patient_mpi_id=patient.mpi_id if patient else None, facility_code=facility.code if facility else None, details=json.dumps({"before": before, "after": new_status, "note": payload.note}))
    db.commit()
    return {"walkin_id": item.walkin_id, "status": item.status, "encounter_id": encounter.encounter_id if encounter else None}


class WorkQueueItemCreateIn(BaseModel):
    patient_mpi_id: str | None = None
    encounter_id: str | None = None
    appointment_id: str | None = None
    title: str = Field(min_length=2, max_length=240)
    reason: str = Field(min_length=2, max_length=4000)
    priority: str = "ROUTINE"
    assigned_to: str | None = None
    due_hours: int = Field(default=24, ge=1, le=8760)
    created_by: str


class WorkQueueActionIn(BaseModel):
    action: Literal["ASSIGN", "ROUTE", "DEFER", "RESUME", "COMPLETE", "REOPEN", "CANCEL"]
    actor: str
    assigned_to: str | None = None
    target_queue_code: str | None = None
    defer_hours: int | None = Field(default=None, ge=1, le=8760)
    note: str | None = Field(default=None, max_length=4000)


def workqueue_metrics(db: Session, queue: WorkQueueDefinition) -> dict:
    total = int(db.scalar(select(func.count(WorkQueueItem.id)).where(WorkQueueItem.queue_definition_id == queue.id)) or 0)
    active = int(db.scalar(select(func.count(WorkQueueItem.id)).where(WorkQueueItem.queue_definition_id == queue.id, WorkQueueItem.status == "ACTIVE")) or 0)
    deferred = int(db.scalar(select(func.count(WorkQueueItem.id)).where(WorkQueueItem.queue_definition_id == queue.id, WorkQueueItem.status == "DEFERRED")) or 0)
    overdue = int(db.scalar(select(func.count(WorkQueueItem.id)).where(WorkQueueItem.queue_definition_id == queue.id, WorkQueueItem.status.in_(["ACTIVE", "DEFERRED"]), WorkQueueItem.due_at < now())) or 0)
    high = int(db.scalar(select(func.count(WorkQueueItem.id)).where(WorkQueueItem.queue_definition_id == queue.id, WorkQueueItem.status.in_(["ACTIVE", "DEFERRED"]), WorkQueueItem.priority.in_(["HIGH", "URGENT", "STAT", "CRITICAL"]))) or 0)
    oldest = db.scalar(select(func.min(WorkQueueItem.created_at)).where(WorkQueueItem.queue_definition_id == queue.id, WorkQueueItem.status.in_(["ACTIVE", "DEFERRED"])))
    avg_age = db.scalar(select(func.avg(func.julianday(func.current_timestamp()) - func.julianday(WorkQueueItem.created_at))).where(WorkQueueItem.queue_definition_id == queue.id, WorkQueueItem.status.in_(["ACTIVE", "DEFERRED"]))) if db.bind and db.bind.dialect.name == "sqlite" else None
    if avg_age is None:
        active_items = list(db.scalars(select(WorkQueueItem).where(WorkQueueItem.queue_definition_id == queue.id, WorkQueueItem.status.in_(["ACTIVE", "DEFERRED"]))).all())
        def aware(value):
            return value if not value or value.tzinfo else value.replace(tzinfo=timezone.utc)
        avg_age = sum((now() - aware(item.created_at)).total_seconds() / 86400 for item in active_items) / len(active_items) if active_items else 0
    return {
        "active": active,
        "deferred": deferred,
        "total": total,
        "overdue": overdue,
        "high_priority": high,
        "avg_age_days": round(float(avg_age or 0), 1),
        "oldest_age_days": int((now() - (oldest if oldest.tzinfo else oldest.replace(tzinfo=timezone.utc))).total_seconds() // 86400) if oldest else 0,
    }


@router.get("/workqueues")
def workqueues(
    category: str | None = Query(default=None),
    facility_code: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    query = select(WorkQueueDefinition)
    if category:
        query = query.where(WorkQueueDefinition.category == category.upper())
    if facility_code and facility_code != "ALL":
        query = query.where(or_(WorkQueueDefinition.facility_code.is_(None), WorkQueueDefinition.facility_code == facility_code))
    if active_only:
        query = query.where(WorkQueueDefinition.active.is_(True))
    queues = list(db.scalars(query.order_by(WorkQueueDefinition.category, WorkQueueDefinition.name)).all())
    return [
        {
            "queue_id": queue.queue_id,
            "code": queue.code,
            "name": queue.name,
            "category": queue.category,
            "service_area": queue.service_area,
            "owner_team": queue.owner_team,
            "facility_code": queue.facility_code,
            "description": queue.description,
            "sla_hours": queue.sla_hours,
            "active": queue.active,
            "metrics": workqueue_metrics(db, queue),
        }
        for queue in queues
    ]


@router.get("/workqueues/summary")
def workqueue_summary(facility_code: str | None = Query(default=None), db: Session = Depends(get_db)):
    queues = workqueues(category=None, facility_code=facility_code, active_only=True, db=db)
    totals = {
        "active_queues": len(queues),
        "active_items": sum(q["metrics"]["active"] for q in queues),
        "deferred_items": sum(q["metrics"]["deferred"] for q in queues),
        "total_items": sum(q["metrics"]["total"] for q in queues),
        "overdue_items": sum(q["metrics"]["overdue"] for q in queues),
        "high_priority": sum(q["metrics"]["high_priority"] for q in queues),
    }
    return {"totals": totals, "queues": queues}


@router.get("/workqueues/{queue_id}/items")
def workqueue_items(
    queue_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    queue = db.scalar(select(WorkQueueDefinition).where(or_(WorkQueueDefinition.queue_id == queue_id, WorkQueueDefinition.code == queue_id)))
    if not queue:
        raise HTTPException(status_code=404, detail="Workqueue not found")
    query = select(WorkQueueItem).where(WorkQueueItem.queue_definition_id == queue.id)
    if status:
        query = query.where(WorkQueueItem.status == status.upper())
    items = list(db.scalars(query.order_by(WorkQueueItem.priority.desc(), WorkQueueItem.due_at, WorkQueueItem.created_at).limit(limit)).all())
    output = []
    for item in items:
        patient = db.get(Patient, item.patient_id) if item.patient_id else None
        encounter = db.get(Encounter, item.encounter_id) if item.encounter_id else None
        output.append({
            "item_id": item.item_id,
            "queue": {"queue_id": queue.queue_id, "code": queue.code, "name": queue.name},
            "patient": patient_brief(patient),
            "encounter_id": encounter.encounter_id if encounter else None,
            "title": item.title,
            "reason": item.reason,
            "priority": item.priority,
            "status": item.status,
            "assigned_to": item.assigned_to,
            "due_at": item.due_at,
            "deferred_until": item.deferred_until,
            "created_by": item.created_by,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        })
    return {
        "queue": {
            "queue_id": queue.queue_id,
            "code": queue.code,
            "name": queue.name,
            "category": queue.category,
            "service_area": queue.service_area,
            "owner_team": queue.owner_team,
            "facility_code": queue.facility_code,
            "description": queue.description,
            "sla_hours": queue.sla_hours,
            "routing_rule_json": queue.routing_rule_json,
            "active": queue.active,
        },
        "metrics": workqueue_metrics(db, queue),
        "items": output,
    }


@router.get("/workqueue-items/{item_id}/events")
def workqueue_item_events(item_id: str, db: Session = Depends(get_db)):
    item = db.scalar(select(WorkQueueItem).where(WorkQueueItem.item_id == item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Workqueue item not found")
    events = list(db.scalars(select(WorkQueueEvent).where(WorkQueueEvent.work_queue_item_id == item.id).order_by(WorkQueueEvent.occurred_at.desc())).all())
    return [
        {
            "event_id": event.event_id,
            "action": event.action,
            "status_before": event.status_before,
            "status_after": event.status_after,
            "actor": event.actor,
            "note": event.note,
            "occurred_at": event.occurred_at,
        }
        for event in events
    ]


@router.post("/workqueues/{queue_id}/items", status_code=201)
def create_workqueue_item(queue_id: str, payload: WorkQueueItemCreateIn, db: Session = Depends(get_db)):
    queue = db.scalar(select(WorkQueueDefinition).where(or_(WorkQueueDefinition.queue_id == queue_id, WorkQueueDefinition.code == queue_id)))
    if not queue:
        raise HTTPException(status_code=404, detail="Workqueue not found")
    patient = patient_by_mpi(db, payload.patient_mpi_id) if payload.patient_mpi_id else None
    encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == payload.encounter_id)) if payload.encounter_id else None
    appointment = db.scalar(select(Appointment).where(Appointment.appointment_id == payload.appointment_id)) if payload.appointment_id else None
    item = WorkQueueItem(
        queue_definition_id=queue.id,
        patient_id=patient.id if patient else None,
        encounter_id=encounter.id if encounter else None,
        appointment_id=appointment.id if appointment else None,
        title=payload.title,
        reason=payload.reason,
        priority=payload.priority.upper(),
        status="ACTIVE",
        assigned_to=payload.assigned_to or queue.owner_team,
        due_at=now() + timedelta(hours=payload.due_hours),
        created_by=payload.created_by,
    )
    db.add(item)
    db.flush()
    db.add(WorkQueueEvent(work_queue_item_id=item.id, action="CREATE", status_after="ACTIVE", actor=payload.created_by, note=payload.reason))
    write_audit(db, action="CREATE_WORKQUEUE_ITEM", resource_type="WorkQueueItem", resource_id=item.item_id, actor=payload.created_by, role="workqueues.manage", patient_mpi_id=patient.mpi_id if patient else None, details=queue.code)
    db.commit()
    return {"item_id": item.item_id, "status": item.status, "queue_code": queue.code}


@router.patch("/workqueue-items/{item_id}")
def update_workqueue_item(item_id: str, payload: WorkQueueActionIn, db: Session = Depends(get_db)):
    item = db.scalar(select(WorkQueueItem).where(WorkQueueItem.item_id == item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Workqueue item not found")
    before = item.status
    action = payload.action
    if action == "ASSIGN":
        if not payload.assigned_to:
            raise HTTPException(status_code=422, detail="assigned_to is required")
        item.assigned_to = payload.assigned_to
    elif action == "ROUTE":
        if not payload.target_queue_code:
            raise HTTPException(status_code=422, detail="target_queue_code is required")
        target = db.scalar(select(WorkQueueDefinition).where(WorkQueueDefinition.code == payload.target_queue_code))
        if not target:
            raise HTTPException(status_code=404, detail="Target workqueue not found")
        item.queue_definition_id = target.id
        item.assigned_to = target.owner_team
    elif action == "DEFER":
        if not payload.defer_hours:
            raise HTTPException(status_code=422, detail="defer_hours is required")
        item.status = "DEFERRED"
        item.deferred_until = now() + timedelta(hours=payload.defer_hours)
    elif action == "RESUME":
        item.status = "ACTIVE"
        item.deferred_until = None
    elif action == "COMPLETE":
        item.status = "COMPLETED"
        item.closed_at = now()
    elif action == "REOPEN":
        item.status = "ACTIVE"
        item.closed_at = None
    elif action == "CANCEL":
        item.status = "CANCELLED"
        item.closed_at = now()
    item.updated_at = now()
    db.add(WorkQueueEvent(work_queue_item_id=item.id, action=action, status_before=before, status_after=item.status, actor=payload.actor, note=payload.note))
    patient = db.get(Patient, item.patient_id) if item.patient_id else None
    write_audit(db, action=f"WORKQUEUE_{action}", resource_type="WorkQueueItem", resource_id=item.item_id, actor=payload.actor, role="workqueues.manage", patient_mpi_id=patient.mpi_id if patient else None, details=payload.note)
    db.commit()
    return {"item_id": item.item_id, "status": item.status, "assigned_to": item.assigned_to}


@router.get("/notifications")
def notifications(
    facility_code: str = Query(default="MNH-UPANGA"),
    since: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = select(WorkflowNotification).where(WorkflowNotification.facility_code == facility_code)
    if since:
        query = query.where(WorkflowNotification.created_at > since)
    query = query.where(or_(WorkflowNotification.expires_at.is_(None), WorkflowNotification.expires_at > now()))
    items = list(db.scalars(query.order_by(WorkflowNotification.created_at.desc()).limit(limit)).all())
    return [
        {
            "notification_id": item.notification_id,
            "event_type": item.event_type,
            "facility_code": item.facility_code,
            "audience": item.audience,
            "message_en": item.message_en,
            "message_sw": item.message_sw,
            "payload": json.loads(item.payload_json) if item.payload_json else {},
            "created_at": item.created_at,
            "expires_at": item.expires_at,
        }
        for item in items
    ]


class BreakGlassIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str | None = None
    reason: str = Field(min_length=10, max_length=4000)
    emergency_type: str = "PATIENT_SAFETY"
    duration_minutes: int = Field(default=30, ge=5, le=120)


@router.post("/break-glass", status_code=201)
def break_glass(
    payload: BreakGlassIn,
    user: UserAccount | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    patient = patient_by_mpi(db, payload.patient_mpi_id)
    encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == payload.encounter_id)) if payload.encounter_id else None
    item = BreakGlassAccess(
        user_account_id=user.id,
        patient_id=patient.id,
        encounter_id=encounter.id if encounter else None,
        reason=payload.reason,
        emergency_type=payload.emergency_type,
        expires_at=now() + timedelta(minutes=payload.duration_minutes),
    )
    db.add(item)
    write_audit(db, action="BREAK_GLASS_ACCESS", resource_type="Patient", resource_id=patient.mpi_id, actor=user.display_name, role="emergency_access", patient_mpi_id=patient.mpi_id, facility_code=user.facility_code, details=payload.reason)
    db.commit()
    return {"access_id": item.access_id, "expires_at": item.expires_at, "status": item.status}

# ---------------------------------------------------------------------------
# Release 8.0 front-desk document, coverage and screening workflows.
# ---------------------------------------------------------------------------

PRINT_TEMPLATE_CATALOG = [
    {"code": "PATIENT_ID_LABEL", "name": "Patient identification label", "category": "LABEL", "media": "1 x 3 label", "description": "Name, MRN, MPI, DOB, sex and barcode/QR identifier."},
    {"code": "ENCOUNTER_LABEL", "name": "Encounter / visit label", "category": "LABEL", "media": "1 x 3 label", "description": "Patient identity plus visit ID, service, location and arrival date."},
    {"code": "CHART_LABEL", "name": "Chart folder / spine label", "category": "LABEL", "media": "Chart label", "description": "Patient name, MRN, year of birth and facility context."},
    {"code": "SPECIMEN_LABEL", "name": "Specimen collection label", "category": "LABEL", "media": "2 x 1 label", "description": "Patient and encounter identifiers with collection fields and barcode."},
    {"code": "ADULT_WRISTBAND", "name": "Adult identification wristband", "category": "WRISTBAND", "media": "Adult wristband", "description": "Patient identity, allergies, MRN, visit ID and machine-readable identifier."},
    {"code": "PEDIATRIC_WRISTBAND", "name": "Paediatric identification wristband", "category": "WRISTBAND", "media": "Paediatric wristband", "description": "Child identity, guardian prompt, allergies and encounter identifiers."},
    {"code": "NEWBORN_WRISTBAND", "name": "Newborn mother–baby wristband", "category": "WRISTBAND", "media": "Newborn wristband", "description": "Baby identity, mother linkage, birth details and matching identifiers."},
    {"code": "FACESHEET", "name": "Patient facesheet", "category": "DOCUMENT", "media": "A4", "description": "Demographics, contacts, coverage, encounter, care team and alerts."},
    {"code": "REGISTRATION_SUMMARY", "name": "Registration and consent summary", "category": "DOCUMENT", "media": "A4", "description": "Identity verification, contacts, coverage and consent status."},
    {"code": "ENCOUNTER_SUMMARY", "name": "Encounter summary", "category": "DOCUMENT", "media": "A4", "description": "Visit context, service, location, status, reason and care team."},
    {"code": "REFERRAL_COVER", "name": "Referral cover sheet", "category": "DOCUMENT", "media": "A4", "description": "Patient identity and destination/referral communication header."},
    {"code": "DISCHARGE_FACESHEET", "name": "Discharge transition facesheet", "category": "DOCUMENT", "media": "A4", "description": "Patient identity, encounter disposition and follow-up header."},
]


class PrintJobCreateIn(BaseModel):
    template_codes: list[str] = Field(min_length=1, max_length=12)
    encounter_id: str | None = None
    copies: int = Field(default=1, ge=1, le=20)
    language: Literal["en", "sw"] = "en"
    printer_name: str | None = Field(default="Browser / PDF", max_length=160)
    requested_by: str = Field(default="Front Desk", min_length=2, max_length=160)


class BenefitCheckIn(BaseModel):
    encounter_id: str | None = None
    payer: str = Field(min_length=2, max_length=160)
    member_number: str | None = Field(default=None, max_length=160)
    service: str | None = Field(default=None, max_length=160)
    requested_by: str = Field(default="Front Desk", min_length=2, max_length=160)


class TravelScreeningIn(BaseModel):
    encounter_id: str | None = None
    responses: dict[str, bool | str | int | float | None]
    completed_by: str = Field(default="Front Desk", min_length=2, max_length=160)


def _encounter_for_patient(db: Session, patient: Patient, encounter_id: str | None) -> Encounter | None:
    if encounter_id:
        encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == encounter_id, Encounter.patient_id == patient.id))
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found for selected patient")
        return encounter
    return db.scalar(select(Encounter).where(Encounter.patient_id == patient.id).order_by(Encounter.arrival_at.desc()).limit(1))


def _print_context(patient: Patient, encounter: Encounter | None, facility_code: str) -> dict:
    return {
        "patient": {
            "mpi_id": patient.mpi_id,
            "mrn": patient.mrn,
            "full_name": patient.full_name,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            "sex": patient.sex,
            "phone": patient.phone,
            "nida_number": patient.nida_number,
            "address": patient.address,
            "region": patient.region,
            "district": patient.district,
            "next_of_kin": patient.next_of_kin,
            "payer": patient.payer,
            "member_number": patient.member_number,
            "allergies": patient.allergies,
            "consent_status": patient.consent_status,
        },
        "encounter": None if not encounter else {
            "encounter_id": encounter.encounter_id,
            "encounter_type": encounter.encounter_type,
            "service": encounter.service,
            "status": encounter.status.value if hasattr(encounter.status, "value") else str(encounter.status),
            "location": encounter.location,
            "room": encounter.room,
            "provider": encounter.provider,
            "reason_for_visit": encounter.reason_for_visit,
            "arrival_at": encounter.arrival_at.isoformat() if encounter.arrival_at else None,
            "discharge_at": encounter.discharge_at.isoformat() if encounter.discharge_at else None,
        },
        "facility_code": facility_code,
        "generated_at": now().isoformat(),
    }


@router.get("/print-templates")
def print_templates():
    return PRINT_TEMPLATE_CATALOG


@router.post("/patients/{mpi_id}/print-jobs", status_code=201)
def create_print_jobs(mpi_id: str, payload: PrintJobCreateIn, db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, mpi_id)
    encounter = _encounter_for_patient(db, patient, payload.encounter_id)
    facility_code = operation_facility_code = "UNKNOWN"
    if encounter:
        facility = db.get(Facility, encounter.facility_id)
        facility_code = facility.code if facility else "UNKNOWN"
    catalog = {item["code"]: item for item in PRINT_TEMPLATE_CATALOG}
    invalid = [code for code in payload.template_codes if code not in catalog]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unknown print template(s): {', '.join(invalid)}")
    context = _print_context(patient, encounter, facility_code)
    jobs = []
    for code in payload.template_codes:
        definition = catalog[code]
        job = PrintJob(
            patient_id=patient.id,
            encounter_id=encounter.id if encounter else None,
            facility_code=facility_code,
            template_code=code,
            template_name=definition["name"],
            copies=payload.copies,
            language=payload.language,
            printer_name=payload.printer_name,
            status="COMPLETED",
            payload_json=json.dumps(context, default=str),
            requested_by=payload.requested_by,
            completed_at=now(),
        )
        db.add(job)
        db.flush()
        jobs.append({
            "job_id": job.job_id,
            "template": definition,
            "copies": job.copies,
            "language": job.language,
            "printer_name": job.printer_name,
            "status": job.status,
        })
    write_audit(
        db,
        action="CREATE_PRINT_JOB",
        resource_type="PatientPrint",
        resource_id=",".join(job["job_id"] for job in jobs),
        actor=payload.requested_by,
        role="Patient Access",
        patient_mpi_id=patient.mpi_id,
        facility_code=facility_code,
        details=f"Templates={','.join(payload.template_codes)}; copies={payload.copies}; printer={payload.printer_name}",
    )
    db.commit()
    return {"jobs": jobs, "document_context": context}


@router.get("/patients/{mpi_id}/print-jobs")
def list_print_jobs(mpi_id: str, limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, mpi_id)
    jobs = list(db.scalars(select(PrintJob).where(PrintJob.patient_id == patient.id).order_by(PrintJob.created_at.desc()).limit(limit)).all())
    return [{
        "job_id": item.job_id,
        "template_code": item.template_code,
        "template_name": item.template_name,
        "copies": item.copies,
        "language": item.language,
        "printer_name": item.printer_name,
        "status": item.status,
        "requested_by": item.requested_by,
        "created_at": item.created_at,
    } for item in jobs]


@router.post("/patients/{mpi_id}/benefit-checks", status_code=201)
def create_benefit_check(mpi_id: str, payload: BenefitCheckIn, db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, mpi_id)
    encounter = _encounter_for_patient(db, patient, payload.encounter_id)
    payer = payload.payer.strip()
    member = (payload.member_number or "").strip()
    lower = payer.lower()
    if lower in {"cash", "self pay", "self-pay", "private cash"}:
        status, code, message, copay = "SELF_PAY", "CASH", "No electronic eligibility is required. Route the account through the cash/self-pay workflow.", "Per tariff"
    elif not member:
        status, code, message, copay = "NEEDS_REVIEW", "MEMBER_REQUIRED", "Member or policy number is missing. The item was routed to coverage follow-up.", None
    else:
        status, code, message, copay = "ELIGIBLE", "ACTIVE", f"{payer} coverage returned active for the selected service in the Docker review simulator.", "TZS 2,000"
    verification = CoverageVerification(
        patient_id=patient.id,
        encounter_id=encounter.id if encounter else None,
        payer=payer,
        member_number=member or None,
        service=payload.service or (encounter.service if encounter else None),
        status=status,
        response_code=code,
        response_message=message,
        copay_amount=copay,
        requested_by=payload.requested_by,
        completed_at=now(),
    )
    db.add(verification)
    db.flush()
    if status == "NEEDS_REVIEW":
        queue = db.scalar(select(WorkQueueDefinition).where(WorkQueueDefinition.code == "NHIF_ELIGIBILITY_PENDING"))
        if queue:
            db.add(WorkQueueItem(
                queue_definition_id=queue.id,
                patient_id=patient.id,
                encounter_id=encounter.id if encounter else None,
                title=f"Coverage eligibility follow-up — {patient.full_name}",
                reason=message,
                priority="HIGH",
                status="ACTIVE",
                assigned_to=queue.owner_team,
                due_at=now() + timedelta(hours=queue.sla_hours or 8),
                created_by=payload.requested_by,
            ))
    write_audit(
        db,
        action="COVERAGE_ELIGIBILITY_CHECK",
        resource_type="CoverageVerification",
        resource_id=verification.verification_id,
        actor=payload.requested_by,
        role="Patient Access",
        patient_mpi_id=patient.mpi_id,
        facility_code=(db.get(Facility, encounter.facility_id).code if encounter and db.get(Facility, encounter.facility_id) else None),
        details=f"payer={payer}; status={status}; response={code}",
    )
    db.commit()
    return {
        "verification_id": verification.verification_id,
        "payer": payer,
        "member_number": member or None,
        "service": verification.service,
        "status": status,
        "response_code": code,
        "message": message,
        "copay_amount": copay,
        "completed_at": verification.completed_at,
    }


@router.get("/patients/{mpi_id}/benefit-checks")
def list_benefit_checks(mpi_id: str, limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, mpi_id)
    items = list(db.scalars(select(CoverageVerification).where(CoverageVerification.patient_id == patient.id).order_by(CoverageVerification.requested_at.desc()).limit(limit)).all())
    return [{
        "verification_id": item.verification_id,
        "payer": item.payer,
        "member_number": item.member_number,
        "service": item.service,
        "status": item.status,
        "response_code": item.response_code,
        "response_message": item.response_message,
        "copay_amount": item.copay_amount,
        "requested_by": item.requested_by,
        "requested_at": item.requested_at,
    } for item in items]


@router.post("/patients/{mpi_id}/travel-screenings", status_code=201)
def create_travel_screening(mpi_id: str, payload: TravelScreeningIn, db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, mpi_id)
    encounter = _encounter_for_patient(db, patient, payload.encounter_id)
    responses = payload.responses or {}
    yes = lambda key: responses.get(key) is True or str(responses.get(key, "")).strip().lower() in {"yes", "true", "1", "positive"}
    symptom_keys = ["fever", "cough", "breathing_difficulty", "rash", "diarrhoea", "bleeding"]
    symptom_count = sum(1 for key in symptom_keys if yes(key))
    exposure = yes("recent_travel") or yes("infectious_exposure") or yes("outbreak_area")
    if yes("bleeding") or (symptom_count >= 2 and exposure):
        risk, disposition = "HIGH", "Isolate or mask as appropriate and notify the clinical triage/infection-prevention team immediately."
    elif symptom_count or exposure:
        risk, disposition = "MODERATE", "Route to clinical triage for focused communicable-disease assessment."
    else:
        risk, disposition = "LOW", "Continue the standard patient-flow pathway."
    screening = TravelScreening(
        patient_id=patient.id,
        encounter_id=encounter.id if encounter else None,
        responses_json=json.dumps(responses, default=str),
        risk_level=risk,
        disposition=disposition,
        status="COMPLETED",
        completed_by=payload.completed_by,
    )
    db.add(screening)
    db.flush()
    if risk in {"HIGH", "MODERATE"}:
        queue = db.scalar(select(WorkQueueDefinition).where(WorkQueueDefinition.code == "FRONT_DESK_ARRIVAL_EXCEPTIONS"))
        if queue:
            db.add(WorkQueueItem(
                queue_definition_id=queue.id,
                patient_id=patient.id,
                encounter_id=encounter.id if encounter else None,
                title=f"Travel / infection screening follow-up — {patient.full_name}",
                reason=f"{risk} screening risk. {disposition}",
                priority="URGENT" if risk == "HIGH" else "HIGH",
                status="ACTIVE",
                assigned_to=queue.owner_team,
                due_at=now() + timedelta(hours=1 if risk == "HIGH" else 4),
                created_by=payload.completed_by,
            ))
    write_audit(
        db,
        action="TRAVEL_SCREENING_COMPLETED",
        resource_type="TravelScreening",
        resource_id=screening.screening_id,
        actor=payload.completed_by,
        role="Patient Access",
        patient_mpi_id=patient.mpi_id,
        facility_code=(db.get(Facility, encounter.facility_id).code if encounter and db.get(Facility, encounter.facility_id) else None),
        details=f"risk={risk}; disposition={disposition}",
    )
    db.commit()
    return {
        "screening_id": screening.screening_id,
        "risk_level": risk,
        "disposition": disposition,
        "status": screening.status,
        "completed_at": screening.completed_at,
    }


@router.get("/patients/{mpi_id}/travel-screenings")
def list_travel_screenings(mpi_id: str, limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, mpi_id)
    items = list(db.scalars(select(TravelScreening).where(TravelScreening.patient_id == patient.id).order_by(TravelScreening.completed_at.desc()).limit(limit)).all())
    return [{
        "screening_id": item.screening_id,
        "screening_type": item.screening_type,
        "responses": json.loads(item.responses_json or "{}"),
        "risk_level": item.risk_level,
        "disposition": item.disposition,
        "status": item.status,
        "completed_by": item.completed_by,
        "completed_at": item.completed_at,
    } for item in items]
