from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import (
    Encounter,
    EncounterStatus,
    Facility,
    FlowSheet,
    FlowSheetEvent,
    FlowSheetObservation,
    FlowSheetStatus,
    Order,
    Patient,
    Result,
)


def _dt(hours_ago: int = 0, minutes_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours_ago, minutes=minutes_ago)


def seed_synthetic_patients(db: Session, target_count: int) -> None:
    current = int(db.scalar(select(func.count(Patient.id))) or 0)
    if target_count <= current:
        return
    first_names = ["Amina", "Baraka", "Chausiku", "Daudi", "Ester", "Faraja", "Grace", "Hamisi", "Imani", "Juma", "Khadija", "Lucas", "Mariam", "Neema", "Omari", "Pendo", "Rahma", "Salim", "Tumaini", "Yohana"]
    last_names = ["Abdallah", "Bakari", "Chacha", "Dotto", "Edward", "Juma", "Kassim", "Kileo", "Lema", "Mallya", "Mashauri", "Mbise", "Mhando", "Mrema", "Mushi", "Mwangosi", "Nyerere", "Said", "Salum", "Shayo"]
    regions = [("Dar es Salaam", "Kinondoni"), ("Dar es Salaam", "Ilala"), ("Dar es Salaam", "Temeke"), ("Pwani", "Kibaha"), ("Morogoro", "Morogoro"), ("Dodoma", "Dodoma"), ("Arusha", "Arusha"), ("Mwanza", "Nyamagana"), ("Kilimanjaro", "Moshi"), ("Tanga", "Tanga") ]
    payers = ["NHIF", "Cash", "iCHF", "UHI"]
    rows = []
    for ordinal in range(current + 1, target_count + 1):
        index = ordinal - 1
        first = first_names[index % len(first_names)]
        last = last_names[(index * 7) % len(last_names)]
        region, district = regions[(index * 3) % len(regions)]
        year = 1940 + (index % 75)
        month = 1 + (index % 12)
        day = 1 + (index % 27)
        sex = "Female" if index % 2 == 0 else "Male"
        number = 80000000 + ordinal
        rows.append({
            "mpi_id": f"TZ-MPI-{number:08d}",
            "mrn": f"DEMO-{number:08d}",
            "first_name": first,
            "middle_name": None,
            "last_name": last,
            "date_of_birth": date(year, month, day),
            "sex": sex,
            "phone": f"+255 7{(10000000 + ordinal) % 90000000:08d}",
            "nida_number": None,
            "address": f"{district}, {region}",
            "region": region,
            "district": district,
            "next_of_kin": None,
            "payer": payers[index % len(payers)],
            "member_number": f"DEMO-{ordinal:07d}",
            "allergies": "No known drug allergies",
            "problems": "Not yet assessed",
            "medications": "Medication reconciliation pending",
            "consent_status": "OBTAINED",
            "identity_status": "DEMO_VERIFIED",
            "created_at": datetime.now(timezone.utc),
        })
        if len(rows) >= 1000:
            db.execute(insert(Patient), rows)
            rows.clear()
    if rows:
        db.execute(insert(Patient), rows)
    db.commit()



