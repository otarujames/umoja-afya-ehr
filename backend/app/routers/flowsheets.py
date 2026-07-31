from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..audit import write_audit
from ..database import get_db
from ..models import Encounter, FlowSheet, FlowSheetEvent, FlowSheetObservation, FlowSheetStatus, Patient
from ..schemas import FlowSheetAction, FlowSheetCreate, FlowSheetObservationIn
from ..serializers import flowsheet_dict

router = APIRouter(tags=["Clinical Flowsheets"])


def _get_flowsheet(db: Session, flowsheet_id: str) -> FlowSheet:
    flowsheet = db.scalar(
        select(FlowSheet)
        .options(selectinload(FlowSheet.patient), selectinload(FlowSheet.events), selectinload(FlowSheet.observations))
        .where(FlowSheet.flowsheet_id == flowsheet_id)
    )
    if not flowsheet:
        raise HTTPException(status_code=404, detail="Flowsheet not found")
    if flowsheet.encounter_id:
        encounter = db.get(Encounter, flowsheet.encounter_id)
        setattr(flowsheet, "_encounter_public_id", encounter.encounter_id if encounter else None)
    return flowsheet


def _accumulate_elapsed(flowsheet: FlowSheet, now: datetime) -> None:
    if flowsheet.active_since:
        active_since = flowsheet.active_since
        if active_since.tzinfo is None:
            active_since = active_since.replace(tzinfo=timezone.utc)
        flowsheet.elapsed_seconds += max(0, int((now - active_since).total_seconds()))
        flowsheet.active_since = None


@router.get("/flowsheets")
def list_flowsheets(
    patient_mpi_id: str | None = Query(default=None),
    status: FlowSheetStatus | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(FlowSheet).options(
        selectinload(FlowSheet.patient),
        selectinload(FlowSheet.events),
        selectinload(FlowSheet.observations),
    )
    if patient_mpi_id:
        query = query.join(Patient).where(Patient.mpi_id == patient_mpi_id)
    if status:
        query = query.where(FlowSheet.status == status)
    items = list(db.scalars(query.order_by(FlowSheet.created_at.desc())).all())
    for item in items:
        if item.encounter_id:
            encounter = db.get(Encounter, item.encounter_id)
            setattr(item, "_encounter_public_id", encounter.encounter_id if encounter else None)
    return [flowsheet_dict(item) for item in items]


@router.post("/flowsheets", status_code=201)
def create_flowsheet(payload: FlowSheetCreate, db: Session = Depends(get_db)):
    patient = db.scalar(select(Patient).where(Patient.mpi_id == payload.patient_mpi_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    encounter_pk = None
    if payload.encounter_id:
        encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == payload.encounter_id))
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        encounter_pk = encounter.id
    flowsheet = FlowSheet(
        patient=patient,
        encounter_id=encounter_pk,
        name=payload.name,
        template_code=payload.template_code,
        cadence_minutes=payload.cadence_minutes,
        parameters_json=json.dumps(payload.parameters),
        owner=payload.owner,
    )
    db.add(flowsheet)
    db.flush()
    db.add(FlowSheetEvent(flowsheet=flowsheet, action="CREATE", actor=payload.owner, note="Flowsheet created"))
    write_audit(db, action="CREATE_FLOWSHEET", resource_type="FlowSheet", resource_id=flowsheet.flowsheet_id, actor=payload.owner, role="Nursing", patient_mpi_id=patient.mpi_id)
    db.commit()
    return flowsheet_dict(_get_flowsheet(db, flowsheet.flowsheet_id))


@router.post("/flowsheets/{flowsheet_id}/actions")
def control_flowsheet(flowsheet_id: str, payload: FlowSheetAction, db: Session = Depends(get_db)):
    flowsheet = _get_flowsheet(db, flowsheet_id)
    now = datetime.now(timezone.utc)
    action = payload.action

    if action == "START":
        if flowsheet.status != FlowSheetStatus.DRAFT:
            raise HTTPException(status_code=409, detail="Only a draft flowsheet can be started")
        flowsheet.status = FlowSheetStatus.RUNNING
        flowsheet.started_at = now
        flowsheet.active_since = now
    elif action == "PAUSE":
        if flowsheet.status != FlowSheetStatus.RUNNING:
            raise HTTPException(status_code=409, detail="Only a running flowsheet can be paused")
        _accumulate_elapsed(flowsheet, now)
        flowsheet.status = FlowSheetStatus.PAUSED
    elif action == "RESUME":
        if flowsheet.status != FlowSheetStatus.PAUSED:
            raise HTTPException(status_code=409, detail="Only a paused flowsheet can be resumed")
        flowsheet.status = FlowSheetStatus.RUNNING
        flowsheet.active_since = now
    elif action == "CHANGE":
        if flowsheet.status == FlowSheetStatus.STOPPED:
            raise HTTPException(status_code=409, detail="A stopped flowsheet cannot be changed")
        if payload.name:
            flowsheet.name = payload.name
        if payload.cadence_minutes:
            flowsheet.cadence_minutes = payload.cadence_minutes
        if payload.parameters is not None:
            flowsheet.parameters_json = json.dumps(payload.parameters)
    elif action == "STOP":
        if flowsheet.status not in {FlowSheetStatus.RUNNING, FlowSheetStatus.PAUSED}:
            raise HTTPException(status_code=409, detail="Only an active or paused flowsheet can be stopped")
        if flowsheet.status == FlowSheetStatus.RUNNING:
            _accumulate_elapsed(flowsheet, now)
        flowsheet.status = FlowSheetStatus.STOPPED
        flowsheet.stopped_at = now
    else:
        raise HTTPException(status_code=400, detail="Unsupported action")

    db.add(FlowSheetEvent(flowsheet=flowsheet, action=action, actor=payload.actor, note=payload.note))
    write_audit(db, action=f"FLOWSHEET_{action}", resource_type="FlowSheet", resource_id=flowsheet.flowsheet_id, actor=payload.actor, role="Nursing", patient_mpi_id=flowsheet.patient.mpi_id, details=payload.note)
    db.commit()
    return flowsheet_dict(_get_flowsheet(db, flowsheet_id))


@router.post("/flowsheets/{flowsheet_id}/observations", status_code=201)
def record_observation(flowsheet_id: str, payload: FlowSheetObservationIn, db: Session = Depends(get_db)):
    flowsheet = _get_flowsheet(db, flowsheet_id)
    if flowsheet.status == FlowSheetStatus.STOPPED:
        raise HTTPException(status_code=409, detail="Cannot record observations on a stopped flowsheet")
    observation = FlowSheetObservation(
        flowsheet=flowsheet,
        parameter=payload.parameter,
        value=payload.value,
        unit=payload.unit,
        source=payload.source,
        recorded_by=payload.recorded_by,
    )
    db.add(observation)
    write_audit(db, action="RECORD_FLOWSHEET_OBSERVATION", resource_type="FlowSheet", resource_id=flowsheet.flowsheet_id, actor=payload.recorded_by, role="Nursing", patient_mpi_id=flowsheet.patient.mpi_id, details=f"{payload.parameter}={payload.value}{payload.unit or ''}")
    db.commit()
    return flowsheet_dict(_get_flowsheet(db, flowsheet_id))
