from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel, Field

from ..database import get_db
from ..audit import write_audit
from ..models import Encounter, Patient
from ..serializers import encounter_dict, patient_dict

router = APIRouter(tags=["Patients"])


@router.get("/patients")
def list_patients(
    search: str | None = Query(default=None, min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    country_code: str | None = Query(default=None, min_length=2, max_length=3),
    db: Session = Depends(get_db),
):
    query = select(Patient).order_by(Patient.last_name, Patient.first_name)
    if country_code:
        query = query.where(Patient.country_code == country_code.upper())
    if search:
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Patient.first_name).like(pattern),
                func.lower(Patient.middle_name).like(pattern),
                func.lower(Patient.last_name).like(pattern),
                func.lower(Patient.mpi_id).like(pattern),
                func.lower(Patient.mrn).like(pattern),
                func.lower(Patient.phone).like(pattern),
                func.lower(Patient.nida_number).like(pattern),
            )
        )
    return [patient_dict(p) for p in db.scalars(query.limit(limit)).all()]


@router.get("/patients/{mpi_id}")
def get_patient(mpi_id: str, db: Session = Depends(get_db)):
    patient = db.scalar(
        select(Patient)
        .options(selectinload(Patient.encounters).selectinload(Encounter.facility))
        .where(Patient.mpi_id == mpi_id)
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    payload = patient_dict(patient)
    payload["encounters"] = [encounter_dict(e) for e in sorted(patient.encounters, key=lambda item: item.arrival_at, reverse=True)]
    return payload


class PatientUpdateIn(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    middle_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=80)
    nida_number: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=500)
    region: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    next_of_kin: str | None = Field(default=None, max_length=300)
    payer: str | None = Field(default=None, max_length=120)
    member_number: str | None = Field(default=None, max_length=180)
    consent_status: str | None = Field(default=None, max_length=80)
    actor: str = Field(default="Registration User", min_length=2, max_length=180)


@router.patch("/patients/{mpi_id}")
def update_patient(mpi_id: str, payload: PatientUpdateIn, db: Session = Depends(get_db)):
    patient = db.scalar(select(Patient).where(Patient.mpi_id == mpi_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    before = patient_dict(patient)
    values = payload.model_dump(exclude_unset=True, exclude={"actor"})
    if "nida_number" in values and values["nida_number"]:
        duplicate = db.scalar(select(Patient).where(Patient.nida_number == values["nida_number"], Patient.id != patient.id))
        if duplicate:
            raise HTTPException(status_code=409, detail="NIDA number is already linked to another patient record")
    for field, value in values.items():
        setattr(patient, field, value.strip() if isinstance(value, str) else value)
    db.flush()
    after = patient_dict(patient)
    changed = sorted(key for key in values if before.get(key) != after.get(key))
    write_audit(
        db, action="UPDATE_PATIENT_REGISTRATION", resource_type="Patient", resource_id=patient.mpi_id,
        actor=payload.actor, role="registration.manage", patient_mpi_id=patient.mpi_id,
        details=f"Changed fields: {', '.join(changed) if changed else 'none'}",
    )
    db.commit()
    return patient_dict(patient)
