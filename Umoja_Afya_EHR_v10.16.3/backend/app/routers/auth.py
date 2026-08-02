from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access_control import ROLE_TEMPLATES, get_user_access, replace_user_access
from ..audit import write_audit
from ..config import get_settings
from ..database import get_db
from ..enterprise_models import UserAccount
from ..models import Facility
from ..security import create_token, optional_user, password_is_strong, password_needs_rehash, hash_password, revoke_session, verify_password

router = APIRouter(tags=["Authentication and Access"])


class LoginIn(BaseModel):
    username: str
    password: str
    country_code: str = Field(default="TZ", min_length=2, max_length=3)


@router.post("/auth/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    username = payload.username.lower().strip()
    user = db.scalar(select(UserAccount).where(UserAccount.username == username))
    current = datetime.now(timezone.utc)
    if user and user.locked_until:
        locked_until = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)
        if locked_until > current:
            raise HTTPException(status_code=423, detail="Account temporarily locked after repeated failed sign-in attempts")
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_count = int(user.failed_login_count or 0) + 1
            if user.failed_login_count >= 5:
                user.locked_until = current + timedelta(minutes=15)
            write_audit(db, action="LOGIN_FAILED", resource_type="UserAccount", resource_id=user.user_id, actor=username, role="authentication", facility_code=user.facility_code, details=f"failed_count={user.failed_login_count}")
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access = get_user_access(db, user)
    requested_country = payload.country_code.upper().strip()
    if requested_country not in access.get("countries", []):
        write_audit(db, action="COUNTRY_LOGIN_DENIED", resource_type="UserAccount", resource_id=user.user_id, actor=user.display_name, role=user.role_code, facility_code=user.facility_code, details=f"country={requested_country}")
        db.commit()
        raise HTTPException(status_code=403, detail="Your account is not authorized for the selected country of practice")
    allowed_facilities = list(db.scalars(select(Facility.code).where(Facility.country_code == requested_country, Facility.code.in_(access.get("facilities", [])))).all())
    if not allowed_facilities:
        raise HTTPException(status_code=403, detail="No facility access is assigned in the selected country")
    user.facility_code = allowed_facilities[0]
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = current
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        user.password_changed_at = current
    token = create_token(user, db, source_ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    write_audit(db, action="LOGIN", resource_type="UserAccount", resource_id=user.user_id, actor=user.display_name, role=user.role_code, facility_code=user.facility_code)
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": get_settings().session_timeout_minutes,
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "display_name": user.display_name,
            "role_code": user.role_code,
            "facility_code": user.facility_code,
            "requires_mfa": user.requires_mfa,
            "must_change_password": user.must_change_password,
            "country_code": requested_country,
            "profile_photo_url": f"/profile-photos/{user.user_id}?v={int(user.profile_photo_updated_at.timestamp())}" if user.profile_photo_data and user.profile_photo_updated_at else None,
            **access,
        },
    }


@router.post("/auth/logout")
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    revoked = revoke_session(authorization.split(" ", 1)[1], db)
    db.commit()
    return {"revoked": revoked}


@router.get("/auth/me")
def me(user: UserAccount | None = Depends(optional_user), db: Session = Depends(get_db)):
    if not user:
        return {"authenticated": False, "environment": get_settings().environment}
    return {
        "authenticated": True,
        "user_id": user.user_id,
        "username": user.username,
        "display_name": user.display_name,
        "role_code": user.role_code,
        "facility_code": user.facility_code,
        "requires_mfa": user.requires_mfa,
        "must_change_password": user.must_change_password,
        "profile_photo_url": f"/profile-photos/{user.user_id}?v={int(user.profile_photo_updated_at.timestamp())}" if user.profile_photo_data and user.profile_photo_updated_at else None,
        **get_user_access(db, user),
    }




class FirstAdminSetupIn(BaseModel):
    bootstrap_token: str = Field(min_length=1, max_length=512)
    username: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=2, max_length=180)
    facility_code: str = Field(default="MNH-UPANGA", min_length=2, max_length=80)
    password: str = Field(min_length=12, max_length=256)


def _active_admin_count(db: Session) -> int:
    return int(db.scalar(select(func.count(UserAccount.id)).where(UserAccount.active.is_(True), UserAccount.role_code == "admin")) or 0)


@router.get("/auth/setup-status")
def setup_status(db: Session = Depends(get_db)):
    settings = get_settings()
    required = bool(settings.first_run_setup_enabled and _active_admin_count(db) == 0)
    return {
        "setup_required": required,
        "bootstrap_token_required": required and bool(settings.bootstrap_token),
        "environment": settings.environment,
    }


@router.post("/auth/setup-admin", status_code=201)
def setup_first_admin(payload: FirstAdminSetupIn, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.first_run_setup_enabled:
        raise HTTPException(status_code=404, detail="First-run setup is disabled")
    if _active_admin_count(db) > 0:
        raise HTTPException(status_code=409, detail="An active administrator already exists; use institutional account administration")
    if not settings.bootstrap_token or not secrets.compare_digest(payload.bootstrap_token, settings.bootstrap_token):
        write_audit(db, action="FIRST_ADMIN_SETUP_REJECTED", resource_type="UserAccount", resource_id="bootstrap", actor=request.client.host if request.client else "unknown", role="bootstrap", facility_code=payload.facility_code, details="Invalid one-time setup token")
        db.commit()
        raise HTTPException(status_code=403, detail="The one-time setup token is invalid")
    if not password_is_strong(payload.password):
        raise HTTPException(status_code=422, detail="Password must contain at least 12 characters, upper and lower case letters, a number and a symbol")
    username = payload.username.lower().strip()
    if db.scalar(select(UserAccount).where(func.lower(UserAccount.username) == username)):
        raise HTTPException(status_code=409, detail="Username already exists")
    facility = db.scalar(select(Facility).where(Facility.code == payload.facility_code))
    if not facility:
        raise HTTPException(status_code=422, detail="Selected facility does not exist")
    all_facilities = list(db.scalars(select(Facility.code).order_by(Facility.code)).all()) or [payload.facility_code]
    all_countries = list(db.scalars(select(Facility.country_code).distinct().order_by(Facility.country_code)).all()) or [facility.country_code]
    template = ROLE_TEMPLATES["admin"]
    user = UserAccount(
        username=username,
        display_name=payload.display_name.strip(),
        role_code="admin",
        facility_code=payload.facility_code,
        password_hash=hash_password(payload.password),
        active=True,
        requires_mfa=True,
        must_change_password=False,
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()
    replace_user_access(
        db, user,
        functions=template["functions"],
        departments=template["departments"],
        facilities=all_facilities,
        countries=all_countries,
        actor=payload.display_name.strip(),
        reason="Secure first-run administrator setup",
    )
    write_audit(db, action="FIRST_ADMIN_CREATED", resource_type="UserAccount", resource_id=user.user_id, actor=payload.display_name.strip(), role="bootstrap", facility_code=payload.facility_code, details=f"username={username}; source_ip={request.client.host if request.client else 'unknown'}")
    db.commit()
    return {"created": True, "username": username, "message": "Administrator created. Sign in using the credentials you just chose."}
