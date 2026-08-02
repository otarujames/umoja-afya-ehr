from __future__ import annotations

from sqlalchemy.orm import Session

from .config import get_settings
from .models import AuditEvent


def write_audit(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    actor: str = "demo-user",
    role: str = "demo",
    patient_mpi_id: str | None = None,
    facility_code: str | None = None,
    outcome: str = "SUCCESS",
    details: str | None = None,
) -> None:
    if not get_settings().audit_enabled:
        return
    db.add(
        AuditEvent(
            actor=actor,
            role=role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_mpi_id=patient_mpi_id,
            facility_code=facility_code,
            outcome=outcome,
            details=details,
        )
    )
