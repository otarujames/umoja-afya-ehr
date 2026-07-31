from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import get_settings


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
