from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .access_control import get_user_access
from .config import get_settings
from .database import get_db
from .enterprise_models import UserAccount
from .operational_models import UserSession

_ARGON2 = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)


def hash_password(password: str, salt: str | None = None) -> str:
    """Hash new passwords with Argon2id; salt remains accepted for legacy tests."""
    if salt:
        salt_bytes = bytes.fromhex(salt)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 240_000)
        return f"pbkdf2_sha256${salt_bytes.hex()}${digest.hex()}"
    return _ARGON2.hash(password)


def password_is_strong(password: str) -> bool:
    blocked = {"change-this-before-production", "Password123!", "Admin123456!"}
    return (
        len(password) >= 12
        and any(c.islower() for c in password)
        and any(c.isupper() for c in password)
        and any(c.isdigit() for c in password)
        and any(not c.isalnum() for c in password)
        and password not in blocked
    )


def verify_password(password: str, encoded: str) -> bool:
    if encoded.startswith("$argon2"):
        try:
            return _ARGON2.verify(encoded, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
    try:
        algorithm, salt, digest = encoded.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hash_password(password, salt).split("$", 2)[2]
    return hmac.compare_digest(candidate, digest)


def password_needs_rehash(encoded: str) -> bool:
    return not encoded.startswith("$argon2") or _ARGON2.check_needs_rehash(encoded)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(user: UserAccount, db: Session, *, source_ip: str | None = None, user_agent: str | None = None) -> str:
    settings = get_settings()
    issued = datetime.now(timezone.utc)
    expires = issued + timedelta(minutes=settings.session_timeout_minutes)
    jti = secrets.token_urlsafe(24)
    access = get_user_access(db, user)
    payload = {
        "sub": user.user_id,
        "username": user.username,
        "name": user.display_name,
        "role": user.role_code,
        "facility": user.facility_code,
        "functions": access["functions"],
        "departments": access["departments"],
        "facilities": access["facilities"],
        "jti": jti,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    db.add(UserSession(user_account_id=user.id, token_jti=jti, issued_at=issued, expires_at=expires, source_ip=source_ip, user_agent=(user_agent or "")[:500] or None))
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.security_secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(settings.security_secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(signature), expected):
            raise ValueError("invalid signature")
        payload = json.loads(_b64decode(body))
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc


def _session_is_active(db: Session, payload: dict) -> bool:
    jti = payload.get("jti")
    if not jti:
        return get_settings().environment in {"development", "test"}
    session = db.scalar(select(UserSession).where(UserSession.token_jti == jti))
    if not session or session.revoked_at is not None:
        return False
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > datetime.now(timezone.utc)


def optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> UserAccount | None:
    settings = get_settings()
    if not authorization:
        if settings.enforce_auth:
            raise HTTPException(status_code=401, detail="Authentication required")
        return None
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    payload = decode_token(authorization.split(" ", 1)[1])
    if not _session_is_active(db, payload):
        raise HTTPException(status_code=401, detail="Session has been revoked or expired")
    user = db.scalar(select(UserAccount).where(UserAccount.user_id == payload["sub"], UserAccount.active.is_(True)))
    if not user:
        raise HTTPException(status_code=401, detail="User account is not active")
    if user.locked_until:
        locked_until = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)
        if locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=423, detail="User account is temporarily locked")
    return user


def revoke_session(token: str, db: Session) -> bool:
    payload = decode_token(token)
    jti = payload.get("jti")
    if not jti:
        return False
    session = db.scalar(select(UserSession).where(UserSession.token_jti == jti))
    if not session:
        return False
    session.revoked_at = datetime.now(timezone.utc)
    return True


def require_user(user: UserAccount | None = Depends(optional_user)) -> UserAccount:
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
