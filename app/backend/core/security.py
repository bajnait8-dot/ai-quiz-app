"""CSRF protection, rate limiting and security headers.

The app has no user accounts, but form posts still trigger paid LLM calls, so
they need CSRF and abuse protection. We use a double-submit cookie: the token is
stored in an HttpOnly cookie and echoed in a hidden form field.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections import deque
from typing import Deque

from fastapi import Request, Response

from core.config import settings

CSRF_COOKIE_NAME = "quiz_csrf"
CSRF_FIELD_NAME = "csrf_token"
CSRF_MAX_AGE = 60 * 60 * 24 * 7  # one week


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def csrf_token_for_request(request: Request) -> tuple[str, bool]:
    """Return (token, created). The middleware sets the cookie when created."""

    token = request.cookies.get(CSRF_COOKIE_NAME)
    if token and len(token) >= 32:
        return token, False
    return secrets.token_urlsafe(32), True


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        max_age=CSRF_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def csrf_is_valid(request: Request, submitted: str | None) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if not cookie or not submitted:
        return False
    return secrets.compare_digest(cookie, str(submitted))


class SlidingWindowRateLimiter:
    """Small in-process limiter. Good enough for a single-instance deployment."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = max(1, limit)
        self.window = max(1, window_seconds)
        self._hits: dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""

        if not settings.rate_limit_enabled:
            return True, 0

        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self.window:
                hits.popleft()

            if len(hits) >= self.limit:
                retry_after = max(1, int(self.window - (now - hits[0])) + 1)
                return False, retry_after

            hits.append(now)

            # Opportunistic cleanup so the dict cannot grow without bound.
            if len(self._hits) > 10_000:
                for stale_key in [k for k, v in self._hits.items() if not v]:
                    self._hits.pop(stale_key, None)

            return True, 0


rate_limiter = SlidingWindowRateLimiter(
    settings.rate_limit_requests, settings.rate_limit_window_seconds
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    ),
}


def apply_security_headers(response: Response) -> None:
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
