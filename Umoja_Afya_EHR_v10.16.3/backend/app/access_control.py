from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .enterprise_models import UserAccessGrant, UserAccount


@dataclass(frozen=True)
class AccessItem:
    code: str
    label: str
    group: str
    description: str


FUNCTION_CATALOG: tuple[AccessItem, ...] = (
    AccessItem("dashboard.view", "Command center", "Workspace", "View operational summaries and dashboards."),
    AccessItem("patient_flow.view", "Patient flow tracker", "Workspace", "View arrived, triaged, roomed, in-progress and discharge-ready encounters."),
    AccessItem("patient_flow.manage", "Manage patient flow", "Workspace", "Advance encounter states and update care locations."),
    AccessItem("patient.search", "Patient search and MPI", "Record", "Search and select a longitudinal patient record."),
    AccessItem("patient.chart", "Longitudinal chart", "Record", "Open the selected patient chart and encounter history."),
    AccessItem("registration.manage", "Registration and identity", "Patient Access", "Create and update registrations, coverage, consent and identity records."),
    AccessItem("scheduling.manage", "Scheduling and referrals", "Patient Access", "Create and maintain appointments, waitlists and referrals."),
    AccessItem("walkins.manage", "Walk-in workflow", "Patient Access", "Register, arrive, route, triage and close walk-in encounters."),
    AccessItem("service_roster.manage", "Service points and duty rosters", "Patient Access", "View and manage government duty-roster service points and shifts."),
    AccessItem("workqueues.view", "View workqueues", "Workspace", "View operational workqueue summaries and patient-linked queue items."),
    AccessItem("workqueues.manage", "Manage workqueues", "Workspace", "Assign, route, defer, resume, complete and reopen queue items."),
    AccessItem("emergency_access", "Emergency break-glass access", "Record", "Request time-limited emergency access with mandatory reason and audit."),
    AccessItem("adt.manage", "ADT and bed management", "Patient Access", "Admit, transfer, discharge, assign beds and coordinate patient movement."),
    AccessItem("emergency.manage", "Emergency and triage", "Clinical", "Manage emergency tracking, acuity and disposition workflows."),
    AccessItem("notes.manage", "Clinical documentation", "Clinical", "Create, edit, sign and cosign clinical documentation."),
    AccessItem("audio_notes.use", "Audio-assisted notes", "Clinical", "Capture audio/transcript and create clinician-reviewed draft notes."),
    AccessItem("advisories.view", "Practice advisories", "Clinical", "View patient-specific clinical practice advisories."),
    AccessItem("flowsheets.manage", "Flowsheets", "Clinical", "Start, pause, resume, change and stop flowsheets and add observations."),
    AccessItem("orders.create", "Create orders", "Clinical", "Create laboratory, imaging, medication, blood, procedure and referral orders."),
    AccessItem("orders.manage", "Manage order course", "Clinical", "Hold, resume, cancel and reinstate orders with reasons and history."),
    AccessItem("results.review", "Results review", "Clinical", "Review patient-linked diagnostic results."),
    AccessItem("results.acknowledge", "Acknowledge critical results", "Clinical", "Acknowledge critical results and document follow-up action."),
    AccessItem("nursing.manage", "Nursing workspace", "Clinical", "Manage assessments, care plans, tasks, intake/output and handoff."),
    AccessItem("medications.order", "Medication ordering", "Medication", "Create medication orders within a selected patient record."),
    AccessItem("medications.verify", "Pharmacy verification", "Medication", "Verify medication orders and dispensing readiness."),
    AccessItem("emar.manage", "Medication administration", "Medication", "Document administered, held, refused or omitted doses."),
    AccessItem("laboratory.manage", "Laboratory", "Ancillary", "Manage specimens, testing, validation and release."),
    AccessItem("blood_bank.manage", "Blood bank", "Ancillary", "Manage blood product requests, compatibility and issue."),
    AccessItem("radiology.manage", "Radiology and imaging", "Ancillary", "Manage imaging protocol, worklists, acquisition and reporting."),
    AccessItem("theatre.manage", "Theatre and procedures", "Procedural", "Manage surgical scheduling, intraoperative records and recovery."),
    AccessItem("anesthesia.manage", "Anesthesia", "Procedural", "Manage pre-anesthesia assessment and intraoperative anesthesia records."),
    AccessItem("maternity.manage", "Maternity and newborn", "Specialty", "Manage ANC, labour, delivery, newborn and postnatal workflows."),
    AccessItem("cardiology.manage", "Cardiology", "Specialty", "Manage cardiology diagnostics, procedures and care pathways."),
    AccessItem("orthopaedics.manage", "Orthopaedics and trauma", "Specialty", "Manage orthopaedic, trauma and neurosurgery workflows."),
    AccessItem("oncology.manage", "Oncology", "Specialty", "Manage protocols, chemotherapy, radiotherapy and toxicity monitoring."),
    AccessItem("critical_care.manage", "Critical care", "Specialty", "Manage ICU flowsheets, devices and critical-care pathways."),
    AccessItem("rehab.manage", "Rehabilitation, mental health and dental", "Specialty", "Manage specialty assessments, plans and outcomes."),
    AccessItem("revenue.manage", "Revenue cycle and claims", "Enterprise", "Manage eligibility, charges, claims, denials and payments."),
    AccessItem("supply.manage", "Supply chain and assets", "Enterprise", "Manage stock, expiry, procurement and equipment workflows."),
    AccessItem("telehealth.manage", "Telehealth", "Enterprise", "Schedule and conduct patient-linked remote encounters."),
    AccessItem("public_health.manage", "Public health and registries", "Enterprise", "Manage registries, surveillance and reporting events."),
    AccessItem("quality.manage", "Quality and safety", "Enterprise", "Manage incidents, near misses, infection prevention and quality work."),
    AccessItem("analytics.view", "Analytics, M&E and research", "Enterprise", "View aggregate operational, clinical and programme analytics."),
    AccessItem("workforce.manage", "Workforce and learning", "Enterprise", "Manage provider directory, rosters, credentials and learning."),
    AccessItem("system.users.manage", "User administration", "Administration", "Create, edit, disable, unlock and assign user access matrices."),
    AccessItem("system.audit.view", "Audit review", "Administration", "Review access, configuration and transaction audit events."),
    AccessItem("system.interfaces.manage", "Interface operations", "Administration", "Review and operate national and facility interfaces."),
    AccessItem("system.configuration.manage", "System configuration", "Administration", "Manage facilities, terminology, content and releases."),
    AccessItem("fhir.exchange", "FHIR and interoperability", "Administration", "Use standards-based exchange and conformance services."),
)

