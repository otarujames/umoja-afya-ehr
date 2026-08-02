from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..audit import write_audit
from ..database import get_db
from ..event_management import record_managed_event
from ..models import Encounter, EncounterStatus, Facility, Patient
from ..schemas import DischargeIn, EncounterCreateIn, EncounterStatusUpdate
from ..serializers import encounter_dict

router = APIRouter(tags=["Patient Flow and ADT"])

ALLOWED_TRANSITIONS = {
    EncounterStatus.PRE_REGISTERED: {EncounterStatus.ARRIVED, EncounterStatus.REGISTERED},
    EncounterStatus.ARRIVED: {EncounterStatus.WAITING_REGISTRATION, EncounterStatus.REGISTERED, EncounterStatus.WAITING_TRIAGE, EncounterStatus.LEFT_WITHOUT_BEING_SEEN},
    EncounterStatus.WAITING_REGISTRATION: {EncounterStatus.REGISTERED, EncounterStatus.LEFT_WITHOUT_BEING_SEEN},
    EncounterStatus.REGISTERED: {EncounterStatus.WAITING_TRIAGE, EncounterStatus.TRANSFERRED},
    EncounterStatus.WAITING_TRIAGE: {EncounterStatus.TRIAGED, EncounterStatus.LEFT_WITHOUT_BEING_SEEN},
    EncounterStatus.TRIAGED: {EncounterStatus.READY_FOR_PROVIDER, EncounterStatus.TRANSFERRED},
    EncounterStatus.READY_FOR_PROVIDER: {EncounterStatus.ROOMED, EncounterStatus.LEFT_WITHOUT_BEING_SEEN},
    EncounterStatus.ROOMED: {EncounterStatus.IN_PROGRESS},
    EncounterStatus.IN_PROGRESS: {EncounterStatus.WAITING_RESULTS, EncounterStatus.READY_FOR_DISCHARGE, EncounterStatus.TRANSFERRED},
    EncounterStatus.WAITING_RESULTS: {EncounterStatus.IN_PROGRESS, EncounterStatus.READY_FOR_DISCHARGE, EncounterStatus.TRANSFERRED},
    EncounterStatus.READY_FOR_DISCHARGE: {EncounterStatus.DISCHARGED, EncounterStatus.IN_PROGRESS},
    EncounterStatus.DISCHARGED: set(),
    EncounterStatus.TRANSFERRED: set(),
    EncounterStatus.LEFT_WITHOUT_BEING_SEEN: set(),
}


