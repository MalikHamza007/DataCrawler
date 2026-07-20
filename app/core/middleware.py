from __future__ import annotations

import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings
from app.core.request_context import request_id_var


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if 1 <= len(incoming) <= 80 and all(ch.isalnum() or ch in "-_." for ch in incoming) else str(uuid4())
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and int(length) > self.max_bytes:
            return JSONResponse(status_code=413, content={"detail": "Payload too large.", "error_code": "PAYLOAD_TOO_LARGE"})
        return await call_next(request)


class LocalRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings):
        super().__init__(app)
        self.settings = settings
        self.events: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        key = self._bucket(request)
        if key:
            now = time.monotonic()
            window = 3600 if key == "exports" else 60
            limit = 10 if key == "exports" else 30
            bucket = self.events[key]
            while bucket and bucket[0] < now - window:
                bucket.popleft()
            if len(bucket) >= limit:
                return JSONResponse(status_code=429, content={"detail": "Local rate limit exceeded.", "error_code": "RATE_LIMITED"})
            bucket.append(now)
        return await call_next(request)

    def _bucket(self, request: Request) -> str | None:
        if request.method != "POST":
            return None
        path = request.url.path
        if path == "/api/exports":
            return "exports"
        if path == "/api/social-captures":
            return "extension"
        if path == "/api/dashboard/bulk-actions":
            return "bulk"
        return None