DEPARTMENT_CATALOG: tuple[AccessItem, ...] = (
    AccessItem("REGISTRATION", "Registration and Patient Access", "Administrative", "Identity, registration, coverage and consent."),
    AccessItem("SCHEDULING", "Scheduling and Referrals", "Administrative", "Appointments, rosters, waitlists and referrals."),
    AccessItem("OPD", "Outpatient Services", "Clinical", "General and specialist outpatient care."),
    AccessItem("EMERGENCY", "Emergency Department", "Clinical", "Emergency, trauma and observation."),
    AccessItem("INPATIENT", "Inpatient Services", "Clinical", "Ward and multidisciplinary inpatient care."),
    AccessItem("NURSING", "Nursing", "Clinical", "Nursing care and medication administration."),
    AccessItem("PHARMACY", "Pharmacy", "Ancillary", "Pharmacy and medication operations."),
    AccessItem("LABORATORY", "Laboratory", "Ancillary", "Laboratory and specimen operations."),
    AccessItem("BLOOD_BANK", "Blood Bank", "Ancillary", "Transfusion and blood product services."),
    AccessItem("RADIOLOGY", "Radiology and Imaging", "Ancillary", "Imaging services and reporting."),
    AccessItem("THEATRE", "Theatre and Procedures", "Procedural", "Surgery, procedures and recovery."),
    AccessItem("ANESTHESIA", "Anesthesia", "Procedural", "Anesthesia and perioperative care."),
    AccessItem("MATERNITY", "Maternity and Newborn", "Specialty", "Maternal and newborn services."),
    AccessItem("MOI", "Orthopaedics and Trauma", "Specialty", "Orthopaedics, trauma and neurosurgery."),
    AccessItem("JKCI", "Cardiology", "Specialty", "Cardiovascular services."),
    AccessItem("ORCI", "Oncology", "Specialty", "Cancer care services."),
    AccessItem("ICU", "Critical Care", "Specialty", "Intensive and high-dependency care."),
    AccessItem("REHAB", "Rehabilitation and Allied Health", "Specialty", "Rehabilitation, mental health and dental."),
    AccessItem("FINANCE", "Finance and Revenue Cycle", "Enterprise", "Billing, claims and reconciliation."),
    AccessItem("SUPPLY", "Supply Chain and Assets", "Enterprise", "Inventory, procurement and equipment."),
    AccessItem("PUBLIC_HEALTH", "Public Health and M&E", "Enterprise", "Surveillance, registries, reporting and M&E."),
    AccessItem("QUALITY", "Quality, Safety and IPC", "Enterprise", "Quality, patient safety and infection prevention."),
    AccessItem("HIM", "Health Information Management", "Enterprise", "Record integrity, coding, release and data quality."),
    AccessItem("ICT", "ICT and Digital Health", "Administration", "User, configuration, interface and infrastructure support."),
)