@router.post("/patients/{patient_mpi_id}/encounters", status_code=201)
def create_patient_encounter(
    patient_mpi_id: str,
    payload: EncounterCreateIn,
    db: Session = Depends(get_db),
):
    """Create a real encounter while keeping identifiers server controlled."""
    patient = db.scalar(select(Patient).where(Patient.mpi_id == patient_mpi_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    facility = db.scalar(
        select(Facility).where(Facility.code == payload.facility_code, Facility.active.is_(True))
    )
    if not facility:
        raise HTTPException(status_code=404, detail="Active facility not found")

    encounter_type = payload.encounter_type.upper()
    status = EncounterStatus.ARRIVED if encounter_type == "EMERGENCY" else EncounterStatus.REGISTERED
    encounter = Encounter(
        patient=patient,
        facility=facility,
        encounter_type=encounter_type,
        service=payload.service.strip(),
        status=status,
        location="Emergency arrival" if encounter_type == "EMERGENCY" else "Registration",
        reason_for_visit=(payload.reason_for_visit or "").strip() or None,
    )
    db.add(encounter)
    db.flush()  # Generates the ENC- identifier before audit and response serialization.
    record_managed_event(
        db,
        entity_type="ENCOUNTER",
        entity_id=encounter.encounter_id,
        action="CREATE",
        actor=payload.actor,
        status_after=status.value,
        patient_id=patient.id,
        encounter_id=encounter.id,
        reason=encounter.reason_for_visit,
        reversible=False,
        metadata={
            "encounter_type": encounter_type,
            "service": encounter.service,
            "facility_code": facility.code,
            "identifier_source": "SERVER_GENERATED",
        },
    )
    write_audit(
        db,
        action="CREATE_ENCOUNTER",
        resource_type="Encounter",
        resource_id=encounter.encounter_id,
        actor=payload.actor,
        role="Registration",
        patient_mpi_id=patient.mpi_id,
        facility_code=facility.code,
        details=f"Type={encounter_type}; service={encounter.service}; identifier=server-generated",
    )
    db.commit()
    created = db.scalar(
        select(Encounter)
        .options(selectinload(Encounter.patient), selectinload(Encounter.facility))
        .where(Encounter.id == encounter.id)
    )
    return encounter_dict(created)


@router.get("/tracker")
def get_tracker(
    facility_code: str | None = Query(default=None),
    include_discharged: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    query = select(Encounter).options(selectinload(Encounter.patient), selectinload(Encounter.facility))
    if facility_code and facility_code != "ALL":
        query = query.join(Facility).where(Facility.code == facility_code)
    if not include_discharged:
        query = query.where(Encounter.status.not_in([EncounterStatus.DISCHARGED, EncounterStatus.TRANSFERRED]))
    encounters = list(db.scalars(query.order_by(Encounter.arrival_at)).all())
    return [encounter_dict(item) for item in encounters]


@router.patch("/encounters/{encounter_id}/status")
def update_status(encounter_id: str, payload: EncounterStatusUpdate, db: Session = Depends(get_db)):
    encounter = db.scalar(
        select(Encounter)
        .options(selectinload(Encounter.patient), selectinload(Encounter.facility))
        .where(Encounter.encounter_id == encounter_id)
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    if payload.status != encounter.status and payload.status not in ALLOWED_TRANSITIONS.get(encounter.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid encounter transition: {encounter.status.value} -> {payload.status.value}",
        )

    previous_status = encounter.status.value
    encounter.status = payload.status
    if payload.location is not None:
        encounter.location = payload.location
    if payload.room is not None:
        encounter.room = payload.room
    if payload.provider is not None:
        encounter.provider = payload.provider
    if payload.acuity is not None:
        encounter.acuity = payload.acuity
    now = datetime.now(timezone.utc)
    if payload.status == EncounterStatus.TRIAGED:
        encounter.triage_at = now
    # Rooming records physical placement only. Provider time begins when care
    # is explicitly moved to IN_PROGRESS.
    if payload.status == EncounterStatus.IN_PROGRESS and not encounter.provider_start_at:
        encounter.provider_start_at = now
    if payload.status == EncounterStatus.DISCHARGED:
        encounter.discharge_at = now

    record_managed_event(db, entity_type="ENCOUNTER", entity_id=encounter.encounter_id, action="STATUS_CHANGE", actor=payload.actor, status_before=previous_status, status_after=encounter.status.value, patient_id=encounter.patient_id, encounter_id=encounter.id, reason=payload.note, reversible=True, metadata={"location": encounter.location, "room": encounter.room, "provider": encounter.provider, "acuity": encounter.acuity})
    write_audit(
        db,
        action="UPDATE_ENCOUNTER_STATUS",
        resource_type="Encounter",
        resource_id=encounter.encounter_id,
        actor=payload.actor,
        role="Care Team",
        patient_mpi_id=encounter.patient.mpi_id,
        facility_code=encounter.facility.code,
        details=f"Status={payload.status.value}; note={payload.note or ''}",
    )
    db.commit()
    return encounter_dict(encounter)


@router.post("/encounters/{encounter_id}/discharge")
def discharge(encounter_id: str, payload: DischargeIn, db: Session = Depends(get_db)):
    encounter = db.scalar(
        select(Encounter)
        .options(selectinload(Encounter.patient), selectinload(Encounter.facility))
        .where(Encounter.encounter_id == encounter_id)
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    previous_status = encounter.status.value
    encounter.status = EncounterStatus.DISCHARGED
    encounter.discharge_at = datetime.now(timezone.utc)
    encounter.discharge_disposition = payload.disposition
    encounter.discharge_summary = payload.summary
    encounter.follow_up = payload.follow_up
    record_managed_event(db, entity_type="ENCOUNTER", entity_id=encounter.encounter_id, action="DISCHARGE", actor=payload.actor, status_before=previous_status, status_after=EncounterStatus.DISCHARGED.value, patient_id=encounter.patient_id, encounter_id=encounter.id, reason=payload.disposition, reversible=True, metadata={"summary": payload.summary, "follow_up": payload.follow_up})
    write_audit(
        db,
        action="DISCHARGE_PATIENT",
        resource_type="Encounter",
        resource_id=encounter.encounter_id,
        actor=payload.actor,
        role="Provider",
        patient_mpi_id=encounter.patient.mpi_id,
        facility_code=encounter.facility.code,
        details=payload.disposition,
    )
    db.commit()
    return encounter_dict(encounter)


@router.get("/recent-discharges")
def recent_discharges(
    facility_code: str | None = Query(default=None),
    hours: int = Query(default=72, ge=1, le=720),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = (
        select(Encounter)
        .options(selectinload(Encounter.patient), selectinload(Encounter.facility))
        .where(Encounter.status == EncounterStatus.DISCHARGED, Encounter.discharge_at >= since)
    )
    if facility_code and facility_code != "ALL":
        query = query.join(Facility).where(Facility.code == facility_code)
    encounters = list(db.scalars(query.order_by(Encounter.discharge_at.desc()).limit(limit)).all())
    return [encounter_dict(item) for item in encounters]
