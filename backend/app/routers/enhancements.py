from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..access_control import get_user_access
from ..audit import write_audit
from ..config import PROJECT_ROOT
from ..database import get_db
from ..enhancement_models import DeviceEndpoint, DeviceReading, ManagedEvent, OrderCatalogItem, OrderSet, OrderSetItem, UserMessage
from ..enterprise_models import Appointment, AppointmentStatusEvent, Bed, UserAccessGrant, UserAccount, WorkItem
from ..event_management import record_managed_event
from ..models import Encounter, EncounterStatus, Facility, FlowSheet, FlowSheetObservation, Order, OrderStatusEvent, Patient
from ..security import optional_user

router = APIRouter(tags=["Enterprise Enhancements"])


def now() -> datetime:
    return datetime.now(timezone.utc)


def patient_by_mpi(db: Session, mpi_id: str) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.mpi_id == mpi_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def encounter_by_public_id(db: Session, encounter_id: str) -> Encounter:
    encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == encounter_id))
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return encounter


def current_actor(user: UserAccount | None, fallback: str = "Review User") -> str:
    return user.display_name if user else fallback


def _json_object(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _catalog_payload(item: OrderCatalogItem) -> dict[str, Any]:
    metadata = _json_object(item.metadata_json, {})
    return {
        "orderable_code": item.orderable_code,
        "display_name": item.display_name,
        "category": item.category,
        "subcategory": item.subcategory,
        "clinical": item.clinical,
        "department": item.department,
        "specimen": item.specimen,
        "default_priority": item.default_priority,
        "default_instructions": item.default_instructions,
        "synonyms": item.synonyms,
        "units": item.units,
        "route": item.route,
        "requires_reason": item.requires_reason,
        "requires_cosign": item.requires_cosign,
        "active": item.active,
        "metadata": metadata,
        "custom": metadata.get("source") == "LOCAL_APPROVED",
    }


def _require_catalog_admin(user: UserAccount | None, db: Session) -> UserAccount:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    access = get_user_access(db, user)
    if user.role_code != "admin" and "system.configuration.manage" not in set(access["functions"]):
        raise HTTPException(status_code=403, detail="Order catalog and order set authoring is restricted to configuration administrators")
    return user


def _unique_governed_code(db: Session, model: type, attribute: str, prefix: str, value: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")[:60] or "ITEM"
    candidate = f"{prefix}-{slug}"
    column = getattr(model, attribute)
    suffix = 2
    while db.scalar(select(model).where(column == candidate)):
        candidate = f"{prefix}-{slug}-{suffix}"
        suffix += 1
    return candidate


@router.get("/order-catalog")
def order_catalog(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    department: str | None = Query(default=None),
    clinical: bool | None = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(OrderCatalogItem)
    if active_only:
        query = query.where(OrderCatalogItem.active.is_(True))
    if category:
        query = query.where(OrderCatalogItem.category == category.upper())
    if department:
        query = query.where(func.lower(OrderCatalogItem.department) == department.lower())
    if clinical is not None:
        query = query.where(OrderCatalogItem.clinical.is_(clinical))
    normalized_search = " ".join((search or "").strip().lower().split())
    if normalized_search:
        for token in normalized_search.split():
            needle = f"%{token}%"
            query = query.where(or_(
                func.lower(OrderCatalogItem.display_name).like(needle),
                func.lower(OrderCatalogItem.orderable_code).like(needle),
                func.lower(func.coalesce(OrderCatalogItem.synonyms, "")).like(needle),
                func.lower(func.coalesce(OrderCatalogItem.subcategory, "")).like(needle),
            ))
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    ordering = [OrderCatalogItem.category, OrderCatalogItem.display_name]
    if normalized_search:
        exact = normalized_search
        ordering = [
            case(
                (func.lower(OrderCatalogItem.display_name) == exact, 0),
                (func.lower(OrderCatalogItem.display_name).like(f"{exact}%"), 1),
                (func.lower(OrderCatalogItem.orderable_code) == exact, 2),
                else_=3,
            ),
            OrderCatalogItem.display_name,
        ]
    items = list(db.scalars(query.order_by(*ordering).offset(offset).limit(limit)).all())
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [_catalog_payload(item) for item in items],
    }


@router.get("/order-catalog/categories")
def order_catalog_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(OrderCatalogItem.category, OrderCatalogItem.clinical, func.count(OrderCatalogItem.id))
        .where(OrderCatalogItem.active.is_(True))
        .group_by(OrderCatalogItem.category, OrderCatalogItem.clinical)
        .order_by(OrderCatalogItem.category)
    ).all()
    categories: dict[str, dict[str, Any]] = {}
    for category, clinical, count in rows:
        item = categories.setdefault(category, {"category": category, "total": 0, "clinical": 0, "non_clinical": 0})
        item["total"] += int(count)
        item["clinical" if clinical else "non_clinical"] += int(count)
    return list(categories.values())


class OrderCatalogCreateIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=255)
    category: str = Field(min_length=2, max_length=80)
    subcategory: str | None = Field(default=None, max_length=120)
    clinical: bool = True
    department: str | None = Field(default=None, max_length=120)
    specimen: str | None = Field(default=None, max_length=120)
    default_priority: Literal["ROUTINE", "URGENT", "STAT"] = "ROUTINE"
    default_instructions: str | None = Field(default=None, max_length=10000)
    synonyms: str | None = Field(default=None, max_length=5000)
    units: str | None = Field(default=None, max_length=120)
    route: str | None = Field(default=None, max_length=80)
    requires_reason: bool = False
    requires_cosign: bool = False
    governance_reason: str = Field(min_length=5, max_length=1000)


class OrderCatalogUpdateIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=255)
    subcategory: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    specimen: str | None = Field(default=None, max_length=120)
    default_priority: Literal["ROUTINE", "URGENT", "STAT"] | None = None
    default_instructions: str | None = Field(default=None, max_length=10000)
    synonyms: str | None = Field(default=None, max_length=5000)
    units: str | None = Field(default=None, max_length=120)
    route: str | None = Field(default=None, max_length=80)
    requires_reason: bool | None = None
    requires_cosign: bool | None = None
    active: bool | None = None
    governance_reason: str = Field(min_length=5, max_length=1000)


