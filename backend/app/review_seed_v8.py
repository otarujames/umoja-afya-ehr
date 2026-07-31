from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .enterprise_models import Bed
from .models import Facility, Patient, Result


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", value.upper())[:30] or "UNIT"


BASE_UNITS: list[tuple[str, int, str]] = [
    ("Emergency Observation Unit", 12, "OBSERVATION"),
    ("General Medical Ward 1", 24, "GENERAL"),
    ("General Surgical Ward 1", 24, "GENERAL"),
    ("Maternity Ward", 20, "MATERNITY"),
    ("Postnatal Ward", 20, "MATERNITY"),
    ("Paediatric Ward", 20, "PAEDIATRIC"),
    ("High Dependency Unit", 10, "HDU"),
    ("Intensive Care Unit", 10, "ICU"),
    ("Isolation Ward", 12, "ISOLATION"),
    ("Theatre Recovery / PACU", 12, "PACU"),
]

REFERRAL_UNITS: list[tuple[str, int, str]] = [
    ("General Medical Ward 2", 24, "GENERAL"),
    ("General Medical Ward 3", 24, "GENERAL"),
    ("General Surgical Ward 2", 24, "GENERAL"),
    ("Orthopaedic Ward", 20, "ORTHOPAEDIC"),
    ("Trauma Ward", 20, "TRAUMA"),
    ("Neurology / Neurosurgery Ward", 18, "NEURO"),
    ("Cardiology Ward", 20, "CARDIAC"),
    ("Cardiac High Dependency Unit", 10, "CARDIAC_HDU"),
    ("Neonatal Intensive Care Unit", 18, "NICU"),
    ("Paediatric Intensive Care Unit", 10, "PICU"),
    ("Antenatal Ward", 20, "MATERNITY"),
    ("Labour and Delivery Unit", 16, "LABOUR"),
    ("Gynaecology Ward", 20, "GYNAECOLOGY"),
    ("Oncology Ward", 20, "ONCOLOGY"),
    ("Haematology Ward", 16, "HAEMATOLOGY"),
    ("Burns and Plastic Surgery Unit", 14, "BURNS"),
    ("Renal / Nephrology Ward", 18, "RENAL"),
    ("Dialysis Unit", 20, "DIALYSIS_STATION"),
    ("Psychiatry Ward", 20, "MENTAL_HEALTH"),
    ("Rehabilitation Ward", 16, "REHABILITATION"),
    ("Palliative Care Unit", 14, "PALLIATIVE"),
    ("Day Care / Infusion Unit", 24, "DAY_CARE_CHAIR"),
]

MNH_EXTRA: list[tuple[str, int, str]] = [
    ("Ward 5A - Internal Medicine", 28, "GENERAL"),
    ("Ward 5B - Nephrology", 28, "RENAL"),
    ("Ward 6A - Gastroenterology", 24, "GENERAL"),
    ("Ward 6B - Pulmonology", 24, "GENERAL"),
    ("Ward 7A - Infectious Diseases", 24, "ISOLATION"),
    ("Ward 7B - Endocrinology", 24, "GENERAL"),
    ("Medical ICU", 14, "ICU"),
    ("Surgical ICU", 14, "ICU"),
    ("Emergency Resuscitation Unit", 10, "RESUSCITATION"),
    ("Stroke Unit", 12, "STROKE"),
    ("Transplant / Immunosuppressed Unit", 12, "PROTECTIVE_ISOLATION"),
]

