from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..config import get_settings
from ..database import engine
from ..version import __version__
from ..transcription import transcription_service_status

router = APIRouter(tags=["System"])

CAPABILITIES = [
    "MPI", "automatic MRN assignment", "patient registration", "scheduling", "walk-in routing",
    "referrals", "ADT/unit management", "patient tracker", "filtered front-desk worklists",
    "patient print center", "coverage verification", "travel screening", "clinical notes",
    "audio-assisted notes", "practice advisories", "spreadsheet flowsheets", "device observations",
    "eMAR", "pharmacy verification", "enterprise order catalog", "orders", "order course changes",
    "results", "secure messages", "workqueues", "event management", "patient expiry",
    "emergency department", "specialty pathways", "revenue cycle", "claims", "payments",
    "inventory", "quality", "public health", "telehealth", "FHIR R4", "user access matrix", "audit",
    "installable PWA", "encrypted offline record cache", "idempotent offline transaction sync",
]


def _base(status: str) -> dict:
    settings = get_settings()
    return {
        "status": status,
        "service": settings.app_name,
        "environment": settings.environment,
        "time": datetime.now(timezone.utc),
        "release": __version__,
    }


@router.get("/health/live")
def liveness() -> dict:
    return _base("ok")


@router.get("/health/ready")
def readiness() -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database readiness check failed") from exc
    payload = _base("ready")
    payload["database"] = "available"
    payload["transcription"] = transcription_service_status()
    return payload


@router.get("/health")
def health() -> dict:
    payload = readiness()
    payload["capabilities"] = CAPABILITIES
    return payload