@router.post("/order-catalog", status_code=201)
def create_catalog_orderable(payload: OrderCatalogCreateIn, user: UserAccount | None = Depends(optional_user), db: Session = Depends(get_db)):
    admin = _require_catalog_admin(user, db)
    category = payload.category.strip().upper()
    code = _unique_governed_code(db, OrderCatalogItem, "orderable_code", f"CUSTOM-{category[:10]}", payload.display_name)
    item = OrderCatalogItem(
        orderable_code=code,
        display_name=payload.display_name.strip(),
        category=category,
        subcategory=payload.subcategory,
        clinical=payload.clinical,
        department=payload.department,
        specimen=payload.specimen,
        default_priority=payload.default_priority,
        default_instructions=payload.default_instructions,
        synonyms=payload.synonyms,
        units=payload.units,
        route=payload.route,
        requires_reason=payload.requires_reason,
        requires_cosign=payload.requires_cosign,
        metadata_json=json.dumps({"source": "LOCAL_APPROVED", "created_by": admin.display_name, "governance_reason": payload.governance_reason, "version": 1}),
    )
    db.add(item)
    write_audit(db, action="CREATE_ORDERABLE", resource_type="OrderCatalogItem", resource_id=code, actor=admin.display_name, role=admin.role_code, details=payload.governance_reason)
    db.commit()
    db.refresh(item)
    return _catalog_payload(item)


