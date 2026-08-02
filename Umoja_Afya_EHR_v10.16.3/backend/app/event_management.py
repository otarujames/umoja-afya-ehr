from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .enhancement_models import ManagedEvent


def record_managed_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str,
    status_before: str | None = None,
    status_after: str | None = None,
    patient_id: int | None = None,
    encounter_id: int | None = None,
    reason: str | None = None,
    reversible: bool = False,
    metadata: dict[str, Any] | None = None,
) -> ManagedEvent:
    event = ManagedEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        action=action,
        status_before=status_before,
        status_after=status_after,
        actor=actor,
        reason=reason,
        reversible=reversible,
        metadata_json=json.dumps(metadata or {}, default=str),
    )
    db.add(event)
    db.flush()
    return event
