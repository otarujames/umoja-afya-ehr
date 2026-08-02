from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..audit import write_audit
from ..database import get_db
from ..enhancement_models import OrderCatalogItem
from ..event_management import record_managed_event
from ..models import Encounter, EncounterStatus, Order, OrderStatusEvent, Patient, Result
from ..schemas import AcknowledgeIn, OrderActionIn, OrderBatchIn, OrderIn
from ..serializers import order_dict, result_dict

router = APIRouter(tags=["Orders and Results"])

CLOSED_ENCOUNTER_STATUSES = {
    EncounterStatus.DISCHARGED,
    EncounterStatus.TRANSFERRED,
    EncounterStatus.LEFT_WITHOUT_BEING_SEEN,
}


def _prepare_order(db: Session, payload: OrderIn) -> tuple[Order, OrderCatalogItem | None, Encounter]:
    encounter = db.scalar(
        select(Encounter)
        .options(selectinload(Encounter.patient), selectinload(Encounter.facility))
        .where(Encounter.encounter_id == payload.encounter_id)
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if encounter.status in CLOSED_ENCOUNTER_STATUSES:
        raise HTTPException(status_code=409, detail="New orders must be placed in an active encounter; historical encounters are review-only")
    if encounter.patient.record_status == "DECEASED":
        raise HTTPException(status_code=409, detail="New orders cannot be placed on a deceased patient record")

    catalog_item = None
    if payload.orderable_code:
        catalog_item = db.scalar(
            select(OrderCatalogItem).where(
                OrderCatalogItem.orderable_code == payload.orderable_code,
                OrderCatalogItem.active.is_(True),
            )
        )
        if not catalog_item:
            raise HTTPException(status_code=404, detail="Orderable not found in active order catalog")
    if not catalog_item and not ((payload.order_type or "").strip() and (payload.order_name or "").strip()):
        raise HTTPException(status_code=422, detail="Select an approved orderable from the catalog")

    order_type = catalog_item.category if catalog_item else payload.order_type.strip().upper()
    order_name = catalog_item.display_name if catalog_item else payload.order_name.strip()
    priority = (payload.priority or (catalog_item.default_priority if catalog_item else "ROUTINE")).upper()
    if priority not in {"ROUTINE", "URGENT", "STAT"}:
        raise HTTPException(status_code=422, detail="Priority must be ROUTINE, URGENT or STAT")
    indication = (payload.indication or "").strip() or None
    if catalog_item and catalog_item.requires_reason and not indication:
        raise HTTPException(status_code=422, detail="This orderable requires a clinical or operational reason")
    instructions = (payload.instructions or (catalog_item.default_instructions if catalog_item else None) or "").strip() or None
    details = dict(payload.details or {})
    if catalog_item:
        if catalog_item.route and not details.get("route"):
            details["route"] = catalog_item.route
        if catalog_item.specimen and not details.get("specimen"):
            details["specimen"] = catalog_item.specimen
        if catalog_item.units and not details.get("units"):
            details["units"] = catalog_item.units
    if order_type == "MEDICATION":
        missing = [name for name in ("dose", "route", "frequency") if not str(details.get(name) or "").strip()]
        if missing:
            raise HTTPException(status_code=422, detail=f"Medication order requires: {', '.join(missing)}")
    details_json = json.dumps(details, separators=(",", ":"), ensure_ascii=False)
    if len(details_json.encode("utf-8")) > 20000:
        raise HTTPException(status_code=422, detail="Structured order details exceed the 20 KB limit")

    order = Order(
        encounter=encounter,
        order_type=order_type,
        order_name=order_name,
        orderable_code=catalog_item.orderable_code if catalog_item else None,
        priority=priority,
        indication=indication,
        instructions=instructions,
        details_json=details_json,
        ordered_by=payload.ordered_by,
    )
    db.add(order)
    db.flush()
    reason = indication or instructions or "Approved order entry"
    db.add(OrderStatusEvent(order_id=order.id, action="CREATE", status_before="NONE", status_after=order.status, reason=reason, actor=payload.ordered_by))
    record_managed_event(
        db,
        entity_type="ORDER",
        entity_id=order.order_id,
        action="CREATE",
        actor=payload.ordered_by,
        status_before="NONE",
        status_after=order.status,
        patient_id=encounter.patient_id,
        encounter_id=encounter.id,
        reason=reason,
        reversible=True,
        metadata={
            "orderable_code": catalog_item.orderable_code if catalog_item else None,
            "category": order_type,
            "clinical": catalog_item.clinical if catalog_item else True,
            "details": details,
        },
    )
    write_audit(
        db,
        action="SIGN_ORDER",
        resource_type="Order",
        resource_id=order.order_id,
        actor=payload.ordered_by,
        role="Provider",
        patient_mpi_id=encounter.patient.mpi_id,
        facility_code=encounter.facility.code,
        details=f"{priority} {order_type}: {order_name}",
    )
    return order, catalog_item, encounter


@router.get("/orders")
def list_orders(patient_mpi_id: str = Query(..., min_length=3), db: Session = Depends(get_db)):
    patient = db.scalar(select(Patient).where(Patient.mpi_id == patient_mpi_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    query = select(Order).options(selectinload(Order.encounter).selectinload(Encounter.patient)).join(Encounter).where(Encounter.patient_id == patient.id)
    orders = list(db.scalars(query.order_by(Order.ordered_at.desc())).all())
    output = []
    for item in orders:
        payload = order_dict(item)
        events = list(db.scalars(select(OrderStatusEvent).where(OrderStatusEvent.order_id == item.id).order_by(OrderStatusEvent.occurred_at.desc())).all())
        payload["history"] = [{"event_id": event.event_id, "action": event.action, "status_before": event.status_before, "status_after": event.status_after, "reason": event.reason, "actor": event.actor, "occurred_at": event.occurred_at} for event in events]
        output.append(payload)
    return output


@router.post("/orders", status_code=201)
def create_order(payload: OrderIn, db: Session = Depends(get_db)):
    order, _, _ = _prepare_order(db, payload)
    db.commit()
    db.refresh(order)
    return order_dict(order)


@router.post("/orders/batch", status_code=201)
def create_order_batch(payload: OrderBatchIn, db: Session = Depends(get_db)):
    encounter_ids = {item.encounter_id for item in payload.orders}
    if len(encounter_ids) != 1:
        raise HTTPException(status_code=422, detail="One signing batch must belong to one encounter")
    created: list[Order] = []
    try:
        for item in payload.orders:
            order, _, _ = _prepare_order(db, item)
            created.append(order)
        first = created[0]
        write_audit(
            db,
            action="SIGN_ORDER_BATCH",
            resource_type="Encounter",
            resource_id=first.encounter.encounter_id,
            actor=first.ordered_by,
            role="Provider",
            patient_mpi_id=first.encounter.patient.mpi_id,
            facility_code=first.encounter.facility.code,
            details=f"count={len(created)}; order_set={payload.order_set_code or 'none'}; attestation={payload.sign_reason or 'not supplied'}",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    for order in created:
        db.refresh(order)
    return {
        "count": len(created),
        "order_set_code": payload.order_set_code,
        "orders": [order_dict(order) for order in created],
    }


@router.post("/orders/{order_id}/actions")
def change_order_course(order_id: str, payload: OrderActionIn, db: Session = Depends(get_db)):
    order = db.scalar(select(Order).options(selectinload(Order.encounter).selectinload(Encounter.patient), selectinload(Order.encounter).selectinload(Encounter.facility)).where(Order.order_id == order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    current = order.status.upper()
    transitions = {
        "HOLD": ({"SIGNED", "SCHEDULED", "COLLECTED", "READY", "IN_PROGRESS"}, "ON_HOLD"),
        "RESUME": ({"ON_HOLD"}, "SIGNED"),
        "CANCEL": ({"SIGNED", "SCHEDULED", "COLLECTED", "READY", "IN_PROGRESS", "ON_HOLD"}, "CANCELLED"),
        "REINSTATE": ({"CANCELLED"}, "SIGNED"),
    }
    if payload.action not in transitions:
        raise HTTPException(status_code=422, detail="Unsupported order action")
    allowed_from, next_status = transitions[payload.action]
    if current not in allowed_from:
        raise HTTPException(status_code=409, detail=f"Cannot {payload.action.lower()} an order in {current} status")
    order.status = next_status
    event = OrderStatusEvent(order_id=order.id, action=payload.action, status_before=current, status_after=next_status, reason=payload.reason, actor=payload.actor)
    db.add(event)
    db.flush()
    record_managed_event(db, entity_type="ORDER", entity_id=order.order_id, action=payload.action, actor=payload.actor, status_before=current, status_after=next_status, patient_id=order.encounter.patient_id, encounter_id=order.encounter.id, reason=payload.reason, reversible=True)
    write_audit(db, action=f"ORDER_{payload.action}", resource_type="Order", resource_id=order.order_id, actor=payload.actor, role="Provider", patient_mpi_id=order.encounter.patient.mpi_id, facility_code=order.encounter.facility.code, details=payload.reason)
    db.commit()
    result = order_dict(order)
    result["latest_event"] = {"event_id": event.event_id, "action": event.action, "status_before": event.status_before, "status_after": event.status_after, "reason": event.reason, "actor": event.actor, "occurred_at": event.occurred_at}
    return result


@router.get("/results")
def list_results(patient_mpi_id: str = Query(..., min_length=3), critical_only: bool = Query(default=False), db: Session = Depends(get_db)):
    patient = db.scalar(select(Patient).where(Patient.mpi_id == patient_mpi_id))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    query = select(Result, Patient).join(Patient, Result.patient_id == Patient.id).where(Patient.id == patient.id)
    if critical_only:
        query = query.where(Result.flag == "CRITICAL")
    rows = db.execute(query.order_by(Result.issued_at.desc())).all()
    return [result_dict(result, patient) for result, patient in rows]


@router.post("/results/{result_id}/acknowledge")
def acknowledge_result(result_id: str, payload: AcknowledgeIn, db: Session = Depends(get_db)):
    row = db.execute(select(Result, Patient).join(Patient, Result.patient_id == Patient.id).where(Result.result_id == result_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Result not found")
    result, patient = row
    result.acknowledged = True
    result.acknowledged_by = payload.actor
    result.acknowledged_at = datetime.now(timezone.utc)
    write_audit(db, action="ACKNOWLEDGE_RESULT", resource_type="Result", resource_id=result.result_id, actor=payload.actor, role="Provider", patient_mpi_id=patient.mpi_id, details=payload.action_taken)
    db.commit()
    return result_dict(result, patient)