ROLE_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "physician": {
        "functions": ["dashboard.view", "patient_flow.view", "patient_flow.manage", "patient.search", "patient.chart", "scheduling.manage", "walkins.manage", "service_roster.manage", "workqueues.view", "workqueues.manage", "emergency_access", "emergency.manage", "notes.manage", "audio_notes.use", "advisories.view", "flowsheets.manage", "orders.create", "orders.manage", "results.review", "results.acknowledge", "medications.order", "laboratory.manage", "blood_bank.manage", "radiology.manage", "theatre.manage", "anesthesia.manage", "maternity.manage", "cardiology.manage", "orthopaedics.manage", "oncology.manage", "critical_care.manage", "rehab.manage", "telehealth.manage", "public_health.manage", "quality.manage", "analytics.view", "fhir.exchange"],
        "departments": ["OPD", "EMERGENCY", "INPATIENT"],
    },
    "nurse": {
        "functions": ["dashboard.view", "patient_flow.view", "patient_flow.manage", "patient.search", "patient.chart", "adt.manage", "emergency.manage", "notes.manage", "audio_notes.use", "advisories.view", "flowsheets.manage", "results.review", "nursing.manage", "emar.manage", "laboratory.manage", "blood_bank.manage", "radiology.manage", "theatre.manage", "anesthesia.manage", "maternity.manage", "cardiology.manage", "orthopaedics.manage", "oncology.manage", "critical_care.manage", "rehab.manage", "telehealth.manage", "quality.manage", "analytics.view"],
        "departments": ["NURSING", "OPD", "INPATIENT"],
    },
    "registration": {
        "functions": ["dashboard.view", "patient_flow.view", "patient.search", "patient.chart", "registration.manage", "scheduling.manage", "walkins.manage", "service_roster.manage", "workqueues.view", "workqueues.manage", "adt.manage", "telehealth.manage"],
        "departments": ["REGISTRATION", "SCHEDULING"],
    },
    "pharmacy": {
        "functions": ["dashboard.view", "patient.search", "patient.chart", "orders.manage", "results.review", "medications.verify", "supply.manage", "quality.manage", "analytics.view"],
        "departments": ["PHARMACY", "SUPPLY"],
    },
    "laboratory": {
        "functions": ["dashboard.view", "patient.search", "patient.chart", "orders.manage", "results.review", "laboratory.manage", "blood_bank.manage", "radiology.manage", "supply.manage", "public_health.manage", "quality.manage", "analytics.view"],
        "departments": ["LABORATORY", "BLOOD_BANK"],
    },
    "operations": {
        "functions": ["dashboard.view", "patient_flow.view", "patient_flow.manage", "patient.search", "patient.chart", "scheduling.manage", "walkins.manage", "service_roster.manage", "workqueues.view", "workqueues.manage", "adt.manage", "emergency.manage", "blood_bank.manage", "radiology.manage", "theatre.manage", "anesthesia.manage", "critical_care.manage", "supply.manage", "quality.manage", "analytics.view", "workforce.manage"],
        "departments": ["INPATIENT", "EMERGENCY", "QUALITY"],
    },
    "finance": {
        "functions": ["dashboard.view", "patient.search", "patient.chart", "workqueues.view", "workqueues.manage", "revenue.manage", "analytics.view"],
        "departments": ["FINANCE"],
    },
    "admin": {
        "functions": [item.code for item in FUNCTION_CATALOG],
        "departments": [item.code for item in DEPARTMENT_CATALOG],
    },
    "custom": {"functions": ["dashboard.view", "patient.search"], "departments": []},
}

