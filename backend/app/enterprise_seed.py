from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .enterprise_models import (
    Appointment,
    Bed,
    Charge,
    Claim,
    ClinicalNote,
    IntegrationEvent,
    InventoryItem,
    MedicationAdministration,
    MedicationOrder,
    ModuleActivity,
    PublicHealthEvent,
    QualityIncident,
    Referral,
    TelehealthSession,
    UserAccessGrant,
    UserAccount,
    WorkItem,
)
from .models import Encounter, Facility, Patient
from .access_control import ROLE_TEMPLATES, replace_user_access


def _now() -> datetime:
    return datetime.now(timezone.utc)


def seed_enterprise_data(db: Session) -> None:
    # Enterprise reference and synthetic workflow data are idempotent.
    # User accounts are deliberately never seeded; first-run setup creates the
    # initial administrator and all subsequent accounts are provisioned by IT.
    if db.scalar(select(Appointment.id).limit(1)):
        existing_users = list(db.scalars(select(UserAccount)).all())
        if existing_users and not db.scalar(select(UserAccessGrant.id).limit(1)):
            facility_codes = {x.code for x in db.scalars(select(Facility)).all()}
            for user in existing_users:
                template = ROLE_TEMPLATES.get(user.role_code, ROLE_TEMPLATES["custom"])
                facility = user.facility_code if user.facility_code in facility_codes else "MNH-UPANGA"
                replace_user_access(db, user, functions=template["functions"], departments=template["departments"], facilities=[facility], actor="Access Migration", reason="Backfill access matrix for an existing account")
            db.commit()
        return

    facilities = {x.code: x for x in db.scalars(select(Facility)).all()}
    patients = {x.mpi_id: x for x in db.scalars(select(Patient)).all()}
    encounters = {x.encounter_id: x for x in db.scalars(select(Encounter)).all()}
    if not facilities or not patients or not encounters:
        return

    p1 = patients["TZ-MPI-00018422"]
    p2 = patients["TZ-MPI-00022410"]
    p3 = patients["TZ-MPI-00009175"]
    p4 = patients["TZ-MPI-00030155"]
    p5 = patients["TZ-MPI-00041572"]
    p6 = patients["TZ-MPI-00050991"]
    e1 = encounters["ENC-20260727-00492"]
    e2 = encounters["ENC-20260727-00614"]
    e3 = encounters["ENC-20260727-00334"]
    e4 = encounters["ENC-20260727-00110"]

    appointments = [
        Appointment(appointment_id="APT-MNH-1001", patient_id=p3.id, facility_id=facilities["JKCI"].id, service="Heart Failure Clinic", provider="Dr. Mushi", scheduled_start=_now()+timedelta(minutes=35), scheduled_end=_now()+timedelta(minutes=65), status="ARRIVED", notes="Follow-up after medication optimization", created_by="Amina Salum"),
        Appointment(appointment_id="APT-MNH-1002", patient_id=p5.id, facility_id=facilities["MNH-MLOGANZILA"].id, service="Paediatric Asthma Clinic", provider="Dr. Mallya", scheduled_start=_now()+timedelta(hours=2), scheduled_end=_now()+timedelta(hours=2, minutes=30), status="SCHEDULED", notes="Bring inhalers", created_by="Amina Salum"),
        Appointment(appointment_id="APT-MNH-1003", patient_id=p6.id, facility_id=facilities["MNH-UPANGA"].id, service="Postnatal Hypertension", provider="Dr. Mwita", scheduled_start=_now()+timedelta(days=2), scheduled_end=_now()+timedelta(days=2, minutes=30), status="CONFIRMED", created_by="Amina Salum"),
        Appointment(appointment_id="APT-MNH-1004", patient_id=p4.id, facility_id=facilities["ORCI"].id, service="Chemotherapy Infusion", provider="Dr. Nyerere", appointment_type="INFUSION", scheduled_start=_now()+timedelta(days=7), scheduled_end=_now()+timedelta(days=7, hours=4), status="SCHEDULED", created_by="ORCI Scheduling"),
    ]
    db.add_all(appointments)

    referrals = [
        Referral(referral_id="REF-2026-0001", patient_id=p2.id, source_facility_code="MNH-UPANGA", destination_facility_code="MOI", service="Trauma and Orthopaedics", priority="STAT", reason="Open femoral fracture requiring specialist surgical management", status="ACCEPTED", requested_by="Dr. A. Mrema", accepted_by="Dr. Issa K."),
        Referral(referral_id="REF-2026-0002", patient_id=p3.id, source_facility_code="MNH-MLOGANZILA", destination_facility_code="JKCI", service="Heart Failure", priority="URGENT", reason="Reduced ejection fraction with recurrent decompensation", status="SCHEDULED", requested_by="Dr. Mallya", appointment_id="APT-MNH-1001"),
        Referral(referral_id="REF-2026-0003", patient_id=p4.id, source_facility_code="ORCI", destination_facility_code="MNH-UPANGA", service="Nephrology", priority="ROUTINE", reason="Renal function review before next chemotherapy cycle", status="NEW", requested_by="Dr. Nyerere"),
    ]
    db.add_all(referrals)

    beds = []
    for unit, room, labels, facility_code, bed_type in [
        ("Ward 5B", "501", ["A", "B", "C", "D"], "MNH-UPANGA", "GENERAL"),
        ("Medical ICU", "ICU-1", ["1", "2", "3", "4"], "MNH-UPANGA", "ICU"),
        ("Trauma Ward", "T-12", ["1", "2", "3", "4"], "MOI", "TRAUMA"),
        ("Cardiac ICU", "CICU", ["1", "2", "3", "4"], "JKCI", "ICU"),
        ("Oncology Ward", "ONC-3", ["1", "2", "3", "4"], "ORCI", "ONCOLOGY"),
    ]:
        for index, label in enumerate(labels):
            status = "AVAILABLE"
            encounter_id = None
            if facility_code == "MNH-UPANGA" and unit == "Ward 5B" and index == 0:
                status = "OCCUPIED"; encounter_id = e1.id
            elif facility_code == "MOI" and index == 0:
                status = "OCCUPIED"; encounter_id = e2.id
            elif index == 1:
                status = "DIRTY"
            elif index == 2:
                status = "CLEANING"
            beds.append(Bed(bed_id=f"BED-{facility_code}-{unit.replace(' ','').replace('-','')}-{label}", facility_id=facilities[facility_code].id, unit=unit, room=room, bed_label=label, bed_type=bed_type, status=status, encounter_id=encounter_id, assigned_at=_now()-timedelta(hours=3) if encounter_id else None))
    db.add_all(beds)

    notes = [
        ClinicalNote(note_id="NOTE-0001", patient_id=p1.id, encounter_id=e1.id, note_type="PROGRESS_NOTE", title="Nephrology Progress Note", status="DRAFT", author="Dr. Neema M.", service="Nephrology", body="Severe hypertension with acute kidney injury. Urine output remains reduced. Continue close monitoring, review renal panel, and assess volume status."),
        ClinicalNote(note_id="NOTE-0002", patient_id=p2.id, encounter_id=e2.id, note_type="TRAUMA_H_AND_P", title="Trauma Admission History and Physical", status="SIGNED", author="Dr. Issa K.", service="Trauma / Orthopaedics", body="Road traffic collision with open femoral fracture. Distal perfusion present. Antibiotics and tetanus prophylaxis initiated. Prepared for urgent theatre.", signed_by="Dr. Issa K.", signed_at=_now()-timedelta(hours=1)),
        ClinicalNote(note_id="NOTE-0003", patient_id=p4.id, encounter_id=e4.id, note_type="INFUSION_NOTE", title="Chemotherapy Clearance", status="DRAFT", author="Dr. Nyerere", service="Medical Oncology", body="Cycle 4 clearance pending CBC and renal panel. Review neutrophil count before releasing protocol."),
    ]
    db.add_all(notes)

    meds = [
        MedicationOrder(medication_order_id="MED-0001", patient_id=p1.id, encounter_id=e1.id, medication_name="Amlodipine", dose="10 mg", route="PO", frequency="Daily", indication="Severe hypertension", ordered_by="Dr. Neema M.", verified_by="Pharm. Juma K.", verified_at=_now()-timedelta(hours=2)),
        MedicationOrder(medication_order_id="MED-0002", patient_id=p2.id, encounter_id=e2.id, medication_name="Cefazolin", dose="2 g", route="IV", frequency="Every 8 hours", indication="Open fracture prophylaxis", ordered_by="Dr. Issa K.", verified_by="Pharm. Juma K.", verified_at=_now()-timedelta(hours=1, minutes=45)),
        MedicationOrder(medication_order_id="MED-0003", patient_id=p2.id, encounter_id=e2.id, medication_name="Morphine", dose="4 mg", route="IV", frequency="Every 4 hours PRN", indication="Severe trauma pain", ordered_by="Dr. Issa K."),
        MedicationOrder(medication_order_id="MED-0004", patient_id=p4.id, encounter_id=e4.id, medication_name="Ondansetron", dose="8 mg", route="IV", frequency="Pre-chemotherapy", indication="Antiemetic premedication", ordered_by="Dr. Nyerere", verified_by="ORCI Pharmacist", verified_at=_now()-timedelta(minutes=50)),
    ]
    db.add_all(meds)
    db.flush()
    db.add_all([
        MedicationAdministration(medication_order_id=meds[0].id, scheduled_at=_now()-timedelta(hours=1), action="GIVEN", dose_given="10 mg", administered_by="Neema Kweka, RN", barcode_verified=True, administered_at=_now()-timedelta(minutes=58)),
        MedicationAdministration(medication_order_id=meds[1].id, scheduled_at=_now()-timedelta(minutes=45), action="GIVEN", dose_given="2 g", administered_by="MOI Trauma RN", barcode_verified=True, administered_at=_now()-timedelta(minutes=42)),
    ])

    work_items = [
        WorkItem(work_item_id="TASK-0001", patient_id=p1.id, encounter_id=e1.id, queue="PROVIDER-INBOX", task_type="CRITICAL_RESULT", subject="Acknowledge creatinine 238 µmol/L", details="Critical renal result requires documented action.", priority="CRITICAL", status="OPEN", assigned_to="Dr. Neema M.", due_at=_now()-timedelta(minutes=10), created_by="Laboratory Interface"),
        WorkItem(work_item_id="TASK-0002", patient_id=p4.id, encounter_id=e4.id, queue="ONCOLOGY-CLEARANCE", task_type="TREATMENT_CLEARANCE", subject="Review CBC before chemotherapy", priority="HIGH", status="IN_PROGRESS", assigned_to="Dr. Nyerere", due_at=_now()+timedelta(minutes=20), created_by="Oncology Protocol Engine"),
        WorkItem(work_item_id="TASK-0003", patient_id=p6.id, queue="FOLLOW-UP", task_type="POST_DISCHARGE_CALL", subject="Post-discharge blood pressure follow-up", details="Call patient and confirm medications and danger signs.", priority="ROUTINE", status="OPEN", assigned_to="Postnatal Clinic Pool", due_at=_now()+timedelta(hours=4), created_by="Discharge Workflow"),
        WorkItem(work_item_id="TASK-0004", queue="CLAIMS-DENIAL", task_type="DENIAL_REVIEW", subject="Correct missing authorization", details="NHIF claim denied for authorization mismatch.", priority="HIGH", status="OPEN", assigned_to="Revenue Cycle Pool", due_at=_now()+timedelta(hours=8), created_by="NHIF Interface"),
    ]
    db.add_all(work_items)

    charges = [
        Charge(charge_id="CHG-0001", patient_id=p1.id, encounter_id=e1.id, service_code="LAB-RNP", description="Renal panel", quantity=1, unit_price=45000, payer="NHIF", posted_by="Laboratory Interface"),
        Charge(charge_id="CHG-0002", patient_id=p2.id, encounter_id=e2.id, service_code="MOI-TRAUMA", description="Trauma assessment and stabilization", quantity=1, unit_price=185000, payer="Cash", posted_by="MOI Charge Router"),
        Charge(charge_id="CHG-0003", patient_id=p4.id, encounter_id=e4.id, service_code="ORCI-INFUSION", description="Chemotherapy infusion services", quantity=1, unit_price=420000, payer="NHIF", posted_by="ORCI Charge Router"),
    ]
    db.add_all(charges)

    claims = [
        Claim(claim_id="CLM-0001", patient_id=p1.id, encounter_id=e1.id, payer="NHIF", member_number=p1.member_number, amount=685000, status="READY", authorization_number="NHIF-AUTH-55018"),
        Claim(claim_id="CLM-0002", patient_id=p4.id, encounter_id=e4.id, payer="NHIF", member_number=p4.member_number, amount=1850000, status="SUBMITTED", authorization_number="NHIF-AUTH-77190", submitted_at=_now()-timedelta(hours=3)),
        Claim(claim_id="CLM-0003", patient_id=p3.id, encounter_id=e3.id, payer="NHIF", member_number=p3.member_number, amount=320000, status="DENIED", denial_code="AUTH-07", denial_reason="Authorization number does not match service date"),
    ]
    db.add_all(claims)

    inventory = [
        InventoryItem(item_id="ITEM-0001", facility_id=facilities["MNH-UPANGA"].id, item_code="MED-AMLO-10", item_name="Amlodipine 10 mg tablets", category="MEDICATION", unit="tablets", on_hand=4800, reorder_level=1200, batch_number="AM2407", expiry_at=_now()+timedelta(days=420), location="Central Pharmacy"),
        InventoryItem(item_id="ITEM-0002", facility_id=facilities["MOI"].id, item_code="MED-CEFA-2G", item_name="Cefazolin 2 g vial", category="MEDICATION", unit="vials", on_hand=42, reorder_level=60, batch_number="CF2601", expiry_at=_now()+timedelta(days=180), location="MOI Pharmacy"),
        InventoryItem(item_id="ITEM-0003", facility_id=facilities["MOI"].id, item_code="IMP-FEM-NAIL", item_name="Femoral intramedullary nail", category="IMPLANT", unit="each", on_hand=3, reorder_level=5, batch_number="FN-2026-04", expiry_at=None, location="MOI Implant Store"),
        InventoryItem(item_id="ITEM-0004", facility_id=facilities["ORCI"].id, item_code="CHEMO-DOXO", item_name="Doxorubicin 50 mg", category="CHEMOTHERAPY", unit="vials", on_hand=18, reorder_level=10, batch_number="DXR-2602", expiry_at=_now()+timedelta(days=240), location="ORCI Cytotoxic Store"),
        InventoryItem(item_id="ITEM-0005", facility_id=facilities["MNH-UPANGA"].id, item_code="PPE-N95", item_name="N95 respirator", category="PPE", unit="each", on_hand=620, reorder_level=500, batch_number="N95-26A", expiry_at=_now()+timedelta(days=900), location="Main Warehouse"),
    ]
    db.add_all(inventory)

    db.add_all([
        QualityIncident(incident_id="QSI-0001", facility_id=facilities["MNH-UPANGA"].id, patient_id=p1.id, category="Medication Delay", severity="MEDIUM", description="Antihypertensive administration delayed 42 minutes because medication was not available in ward stock.", status="OPEN", owner="Pharmacy Quality Lead", reported_by="Ward 5B Charge Nurse"),
        QualityIncident(incident_id="QSI-0002", facility_id=facilities["MOI"].id, patient_id=p2.id, category="Device Interface", severity="HIGH", description="Trauma monitor feed intermittently disconnected; manual observations documented until restored.", status="IN_REVIEW", owner="Clinical Engineering", reported_by="MOI Trauma RN"),
    ])

    db.add(PublicHealthEvent(event_id="PHE-0001", patient_id=p5.id, condition_code="J45", condition_name="Asthma exacerbation cluster review", event_type="SYNDROMIC_SIGNAL", status="PENDING_VERIFICATION", district=p5.district, region=p5.region, reported_to="DHIS2/eIDSR"))

    db.add_all([
    ])

    tele_appointment = Appointment(appointment_id="APT-TEL-1001", patient_id=p6.id, facility_id=facilities["MNH-UPANGA"].id, service="Postnatal Hypertension", provider="Dr. Mwita", appointment_type="TELEHEALTH", scheduled_start=_now()+timedelta(hours=1), scheduled_end=_now()+timedelta(hours=1, minutes=30), status="CONFIRMED", notes="Remote blood pressure and medication review", created_by="MNH Scheduling")
    db.add(tele_appointment)
    db.flush()
    db.add(TelehealthSession(session_id="TEL-1001", patient_id=p6.id, facility_id=facilities["MNH-UPANGA"].id, appointment_id=tele_appointment.id, service="Postnatal Hypertension", provider="Dr. Mwita", modality="VIDEO", status="SCHEDULED", reason="Remote blood pressure and medication review", scheduled_start=tele_appointment.scheduled_start, join_code="JOIN-MNH-1001", created_by="MNH Scheduling"))

    db.add_all([
        ModuleActivity(activity_id="ACT-EMERGENCY-001", module_code="EMERGENCY", patient_id=p2.id, encounter_id=e2.id, activity_type="TRAUMA_ACTIVATION", title="Level 1 trauma activation", status="IN_PROGRESS", priority="CRITICAL", assigned_to="MOI Trauma Team", details="Open femoral fracture; resuscitation and theatre readiness in progress.", created_by="Emergency Charge Nurse"),
        ModuleActivity(activity_id="ACT-LABORATORY-001", module_code="LABORATORY", patient_id=p1.id, encounter_id=e1.id, activity_type="SPECIMEN_WORKLIST", title="STAT renal panel specimen", status="IN_PROGRESS", priority="STAT", assigned_to="MNH Core Laboratory", details="Collected and routed to chemistry analyzer.", created_by="CPOE"),
        ModuleActivity(activity_id="ACT-BLOOD-001", module_code="BLOOD_BANK", patient_id=p2.id, encounter_id=e2.id, activity_type="CROSSMATCH", title="Crossmatch 4 units PRBC", status="WAITING", priority="STAT", assigned_to="MOI Blood Bank", details="Type confirmation and issue authorization pending.", created_by="Dr. Issa K."),
        ModuleActivity(activity_id="ACT-RAD-001", module_code="RADIOLOGY", patient_id=p1.id, encounter_id=e1.id, activity_type="IMAGING_STUDY", title="Urgent renal ultrasound", status="NEW", priority="URGENT", assigned_to="MNH Ultrasound Pool", details="Protocol and schedule examination.", created_by="Dr. Neema M."),
        ModuleActivity(activity_id="ACT-OR-001", module_code="THEATRE", patient_id=p2.id, encounter_id=e2.id, activity_type="SURGICAL_CASE", title="Femoral fracture debridement and fixation", status="WAITING", priority="STAT", assigned_to="MOI Theatre 2", details="Awaiting blood availability and anesthesia readiness.", created_by="MOI Trauma Team"),
        ModuleActivity(activity_id="ACT-ANES-001", module_code="ANESTHESIA", patient_id=p2.id, encounter_id=e2.id, activity_type="PRE_ANESTHESIA", title="Emergency anesthesia assessment", status="IN_PROGRESS", priority="STAT", assigned_to="MOI Anesthesia", details="Airway, haemodynamic and transfusion risk assessment.", created_by="Theatre Coordinator"),
        ModuleActivity(activity_id="ACT-MATERNITY-001", module_code="MATERNITY", patient_id=p6.id, activity_type="POSTNATAL_FOLLOWUP", title="Postpartum hypertension follow-up", status="NEW", priority="HIGH", assigned_to="Postnatal Clinic Pool", details="BP review and medication reconciliation due.", created_by="Maternity Discharge Workflow"),
        ModuleActivity(activity_id="ACT-CARDIOLOGY-001", module_code="CARDIOLOGY", patient_id=p3.id, encounter_id=e3.id, activity_type="HEART_FAILURE_REVIEW", title="Heart failure clinic review", status="NEW", priority="MEDIUM", assigned_to="Dr. Mushi", details="Review volume status, medications and recent echo.", created_by="JKCI Scheduling"),
        ModuleActivity(activity_id="ACT-ONC-001", module_code="ONCOLOGY", patient_id=p4.id, encounter_id=e4.id, activity_type="CHEMOTHERAPY_CLEARANCE", title="Cycle 4 treatment clearance", status="WAITING", priority="HIGH", assigned_to="ORCI Oncology", details="Awaiting CBC and renal panel review.", created_by="Oncology Protocol Engine"),
        ModuleActivity(activity_id="ACT-ICU-001", module_code="CRITICAL_CARE", patient_id=p2.id, encounter_id=e2.id, activity_type="ICU_REVIEW", title="Post-operative ICU capacity review", status="NEW", priority="HIGH", assigned_to="MOI ICU Charge Nurse", details="Assess bed availability and postoperative monitoring needs.", created_by="Trauma Team"),
        ModuleActivity(activity_id="ACT-REHAB-001", module_code="REHAB", patient_id=p2.id, encounter_id=e2.id, activity_type="EARLY_REHAB", title="Early rehabilitation assessment", status="NEW", priority="ROUTINE", assigned_to="MOI Physiotherapy", details="Initiate plan after surgical stabilization.", created_by="Care Pathway"),
        ModuleActivity(activity_id="ACT-WORKFORCE-001", module_code="WORKFORCE", activity_type="CREDENTIAL_REVIEW", title="Provider licence expiry review", status="NEW", priority="HIGH", assigned_to="Credentialing Pool", details="Three privileged users require council licence verification.", created_by="HRHIS Interface"),
    ])

    db.add_all([
        IntegrationEvent(integration_event_id="INT-0001", system="NHIF", event_type="ELIGIBILITY_RESPONSE", resource_type="Coverage", resource_id=p1.member_number or p1.mpi_id, status="COMPLETED", attempts=1, payload_json=json.dumps({"eligible": True}), processed_at=_now()-timedelta(minutes=30)),
        IntegrationEvent(integration_event_id="INT-0002", system="DHIS2", event_type="AGGREGATE_EXPORT", resource_type="Report", resource_id="MNH-OPD-DAILY", status="COMPLETED", attempts=1, payload_json=json.dumps({"period": _now().date().isoformat()}), processed_at=_now()-timedelta(hours=1)),
        IntegrationEvent(integration_event_id="INT-0003", system="eLMIS/MSD", event_type="STOCK_REPLENISHMENT", resource_type="InventoryItem", resource_id="ITEM-0002", status="PENDING", attempts=0, payload_json=json.dumps({"requested_quantity": 120})),
    ])

    db.commit()
