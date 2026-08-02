from __future__ import annotations

import random
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..audit import write_audit
from ..database import get_db
from ..models import Encounter, EncounterStatus, Facility, Patient
from ..schemas import RegistrationIn, RegistrationSearchIn
from ..serializers import encounter_dict, patient_dict

router = APIRouter(tags=["Patient Registration Registration"])


def _unique_mpi_id(db: Session) -> str:
    for _ in range(50):
        candidate = f"TZ-MPI-{random.randint(70000000, 99999999)}"
        if not db.scalar(select(Patient.id).where(Patient.mpi_id == candidate)):
            return candidate
    raise HTTPException(status_code=503, detail="Unable to allocate a national MPI identifier; retry registration")


def _next_mrn(db: Session, facility_code: str) -> str:
    prefix = "MNH" if facility_code.startswith("MNH") else re.sub(r"[^A-Z0-9]", "", facility_code.upper())[:8]
    existing = list(db.scalars(select(Patient.mrn).where(Patient.mrn.like(f"{prefix}-%"))).all())
    highest = 0
    for value in existing:
        match = re.search(r"(\d+)$", value or "")
        if match:
            highest = max(highest, int(match.group(1)))
    for number in range(highest + 1, highest + 1000):
        candidate = f"{prefix}-{number:07d}"
        if not db.scalar(select(Patient.id).where(Patient.mrn == candidate)):
            return candidate
    raise HTTPException(status_code=503, detail="Unable to allocate an MRN; retry registration")


def _find_matches(db: Session, payload: RegistrationSearchIn | RegistrationIn) -> list[Patient]:
    conditions = []
    if getattr(payload, "nida_number", None):
        conditions.append(Patient.nida_number == payload.nida_number)
    if getattr(payload, "phone", None):
        conditions.append(Patient.phone == payload.phone)
    if getattr(payload, "date_of_birth", None) and getattr(payload, "last_name", None):
        conditions.append(
            (Patient.date_of_birth == payload.date_of_birth)
            & (func.lower(Patient.last_name) == payload.last_name.lower())
        )
    if getattr(payload, "first_name", None) and getattr(payload, "last_name", None):
        conditions.append(
            (func.lower(Patient.first_name) == payload.first_name.lower())
            & (func.lower(Patient.last_name) == payload.last_name.lower())
        )
    if getattr(payload, "mrn", None):
        conditions.append(Patient.mrn == payload.mrn)
    if not conditions:
        return []
    return list(db.scalars(select(Patient).where(or_(*conditions)).limit(10)).all())


@router.post("/registration/search")
def search_registration(payload: RegistrationSearchIn, db: Session = Depends(get_db)):
    matches = _find_matches(db, payload)
    return {
        "match_count": len(matches),
        "matches": [patient_dict(p) for p in matches],
        "requires_review": len(matches) > 0,
    }


@router.post("/registration", status_code=201)
def register_patient(payload: RegistrationIn, db: Session = Depends(get_db)):
    facility = db.scalar(select(Facility).where(Facility.code == payload.facility_code))
    if not facility:
        raise HTTPException(status_code=400, detail="Unknown facility code")

    possible_duplicates = _find_matches(db, payload)
    if possible_duplicates and not payload.force_create:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Possible duplicate patient found. Review before creating a new national identity.",
                "matches": [patient_dict(p) for p in possible_duplicates],
            },
        )

    stamp = datetime.now(timezone.utc).strftime("%y%m%d")
    mpi_id = _unique_mpi_id(db)
    mrn = _next_mrn(db, payload.facility_code)
    patient = Patient(
        mpi_id=mpi_id,
        mrn=mrn,
        first_name=payload.first_name.strip(),
        middle_name=payload.middle_name.strip() if payload.middle_name else None,
        last_name=payload.last_name.strip(),
        date_of_birth=payload.date_of_birth,
        sex=payload.sex,
        phone=payload.phone,
        nida_number=payload.nida_number,
        address=payload.address,
        region=payload.region,
        district=payload.district,
        next_of_kin=payload.next_of_kin,
        payer=payload.payer,
        member_number=payload.member_number,
        consent_status=payload.consent_status,
        identity_status="TEMPORARY" if payload.registration_mode in {"UNKNOWN", "EMERGENCY"} else "VERIFIED",
    )
    db.add(patient)
    db.flush()

    status = EncounterStatus.PRE_REGISTERED if payload.registration_mode == "PRE_REGISTRATION" else EncounterStatus.REGISTERED
    if payload.registration_mode in {"EMERGENCY", "UNKNOWN"}:
        status = EncounterStatus.ARRIVED

    encounter = Encounter(
        encounter_id=f"ENC-{stamp}-{random.randint(10000, 99999)}",
        patient=patient,
        facility=facility,
        encounter_type=payload.encounter_type,
        service=payload.service,
        status=status,
        location="Patient Registration Registration" if status == EncounterStatus.REGISTERED else "Arrival Desk",
        reason_for_visit=payload.reason_for_visit,
    )
    db.add(encounter)
    write_audit(
        db,
        action="REGISTER_PATIENT",
        resource_type="Patient",
        resource_id=patient.mpi_id,
        actor="Patient Registration user",
        role="Patient Access",
        patient_mpi_id=patient.mpi_id,
        facility_code=facility.code,
        details=f"Mode={payload.registration_mode}; proxy={payload.proxy_name or 'none'}",
    )
    db.commit()
    db.refresh(encounter)
    encounter = db.scalar(
        select(Encounter)
        .options(selectinload(Encounter.patient), selectinload(Encounter.facility))
        .where(Encounter.id == encounter.id)
    )
    warnings = []
    if payload.registration_mode in {"UNKNOWN", "EMERGENCY"}:
        warnings.append("Temporary identity requires reconciliation and demographic verification.")
    if not payload.nida_number:
        warnings.append("No NIDA identifier supplied; demographic matching remains required.")
    return {
        "patient": patient_dict(patient),
        "encounter": encounter_dict(encounter),
        "possible_duplicates": [patient_dict(p) for p in possible_duplicates],
        "warnings": warnings,
    }
