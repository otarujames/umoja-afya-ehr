from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access_control import get_user_access
from ..audit import write_audit
from ..config import get_settings
from ..database import get_db
from ..enterprise_models import UserAccount
from ..models import Facility
from ..security import create_token, optional_user, password_needs_rehash, hash_password, revoke_session, verify_password

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