SPECIALTY_UNITS: dict[str, list[tuple[str, int, str]]] = {
    "MOI": [
        ("Trauma Ward A", 24, "TRAUMA"), ("Trauma Ward B", 24, "TRAUMA"),
        ("Orthopaedic Ward A", 24, "ORTHOPAEDIC"), ("Orthopaedic Ward B", 24, "ORTHOPAEDIC"),
        ("Neurosurgery Ward", 20, "NEURO"), ("Spine Unit", 16, "SPINE"),
        ("MOI Intensive Care Unit", 12, "ICU"), ("MOI High Dependency Unit", 12, "HDU"),
        ("Burns Unit", 16, "BURNS"), ("Trauma Observation Unit", 16, "OBSERVATION"),
        ("Post-Anaesthesia Care Unit", 12, "PACU"), ("Orthopaedic Rehabilitation Unit", 20, "REHABILITATION"),
    ],
    "JKCI": [
        ("Cardiac Intensive Care Unit", 16, "CARDIAC_ICU"), ("Cardiac High Dependency Unit", 16, "CARDIAC_HDU"),
        ("Adult Cardiology Ward", 24, "CARDIAC"), ("Paediatric Cardiology Ward", 18, "PAEDIATRIC_CARDIAC"),
        ("Cardiac Surgery Ward", 24, "CARDIAC_SURGERY"), ("Cath Lab Recovery", 14, "RECOVERY"),
        ("Cardiac Day Care", 18, "DAY_CARE_CHAIR"), ("Cardiac Theatre PACU", 12, "PACU"),
    ],
    "ORCI": [
        ("Medical Oncology Ward", 24, "ONCOLOGY"), ("Surgical Oncology Ward", 20, "ONCOLOGY_SURGERY"),
        ("Haematology Ward", 18, "HAEMATOLOGY"), ("Protective Isolation Unit", 12, "PROTECTIVE_ISOLATION"),
        ("Palliative Care Ward", 18, "PALLIATIVE"), ("Chemotherapy Infusion Unit", 32, "INFUSION_CHAIR"),
        ("Brachytherapy Recovery", 12, "RECOVERY"), ("Oncology Intensive Care Unit", 10, "ICU"),
        ("Oncology Theatre PACU", 10, "PACU"),
    ],
}


def _units_for(facility: Facility) -> list[tuple[str, int, str]]:
    code = facility.code.upper()
    facility_type = (facility.facility_type or "").lower()
    hierarchy = (facility.hierarchy_level or "").upper()
    if code in SPECIALTY_UNITS:
        units = BASE_UNITS[:4] + SPECIALTY_UNITS[code]
    else:
        units = list(BASE_UNITS)
        if any(term in facility_type for term in ("referral", "national", "specialist", "specialty")) or hierarchy in {
            "NATIONAL", "ZONAL", "REGIONAL", "ZANZIBAR_NATIONAL", "ZANZIBAR_REGIONAL"
        }:
            units.extend(REFERRAL_UNITS)
        if code in {"MNH-UPANGA", "MNH-MLOGANZILA"}:
            units.extend(MNH_EXTRA)
    # Preserve order but eliminate duplicate unit names.
    output: list[tuple[str, int, str]] = []
    seen: set[str] = set()
    for item in units:
        if item[0] not in seen:
            seen.add(item[0])
            output.append(item)
    return output