@router.patch("/order-catalog/{orderable_code}")
def update_catalog_orderable(orderable_code: str, payload: OrderCatalogUpdateIn, user: UserAccount | None = Depends(optional_user), db: Session = Depends(get_db)):
    admin = _require_catalog_admin(user, db)
    item = db.scalar(select(OrderCatalogItem).where(OrderCatalogItem.orderable_code == orderable_code))
    if not item:
        raise HTTPException(status_code=404, detail="Orderable not found")
    for field in ("display_name", "subcategory", "department", "specimen", "default_priority", "default_instructions", "synonyms", "units", "route", "requires_reason", "requires_cosign", "active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(item, field, value.strip() if isinstance(value, str) else value)
    metadata = _json_object(item.metadata_json, {})
    metadata.update({"last_updated_by": admin.display_name, "governance_reason": payload.governance_reason, "version": int(metadata.get("version", 1)) + 1})
    item.metadata_json = json.dumps(metadata)
    write_audit(db, action="UPDATE_ORDERABLE", resource_type="OrderCatalogItem", resource_id=item.orderable_code, actor=admin.display_name, role=admin.role_code, details=payload.governance_reason)
    db.commit()
    return _catalog_payload(item)


class OrderSetItemIn(BaseModel):
    orderable_code: str = Field(min_length=2, max_length=100)
    selected_by_default: bool = True
    required: bool = False
    default_priority: Literal["ROUTINE", "URGENT", "STAT"] | None = None
    default_indication: str | None = Field(default=None, max_length=5000)
    default_instructions: str | None = Field(default=None, max_length=10000)
    details: dict = Field(default_factory=dict)


class OrderSetCreateIn(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    specialty: str | None = Field(default=None, max_length=120)
    encounter_types: list[str] = Field(default_factory=list, max_length=20)
    items: list[OrderSetItemIn] = Field(min_length=1, max_length=100)
    governance_reason: str = Field(min_length=5, max_length=1000)


def _order_set_payload(db: Session, order_set: OrderSet) -> dict[str, Any]:
    rows = db.execute(
        select(OrderSetItem, OrderCatalogItem)
        .join(OrderCatalogItem, OrderCatalogItem.orderable_code == OrderSetItem.orderable_code)
        .where(OrderSetItem.order_set_id == order_set.id)
        .order_by(OrderSetItem.sequence)
    ).all()
    return {
        "set_code": order_set.set_code,
        "name": order_set.name,
        "description": order_set.description,
        "specialty": order_set.specialty,
        "encounter_types": _json_object(order_set.encounter_types_json, []),
        "version": order_set.version,
        "source": order_set.source,
        "active": order_set.active,
        "approved_by": order_set.approved_by,
        "approved_at": order_set.approved_at,
        "items": [
            {
                **_catalog_payload(catalog),
                "selected_by_default": row.selected_by_default,
                "required": row.required,
                "default_priority": row.default_priority or catalog.default_priority,
                "default_indication": row.default_indication,
                "default_instructions": row.default_instructions or catalog.default_instructions,
                "details": _json_object(row.details_json, {}),
            }
            for row, catalog in rows
        ],
    }


@router.get("/order-sets")
def list_order_sets(search: str | None = None, specialty: str | None = None, active_only: bool = True, db: Session = Depends(get_db)):
    query = select(OrderSet)
    if active_only:
        query = query.where(OrderSet.active.is_(True))
    if specialty:
        query = query.where(func.lower(func.coalesce(OrderSet.specialty, "")).like(f"%{specialty.strip().lower()}%"))
    if search:
        needle = f"%{search.strip().lower()}%"
        query = query.where(or_(func.lower(OrderSet.name).like(needle), func.lower(OrderSet.set_code).like(needle), func.lower(func.coalesce(OrderSet.description, "")).like(needle)))
    sets = list(db.scalars(query.order_by(OrderSet.specialty, OrderSet.name)).all())
    return [_order_set_payload(db, item) for item in sets]


@router.post("/order-sets", status_code=201)
def create_order_set(payload: OrderSetCreateIn, user: UserAccount | None = Depends(optional_user), db: Session = Depends(get_db)):
    admin = _require_catalog_admin(user, db)
    codes = [item.orderable_code for item in payload.items]
    if len(codes) != len(set(codes)):
        raise HTTPException(status_code=422, detail="An orderable can appear only once in an order set")
    found = set(db.scalars(select(OrderCatalogItem.orderable_code).where(OrderCatalogItem.orderable_code.in_(codes), OrderCatalogItem.active.is_(True))).all())
    missing = sorted(set(codes) - found)
    if missing:
        raise HTTPException(status_code=422, detail=f"Unknown or inactive orderables: {', '.join(missing)}")
    code = _unique_governed_code(db, OrderSet, "set_code", "SET", payload.name)
    order_set = OrderSet(set_code=code, name=payload.name.strip(), description=payload.description, specialty=payload.specialty, encounter_types_json=json.dumps(payload.encounter_types), source="LOCAL_APPROVED", created_by=admin.display_name, approved_by=admin.display_name, approved_at=now())
    db.add(order_set)
    db.flush()
    for index, item in enumerate(payload.items):
        db.add(OrderSetItem(order_set_id=order_set.id, orderable_code=item.orderable_code, sequence=index, selected_by_default=item.selected_by_default, required=item.required, default_priority=item.default_priority, default_indication=item.default_indication, default_instructions=item.default_instructions, details_json=json.dumps(item.details)))
    write_audit(db, action="CREATE_ORDER_SET", resource_type="OrderSet", resource_id=code, actor=admin.display_name, role=admin.role_code, details=payload.governance_reason)
    db.commit()
    return _order_set_payload(db, order_set)


class MessageCreateIn(BaseModel):
    recipient_user_id: str
    subject: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1, max_length=20000)
    priority: Literal["ROUTINE", "HIGH", "URGENT"] = "ROUTINE"
    patient_mpi_id: str | None = None
    encounter_id: str | None = None
    thread_id: str | None = None


class MessageActionIn(BaseModel):
    action: Literal["READ", "UNREAD", "ARCHIVE", "RESTORE"]


def _message_payload(db: Session, item: UserMessage) -> dict[str, Any]:
    sender = db.get(UserAccount, item.sender_user_id)
    recipient = db.get(UserAccount, item.recipient_user_id)
    patient = db.get(Patient, item.patient_id) if item.patient_id else None
    encounter = db.get(Encounter, item.encounter_id) if item.encounter_id else None
    return {
        "message_id": item.message_id,
        "thread_id": item.thread_id,
        "sender": {"user_id": sender.user_id, "display_name": sender.display_name} if sender else None,
        "recipient": {"user_id": recipient.user_id, "display_name": recipient.display_name} if recipient else None,
        "patient": {"mpi_id": patient.mpi_id, "mrn": patient.mrn, "full_name": patient.full_name} if patient else None,
        "encounter_id": encounter.encounter_id if encounter else None,
        "subject": item.subject,
        "body": item.body,
        "priority": item.priority,
        "status": item.status,
        "sent_at": item.sent_at,
        "read_at": item.read_at,
        "archived_at": item.archived_at,
    }


@router.get("/messages/recipients")
def message_recipients(db: Session = Depends(get_db)):
    users = list(db.scalars(select(UserAccount).where(UserAccount.active.is_(True)).order_by(UserAccount.display_name)).all())
    return [{"user_id": u.user_id, "username": u.username, "display_name": u.display_name, "role_code": u.role_code, "facility_code": u.facility_code} for u in users]


@router.get("/messages")
def messages(
    folder: Literal["INBOX", "SENT", "ARCHIVED"] = "INBOX",
    unread_only: bool = False,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: UserAccount | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    if not user:
        user = db.scalar(select(UserAccount).where(UserAccount.username == "admin"))
    if not user:
        return {"unread": 0, "items": []}
    if folder == "SENT":
        query = select(UserMessage).where(UserMessage.sender_user_id == user.id, UserMessage.archived_at.is_(None))
    elif folder == "ARCHIVED":
        query = select(UserMessage).where(UserMessage.recipient_user_id == user.id, UserMessage.archived_at.is_not(None))
    else:
        query = select(UserMessage).where(UserMessage.recipient_user_id == user.id, UserMessage.archived_at.is_(None))
    if unread_only:
        query = query.where(UserMessage.status == "UNREAD")
    if search:
        needle = f"%{search.lower().strip()}%"
        query = query.where(or_(func.lower(UserMessage.subject).like(needle), func.lower(UserMessage.body).like(needle)))
    items = list(db.scalars(query.order_by(UserMessage.sent_at.desc()).limit(limit)).all())
    unread = int(db.scalar(select(func.count(UserMessage.id)).where(UserMessage.recipient_user_id == user.id, UserMessage.status == "UNREAD", UserMessage.archived_at.is_(None))) or 0)
    return {"unread": unread, "items": [_message_payload(db, item) for item in items]}


@router.post("/messages", status_code=201)
def create_message(payload: MessageCreateIn, user: UserAccount | None = Depends(optional_user), db: Session = Depends(get_db)):
    sender = user or db.scalar(select(UserAccount).where(UserAccount.username == "admin"))
    recipient = db.scalar(select(UserAccount).where(UserAccount.user_id == payload.recipient_user_id, UserAccount.active.is_(True)))
    if not sender or not recipient:
        raise HTTPException(status_code=404, detail="Sender or recipient not found")
    patient = patient_by_mpi(db, payload.patient_mpi_id) if payload.patient_mpi_id else None
    encounter = encounter_by_public_id(db, payload.encounter_id) if payload.encounter_id else None
    if encounter and patient and encounter.patient_id != patient.id:
        raise HTTPException(status_code=409, detail="Encounter does not belong to selected patient")
    item = UserMessage(
        sender_user_id=sender.id,
        recipient_user_id=recipient.id,
        patient_id=patient.id if patient else None,
        encounter_id=encounter.id if encounter else None,
        subject=payload.subject.strip(),
        body=payload.body.strip(),
        priority=payload.priority,
        thread_id=payload.thread_id or None,
    )
    if not item.thread_id:
        item.thread_id = f"THREAD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    db.add(item)
    write_audit(db, action="SEND_MESSAGE", resource_type="UserMessage", resource_id=item.message_id, actor=sender.display_name, role=sender.role_code, patient_mpi_id=patient.mpi_id if patient else None, details=f"Recipient={recipient.display_name}; priority={payload.priority}")
    db.commit()
    return _message_payload(db, item)


@router.patch("/messages/{message_id}")
def update_message(message_id: str, payload: MessageActionIn, user: UserAccount | None = Depends(optional_user), db: Session = Depends(get_db)):
    item = db.scalar(select(UserMessage).where(UserMessage.message_id == message_id))
    if not item:
        raise HTTPException(status_code=404, detail="Message not found")
    if user and user.id not in {item.sender_user_id, item.recipient_user_id}:
        raise HTTPException(status_code=403, detail="Message is outside the current user's mailbox")
    if payload.action == "READ":
        item.status, item.read_at = "READ", now()
    elif payload.action == "UNREAD":
        item.status, item.read_at = "UNREAD", None
    elif payload.action == "ARCHIVE":
        item.archived_at = now()
    elif payload.action == "RESTORE":
        item.archived_at = None
    db.commit()
    return _message_payload(db, item)


def classify_unit(unit: str) -> dict[str, Any]:
    text = unit.upper()
    if any(term in text for term in ("EMERGENCY", "RESUSCITATION", "TRAUMA OBSERVATION", "ED ", "ER ")):
        return {"care_setting": "EMERGENCY", "care_setting_label": "Emergency / ED", "icon": "alert-triangle", "station_term": "care spaces"}
    if any(term in text for term in ("ICU", "INTENSIVE", "HDU", "HIGH DEPENDENCY", "NICU", "PICU")):
        return {"care_setting": "CRITICAL_CARE", "care_setting_label": "Critical Care", "icon": "activity", "station_term": "beds"}
    if any(term in text for term in ("MATERNITY", "POSTNATAL", "ANTENATAL", "LABOUR", "DELIVERY", "NEONATAL", "PAEDIATRIC")):
        return {"care_setting": "WOMEN_CHILDREN", "care_setting_label": "Women & Children", "icon": "users", "station_term": "beds"}
    if any(term in text for term in ("THEATRE", "PACU", "RECOVERY", "SURGICAL", "ORTHOPAEDIC", "NEURO", "BURNS", "SPINE")):
        return {"care_setting": "SURGICAL", "care_setting_label": "Surgical & Procedural", "icon": "scissors", "station_term": "beds / bays"}
    if any(term in text for term in ("DIALYSIS", "DAY CARE", "INFUSION", "CATH LAB")):
        return {"care_setting": "AMBULATORY_PROCEDURAL", "care_setting_label": "Procedural / Day Care", "icon": "droplet", "station_term": "stations"}
    if any(term in text for term in ("ISOLATION", "INFECTIOUS", "PROTECTIVE")):
        return {"care_setting": "ISOLATION", "care_setting_label": "Isolation", "icon": "shield", "station_term": "beds"}
    if any(term in text for term in ("PSYCHIATRY", "MENTAL HEALTH")):
        return {"care_setting": "MENTAL_HEALTH", "care_setting_label": "Mental Health", "icon": "heart", "station_term": "beds"}
    return {"care_setting": "INPATIENT", "care_setting_label": "Inpatient", "icon": "bed", "station_term": "beds"}


@router.get("/bed-units")
def bed_units(facility_code: str, db: Session = Depends(get_db)):
    facility = db.scalar(select(Facility).where(Facility.code == facility_code))
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    rows = db.execute(
        select(
            Bed.unit,
            func.count(Bed.id).label("total"),
            func.sum(case((Bed.status == "AVAILABLE", 1), else_=0)).label("available"),
            func.sum(case((Bed.status == "OCCUPIED", 1), else_=0)).label("occupied"),
            func.sum(case((Bed.status.in_(["DIRTY", "CLEANING"]), 1), else_=0)).label("turnover"),
            func.sum(case((Bed.status == "BLOCKED", 1), else_=0)).label("blocked"),
        ).where(Bed.facility_id == facility.id).group_by(Bed.unit).order_by(Bed.unit)
    ).all()
    output = []
    for unit, total, available, occupied, turnover, blocked in rows:
        classification = classify_unit(unit)
        output.append({
            "unit": unit,
            "unit_code": re.sub(r"[^A-Z0-9]+", "-", unit.upper()).strip("-"),
            "total": int(total or 0),
            "available": int(available or 0),
            "occupied": int(occupied or 0),
            "turnover": int(turnover or 0),
            "blocked": int(blocked or 0),
            "occupancy_percent": round((int(occupied or 0) / int(total or 1)) * 100, 1),
            **classification,
        })
    return output


@router.get("/unit-manager/overview")
def unit_manager_overview(facility_code: str, unit: str, db: Session = Depends(get_db)):
    facility = db.scalar(select(Facility).where(Facility.code == facility_code))
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    beds = list(db.scalars(select(Bed).where(Bed.facility_id == facility.id, Bed.unit == unit).order_by(Bed.room, Bed.bed_label)).all())
    if not beds:
        raise HTTPException(status_code=404, detail="Unit not found or no beds/stations configured")
    classification = classify_unit(unit)
    assigned_encounter_ids = {bed.encounter_id for bed in beds if bed.encounter_id}
    active_statuses = [EncounterStatus.ARRIVED, EncounterStatus.WAITING_REGISTRATION, EncounterStatus.REGISTERED, EncounterStatus.WAITING_TRIAGE, EncounterStatus.TRIAGED, EncounterStatus.READY_FOR_PROVIDER, EncounterStatus.ROOMED, EncounterStatus.IN_PROGRESS, EncounterStatus.WAITING_RESULTS, EncounterStatus.READY_FOR_DISCHARGE]
    encounters = list(db.scalars(select(Encounter).where(Encounter.facility_id == facility.id, Encounter.status.in_(active_statuses)).order_by(Encounter.arrival_at)).all())
    pending = []
    for encounter in encounters:
        if encounter.id in assigned_encounter_ids:
            continue
        location_text = f"{encounter.location or ''} {encounter.service or ''} {encounter.encounter_type or ''}".upper()
        emergency_match = classification["care_setting"] == "EMERGENCY" and any(term in location_text for term in ("EMERGENCY", "TRAUMA", "RESUS", "ED", "ER"))
        unit_match = unit.upper() in location_text or any(token and token in location_text for token in re.split(r"[^A-Z0-9]+", unit.upper()) if len(token) > 4)
        if emergency_match or unit_match or len(pending) < 6:
            patient = db.get(Patient, encounter.patient_id)
            pending.append({
                "encounter_id": encounter.encounter_id,
                "patient": {"mpi_id": patient.mpi_id, "mrn": patient.mrn, "full_name": patient.full_name} if patient else None,
                "status": encounter.status.value,
                "service": encounter.service,
                "location": encounter.location,
                "acuity": encounter.acuity,
                "arrival_at": encounter.arrival_at,
            })
        if len(pending) >= 12:
            break
    status_counts = {status: sum(1 for bed in beds if bed.status == status) for status in ("AVAILABLE", "ASSIGNED", "OCCUPIED", "DIRTY", "CLEANING", "BLOCKED")}
    bed_payload = []
    for bed in beds:
        encounter = db.get(Encounter, bed.encounter_id) if bed.encounter_id else None
        patient = db.get(Patient, encounter.patient_id) if encounter else None
        bed_payload.append({
            "bed_id": bed.bed_id, "room": bed.room, "bed_label": bed.bed_label, "bed_type": bed.bed_type, "status": bed.status, "isolation": bed.isolation,
            "encounter": {"encounter_id": encounter.encounter_id, "service": encounter.service, "status": encounter.status.value} if encounter else None,
            "patient": {"mpi_id": patient.mpi_id, "mrn": patient.mrn, "full_name": patient.full_name} if patient else None,
        })
    return {
        "facility": {"code": facility.code, "name": facility.name},
        "unit": {"name": unit, **classification},
        "summary": {"total": len(beds), **status_counts},
        "beds": bed_payload,
        "pending_assignments": pending,
    }


@router.get("/facilities/context-tree")
def facility_context_tree(
    search: str | None = None,
    region: str | None = None,
    hierarchy_level: str | None = None,
    public_only: bool = True,
    db: Session = Depends(get_db),
):
    query = select(Facility).where(Facility.active.is_(True))
    if public_only:
        query = query.where(Facility.ownership_category == "Public")
    if region:
        query = query.where(func.lower(Facility.region) == region.lower())
    if hierarchy_level:
        query = query.where(func.lower(Facility.hierarchy_level) == hierarchy_level.lower())
    if search:
        needle = f"%{search.lower().strip()}%"
        query = query.where(or_(func.lower(Facility.name).like(needle), func.lower(Facility.code).like(needle), func.lower(func.coalesce(Facility.hfr_code, "")).like(needle), func.lower(func.coalesce(Facility.region, "")).like(needle)))
    facilities = list(db.scalars(query.order_by(Facility.region, Facility.hierarchy_level, Facility.name)).all())
    groups: dict[str, list[dict[str, Any]]] = {}
    for facility in facilities:
        key = facility.region or "National / Multi-region"
        groups.setdefault(key, []).append({
            "code": facility.code,
            "hfr_code": facility.hfr_code,
            "name": facility.name,
            "facility_type": facility.facility_type,
            "region": facility.region,
            "council": facility.council,
            "hierarchy_level": facility.hierarchy_level,
            "ownership_category": facility.ownership_category,
            "ownership_authority": facility.ownership_authority,
            "relation": facility.relation,
            "source_system": facility.source_system,
        })
    return {"total": len(facilities), "groups": [{"region": key, "facilities": values} for key, values in groups.items()]}


class FacilityImportItem(BaseModel):
    code: str
    name: str
    facility_type: str
    hfr_code: str | None = None
    region: str | None = None
    council: str | None = None
    ownership_category: str = "Public"
    ownership_authority: str | None = None
    hierarchy_level: str | None = None
    parent_code: str | None = None
    relation: str = "Government health system"


class FacilityImportIn(BaseModel):
    facilities: list[FacilityImportItem] = Field(min_length=1, max_length=20000)
    actor: str = "ICT Administrator"
    source_system: str = "Tanzania HFR import"
    grant_to_system_admins: bool = True


@router.post("/facilities/import-hfr")
def import_hfr(payload: FacilityImportIn, db: Session = Depends(get_db)):
    inserted = updated = 0
    imported_codes: list[str] = []
    for row in payload.facilities:
        item = db.scalar(select(Facility).where(or_(Facility.code == row.code, Facility.hfr_code == row.hfr_code if row.hfr_code else False)))
        if not item:
            item = Facility(code=row.code, name=row.name, facility_type=row.facility_type, relation=row.relation)
            db.add(item)
            inserted += 1
        else:
            updated += 1
        for field in ("name", "facility_type", "hfr_code", "region", "council", "ownership_category", "ownership_authority", "hierarchy_level", "parent_code", "relation"):
            setattr(item, field, getattr(row, field))
        item.source_system = payload.source_system
        item.active = True
        imported_codes.append(item.code)
    db.flush()
    admin_grants = 0
    if payload.grant_to_system_admins and imported_codes:
        administrators = list(db.scalars(select(UserAccount).where(UserAccount.role_code == "admin", UserAccount.active.is_(True))).all())
        for administrator in administrators:
            existing = set(db.scalars(select(UserAccessGrant.scope_code).where(UserAccessGrant.user_account_id == administrator.id, UserAccessGrant.scope_type == "FACILITY")).all())
            for code in imported_codes:
                if code not in existing:
                    db.add(UserAccessGrant(user_account_id=administrator.id, scope_type="FACILITY", scope_code=code, active=True, granted_by=payload.actor, reason=f"HFR facility import: {payload.source_system}"))
                    admin_grants += 1
    write_audit(db, action="IMPORT_HFR_FACILITIES", resource_type="Facility", resource_id="BULK", actor=payload.actor, role="system.configuration.manage", details=f"inserted={inserted}; updated={updated}; source={payload.source_system}")
    db.commit()
    return {"inserted": inserted, "updated": updated, "total_processed": inserted + updated, "system_admin_facility_grants": admin_grants}


class ExpirePatientIn(BaseModel):
    deceased_at: datetime
    location: str
    cause: str | None = None
    death_certificate_number: str | None = None
    actor: str = "Clinician"
    disposition: str = "Expired"
    notify_mortuary: bool = True


class UndoIn(BaseModel):
    actor: str = "ICT Administrator"
    reason: str = Field(min_length=3, max_length=4000)


@router.post("/patients/{mpi_id}/expire")
def expire_patient(mpi_id: str, payload: ExpirePatientIn, db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, mpi_id)
    if patient.record_status == "DECEASED":
        raise HTTPException(status_code=409, detail="Patient is already recorded as deceased")
    before = patient.record_status
    patient.record_status = "DECEASED"
    patient.deceased_at = payload.deceased_at
    patient.deceased_location = payload.location
    patient.deceased_cause = payload.cause
    patient.death_certificate_number = payload.death_certificate_number
    patient.expired_by = payload.actor
    active_encounters = list(db.scalars(select(Encounter).where(Encounter.patient_id == patient.id, Encounter.status.not_in([EncounterStatus.DISCHARGED, EncounterStatus.TRANSFERRED]))).all())
    for encounter in active_encounters:
        encounter.status = EncounterStatus.DISCHARGED
        encounter.discharge_at = payload.deceased_at
        encounter.discharge_disposition = payload.disposition
        encounter.discharge_summary = f"Death recorded at {payload.location}. Cause: {payload.cause or 'Pending certification'}."
    if payload.notify_mortuary:
        db.add(WorkItem(queue="MORTUARY_AND_DEATH_REGISTRATION", task_type="PATIENT_EXPIRY", subject=f"Complete death documentation for {patient.full_name}", patient_id=patient.id, encounter_id=active_encounters[0].id if active_encounters else None, details=f"Location: {payload.location}; certificate: {payload.death_certificate_number or 'pending'}", priority="HIGH", status="OPEN", assigned_to="Mortuary / Health Records", created_by=payload.actor))
    event = record_managed_event(db, entity_type="PATIENT", entity_id=patient.mpi_id, action="EXPIRE_PATIENT", actor=payload.actor, status_before=before, status_after="DECEASED", patient_id=patient.id, encounter_id=active_encounters[0].id if active_encounters else None, reason=payload.cause, reversible=True, metadata={"deceased_at": payload.deceased_at, "location": payload.location, "death_certificate_number": payload.death_certificate_number, "encounters_closed": [e.encounter_id for e in active_encounters]})
    write_audit(db, action="EXPIRE_PATIENT", resource_type="Patient", resource_id=patient.mpi_id, actor=payload.actor, role="clinical.patient_status.manage", patient_mpi_id=patient.mpi_id, details=f"Location={payload.location}; event={event.event_id}")
    db.commit()
    return {"mpi_id": patient.mpi_id, "record_status": patient.record_status, "deceased_at": patient.deceased_at, "event_id": event.event_id, "encounters_closed": [e.encounter_id for e in active_encounters]}


@router.get("/event-management")
def event_management(
    patient_mpi_id: str | None = None,
    entity_type: str | None = None,
    reversible_only: bool = False,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = select(ManagedEvent)
    if patient_mpi_id:
        patient = patient_by_mpi(db, patient_mpi_id)
        query = query.where(ManagedEvent.patient_id == patient.id)
    if entity_type:
        query = query.where(ManagedEvent.entity_type == entity_type.upper())
    if reversible_only:
        query = query.where(ManagedEvent.reversible.is_(True), ManagedEvent.reversed_by_event_id.is_(None))
    items = list(db.scalars(query.order_by(ManagedEvent.occurred_at.desc()).limit(limit)).all())
    output = []
    for item in items:
        patient = db.get(Patient, item.patient_id) if item.patient_id else None
        encounter = db.get(Encounter, item.encounter_id) if item.encounter_id else None
        output.append({
            "event_id": item.event_id,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "patient": {"mpi_id": patient.mpi_id, "mrn": patient.mrn, "full_name": patient.full_name} if patient else None,
            "encounter_id": encounter.encounter_id if encounter else None,
            "action": item.action,
            "status_before": item.status_before,
            "status_after": item.status_after,
            "actor": item.actor,
            "reason": item.reason,
            "reversible": item.reversible,
            "reversed_by_event_id": item.reversed_by_event_id,
            "occurred_at": item.occurred_at,
            "metadata": json.loads(item.metadata_json or "{}"),
        })
    return output


@router.post("/event-management/{event_id}/undo")
def undo_event(event_id: str, payload: UndoIn, db: Session = Depends(get_db)):
    item = db.scalar(select(ManagedEvent).where(ManagedEvent.event_id == event_id))
    if not item:
        raise HTTPException(status_code=404, detail="Event not found")
    if not item.reversible or item.reversed_by_event_id:
        raise HTTPException(status_code=409, detail="Event is not available for reversal")
    metadata = json.loads(item.metadata_json or "{}")
    if item.entity_type == "PATIENT" and item.action == "EXPIRE_PATIENT":
        patient = db.get(Patient, item.patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        patient.record_status = item.status_before or "ACTIVE"
        patient.deceased_at = None
        patient.deceased_location = None
        patient.deceased_cause = None
        patient.death_certificate_number = None
        patient.expired_by = None
    elif item.entity_type == "ORDER":
        order = db.scalar(select(Order).where(Order.order_id == item.entity_id))
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order.status = item.status_before or order.status
        db.add(OrderStatusEvent(order_id=order.id, action="UNDO", status_before=item.status_after or "", status_after=order.status, reason=payload.reason, actor=payload.actor))
    elif item.entity_type == "APPOINTMENT":
        appointment = db.scalar(select(Appointment).where(Appointment.appointment_id == item.entity_id))
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        appointment.status = item.status_before or appointment.status
        db.add(AppointmentStatusEvent(appointment_id=appointment.id, status_before=item.status_after or "", status_after=appointment.status, reason=payload.reason, actor=payload.actor))
    elif item.entity_type == "ENCOUNTER":
        encounter = db.scalar(select(Encounter).where(Encounter.encounter_id == item.entity_id))
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        try:
            encounter.status = EncounterStatus(item.status_before) if item.status_before else encounter.status
        except ValueError as exc:
            raise HTTPException(status_code=409, detail="Original encounter state cannot be restored") from exc
    else:
        raise HTTPException(status_code=422, detail="This event type does not have an automated reversal handler")
    reversal = record_managed_event(db, entity_type=item.entity_type, entity_id=item.entity_id, action="UNDO", actor=payload.actor, status_before=item.status_after, status_after=item.status_before, patient_id=item.patient_id, encounter_id=item.encounter_id, reason=payload.reason, reversible=False, metadata={"reverses_event_id": item.event_id, "original_metadata": metadata})
    item.reversed_by_event_id = reversal.event_id
    write_audit(db, action="UNDO_EVENT", resource_type=item.entity_type, resource_id=item.entity_id, actor=payload.actor, role="event.management", details=f"Original event={item.event_id}; reason={payload.reason}")
    db.commit()
    return {"event_id": item.event_id, "reversed_by_event_id": reversal.event_id, "status_restored": item.status_before}


class DeviceEndpointIn(BaseModel):
    facility_code: str
    unit: str
    room: str | None = None
    bed_label: str | None = None
    name: str
    device_type: str
    manufacturer: str | None = None
    model: str | None = None
    protocol: str = "FHIR_OBSERVATION"


class ReadingIn(BaseModel):
    parameter_code: str
    parameter_name: str
    numeric_value: float | None = None
    text_value: str | None = None
    unit: str | None = None
    quality: str = "VALID"
    recorded_at: datetime | None = None
    source_message_id: str | None = None


class DeviceReadingsIn(BaseModel):
    patient_mpi_id: str
    encounter_id: str
    flowsheet_id: str | None = None
    readings: list[ReadingIn] = Field(min_length=1, max_length=500)
    actor: str = "Device Integration Engine"


@router.get("/devices")
def devices(facility_code: str | None = None, unit: str | None = None, db: Session = Depends(get_db)):
    query = select(DeviceEndpoint)
    if facility_code:
        query = query.where(DeviceEndpoint.facility_code == facility_code)
    if unit:
        query = query.where(DeviceEndpoint.unit == unit)
    items = list(db.scalars(query.order_by(DeviceEndpoint.facility_code, DeviceEndpoint.unit, DeviceEndpoint.name)).all())
    return [{"device_id": x.device_id, "facility_code": x.facility_code, "unit": x.unit, "room": x.room, "bed_label": x.bed_label, "name": x.name, "device_type": x.device_type, "manufacturer": x.manufacturer, "model": x.model, "protocol": x.protocol, "status": x.status, "last_seen_at": x.last_seen_at, "active": x.active} for x in items]


@router.post("/devices", status_code=201)
def create_device(payload: DeviceEndpointIn, db: Session = Depends(get_db)):
    if not db.scalar(select(Facility).where(Facility.code == payload.facility_code)):
        raise HTTPException(status_code=404, detail="Facility not found")
    item = DeviceEndpoint(**payload.model_dump())
    db.add(item)
    db.commit()
    return {"device_id": item.device_id, **payload.model_dump(), "status": item.status}


@router.post("/devices/{device_id}/observations", status_code=201)
def ingest_device_observations(device_id: str, payload: DeviceReadingsIn, db: Session = Depends(get_db)):
    device = db.scalar(select(DeviceEndpoint).where(DeviceEndpoint.device_id == device_id, DeviceEndpoint.active.is_(True)))
    if not device:
        raise HTTPException(status_code=404, detail="Device endpoint not found")
    patient = patient_by_mpi(db, payload.patient_mpi_id)
    encounter = encounter_by_public_id(db, payload.encounter_id)
    if encounter.patient_id != patient.id:
        raise HTTPException(status_code=409, detail="Encounter does not belong to selected patient")
    flowsheet = None
    if payload.flowsheet_id:
        flowsheet = db.scalar(select(FlowSheet).where(FlowSheet.flowsheet_id == payload.flowsheet_id, FlowSheet.patient_id == patient.id))
        if not flowsheet:
            raise HTTPException(status_code=404, detail="Flowsheet not found for selected patient")
    created = []
    for reading in payload.readings:
        item = DeviceReading(device_endpoint_id=device.id, patient_id=patient.id, encounter_id=encounter.id, flowsheet_id=flowsheet.id if flowsheet else None, parameter_code=reading.parameter_code, parameter_name=reading.parameter_name, numeric_value=reading.numeric_value, text_value=reading.text_value, unit=reading.unit, quality=reading.quality, source_message_id=reading.source_message_id, recorded_at=reading.recorded_at or now())
        db.add(item)
        if flowsheet:
            value = str(reading.numeric_value) if reading.numeric_value is not None else str(reading.text_value or "")
            db.add(FlowSheetObservation(flowsheet_id=flowsheet.id, parameter=reading.parameter_name, value=value, unit=reading.unit, source=f"DEVICE:{device.device_id}", recorded_by=payload.actor, recorded_at=reading.recorded_at or now()))
        created.append(item)
    device.last_seen_at = now()
    device.status = "ONLINE"
    write_audit(db, action="INGEST_DEVICE_OBSERVATIONS", resource_type="DeviceEndpoint", resource_id=device.device_id, actor=payload.actor, role="interface.device_ingest", patient_mpi_id=patient.mpi_id, facility_code=device.facility_code, details=f"readings={len(created)}; encounter={encounter.encounter_id}; flowsheet={payload.flowsheet_id or 'none'}")
    db.commit()
    return {"device_id": device.device_id, "patient_mpi_id": patient.mpi_id, "encounter_id": encounter.encounter_id, "flowsheet_id": payload.flowsheet_id, "readings_created": len(created)}


@router.get("/device-readings")
def device_readings(patient_mpi_id: str, encounter_id: str | None = None, limit: int = Query(default=500, ge=1, le=5000), db: Session = Depends(get_db)):
    patient = patient_by_mpi(db, patient_mpi_id)
    query = select(DeviceReading, DeviceEndpoint).join(DeviceEndpoint, DeviceReading.device_endpoint_id == DeviceEndpoint.id).where(DeviceReading.patient_id == patient.id)
    if encounter_id:
        encounter = encounter_by_public_id(db, encounter_id)
        query = query.where(DeviceReading.encounter_id == encounter.id)
    rows = db.execute(query.order_by(DeviceReading.recorded_at.desc()).limit(limit)).all()
    return [{"reading_id": r.reading_id, "device_id": d.device_id, "device_name": d.name, "device_type": d.device_type, "parameter_code": r.parameter_code, "parameter_name": r.parameter_name, "numeric_value": r.numeric_value, "text_value": r.text_value, "unit": r.unit, "quality": r.quality, "recorded_at": r.recorded_at, "received_at": r.received_at} for r, d in rows]


@router.get("/flowsheet-template-library")
def flowsheet_templates():
    path = PROJECT_ROOT / "config" / "flowsheet-templates.yml"
    if not path.exists():
        raise HTTPException(status_code=500, detail="Flowsheet template configuration is missing")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    templates = data.get("templates", data if isinstance(data, list) else [])
    return {"templates": templates}


@router.get("/emergency/board")
def emergency_board(facility_code: str, db: Session = Depends(get_db)):
    facility = db.scalar(select(Facility).where(Facility.code == facility_code))
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    statuses = [EncounterStatus.ARRIVED, EncounterStatus.WAITING_TRIAGE, EncounterStatus.TRIAGED, EncounterStatus.READY_FOR_PROVIDER, EncounterStatus.ROOMED, EncounterStatus.IN_PROGRESS, EncounterStatus.WAITING_RESULTS, EncounterStatus.READY_FOR_DISCHARGE]
    encounters = list(db.scalars(select(Encounter).options(selectinload(Encounter.patient)).where(Encounter.facility_id == facility.id, Encounter.status.in_(statuses), or_(func.upper(Encounter.encounter_type) == "EMERGENCY", func.lower(Encounter.service).like("%emerg%"), func.lower(Encounter.service).like("%trauma%"))).order_by(Encounter.arrival_at)).all())
    columns = {"ARRIVAL": [], "TRIAGE": [], "RESUSCITATION": [], "CARE_IN_PROGRESS": [], "DISPOSITION": []}
    for e in encounters:
        key = "ARRIVAL" if e.status in {EncounterStatus.ARRIVED, EncounterStatus.WAITING_REGISTRATION, EncounterStatus.REGISTERED} else "TRIAGE" if e.status in {EncounterStatus.WAITING_TRIAGE, EncounterStatus.TRIAGED} else "RESUSCITATION" if str(e.acuity).upper() in {"CRITICAL", "RED", "1"} and e.status in {EncounterStatus.READY_FOR_PROVIDER, EncounterStatus.ROOMED, EncounterStatus.IN_PROGRESS} else "DISPOSITION" if e.status in {EncounterStatus.WAITING_RESULTS, EncounterStatus.READY_FOR_DISCHARGE} else "CARE_IN_PROGRESS"
        columns[key].append({"encounter_id": e.encounter_id, "patient": {"mpi_id": e.patient.mpi_id, "mrn": e.patient.mrn, "full_name": e.patient.full_name, "sex": e.patient.sex}, "status": e.status, "acuity": e.acuity, "location": e.location, "room": e.room, "provider": e.provider, "reason_for_visit": e.reason_for_visit, "arrival_at": e.arrival_at})
    return {"facility": {"code": facility.code, "name": facility.name}, "columns": columns, "counts": {key: len(values) for key, values in columns.items()}}


class EmergencyEventIn(BaseModel):
    action: Literal["TRIAGE", "TRAUMA_ACTIVATION", "MOVE_TO_RESUS", "START_CARE", "WAITING_RESULTS", "READY_FOR_DISPOSITION", "ADMIT", "TRANSFER", "DISCHARGE", "LEFT_WITHOUT_BEING_SEEN", "UNDO_LAST"]
    actor: str
    acuity: str | None = None
    location: str | None = None
    provider: str | None = None
    note: str | None = None


@router.post("/emergency/encounters/{encounter_id}/events")
def emergency_event(encounter_id: str, payload: EmergencyEventIn, db: Session = Depends(get_db)):
    encounter = db.scalar(select(Encounter).options(selectinload(Encounter.patient), selectinload(Encounter.facility)).where(Encounter.encounter_id == encounter_id))
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    before = encounter.status.value
    mapping = {
        "TRIAGE": EncounterStatus.TRIAGED,
        "TRAUMA_ACTIVATION": EncounterStatus.READY_FOR_PROVIDER,
        "MOVE_TO_RESUS": EncounterStatus.ROOMED,
        "START_CARE": EncounterStatus.IN_PROGRESS,
        "WAITING_RESULTS": EncounterStatus.WAITING_RESULTS,
        "READY_FOR_DISPOSITION": EncounterStatus.READY_FOR_DISCHARGE,
        "ADMIT": EncounterStatus.TRANSFERRED,
        "TRANSFER": EncounterStatus.TRANSFERRED,
        "DISCHARGE": EncounterStatus.DISCHARGED,
        "LEFT_WITHOUT_BEING_SEEN": EncounterStatus.LEFT_WITHOUT_BEING_SEEN,
    }
    if payload.action == "UNDO_LAST":
        previous = db.scalar(select(ManagedEvent).where(ManagedEvent.entity_type == "ENCOUNTER", ManagedEvent.entity_id == encounter.encounter_id, ManagedEvent.reversible.is_(True), ManagedEvent.reversed_by_event_id.is_(None)).order_by(ManagedEvent.occurred_at.desc()))
        if not previous or not previous.status_before:
            raise HTTPException(status_code=409, detail="No reversible emergency event is available")
        encounter.status = EncounterStatus(previous.status_before)
        previous.reversed_by_event_id = record_managed_event(db, entity_type="ENCOUNTER", entity_id=encounter.encounter_id, action="UNDO", actor=payload.actor, status_before=before, status_after=previous.status_before, patient_id=encounter.patient_id, encounter_id=encounter.id, reason=payload.note or "Undo last emergency event", reversible=False).event_id
    else:
        encounter.status = mapping[payload.action]
        if payload.acuity:
            encounter.acuity = payload.acuity
        if payload.location:
            encounter.location = payload.location
        if payload.provider:
            encounter.provider = payload.provider
        if payload.action == "TRIAGE":
            encounter.triage_at = now()
        if payload.action in {"START_CARE", "TRAUMA_ACTIVATION", "MOVE_TO_RESUS"} and not encounter.provider_start_at:
            encounter.provider_start_at = now()
        if payload.action in {"DISCHARGE", "LEFT_WITHOUT_BEING_SEEN"}:
            encounter.discharge_at = now()
            encounter.discharge_disposition = "Discharged from ED" if payload.action == "DISCHARGE" else "Left without being seen"
        record_managed_event(db, entity_type="ENCOUNTER", entity_id=encounter.encounter_id, action=f"ED_{payload.action}", actor=payload.actor, status_before=before, status_after=encounter.status.value, patient_id=encounter.patient_id, encounter_id=encounter.id, reason=payload.note, reversible=True, metadata={"acuity": encounter.acuity, "location": encounter.location})
    write_audit(db, action=f"ED_{payload.action}", resource_type="Encounter", resource_id=encounter.encounter_id, actor=payload.actor, role="emergency.manage", patient_mpi_id=encounter.patient.mpi_id, facility_code=encounter.facility.code, details=payload.note)
    db.commit()
    return {"encounter_id": encounter.encounter_id, "status": encounter.status, "acuity": encounter.acuity, "location": encounter.location}


@router.get("/specialty-workflows")
def specialty_workflows():
    return {
        "workflows": [
            {"code": "GENERAL_MEDICINE", "name": "General Medicine", "stages": ["Assessment", "Problem List", "Orders", "Results", "Treatment", "Discharge"]},
            {"code": "SURGERY", "name": "Surgery", "stages": ["Consult", "Pre-op Readiness", "Case Booking", "Theatre", "PACU", "Post-op", "Discharge"]},
            {"code": "ORTHO_TRAUMA", "name": "Orthopaedics / Trauma / Neurosurgery", "stages": ["Trauma Activation", "Neurovascular Assessment", "Imaging", "Implant Planning", "Theatre", "Rehabilitation", "Outcome"]},
            {"code": "CARDIOLOGY", "name": "Cardiology / Cardiac Surgery", "stages": ["Triage", "ECG/Echo", "Cath Lab", "Hemodynamics", "Intervention", "Cardiac ICU", "Rehabilitation"]},
            {"code": "ONCOLOGY", "name": "Oncology", "stages": ["Diagnosis", "Staging", "Tumour Board", "Protocol", "Chemo/RT", "Toxicity", "Survivorship/Palliative"]},
            {"code": "MATERNITY", "name": "Maternity & Newborn", "stages": ["ANC", "Risk Assessment", "Labour/Partograph", "Delivery", "Newborn", "PNC", "Immunization"]},
            {"code": "PAEDIATRICS", "name": "Paediatrics", "stages": ["Triage", "Growth/Nutrition", "IMCI", "Orders", "Medication", "Immunization", "Follow-up"]},
            {"code": "CRITICAL_CARE", "name": "Critical Care", "stages": ["Admission", "Device Integration", "Hourly Flowsheet", "Ventilation", "Infusions", "Rounds", "Transfer"]},
            {"code": "RENAL", "name": "Renal & Dialysis", "stages": ["Assessment", "Access", "Prescription", "Pre-dialysis", "Treatment", "Post-dialysis", "Follow-up"]},
            {"code": "MENTAL_HEALTH", "name": "Mental Health", "stages": ["Risk Assessment", "Mental State Exam", "Care Plan", "Medication", "Therapy", "Observation", "Discharge"]},
            {"code": "DENTAL", "name": "Dental", "stages": ["Assessment", "Imaging", "Treatment Plan", "Procedure", "Medication", "Follow-up"]},
        ]
    }