def seed_database(db: Session) -> None:
    from .catalog_seed import seed_order_catalog
    from .enterprise_seed import seed_enterprise_data
    from .enhancement_seed import seed_enhancement_data
    from .facility_seed import seed_public_facilities
    from .operational_seed import seed_operational_data
    from .review_seed_v8 import seed_bed_inventory, seed_review_results
    from .country_seed import seed_country_contexts, seed_multicultural_patients
    if db.scalar(select(Facility.id).limit(1)):
        seed_public_facilities(db)
        seed_synthetic_patients(db, get_settings().demo_patient_count)
        seed_enterprise_data(db)
        seed_operational_data(db)
        seed_order_catalog(db)
        seed_enhancement_data(db)
        seed_bed_inventory(db)
        seed_review_results(db)
        seed_country_contexts(db)
        seed_multicultural_patients(db, 15000)
        return

    facilities = [
        Facility(code="MNH-UPANGA", name="Muhimbili National Hospital — Upanga", facility_type="National referral hospital", relation="MNH campus"),
        Facility(code="MNH-MLOGANZILA", name="Muhimbili National Hospital — Mloganzila", facility_type="National referral hospital", relation="MNH campus"),
        Facility(code="MOI", name="Muhimbili Orthopaedic Institute", facility_type="Orthopaedics, trauma and neurosurgery", relation="Connected specialist institute"),
        Facility(code="JKCI", name="Jakaya Kikwete Cardiac Institute", facility_type="Cardiovascular specialty hospital", relation="Connected specialist institute"),
        Facility(code="ORCI", name="Ocean Road Cancer Institute", facility_type="National cancer referral institute", relation="Connected specialist institute"),
        Facility(code="MUHAS", name="Muhimbili University of Health and Allied Sciences", facility_type="Academic and research partner", relation="Education/research connection"),
    ]
    db.add_all(facilities)
    db.flush()
    f = {item.code: item for item in facilities}

    patients = [
        Patient(mpi_id="TZ-MPI-00018422", mrn="MNH-948201", first_name="Asha", middle_name="M.", last_name="Mrema", date_of_birth=date(1982, 9, 14), sex="Female", phone="+255 754 221 830", nida_number="19820914-14102-00017-22", address="Kinondoni, Dar es Salaam", region="Dar es Salaam", district="Kinondoni", next_of_kin="Joseph Mrema — spouse", payer="NHIF", member_number="NHIF-884120", allergies="Penicillin — anaphylaxis", problems="Severe hypertension; Type 2 diabetes mellitus; Acute kidney injury", medications="Amlodipine 10 mg daily; Insulin glargine 18 units nightly", consent_status="OBTAINED"),
        Patient(mpi_id="TZ-MPI-00022410", mrn="MOI-211840", first_name="Baraka", middle_name="S.", last_name="Lema", date_of_birth=date(1997, 2, 8), sex="Male", phone="+255 688 413 992", nida_number="19970208-11201-00033-18", address="Ubungo, Dar es Salaam", region="Dar es Salaam", district="Ubungo", next_of_kin="Anna Lema — mother", payer="Cash", allergies="No known drug allergies", problems="Open femoral fracture; Road traffic injury", medications="Morphine protocol; IV cefazolin", consent_status="EMERGENCY_BASIS"),
        Patient(mpi_id="TZ-MPI-00009175", mrn="JKCI-771022", first_name="Halima", middle_name="A.", last_name="Said", date_of_birth=date(1959, 6, 19), sex="Female", phone="+255 713 992 112", nida_number="19590619-12105-00007-31", address="Temeke, Dar es Salaam", region="Dar es Salaam", district="Temeke", next_of_kin="Ahmed Said — son", payer="NHIF", member_number="NHIF-771022", allergies="Iodinated contrast — rash", problems="Heart failure with reduced ejection fraction; Atrial fibrillation", medications="Carvedilol 12.5 mg twice daily; Furosemide 40 mg daily"),
        Patient(mpi_id="TZ-MPI-00030155", mrn="ORCI-381099", first_name="Mariam", middle_name="J.", last_name="Kato", date_of_birth=date(1971, 11, 30), sex="Female", phone="+255 762 800 541", nida_number="19711130-13104-00011-25", address="Ilala, Dar es Salaam", region="Dar es Salaam", district="Ilala", next_of_kin="Peter Kato — brother", payer="NHIF", member_number="NHIF-381099", allergies="No known drug allergies", problems="Breast cancer stage III; Chemotherapy-induced anaemia", medications="Doxorubicin protocol; Ondansetron premedication"),
        Patient(mpi_id="TZ-MPI-00041572", mrn="MLOG-665802", first_name="John", middle_name="P.", last_name="Mbise", date_of_birth=date(2018, 4, 21), sex="Male", phone="+255 786 190 222", address="Kibaha, Pwani", region="Pwani", district="Kibaha", next_of_kin="Paul Mbise — guardian", payer="iCHF", member_number="ICHF-665802", allergies="Peanut", problems="Asthma", medications="Salbutamol inhaler as needed", consent_status="GUARDIAN_OBTAINED"),
        Patient(mpi_id="TZ-MPI-00050991", mrn="MNH-509991", first_name="Rehema", middle_name="K.", last_name="Mashauri", date_of_birth=date(1990, 1, 6), sex="Female", phone="+255 744 390 110", nida_number="19900106-14101-00050-19", address="Mbagala, Dar es Salaam", region="Dar es Salaam", district="Temeke", next_of_kin="Musa Mashauri — spouse", payer="NHIF", member_number="NHIF-509991", allergies="No known drug allergies", problems="Postpartum hypertension", medications="Nifedipine 20 mg twice daily"),
        Patient(mpi_id="TZ-MPI-00061244", mrn="MNH-612244", first_name="Daudi", middle_name="R.", last_name="Mwangosi", date_of_birth=date(1968, 3, 22), sex="Male", phone="+255 715 612 244", address="Morogoro Municipal", region="Morogoro", district="Morogoro", next_of_kin="Janeth Mwangosi — daughter", payer="NHIF", member_number="NHIF-612244", allergies="Sulfonamides — rash", problems="Community-acquired pneumonia; Hypertension", medications="Amoxicillin/clavulanate course completed; Losartan 50 mg daily"),
        Patient(mpi_id="TZ-MPI-00073100", mrn="MNH-3102145981", first_name="Juma", middle_name="Ally", last_name="Mwangi", date_of_birth=date(1989, 6, 12), sex="Male", phone="+255 712 345 678", nida_number="19890612-14102-00031-08", address="Mbezi Beach, Dar es Salaam", region="Dar es Salaam", district="Kinondoni", next_of_kin="Amina Mwangi — spouse", payer="NHIF", member_number="NHIF-123456789012", allergies="No known drug allergies", problems="No active chronic problem documented", medications="No active medications", consent_status="OBTAINED"),
    ]
    db.add_all(patients)
    db.flush()
    p = {item.mpi_id: item for item in patients}

    encounters = [
        Encounter(encounter_id="ENC-20260727-00492", patient=p["TZ-MPI-00018422"], facility=f["MNH-UPANGA"], encounter_type="INPATIENT", service="Internal Medicine / Nephrology", status=EncounterStatus.WAITING_RESULTS, acuity="High", location="Ward 5B", room="Bed 12", provider="Dr. Neema M.", reason_for_visit="Severe hypertension and reduced urine output", arrival_at=_dt(hours_ago=7), triage_at=_dt(hours_ago=6, minutes_ago=45), provider_start_at=_dt(hours_ago=6, minutes_ago=20)),
        Encounter(encounter_id="ENC-20260727-00614", patient=p["TZ-MPI-00022410"], facility=f["MOI"], encounter_type="EMERGENCY", service="Trauma / Orthopaedics", status=EncounterStatus.IN_PROGRESS, acuity="Critical", location="Trauma Bay", room="Trauma Bay 2", provider="Dr. Issa K.", reason_for_visit="Road traffic injury with open femoral fracture", arrival_at=_dt(hours_ago=2, minutes_ago=25), triage_at=_dt(hours_ago=2, minutes_ago=20), provider_start_at=_dt(hours_ago=2, minutes_ago=10)),
        Encounter(encounter_id="ENC-20260727-00334", patient=p["TZ-MPI-00009175"], facility=f["JKCI"], encounter_type="OUTPATIENT", service="Cardiology", status=EncounterStatus.READY_FOR_PROVIDER, acuity="Medium", location="Cardiac Clinic", room="Clinic 3", provider="Dr. Mushi", reason_for_visit="Heart failure follow-up", arrival_at=_dt(hours_ago=1, minutes_ago=35), triage_at=_dt(hours_ago=1, minutes_ago=10)),
        Encounter(encounter_id="ENC-20260727-00110", patient=p["TZ-MPI-00030155"], facility=f["ORCI"], encounter_type="INFUSION", service="Medical Oncology", status=EncounterStatus.WAITING_RESULTS, acuity="Medium", location="Infusion Unit", room="Chair 4", provider="Dr. Nyerere", reason_for_visit="Cycle 4 chemotherapy clearance", arrival_at=_dt(hours_ago=3), triage_at=_dt(hours_ago=2, minutes_ago=45), provider_start_at=_dt(hours_ago=2, minutes_ago=35)),
        Encounter(encounter_id="ENC-20260727-00208", patient=p["TZ-MPI-00041572"], facility=f["MNH-MLOGANZILA"], encounter_type="OUTPATIENT", service="Paediatrics", status=EncounterStatus.TRIAGED, acuity="Low", location="Paediatric OPD", room="Waiting Area B", reason_for_visit="Asthma follow-up", arrival_at=_dt(minutes_ago=48), triage_at=_dt(minutes_ago=22)),
        Encounter(encounter_id="ENC-20260727-00701", patient=p["TZ-MPI-00050991"], facility=f["MNH-UPANGA"], encounter_type="OUTPATIENT", service="Postnatal Clinic", status=EncounterStatus.ARRIVED, acuity="Not assigned", location="Arrival Desk", reason_for_visit="Postpartum blood pressure review", arrival_at=_dt(minutes_ago=18)),
        Encounter(encounter_id="ENC-20260727-00722", patient=p["TZ-MPI-00061244"], facility=f["MNH-UPANGA"], encounter_type="OUTPATIENT", service="Medical Clinic", status=EncounterStatus.WAITING_TRIAGE, acuity="Not assigned", location="Triage Queue", reason_for_visit="Post-discharge pneumonia review", arrival_at=_dt(minutes_ago=34)),
        Encounter(encounter_id="ENC-20260729-0142", patient=p["TZ-MPI-00073100"], facility=f["MNH-UPANGA"], encounter_type="OUTPATIENT", service="General OPD Clinic", status=EncounterStatus.ARRIVED, acuity="Not assigned", location="OPD Point A", room="Room 12", provider="Dr. Rehema Msuya", reason_for_visit="Walk-in general clinical assessment", arrival_at=_dt(minutes_ago=12)),
        Encounter(encounter_id="ENC-20260726-00518", patient=p["TZ-MPI-00061244"], facility=f["MNH-UPANGA"], encounter_type="INPATIENT", service="Internal Medicine", status=EncounterStatus.DISCHARGED, acuity="Medium", location="Ward 7A", room="Bed 3", provider="Dr. Kileo", reason_for_visit="Community-acquired pneumonia", arrival_at=_dt(hours_ago=52), triage_at=_dt(hours_ago=51, minutes_ago=40), provider_start_at=_dt(hours_ago=51), discharge_at=_dt(hours_ago=18), discharge_disposition="Home", discharge_summary="Improved after antibiotics and oxygen. Afebrile and stable on room air at discharge.", follow_up="Medical clinic in 7 days; return immediately for breathing difficulty, fever or confusion."),
        Encounter(encounter_id="ENC-20260726-00312", patient=p["TZ-MPI-00050991"], facility=f["MNH-UPANGA"], encounter_type="INPATIENT", service="Maternity", status=EncounterStatus.DISCHARGED, acuity="Medium", location="Postnatal Ward", room="Bed 14", provider="Dr. Mwita", reason_for_visit="Delivery and postpartum hypertension", arrival_at=_dt(hours_ago=60), triage_at=_dt(hours_ago=59), provider_start_at=_dt(hours_ago=58), discharge_at=_dt(hours_ago=26), discharge_disposition="Home with newborn", discharge_summary="Uncomplicated vaginal delivery. Blood pressure controlled at discharge; newborn linked to maternal record.", follow_up="Postnatal clinic in 48–72 hours and blood pressure review in one week."),
    ]
    db.add_all(encounters)
    db.flush()
    e = {item.encounter_id: item for item in encounters}

    flowsheet = FlowSheet(
        flowsheet_id="FS-NEURO-0001",
        patient=p["TZ-MPI-00022410"],
        encounter_id=e["ENC-20260727-00614"].id,
        name="Trauma Neurovascular Observation",
        template_code="MOI_TRAUMA_NV",
        status=FlowSheetStatus.RUNNING,
        cadence_minutes=15,
        parameters_json=json.dumps(["GCS", "Pain score", "Distal pulse", "Capillary refill", "Sensation", "Motor function"]),
        elapsed_seconds=1260,
        active_since=_dt(minutes_ago=9),
        started_at=_dt(minutes_ago=30),
        owner="Neema Kweka, RN",
    )
    db.add(flowsheet)
    db.flush()
    db.add_all([
        FlowSheetEvent(flowsheet=flowsheet, action="START", actor="Neema Kweka, RN", note="Started after trauma assessment", occurred_at=_dt(minutes_ago=30)),
        FlowSheetObservation(flowsheet=flowsheet, parameter="GCS", value="14", unit="/15", source="MANUAL", recorded_by="Neema Kweka, RN", recorded_at=_dt(minutes_ago=15)),
        FlowSheetObservation(flowsheet=flowsheet, parameter="Distal pulse", value="Present", unit=None, source="MANUAL", recorded_by="Neema Kweka, RN", recorded_at=_dt(minutes_ago=15)),
    ])

    orders = [
        Order(order_id="ORD-10290", encounter=e["ENC-20260727-00492"], order_type="Laboratory", order_name="Renal panel", priority="STAT", status="COLLECTED", indication="Acute kidney injury with severe hypertension", ordered_by="Dr. Neema M.", ordered_at=_dt(minutes_ago=48)),
        Order(order_id="ORD-10291", encounter=e["ENC-20260727-00492"], order_type="Imaging", order_name="Renal ultrasound", priority="URGENT", status="SCHEDULED", indication="Evaluate obstruction", ordered_by="Dr. Neema M.", ordered_at=_dt(minutes_ago=42)),
        Order(order_id="ORD-10273", encounter=e["ENC-20260727-00614"], order_type="Blood", order_name="Crossmatch 4 units PRBC", priority="STAT", status="READY", indication="Open femoral fracture and anaemia", ordered_by="Dr. Issa K.", ordered_at=_dt(hours_ago=1, minutes_ago=22)),
    ]
    db.add_all(orders)
    db.flush()
    o = {item.order_id: item for item in orders}

    results = [
        Result(result_id="RES-4410", order=o["ORD-10290"], patient_id=p["TZ-MPI-00018422"].id, test_name="Creatinine", value="238", unit="µmol/L", flag="CRITICAL", status="FINAL", source="MNH Core Laboratory", issued_at=_dt(minutes_ago=16), acknowledged=False),
        Result(result_id="RES-4412", order=o["ORD-10273"], patient_id=p["TZ-MPI-00022410"].id, test_name="Haemoglobin", value="7.4", unit="g/dL", flag="CRITICAL", status="FINAL", source="MOI Laboratory", issued_at=_dt(hours_ago=1, minutes_ago=10), acknowledged=True, acknowledged_by="Dr. Issa K.", acknowledged_at=_dt(hours_ago=1)),
        Result(result_id="RES-4388", patient_id=p["TZ-MPI-00030155"].id, test_name="Absolute neutrophil count", value="1.2", unit="×10⁹/L", flag="LOW", status="FINAL", source="ORCI Laboratory", issued_at=_dt(hours_ago=2), acknowledged=True, acknowledged_by="Dr. Nyerere", acknowledged_at=_dt(hours_ago=1, minutes_ago=45)),
    ]
    db.add_all(results)
    db.commit()
    seed_public_facilities(db)
    seed_synthetic_patients(db, get_settings().demo_patient_count)
    seed_enterprise_data(db)
    seed_operational_data(db)
    seed_order_catalog(db)
    seed_enhancement_data(db)
    seed_bed_inventory(db)
    seed_review_results(db)
    seed_country_contexts(db)
    seed_multicultural_patients(db, 15000)