def seed_bed_inventory(db: Session) -> int:
    """Create a complete, idempotent review bed inventory for every active hospital context."""
    facilities = list(db.scalars(select(Facility).where(Facility.active.is_(True)).order_by(Facility.id)).all())
    existing_ids = set(db.scalars(select(Bed.bed_id)).all())
    added = 0
    batch: list[Bed] = []
    for facility in facilities:
        facility_type = (facility.facility_type or "").lower()
        if any(term in facility_type for term in ("university", "academic", "research partner")):
            continue
        for unit_name, bed_count, bed_type in _units_for(facility):
            slug = _slug(unit_name)
            room_size = 4 if bed_type not in {"ICU", "HDU", "NICU", "PICU", "CARDIAC_ICU", "CARDIAC_HDU", "RESUSCITATION"} else 2
            for index in range(1, bed_count + 1):
                bed_id = f"BED-{facility.code[:18]}-{slug[:28]}-{index:03d}"
                if bed_id in existing_ids:
                    continue
                room_number = ((index - 1) // room_size) + 1
                position = ((index - 1) % room_size) + 1
                if "CHAIR" in bed_type or "DIALYSIS" in bed_type:
                    room = unit_name
                    label = f"Station {index:02d}"
                else:
                    room = f"{slug[:8]}-{room_number:02d}"
                    label = f"Bed {position}"
                # Deterministic review statuses; no patient record is exposed until a unit is selected.
                if index % 29 == 0:
                    status, isolation = "BLOCKED", "Maintenance / infection-control hold"
                elif index % 23 == 0:
                    status, isolation = "CLEANING", None
                elif index % 19 == 0:
                    status, isolation = "DIRTY", None
                else:
                    status, isolation = "AVAILABLE", None
                batch.append(Bed(
                    bed_id=bed_id,
                    facility_id=facility.id,
                    unit=unit_name,
                    room=room,
                    bed_label=label,
                    bed_type=bed_type,
                    status=status,
                    isolation=isolation,
                ))
                existing_ids.add(bed_id)
                added += 1
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.commit()
                    batch.clear()
    if batch:
        db.add_all(batch)
        db.commit()
    return added


RESULT_DEFINITIONS: list[tuple[str, str, str, str]] = [
    ("Haemoglobin", "g/dL", "Haematology", "MNH Core Laboratory"),
    ("White blood cell count", "×10⁹/L", "Haematology", "MNH Core Laboratory"),
    ("Platelet count", "×10⁹/L", "Haematology", "MNH Core Laboratory"),
    ("Creatinine", "µmol/L", "Chemistry", "MNH Core Laboratory"),
    ("Sodium", "mmol/L", "Chemistry", "MNH Core Laboratory"),
    ("Potassium", "mmol/L", "Chemistry", "MNH Core Laboratory"),
    ("Random blood glucose", "mmol/L", "Point of Care", "Connected Glucose Meter"),
    ("Malaria rapid diagnostic test", "", "Microbiology", "MNH Microbiology"),
]


def _result_value(patient_id: int, index: int) -> tuple[str, str]:
    seed = patient_id * 17 + index * 11
    if index == 0:
        value = 7.2 + (seed % 85) / 10
        return f"{value:.1f}", "CRITICAL" if value < 8 else ("LOW" if value < 11 else "NORMAL")
    if index == 1:
        value = 3.0 + (seed % 120) / 10
        return f"{value:.1f}", "HIGH" if value > 11 else ("LOW" if value < 4 else "NORMAL")
    if index == 2:
        value = 70 + seed % 360
        return str(value), "LOW" if value < 150 else ("HIGH" if value > 400 else "NORMAL")
    if index == 3:
        value = 45 + seed % 240
        return str(value), "CRITICAL" if value > 230 else ("HIGH" if value > 120 else "NORMAL")
    if index == 4:
        value = 126 + seed % 25
        return str(value), "LOW" if value < 135 else ("HIGH" if value > 145 else "NORMAL")
    if index == 5:
        value = 2.8 + (seed % 35) / 10
        return f"{value:.1f}", "CRITICAL" if value < 3 or value > 6 else ("HIGH" if value > 5.2 else "NORMAL")
    if index == 6:
        value = 3.5 + (seed % 110) / 10
        return f"{value:.1f}", "HIGH" if value > 11 else "NORMAL"
    return ("Positive", "ABNORMAL") if seed % 13 == 0 else ("Negative", "NORMAL")


def seed_review_results(db: Session, patient_limit: int = 600) -> int:
    """Give review patients a realistic longitudinal result set so Results Review is never a dead screen."""
    patients = list(db.scalars(select(Patient).order_by(Patient.id).limit(patient_limit)).all())
    if not patients:
        return 0
    patient_ids = [p.id for p in patients]
    existing = set(db.scalars(select(Result.result_id).where(Result.patient_id.in_(patient_ids))).all())
    added = 0
    batch: list[Result] = []
    now = _now()
    for patient in patients:
        for index, (test_name, unit, _group, source) in enumerate(RESULT_DEFINITIONS):
            result_id = f"REV8-RES-{patient.id:06d}-{index+1:02d}"
            if result_id in existing:
                continue
            value, flag = _result_value(patient.id, index)
            issued = now - timedelta(hours=(patient.id + index * 7) % 120, minutes=index * 4)
            batch.append(Result(
                result_id=result_id,
                patient_id=patient.id,
                test_name=test_name,
                value=value,
                unit=unit or None,
                flag=flag,
                status="FINAL",
                source=source,
                issued_at=issued,
                acknowledged=flag not in {"CRITICAL"},
                acknowledged_by="Review Data Seeder" if flag not in {"CRITICAL"} else None,
                acknowledged_at=issued + timedelta(minutes=8) if flag not in {"CRITICAL"} else None,
            ))
            added += 1
            if len(batch) >= 1000:
                db.add_all(batch)
                db.commit()
                batch.clear()
    if batch:
        db.add_all(batch)
        db.commit()
    return added
