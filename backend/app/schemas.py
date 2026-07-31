from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import EncounterStatus, FlowSheetStatus


class FacilityOut(BaseModel):
    country_code: str = "TZ"
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str
    facility_type: str
    relation: str
    active: bool
    hfr_code: str | None = None
    region: str | None = None
    council: str | None = None
    ownership_category: str = "Public"
    ownership_authority: str | None = None
    hierarchy_level: str | None = None
    parent_code: str | None = None
    source_system: str = "Umoja Afya"


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    mpi_id: str
    mrn: str
    first_name: str
    middle_name: str | None = None
    last_name: str
    full_name: str
    date_of_birth: date | None = None
    sex: str
    phone: str | None = None
    nida_number: str | None = None
    address: str | None = None
    region: str | None = None
    district: str | None = None
    next_of_kin: str | None = None
    payer: str | None = None
    member_number: str | None = None
    allergies: str
    problems: str
    medications: str
    consent_status: str
    identity_status: str
    record_status: str = "ACTIVE"
    deceased_at: datetime | None = None
    deceased_location: str | None = None
    deceased_cause: str | None = None
    death_certificate_number: str | None = None
    expired_by: str | None = None


class EncounterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    encounter_id: str
    encounter_type: str
    service: str
    status: EncounterStatus
    acuity: str
    location: str
    room: str | None = None
    provider: str | None = None
    reason_for_visit: str | None = None
    arrival_at: datetime
    triage_at: datetime | None = None
    provider_start_at: datetime | None = None
    discharge_at: datetime | None = None
    discharge_disposition: str | None = None
    discharge_summary: str | None = None
    follow_up: str | None = None
    patient: PatientOut
    facility: FacilityOut


class PatientDetail(PatientOut):
    encounters: list[EncounterOut] = Field(default_factory=list)


class RegistrationSearchIn(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    phone: str | None = None
    nida_number: str | None = None
    mrn: str | None = None


class RegistrationIn(BaseModel):
    first_name: str
    middle_name: str | None = None
    last_name: str
    date_of_birth: date | None = None
    sex: str
    phone: str | None = None
    nida_number: str | None = None
    address: str | None = None
    region: str | None = None
    district: str | None = None
    next_of_kin: str | None = None
    payer: str | None = None
    member_number: str | None = None
    facility_code: str
    encounter_type: str = "OUTPATIENT"
    service: str = "General Medicine"
    reason_for_visit: str | None = None
    registration_mode: Literal["STANDARD", "EMERGENCY", "UNKNOWN", "NEWBORN", "PRE_REGISTRATION"] = "STANDARD"
    consent_status: str = "OBTAINED"
    proxy_name: str | None = None
    proxy_relationship: str | None = None
    force_create: bool = False


class RegistrationOut(BaseModel):
    patient: PatientOut
    encounter: EncounterOut
    possible_duplicates: list[PatientOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EncounterStatusUpdate(BaseModel):
    status: EncounterStatus
    location: str | None = None
    room: str | None = None
    provider: str | None = None
    acuity: str | None = None
    actor: str = "demo-user"
    note: str | None = None


class DischargeIn(BaseModel):
    disposition: str
    summary: str
    follow_up: str | None = None
    actor: str = "demo-provider"


class FlowSheetCreate(BaseModel):
    patient_mpi_id: str
    encounter_id: str | None = None
    name: str
    template_code: str = "GENERAL"
    cadence_minutes: int = 15
    parameters: list[str] = Field(default_factory=list)
    owner: str = "demo-user"


class FlowSheetAction(BaseModel):
    action: Literal["START", "PAUSE", "RESUME", "CHANGE", "STOP"]
    actor: str = "demo-user"
    note: str | None = None
    cadence_minutes: int | None = None
    name: str | None = None
    parameters: list[str] | None = None


class FlowSheetObservationIn(BaseModel):
    parameter: str
    value: str
    unit: str | None = None
    source: str = "MANUAL"
    recorded_by: str = "demo-user"


class FlowSheetEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    action: str
    actor: str
    note: str | None = None
    occurred_at: datetime


class FlowSheetObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    parameter: str
    value: str
    unit: str | None = None
    source: str
    recorded_by: str
    recorded_at: datetime


class FlowSheetOut(BaseModel):
    flowsheet_id: str
    patient_mpi_id: str
    encounter_id: str | None = None
    patient_name: str
    name: str
    template_code: str
    status: FlowSheetStatus
    cadence_minutes: int
    parameters: list[str]
    elapsed_seconds: int
    owner: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    events: list[FlowSheetEventOut] = Field(default_factory=list)
    observations: list[FlowSheetObservationOut] = Field(default_factory=list)


class OrderIn(BaseModel):
    encounter_id: str
    orderable_code: str | None = None
    order_type: str | None = None
    order_name: str | None = None
    priority: str | None = None
    indication: str | None = None
    instructions: str | None = None
    ordered_by: str = "demo-provider"


class OrderOut(BaseModel):
    order_id: str
    encounter_id: str
    patient_mpi_id: str
    patient_name: str
    order_type: str
    order_name: str
    priority: str
    status: str
    indication: str | None = None
    ordered_by: str
    ordered_at: datetime


class ResultOut(BaseModel):
    result_id: str
    patient_mpi_id: str
    patient_name: str
    test_name: str
    value: str
    unit: str | None = None
    flag: str
    status: str
    source: str
    issued_at: datetime
    acknowledged: bool
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None


class AcknowledgeIn(BaseModel):
    actor: str = "demo-provider"
    action_taken: str | None = None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: str
    occurred_at: datetime
    actor: str
    role: str
    action: str
    resource_type: str
    resource_id: str | None = None
    patient_mpi_id: str | None = None
    facility_code: str | None = None
    outcome: str
    details: str | None = None


class ModuleDefinition(BaseModel):
    code: str
    name: str
    capability_group: str
    description: str
    status: str
    routes: list[str]
    integrations: list[str]
    capability_reference: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderActionIn(BaseModel):
    action: Literal["HOLD", "RESUME", "CANCEL", "REINSTATE"]
    actor: str = Field(min_length=2, max_length=160)
    reason: str = Field(min_length=3, max_length=1000)
