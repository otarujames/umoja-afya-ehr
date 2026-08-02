from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .enterprise_models import Appointment, AppointmentStatusEvent
from .models import Encounter, EncounterStatus, Facility, Patient
from .operational_models import (
    DutyRoster,
    ServicePoint,
    WalkInEpisode,
    WorkflowNotification,
    WorkQueueDefinition,
    WorkQueueEvent,
    WorkQueueItem,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_service_points(db: Session, facilities: dict[str, Facility]) -> dict[str, ServicePoint]:
    existing = {p.code: p for p in db.scalars(select(ServicePoint)).all()}
    definitions = [
        ("MNH-UPANGA", "OPD-A", "OPD Point A", "Outpatient", "General OPD Clinic", "Room 12", "PUBLIC_DUTY_ROSTER", 30),
        ("MNH-UPANGA", "SURG-A", "Surgical Point A", "Surgery", "Surgical OPD", "Room 21", "PUBLIC_DUTY_ROSTER", 25),
        ("MNH-UPANGA", "PEDS-A", "Pediatric Point A", "Paediatrics", "Pediatric Clinic", "Room 8", "PUBLIC_DUTY_ROSTER", 20),
        ("MNH-UPANGA", "ANC-A", "Maternity Point A", "Maternity", "Antenatal Clinic", "Room 7", "PUBLIC_DUTY_ROSTER", 25),
        ("MNH-UPANGA", "MAT-B", "Maternity Point B", "Maternity", "Maternity Clinic", "Room 9", "PUBLIC_DUTY_ROSTER", 20),
        ("MNH-UPANGA", "EYE-A", "Eye Point A", "Ophthalmology", "Eye Clinic", "Room 13", "PUBLIC_DUTY_ROSTER", 15),
        ("MNH-UPANGA", "DENT-A", "Dental Point A", "Dental", "Dental Clinic", "Room 15", "PUBLIC_DUTY_ROSTER", 15),
        ("MNH-UPANGA", "CARD-A", "Cardiology Point A", "Cardiology", "Cardiology Clinic", "Room 14", "PUBLIC_DUTY_ROSTER", 15),
        ("MNH-UPANGA", "ORTHO-A", "Orthopedic Point A", "Orthopaedics", "Orthopedic OPD", "Room 16", "PUBLIC_DUTY_ROSTER", 20),
        ("MNH-UPANGA", "PHYS-A", "Physio Point A", "Rehabilitation", "Physiotherapy", "Room 17", "PUBLIC_DUTY_ROSTER", 15),
        ("MNH-MLOGANZILA", "MLOG-OPD", "Mloganzila OPD", "Outpatient", "General OPD Clinic", "Clinic 1", "PUBLIC_DUTY_ROSTER", 40),
        ("MOI", "MOI-TRAUMA", "MOI Trauma Reception", "Trauma", "Trauma and Orthopaedics", "Trauma Bay", "PUBLIC_DUTY_ROSTER", 30),
        ("JKCI", "JKCI-CLINIC", "JKCI Cardiac Clinic", "Cardiology", "Cardiology Clinic", "Clinic 3", "PUBLIC_DUTY_ROSTER", 25),
        ("ORCI", "ORCI-CLINIC", "ORCI Oncology Clinic", "Oncology", "Medical Oncology", "Clinic A", "PUBLIC_DUTY_ROSTER", 30),
    ]
    for facility_code, code, name, department, clinic, room, model, capacity in definitions:
        if code in existing:
            continue
        point = ServicePoint(
            facility_id=facilities[facility_code].id,
            code=code,
            name=name,
            department=department,
            clinic=clinic,
            room=room,
            scheduling_model=model,
            queue_capacity=capacity,
        )
        db.add(point)
        db.flush()
        existing[code] = point
    db.commit()
    return existing


def _seed_rosters(db: Session, points: dict[str, ServicePoint]) -> None:
    today = _now().date()
    if db.scalar(select(DutyRoster.id).where(DutyRoster.roster_date == today).limit(1)):
        return
    teams = {
        "OPD-A": ("OPD Team A", "Dr. Rehema Msuya", 4),
        "SURG-A": ("Surgical OPD Team", "Dr. Hamis Kilonzo", 3),
        "PEDS-A": ("Pediatric Team A", "Dr. Amina Salehe", 3),
        "ANC-A": ("Antenatal Team A", "Sr. Amina Salehe", 3),
        "MAT-B": ("Maternity Team B", "Sr. Neema Kerefu", 3),
        "EYE-A": ("Eye Clinic Team", "Dr. Swahili Mfaume", 2),
        "DENT-A": ("Dental Team", "Dr. Neema Kerefu", 2),
        "CARD-A": ("Cardiology Team", "Dr. Ashraf Hanna", 3),
        "ORTHO-A": ("Orthopaedic Team", "Dr. Hamis Kilonzo", 3),
        "PHYS-A": ("Physiotherapy Team", "Mr. Juma Mwamba", 2),
    }
    for code, (team, lead, count) in teams.items():
        point = points[code]
        db.add(DutyRoster(service_point_id=point.id, roster_date=today, shift_start=time(7, 0), shift_end=time(15, 0), team_name=team, lead_provider=lead, staff_count=count, notes="Government service-point roster; named provider is optional for appointment creation."))
    db.commit()


def _seed_todays_patients(db: Session, facilities: dict[str, Facility], points: dict[str, ServicePoint]) -> None:
    facility = facilities["MNH-UPANGA"]
    today = _now().date()
    start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    existing = int(db.scalar(select(func.count(Appointment.id)).where(Appointment.facility_id == facility.id, Appointment.scheduled_start >= start, Appointment.scheduled_start < end)) or 0)
    if existing >= 300:
        return
    patients = list(db.scalars(select(Patient).order_by(Patient.id).limit(500)).all())
    if len(patients) < 350:
        return
    services = [
        (points["OPD-A"], "Dr. Rehema Msuya"),
        (points["SURG-A"], "Dr. Hamis Kilonzo"),
        (points["PEDS-A"], "Dr. Amina Salehe"),
        (points["ANC-A"], "Sr. Amina Salehe"),
        (points["MAT-B"], "Sr. Neema Kerefu"),
        (points["EYE-A"], "Dr. Swahili Mfaume"),
        (points["DENT-A"], "Dr. Neema Kerefu"),
        (points["CARD-A"], "Dr. Ashraf Hanna"),
        (points["ORTHO-A"], "Dr. Hamis Kilonzo"),
        (points["PHYS-A"], "Mr. Juma Mwamba"),
    ]
    status_plan = (
        ["SCHEDULED"] * 56
        + ["ARRIVED"] * 36
        + ["REGISTERED"] * 38
        + ["WAITING_TRIAGE"] * 46
        + ["TRIAGED"] * 22
        + ["READY_FOR_PROVIDER"] * 28
        + ["IN_PROGRESS"] * 30
        + ["WAITING_RESULTS"] * 16
        + ["READY_FOR_DISCHARGE"] * 20
        + ["DISCHARGED"] * 20
    )
    for idx, encounter_status in enumerate(status_plan):
        patient = patients[idx]
        point, lead = services[idx % len(services)]
        minute_offset = idx * 3
        scheduled = start + timedelta(hours=7, minutes=minute_offset)
        apt_status = "SCHEDULED" if encounter_status == "SCHEDULED" else "ARRIVED"
        appointment = Appointment(
            appointment_id=f"APT-{today.strftime('%Y%m%d')}-{idx+1:04d}",
            patient_id=patient.id,
            facility_id=facility.id,
            service=point.clinic,
            provider=lead,
            appointment_type="PUBLIC_DUTY_ROSTER",
            scheduled_start=scheduled,
            scheduled_end=scheduled + timedelta(minutes=30),
            status=apt_status,
            arrival_method="SCHEDULED" if encounter_status == "SCHEDULED" else "FRONT_DESK",
            notes=f"Service point: {point.name}; route to on-duty team.",
            created_by="Review Data Seeder",
        )
        db.add(appointment)
        db.flush()
        db.add(AppointmentStatusEvent(appointment_id=appointment.id, status_before="NEW", status_after=apt_status, reason="Synthetic review schedule", actor="Review Data Seeder"))
        if encounter_status != "SCHEDULED":
            status_enum = EncounterStatus(encounter_status)
            arrival = max(scheduled, _now() - timedelta(minutes=(idx % 120) + 5))
            encounter = Encounter(
                encounter_id=f"ENC-{today.strftime('%Y%m%d')}-REV-{idx+1:04d}",
                patient_id=patient.id,
                facility_id=facility.id,
                encounter_type="OUTPATIENT",
                service=point.clinic,
                status=status_enum,
                acuity=["Low", "Medium", "High"][idx % 3],
                location=point.name if encounter_status not in {"WAITING_TRIAGE", "TRIAGED"} else ("Triage Queue" if encounter_status == "WAITING_TRIAGE" else "Triage Complete"),
                room=point.room,
                provider=lead,
                reason_for_visit=["Follow-up", "New complaint", "Medication review", "Diagnostic review"][idx % 4],
                arrival_at=arrival,
                triage_at=arrival + timedelta(minutes=12) if encounter_status in {"TRIAGED", "READY_FOR_PROVIDER", "IN_PROGRESS", "WAITING_RESULTS", "READY_FOR_DISCHARGE", "DISCHARGED"} else None,
                provider_start_at=arrival + timedelta(minutes=30) if encounter_status in {"IN_PROGRESS", "WAITING_RESULTS", "READY_FOR_DISCHARGE", "DISCHARGED"} else None,
                discharge_at=arrival + timedelta(hours=2) if encounter_status == "DISCHARGED" else None,
                discharge_disposition="Home" if encounter_status == "DISCHARGED" else None,
                discharge_summary="Synthetic completed outpatient encounter." if encounter_status == "DISCHARGED" else None,
                follow_up="Return as clinically indicated." if encounter_status == "DISCHARGED" else None,
            )
            db.add(encounter)
    db.commit()


def _seed_workqueues(db: Session, patients: list[Patient]) -> None:
    specs = [
        ("MISSING_DOCUMENTS_DAILY", "Missing Documents Daily", "PATIENT", "Health Records", "Health Records Team", 232, 36),
        ("WALKIN_REG_FOLLOWUP", "Walk-In Registration Follow-up", "WALK_INS", "Registration", "Front Desk Team A", 180, 8),
        ("NHIF_ELIGIBILITY_PENDING", "NHIF Eligibility Pending", "REGISTRATION", "Insurance", "NHIF Verification Team", 155, 12),
        ("COVERAGE_EXCEPTIONS", "Coverage Exceptions", "ACCOUNT", "Billing", "Coverage Review Team", 128, 24),
        ("UNCLOSED_ENCOUNTERS", "Unclosed Encounters", "FOLLOW_UP", "Clinical Operations", "Care Coordination Team", 124, 24),
        ("CLAIM_EDIT", "Claim Edit Queue", "CLAIMS", "Billing", "Claim Editors", 108, 72),
        ("AUTHORIZATION_FOLLOWUP", "Authorization Follow-up", "REFERRAL_AUTH", "Insurance", "Authorization Team", 99, 48),
        ("BED_ASSIGNMENT_PENDING", "Bed Assignment Pending", "PATIENT", "Patient Access", "Bed Management Team", 76, 4),
        ("REFERRAL_CLOSURE", "Referral Closure", "REFERRAL_AUTH", "Referrals", "Referral Coordinators", 53, 72),
        ("FRONT_DESK_ARRIVAL_EXCEPTIONS", "Front Desk Arrival Exceptions", "REGISTRATION", "Registration", "Front Desk Team A", 25, 4),
    ]
    queues: dict[str, WorkQueueDefinition] = {}
    for code, name, category, area, team, count, sla in specs:
        queue = db.scalar(select(WorkQueueDefinition).where(WorkQueueDefinition.code == code))
        if not queue:
            queue = WorkQueueDefinition(code=code, name=name, category=category, service_area=area, owner_team=team, description=f"Operational workqueue for {name.lower()}.", routing_rule_json=json.dumps({"facility": "MNH-UPANGA", "owner_team": team, "priority": "rule-based"}), sla_hours=sla)
            db.add(queue)
            db.flush()
        queues[code] = queue
    db.commit()

    if int(db.scalar(select(func.count(WorkQueueItem.id))) or 0) > 500:
        return
    cursor = 0
    for code, name, category, area, team, count, sla in specs:
        queue = queues[code]
        for idx in range(count):
            patient = patients[(cursor + idx) % len(patients)]
            priority = "HIGH" if idx % 7 == 0 else ("MEDIUM" if idx % 3 == 0 else "ROUTINE")
            status = "DEFERRED" if idx % 13 == 0 else ("COMPLETED" if idx % 11 == 0 else "ACTIVE")
            age_hours = (idx % 240) + 1
            created = _now() - timedelta(hours=age_hours)
            due = created + timedelta(hours=sla)
            item = WorkQueueItem(
                queue_definition_id=queue.id,
                patient_id=patient.id,
                title=f"{name}: {patient.full_name}",
                reason=[
                    "Required documentation or verification remains incomplete.",
                    "Automated rule identified a follow-up requirement.",
                    "Workflow handoff requires accountable review and closure.",
                ][idx % 3],
                priority=priority,
                status=status,
                assigned_to=team,
                due_at=due,
                deferred_until=_now() + timedelta(hours=12) if status == "DEFERRED" else None,
                created_by="Umoja Afya Workflow Engine",
                created_at=created,
                updated_at=created + timedelta(minutes=10),
                closed_at=created + timedelta(hours=2) if status == "COMPLETED" else None,
            )
            db.add(item)
            db.flush()
            db.add(WorkQueueEvent(work_queue_item_id=item.id, action="CREATE", status_after="ACTIVE", actor="Workflow Engine", note="Synthetic review work item"))
            if status != "ACTIVE":
                db.add(WorkQueueEvent(work_queue_item_id=item.id, action=status, status_before="ACTIVE", status_after=status, actor=team, note="Synthetic lifecycle event"))
        cursor += count
    db.commit()


def _seed_walkins(db: Session, facilities: dict[str, Facility], points: dict[str, ServicePoint], patients: list[Patient]) -> None:
    today = _now().date()
    if int(db.scalar(select(func.count(WalkInEpisode.id)).where(WalkInEpisode.created_at >= _now() - timedelta(hours=24))) or 0) >= 20:
        return
    facility = facilities["MNH-UPANGA"]
    statuses = ["ARRIVED", "SERVICE_ASSIGNED", "WAITING_TRIAGE", "TRIAGED", "READY_FOR_PROVIDER", "COMPLETED"]
    point_codes = ["OPD-A", "SURG-A", "PEDS-A", "ANC-A", "EYE-A", "DENT-A"]
    for idx in range(24):
        patient = patients[350 + idx]
        point = points[point_codes[idx % len(point_codes)]]
        status = statuses[idx % len(statuses)]
        arrived = _now() - timedelta(minutes=(idx + 1) * 4)
        encounter_status = {
            "ARRIVED": EncounterStatus.ARRIVED,
            "SERVICE_ASSIGNED": EncounterStatus.REGISTERED,
            "WAITING_TRIAGE": EncounterStatus.WAITING_TRIAGE,
            "TRIAGED": EncounterStatus.TRIAGED,
            "READY_FOR_PROVIDER": EncounterStatus.READY_FOR_PROVIDER,
            "COMPLETED": EncounterStatus.DISCHARGED,
        }[status]
        encounter = Encounter(
            encounter_id=f"ENC-{today.strftime('%Y%m%d')}-WALK-{idx+1:03d}",
            patient_id=patient.id,
            facility_id=facility.id,
            encounter_type="WALK_IN",
            service=point.clinic,
            status=encounter_status,
            acuity=["Low", "Medium", "High"][idx % 3],
            location=point.name,
            room=point.room,
            provider="Duty roster / next available clinician",
            reason_for_visit=["Fever", "Pain", "Medication refill", "New symptoms"][idx % 4],
            arrival_at=arrived,
            triage_at=arrived + timedelta(minutes=12) if status in {"TRIAGED", "READY_FOR_PROVIDER", "COMPLETED"} else None,
            discharge_at=arrived + timedelta(hours=2) if status == "COMPLETED" else None,
        )
        db.add(encounter)
        db.flush()
        db.add(WalkInEpisode(patient_id=patient.id, encounter_id=encounter.id, facility_id=facility.id, service_point_id=point.id, reason=encounter.reason_for_visit, notes="Synthetic review walk-in", status=status, coverage_route=patient.payer, queue_name=point.name, created_by="Front Desk Review Seeder", created_at=arrived, arrived_at=arrived, completed_at=encounter.discharge_at))
    db.add(WorkflowNotification(event_type="QUEUE_ALERT", facility_code="MNH-UPANGA", audience="FRONT_DESK", message_en="3 patients have waited more than 60 minutes", message_sw="Wagonjwa 3 wamesubiri zaidi ya dakika 60", payload_json=json.dumps({"severity": "warning", "duration_ms": 1000}), expires_at=_now() + timedelta(hours=8)))
    db.commit()


def seed_operational_data(db: Session) -> None:
    facilities = {item.code: item for item in db.scalars(select(Facility)).all()}
    if "MNH-UPANGA" not in facilities:
        return
    patients = list(db.scalars(select(Patient).order_by(Patient.id).limit(2000)).all())
    if len(patients) < 500:
        return
    points = _seed_service_points(db, facilities)
    _seed_rosters(db, points)
    _seed_todays_patients(db, facilities, points)
    _seed_workqueues(db, patients)
    _seed_walkins(db, facilities, points, patients)
