from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditEvent
from ..schemas import AuditOut

router = APIRouter(tags=["Audit"])


@router.get("/audit", response_model=list[AuditOut])
def list_audit(
    patient_mpi_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = select(AuditEvent)
    if patient_mpi_id:
        query = query.where(AuditEvent.patient_mpi_id == patient_mpi_id)
    return list(db.scalars(query.order_by(AuditEvent.occurred_at.desc()).limit(limit)).all())
