from __future__ import annotations
import gzip

import secrets
import time
from datetime import datetime, timezone
from hashlib import sha256
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .audit import write_audit
from .config import get_settings
from .database import SessionLocal
from .enterprise_models import UserAccount
from .offline_models import IdempotencyReceipt, OfflineDevice
from .security import decode_token



def _safe_idempotency_response_text(payload: bytes | bytearray | str | None) -> str:
    """Convert a response body into PostgreSQL-safe text.

    Starlette may return a gzip-compressed body after response middleware has
    executed. PostgreSQL TEXT columns cannot contain NUL bytes, so compressed
    responses must be decompressed before persistence.
    """
    if payload is None:
        return ""

    if isinstance(payload, str):
        return payload.replace("\x00", "")

    raw = bytes(payload)

    if raw.startswith(b"\x1f\x8b"):
        try:
            raw = gzip.decompress(raw)
        except (OSError, EOFError):
            # Preserve request completion even if the compressed stream is
            # malformed. NUL removal below still guarantees PostgreSQL safety.
            pass

    return raw.decode("utf-8", errors="replace").replace("\x00", "")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or secrets.token_hex(12)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=(), payment=(), usb=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
        if get_settings().environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        maximum = get_settings().max_request_bytes
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > maximum:
                    return JSONResponse(status_code=413, content={"detail": "Request body exceeds configured limit"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header"})
        return await call_next(request)


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Make encrypted browser-outbox retries safe to replay.

    The clinical endpoint remains the source of truth and performs its normal
    authorization and validation. This middleware only reserves a per-user
    operation key and persists the exact response so a reconnect retry cannot
    create the same clinical or financial transaction twice.
    """

    async def dispatch(self, request: Request, call_next):
        key = request.headers.get("x-idempotency-key", "").strip()
        if not key:
            return await call_next(request)
        if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
            return JSONResponse(status_code=400, content={"detail": "Idempotency keys are only valid for mutations"})
        if len(key) < 16 or len(key) > 100 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._:" for ch in key):
            return JSONResponse(status_code=400, content={"detail": "Invalid idempotency key"})

        authorization = request.headers.get("authorization", "")
        if not authorization.lower().startswith("bearer "):
            return JSONResponse(status_code=401, content={"detail": "Authentication is required for idempotent mutations"})
        try:
            token_payload = decode_token(authorization.split(" ", 1)[1])
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired session"})

        actor_user_id = str(token_payload.get("sub") or "")
        offline_device_id = request.headers.get("x-offline-device-id", "").strip()
        body = await request.body()
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        request_hash = sha256(request.method.upper().encode() + b"\n" + target.encode() + b"\n" + body).hexdigest()

        with SessionLocal() as db:
            if offline_device_id:
                enrolled_device = db.scalar(
                    select(OfflineDevice)
                    .join(UserAccount, OfflineDevice.user_account_id == UserAccount.id)
                    .where(
                        UserAccount.user_id == actor_user_id,
                        OfflineDevice.device_id == offline_device_id,
                        OfflineDevice.revoked_at.is_(None),
                    )
                )
                if enrolled_device is None:
                    return JSONResponse(status_code=403, content={"detail": "This offline device is not enrolled or has been revoked"})
            existing = db.scalar(select(IdempotencyReceipt).where(
                IdempotencyReceipt.actor_user_id == actor_user_id,
                IdempotencyReceipt.idempotency_key == key,
            ))
            if existing:
                if existing.request_method != request.method.upper() or existing.request_path != target or existing.request_hash != request_hash:
                    return JSONResponse(status_code=409, content={"detail": "This idempotency key was already used for a different request"})
                if existing.response_status is not None:
                    return Response(
                        content=(existing.response_body or "").encode("utf-8"),
                        status_code=existing.response_status,
                        media_type=existing.response_content_type or "application/json",
                        headers={"X-Idempotent-Replay": "true", "X-Offline-Operation-ID": key},
                    )
                return JSONResponse(
                    status_code=409,
                    content={"detail": "This operation is already processing; retry after reconciliation"},
                    headers={"Retry-After": "10", "X-Offline-Operation-ID": key},
                )

            receipt = IdempotencyReceipt(
                actor_user_id=actor_user_id,
                idempotency_key=key,
                request_method=request.method.upper(),
                request_path=target,
                request_hash=request_hash,
                status="PROCESSING",
                device_id=offline_device_id[:80] or None,
                offline_created_at=request.headers.get("x-offline-created-at", "")[:80] or None,
            )
            db.add(receipt)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                return JSONResponse(
                    status_code=409,
                    content={"detail": "This operation is already processing; retry after reconciliation"},
                    headers={"Retry-After": "10", "X-Offline-Operation-ID": key},
                )

        try:
            response = await call_next(request)
            chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode("utf-8"))
            response_body = b"".join(chunks)
        except Exception:
            with SessionLocal() as db:
                receipt = db.scalar(select(IdempotencyReceipt).where(
                    IdempotencyReceipt.actor_user_id == actor_user_id,
                    IdempotencyReceipt.idempotency_key == key,
                ))
                if receipt:
                    receipt.status = "FAILED_UNKNOWN"
                    receipt.response_status = 503
                    receipt.response_content_type = "application/json"
                    receipt.response_body = '{"detail":"Server outcome requires reconciliation before this operation can be retried"}'
                    receipt.completed_at = datetime.now(timezone.utc)
                    db.commit()
            raise

        content_type = response.headers.get("content-type", "application/json")
        response_text = _safe_idempotency_response_text(response_body)
        with SessionLocal() as db:
            receipt = db.scalar(select(IdempotencyReceipt).where(
                IdempotencyReceipt.actor_user_id == actor_user_id,
                IdempotencyReceipt.idempotency_key == key,
            ))
            if receipt:
                receipt.status = "COMPLETED" if response.status_code < 500 else "FAILED_UNKNOWN"
                receipt.response_status = response.status_code
                receipt.response_content_type = content_type[:160]
                receipt.response_body = response_text
                receipt.completed_at = datetime.now(timezone.utc)
                if receipt.device_id:
                    write_audit(
                        db,
                        action="OFFLINE_MUTATION_RECONCILED",
                        resource_type="OfflineOperation",
                        resource_id=key,
                        actor=str(token_payload.get("name") or token_payload.get("username") or actor_user_id),
                        role=str(token_payload.get("role") or "offline"),
                        facility_code=str(token_payload.get("facility") or "") or None,
                        outcome="SUCCESS" if response.status_code < 400 else "REVIEW",
                        details=f"device={receipt.device_id}; created_offline={receipt.offline_created_at}; path={request.url.path}; status={response.status_code}",
                    )
                db.commit()

        headers = dict(response.headers)
        headers["X-Offline-Operation-ID"] = key
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=headers,
            media_type=None,
            background=response.background,
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Application-layer abuse control.

    The production Nginx gateway also enforces per-IP login and API limits,
    providing a shared boundary before requests reach multiple application workers.
    """

    _events: dict[str, deque[float]] = defaultdict(deque)
    _lock = Lock()

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if (request.client and request.client.host == "testclient") or settings.environment in {"development", "test"} or request.url.path in {"/api/v1/health", "/api/v1/health/live", "/api/v1/health/ready", "/manifest.json", "/service-worker.js"}:
            return await call_next(request)
        limit = settings.login_rate_limit_per_minute if request.url.path.endswith("/auth/login") else settings.rate_limit_per_minute
        identity = request.client.host if request.client else "unknown"
        key = f"{identity}:{request.url.path}"
        current = time.monotonic()
        with self._lock:
            queue = self._events[key]
            while queue and queue[0] < current - 60:
                queue.popleft()
            if len(queue) >= limit:
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded; retry later"}, headers={"Retry-After": "60"})
            queue.append(current)
        return await call_next(request)
