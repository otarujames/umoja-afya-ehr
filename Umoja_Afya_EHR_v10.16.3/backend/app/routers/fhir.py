from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Encounter, Patient, Result
from ..security import optional_user

router = APIRouter(tags=["FHIR R4"], dependencies=[Depends(optional_user)])


def patient_resource(patient: Patient) -> dict:
    return {
        "resourceType": "Patient",
        "id": patient.mpi_id,
        "identifier": [
            {"system": "https://umoja-afya.go.tz/id/mpi", "value": patient.mpi_id},
            {"system": "https://umoja-afya.go.tz/id/mrn", "value": patient.mrn},
        ],
        "active": True,
        "name": [{"use": "official", "family": patient.last_name, "given": [x for x in [patient.first_name, patient.middle_name] if x]}],
        "telecom": [{"system": "phone", "value": patient.phone}] if patient.phone else [],
        "gender": {"Male": "male", "Female": "female", "Unknown": "unknown"}.get(patient.sex, "other"),
        "birthDate": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        "address": [{"text": patient.address, "district": patient.district, "state": patient.region, "country": "TZ"}] if patient.address else [],
    }


@router.get("/fhir/R4/Patient/{patient_id}")
def fhir_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.scalar(select(Patient).where(Patient.mpi_id == patient_id))
    if not patient:
        raise HTTPException(status_code=404, detail={"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found"}]})
    return patient_resource(patient)


@router.get("/fhir/R4/Patient")
def fhir_patient_search(identifier: str | None = None, name: str | None = None, db: Session = Depends(get_db)):
    query = select(Patient)
    if identifier:
        query = query.where((Patient.mpi_id == identifier) | (Patient.mrn == identifier) | (Patient.nida_number == identifier))
    if name:
        like = f"%{name.strip()}%"
        query = query.where((Patient.first_name.ilike(like)) | (Patient.last_name.ilike(like)))
    patients = list(db.scalars(query.limit(50)).all())
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(patients),
        "entry": [{"fullUrl": f"https://umoja-afya.go.tz/fhir/R4/Patient/{p.mpi_id}", "resource": patient_resource(p)} for p in patients],
    }


@router.get("/fhir/R4/Encounter/{encounter_id}")
def fhir_encounter(encounter_id: str, db: Session = Depends(get_db)):
    encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == encounter_id))
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return {
        "resourceType": "Encounter",
        "id": encounter.encounter_id,
        "status": "finished" if encounter.discharge_at else "in-progress",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP" if encounter.encounter_type == "INPATIENT" else "AMB"},
        "subject": {"reference": f"Patient/{encounter.patient.mpi_id}", "display": encounter.patient.full_name},
        "serviceType": {"text": encounter.service},
        "period": {"start": encounter.arrival_at.isoformat(), "end": encounter.discharge_at.isoformat() if encounter.discharge_at else None},
        "location": [{"location": {"display": f"{encounter.location} {encounter.room or ''}".strip()}}],
    }


@router.get("/fhir/R4/Observation")
def fhir_observations(patient: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Patient).where(Patient.mpi_id == patient))
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    results = list(db.scalars(select(Result).where(Result.patient_id == p.id).order_by(Result.issued_at.desc()).limit(100)).all())
    entries = []
    for result in results:
        entries.append({
            "resource": {
                "resourceType": "Observation",
                "id": result.result_id,
                "status": "final",
                "category": [{"text": "laboratory"}],
                "code": {"text": result.test_name},
                "subject": {"reference": f"Patient/{p.mpi_id}"},
                "effectiveDateTime": result.issued_at.isoformat(),
                "valueQuantity": {"value": result.value, "unit": result.unit},
                "interpretation": [{"text": result.flag}],
            }
        })
    return {"resourceType": "Bundle", "type": "searchset", "total": len(entries), "entry": entries}
