from __future__ import annotations

import json

import json
from datetime import datetime, timezone

from .models import Encounter, FlowSheet, Order, Patient, Result


def patient_dict(patient: Patient) -> dict:
    return {
        "mpi_id": patient.mpi_id,
        "mrn": patient.mrn,
        "first_name": patient.first_name,
        "middle_name": patient.middle_name,
        "last_name": patient.last_name,
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth,
        "sex": patient.sex,
        "phone": patient.phone,
        "nida_number": patient.nida_number,
        "address": patient.address,
        "region": patient.region,
        "district": patient.district,
        "next_of_kin": patient.next_of_kin,
        "payer": patient.payer,
        "member_number": patient.member_number,
        "allergies": patient.allergies,
        "problems": patient.problems,
        "medications": patient.medications,
        "consent_status": patient.consent_status,
        "identity_status": patient.identity_status,
        "record_status": patient.record_status,
        "deceased_at": patient.deceased_at,
        "deceased_location": patient.deceased_location,
        "deceased_cause": patient.deceased_cause,
        "death_certificate_number": patient.death_certificate_number,
        "expired_by": patient.expired_by,
        "country_code": patient.country_code,
    }


def facility_dict(facility) -> dict:
    return {
        "code": facility.code,
        "name": facility.name,
        "facility_type": facility.facility_type,
        "relation": facility.relation,
        "active": facility.active,
        "hfr_code": facility.hfr_code,
        "region": facility.region,
        "council": facility.council,
        "ownership_category": facility.ownership_category,
        "ownership_authority": facility.ownership_authority,
        "hierarchy_level": facility.hierarchy_level,
        "parent_code": facility.parent_code,
        "source_system": facility.source_system,
        "country_code": facility.country_code,
    }


def encounter_dict(encounter: Encounter) -> dict:
    return {
        "encounter_id": encounter.encounter_id,
        "encounter_type": encounter.encounter_type,
        "service": encounter.service,
        "status": encounter.status,
        "acuity": encounter.acuity,
        "location": encounter.location,
        "room": encounter.room,
        "provider": encounter.provider,
        "reason_for_visit": encounter.reason_for_visit,
        "arrival_at": encounter.arrival_at,
        "triage_at": encounter.triage_at,
        "provider_start_at": encounter.provider_start_at,
        "discharge_at": encounter.discharge_at,
        "discharge_disposition": encounter.discharge_disposition,
        "discharge_summary": encounter.discharge_summary,
        "follow_up": encounter.follow_up,
        "patient": patient_dict(encounter.patient),
        "facility": facility_dict(encounter.facility),
    }




def _dt_sort_value(value: datetime | None) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()

def _elapsed_seconds(flowsheet: FlowSheet) -> int:
    total = flowsheet.elapsed_seconds
    if flowsheet.status.value == "RUNNING" and flowsheet.active_since:
        now = datetime.now(timezone.utc)
        active_since = flowsheet.active_since
        if active_since.tzinfo is None:
            active_since = active_since.replace(tzinfo=timezone.utc)
        total += max(0, int((now - active_since).total_seconds()))
    return total


def flowsheet_dict(flowsheet: FlowSheet) -> dict:
    encounter_id = flowsheet.events and None
    if flowsheet.encounter_id:
        # Relationship is intentionally not loaded; resolve from scalar cache added by router.
        encounter_id = getattr(flowsheet, "_encounter_public_id", None)
    return {
        "flowsheet_id": flowsheet.flowsheet_id,
        "patient_mpi_id": flowsheet.patient.mpi_id,
        "encounter_id": encounter_id,
        "patient_name": flowsheet.patient.full_name,
        "name": flowsheet.name,
        "template_code": flowsheet.template_code,
        "status": flowsheet.status,
        "cadence_minutes": flowsheet.cadence_minutes,
        "parameters": json.loads(flowsheet.parameters_json or "[]"),
        "elapsed_seconds": _elapsed_seconds(flowsheet),
        "owner": flowsheet.owner,
        "started_at": flowsheet.started_at,
        "stopped_at": flowsheet.stopped_at,
        "events": [
            {
                "action": event.action,
                "actor": event.actor,
                "note": event.note,
                "occurred_at": event.occurred_at,
            }
            for event in sorted(flowsheet.events, key=lambda e: _dt_sort_value(e.occurred_at), reverse=True)
        ],
        "observations": [
            {
                "parameter": observation.parameter,
                "value": observation.value,
                "unit": observation.unit,
                "source": observation.source,
                "recorded_by": observation.recorded_by,
                "recorded_at": observation.recorded_at,
            }
            for observation in sorted(flowsheet.observations, key=lambda o: _dt_sort_value(o.recorded_at), reverse=True)
        ],
    }


def order_dict(order: Order) -> dict:
    try:
        details = json.loads(order.details_json or "{}")
    except (TypeError, ValueError):
        details = {}
    return {
        "order_id": order.order_id,
        "encounter_id": order.encounter.encounter_id,
        "patient_mpi_id": order.encounter.patient.mpi_id,
        "patient_name": order.encounter.patient.full_name,
        "order_type": order.order_type,
        "order_name": order.order_name,
        "orderable_code": order.orderable_code,
        "priority": order.priority,
        "status": order.status,
        "indication": order.indication,
        "instructions": order.instructions,
        "details": details,
        "ordered_by": order.ordered_by,
        "ordered_at": order.ordered_at,
    }


def result_dict(result: Result, patient: Patient) -> dict:
    return {
        "result_id": result.result_id,
        "patient_mpi_id": patient.mpi_id,
        "patient_name": patient.full_name,
        "test_name": result.test_name,
        "value": result.value,
        "unit": result.unit,
        "flag": result.flag,
        "status": result.status,
        "source": result.source,
        "issued_at": result.issued_at,
        "acknowledged": result.acknowledged,
        "acknowledged_by": result.acknowledged_by,
        "acknowledged_at": result.acknowledged_at,
    }
