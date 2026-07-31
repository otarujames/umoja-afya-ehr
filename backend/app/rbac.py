from __future__ import annotations

from fastapi import Request
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .access_control import get_user_access
from .config import get_settings
from .database import SessionLocal
from .enterprise_models import UserAccount
from .security import decode_token


def required_function(path: str, method: str) -> str | None:
    """Map an API request to a functional capability.

    The EHR uses a per-user function/facility/department matrix. Job titles are
    templates only and do not become hard workflow boundaries.
    """
    method = method.upper()
    write = method not in {"GET", "HEAD", "OPTIONS"}
    if path.startswith("/api/v1/auth") or path.startswith("/api/v1/health") or path.startswith("/api/v1/facilities") or path.startswith("/api/v1/modules"):
        return None
    if path.startswith("/api/v1/admin/users") or path.startswith("/api/v1/admin/access-catalog"):
        return "system.users.manage"
    if path.startswith("/api/v1/audit"):
        return "system.audit.view"
    if path.startswith("/api/v1/integration-events"):
        return "system.interfaces.manage"
    if path.startswith("/api/v1/registration"):
        return "registration.manage"
    if path.startswith("/api/v1/appointments") or path.startswith("/api/v1/referrals"):
        return "scheduling.manage"
    if path.startswith("/api/v1/today-patients"):
        return "patient_flow.view"
    if path.startswith("/api/v1/service-points") or path.startswith("/api/v1/duty-rosters"):
        return "service_roster.manage" if write else "patient_flow.view"
    if path.startswith("/api/v1/walk-ins"):
        return "walkins.manage"
    if path.startswith("/api/v1/workqueues") or path.startswith("/api/v1/workqueue-items"):
        return "workqueues.manage" if write else "workqueues.view"
    if path.startswith("/api/v1/notifications"):
        return "patient_flow.view"
    if path.startswith("/api/v1/break-glass"):
        return "emergency_access"
    if path.startswith("/api/v1/beds") or path.startswith("/api/v1/recent-discharges"):
        return "adt.manage" if write else "patient_flow.view"
    if path.startswith("/api/v1/tracker"):
        return "patient_flow.manage" if write else "patient_flow.view"
    if path.startswith("/api/v1/patients"):
        suffix = path.removeprefix("/api/v1/patients").strip("/")
        return "patient.chart" if suffix else "patient.search"
    if path.startswith("/api/v1/notes/audio"):
        return "audio_notes.use"
    if path.startswith("/api/v1/practice-advisories"):
        return "advisories.view"
    if path.startswith("/api/v1/notes"):
        return "notes.manage"
    if path.startswith("/api/v1/flowsheets"):
        return "flowsheets.manage"
    if path.startswith("/api/v1/orders"):
        if write and path != "/api/v1/orders":
            return "orders.manage"
        return "orders.create" if write else "results.review"
    if path.startswith("/api/v1/results"):
        return "results.acknowledge" if write else "results.review"
    if path.startswith("/api/v1/medications"):
        if path.endswith("/verify"):
            return "medications.verify"
        if "/administrations" in path:
            return "emar.manage"
        return "medications.order" if write else "patient.chart"
    if path.startswith("/api/v1/charges") or path.startswith("/api/v1/claims") or path.startswith("/api/v1/payments"):
        return "revenue.manage"
    if path.startswith("/api/v1/inventory"):
        return "supply.manage"
    if path.startswith("/api/v1/quality-incidents"):
        return "quality.manage"
    if path.startswith("/api/v1/public-health-events"):
        return "public_health.manage"
    if path.startswith("/api/v1/telehealth-sessions"):
        return "telehealth.manage"
    if path.startswith("/api/v1/fhir"):
        return "fhir.exchange"
    if path.startswith("/api/v1/analytics/summary"):
        return "analytics.view"
    if path.startswith("/api/v1/enterprise/summary"):
        return "dashboard.view"
    if path.startswith("/api/v1/module-activities"):
        return "patient.chart"
    return None


class AccessMatrixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if request.method.upper() == "OPTIONS" or not settings.enforce_rbac:
            return await call_next(request)
        capability = required_function(request.url.path, request.method)
        if not capability:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        try:
            payload = decode_token(authorization.split(" ", 1)[1])
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired session"})
        with SessionLocal() as db:
            user = db.scalar(select(UserAccount).where(UserAccount.user_id == payload.get("sub"), UserAccount.active.is_(True)))
            if not user:
                return JSONResponse(status_code=401, content={"detail": "User account is not active"})
            access = get_user_access(db, user)
            if capability not in set(access["functions"]):
                return JSONResponse(
                    status_code=403,
                    content={"detail": f"This account is not assigned the required function: {capability}"},
                )
        return await call_next(request)


# Backward-compatible import name used by main.py in earlier releases.
RoleGateMiddleware = AccessMatrixMiddleware
