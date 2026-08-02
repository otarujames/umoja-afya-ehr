from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .enhancement_models import DeviceEndpoint, UserMessage
from .enterprise_models import UserAccount
from .models import Facility, Patient
from .access_control import get_user_access, replace_user_access


def seed_enhancement_data(db: Session) -> None:
    if not db.scalar(select(DeviceEndpoint.id).limit(1)):
        db.add_all([
            DeviceEndpoint(device_id="DEV-MNH-ICU-MON-01", facility_code="MNH-UPANGA", unit="Adult ICU", room="ICU 1", bed_label="Bed 01", name="ICU Bedside Monitor 01", device_type="MULTIPARAMETER_MONITOR", manufacturer="Review Device", model="UA-MP100", protocol="FHIR_OBSERVATION"),
            DeviceEndpoint(device_id="DEV-MNH-ICU-VENT-01", facility_code="MNH-UPANGA", unit="Adult ICU", room="ICU 1", bed_label="Bed 01", name="ICU Ventilator 01", device_type="VENTILATOR", manufacturer="Review Device", model="UA-V200", protocol="HL7_ORU_FHIR"),
            DeviceEndpoint(device_id="DEV-MOI-TRAUMA-MON-02", facility_code="MOI", unit="Trauma Ward", room="Trauma Bay 2", bed_label="Bay 2", name="Trauma Monitor 02", device_type="MULTIPARAMETER_MONITOR", manufacturer="Review Device", model="UA-MP100", protocol="FHIR_OBSERVATION"),
            DeviceEndpoint(device_id="DEV-MNH-MAT-CTG-01", facility_code="MNH-UPANGA", unit="Labour Ward", room="Delivery 1", bed_label="Bed 1", name="Fetal Monitor 01", device_type="CTG_FETAL_MONITOR", manufacturer="Review Device", model="UA-CTG1", protocol="FHIR_OBSERVATION"),
        ])
    if int(db.scalar(select(func.count(UserMessage.id))) or 0) == 0:
        admin = db.scalar(select(UserAccount).where(UserAccount.username == "admin"))
        registration = db.scalar(select(UserAccount).where(UserAccount.username == "registration"))
        doctor = db.scalar(select(UserAccount).where(UserAccount.username == "doctor"))
        patient = db.scalar(select(Patient).where(Patient.mpi_id == "TZ-MPI-00073100"))
        if admin and registration and doctor:
            db.add_all([
                UserMessage(sender_user_id=registration.id, recipient_user_id=admin.id, patient_id=patient.id if patient else None, subject="Walk-in registration configuration review", body="Please review the new public-hospital service-point routing and registration follow-up queue.", priority="HIGH"),
                UserMessage(sender_user_id=doctor.id, recipient_user_id=admin.id, patient_id=patient.id if patient else None, subject="Flowsheet device integration test", body="The Adult ICU bedside monitor interface is ready for a controlled observation-ingestion test.", priority="ROUTINE"),
                UserMessage(sender_user_id=admin.id, recipient_user_id=registration.id, subject="Access matrix updated", body="Cross-department registration and scheduling functions were enabled for the review account.", priority="ROUTINE", status="READ", read_at=datetime.now(timezone.utc)),
            ])

    # Review administrators must be able to change context across every seeded public facility.
    # Runtime access remains the explicit function × department × facility matrix.
    public_codes = list(db.scalars(select(Facility.code).where(Facility.active.is_(True), Facility.ownership_category == "Public").order_by(Facility.code)).all())
    for username in ("admin", "operations"):
        account = db.scalar(select(UserAccount).where(UserAccount.username == username))
        if account and public_codes:
            current = get_user_access(db, account)
            target_facilities = public_codes if username == "admin" else sorted(set(current["facilities"] + [code for code in public_codes if code.startswith(("MNH", "MOI", "JKCI", "ORCI"))]))
            replace_user_access(
                db, account,
                functions=current["functions"],
                departments=current["departments"],
                facilities=target_facilities,
                actor="Review Seeder",
                reason="Docker review facility-context access",
            )
    db.commit()
