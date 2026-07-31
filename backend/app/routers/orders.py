from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..audit import write_audit
from ..database import get_db
from ..enhancement_models import OrderCatalogItem
from ..event_management import record_managed_event
from ..models import Encounter, Order, OrderStatusEvent, Patient, Result
from ..schemas import AcknowledgeIn, OrderActionIn, OrderIn
from ..serializers import order_dict, result_dict

router = APIRouter(tags=["Orders and Results"])


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
    encounter = db.scalar(select(Encounter).options(selectinload(Encounter.patient), selectinload(Encounter.facility)).where(Encounter.encounter_id == payload.encounter_id))
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    if encounter.patient.record_status == "DECEASED":
        raise HTTPException(status_code=409, detail="New orders cannot be placed on a deceased patient record")
    catalog_item = None
    if payload.orderable_code:
        catalog_item = db.scalar(select(OrderCatalogItem).where(OrderCatalogItem.orderable_code == payload.orderable_code, OrderCatalogItem.active.is_(True)))
        if not catalog_item:
            raise HTTPException(status_code=404, detail="Orderable not found in active order catalog")
    if not catalog_item and not ((payload.order_type or "").strip() and (payload.order_name or "").strip()):
        raise HTTPException(status_code=422, detail="Select an orderable from lookup or provide both order type and order name")
    order_type = catalog_item.category if catalog_item else payload.order_type.strip()
    order_name = catalog_item.display_name if catalog_item else payload.order_name.strip()
    priority = (payload.priority or (catalog_item.default_priority if catalog_item else "ROUTINE")).upper()
    indication = payload.indication
    if catalog_item and catalog_item.requires_reason and not (indication or "").strip():
        raise HTTPException(status_code=422, detail="This orderable requires a clinical or operational reason")
    instructions = payload.instructions or (catalog_item.default_instructions if catalog_item else None)
    if instructions:
        indication = f"{indication or ''}\nInstructions: {instructions}".strip()
    order = Order(encounter=encounter, order_type=order_type, order_name=order_name, priority=priority, indication=indication, ordered_by=payload.ordered_by)
    db.add(order)
    db.flush()
    db.add(OrderStatusEvent(order_id=order.id, action="CREATE", status_before="NONE", status_after=order.status, reason=indication, actor=payload.ordered_by))
    record_managed_event(db, entity_type="ORDER", entity_id=order.order_id, action="CREATE", actor=payload.ordered_by, status_before="NONE", status_after=order.status, patient_id=encounter.patient_id, encounter_id=encounter.id, reason=indication, reversible=True, metadata={"orderable_code": catalog_item.orderable_code if catalog_item else None, "category": order_type, "clinical": catalog_item.clinical if catalog_item else True})
    write_audit(db, action="SIGN_ORDER", resource_type="Order", resource_id=order.order_id, actor=payload.ordered_by, role="Provider", patient_mpi_id=encounter.patient.mpi_id, facility_code=encounter.facility.code, details=f"{priority} {order_type}: {order_name}")
    db.commit()
    db.refresh(order)
    result = order_dict(order)
    result["orderable_code"] = catalog_item.orderable_code if catalog_item else None
    return result


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