FUNCTION_CODES = {item.code for item in FUNCTION_CATALOG}
DEPARTMENT_CODES = {item.code for item in DEPARTMENT_CATALOG}


def normalize_codes(values: Iterable[str] | None, allowed: set[str]) -> list[str]:
    result: list[str] = []
    for value in values or []:
        code = str(value).strip()
        if code and code in allowed and code not in result:
            result.append(code)
    return result


def get_user_access(db: Session, user: UserAccount) -> dict[str, list[str]]:
    rows = list(db.scalars(select(UserAccessGrant).where(UserAccessGrant.user_account_id == user.id, UserAccessGrant.active.is_(True))).all())
    grouped: dict[str, list[str]] = {"FUNCTION": [], "DEPARTMENT": [], "FACILITY": [], "COUNTRY": []}
    for row in rows:
        if row.scope_type in grouped and row.scope_code not in grouped[row.scope_type]:
            grouped[row.scope_type].append(row.scope_code)
    if not grouped["FUNCTION"]:
        template = ROLE_TEMPLATES.get(user.role_code, ROLE_TEMPLATES["custom"])
        grouped["FUNCTION"] = list(template["functions"])
    if not grouped["DEPARTMENT"]:
        grouped["DEPARTMENT"] = list(ROLE_TEMPLATES.get(user.role_code, ROLE_TEMPLATES["custom"])["departments"])
    if not grouped["FACILITY"]:
        grouped["FACILITY"] = [user.facility_code]
    if not grouped["COUNTRY"]:
        facility = db.scalar(select(Facility).where(Facility.code == user.facility_code))
        grouped["COUNTRY"] = [getattr(facility, "country_code", "TZ") if facility else "TZ"]
    return {
        "functions": sorted(grouped["FUNCTION"]),
        "departments": sorted(grouped["DEPARTMENT"]),
        "facilities": sorted(grouped["FACILITY"]),
        "countries": sorted(grouped["COUNTRY"]),
    }


def replace_user_access(
    db: Session,
    user: UserAccount,
    *,
    functions: Iterable[str],
    departments: Iterable[str],
    facilities: Iterable[str],
    countries: Iterable[str] | None = None,
    actor: str,
    reason: str | None = None,
) -> dict[str, list[str]]:
    function_codes = normalize_codes(functions, FUNCTION_CODES)
    department_codes = normalize_codes(departments, DEPARTMENT_CODES)
    facility_codes = list(dict.fromkeys(str(code).strip() for code in facilities if str(code).strip()))
    country_codes = list(dict.fromkeys(str(code).upper().strip() for code in (countries or []) if str(code).strip()))
    if not country_codes:
        country_codes = sorted({(db.scalar(select(Facility).where(Facility.code == code)).country_code if db.scalar(select(Facility).where(Facility.code == code)) else "TZ") for code in facility_codes})
    if not function_codes:
        raise ValueError("At least one function must be selected")
    if not facility_codes:
        raise ValueError("At least one facility must be selected")
    db.execute(delete(UserAccessGrant).where(UserAccessGrant.user_account_id == user.id))
    for scope_type, codes in (("FUNCTION", function_codes), ("DEPARTMENT", department_codes), ("FACILITY", facility_codes), ("COUNTRY", country_codes)):
        for code in codes:
            db.add(UserAccessGrant(user_account_id=user.id, scope_type=scope_type, scope_code=code, granted_by=actor, reason=reason))
    user.facility_code = facility_codes[0]
    db.flush()
    return {"functions": sorted(function_codes), "departments": sorted(department_codes), "facilities": sorted(facility_codes), "countries": sorted(country_codes)}


def template_access(template_code: str, facility_code: str) -> dict[str, list[str]]:
    template = ROLE_TEMPLATES.get(template_code, ROLE_TEMPLATES["custom"])
    return {
        "functions": list(template["functions"]),
        "departments": list(template["departments"]),
        "facilities": [facility_code],
        "countries": ["TZ"],
    }
