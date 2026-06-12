"""In-memory sliding-window rate limiter.

No Redis, no external dependencies — suitable for the single-process
Render Free deployment described in the plan.

Usage as a FastAPI dependency::

    login_limiter = RateLimiter(max_requests=5, window_seconds=60)

    @router.post("/login")
    def login(request: Request, _=Depends(login_limiter)):
        ...

For login and forgot-password endpoints the key is IP + normalized email
to prevent both credential stuffing from one IP and distributed attacks
against a single account.
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict

from fastapi import Request

from app.core.errors import RateLimitError


class RateLimiter:
    """Sliding-window rate limiter backed by an in-process dict."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Key builders
    # ------------------------------------------------------------------
    @staticmethod
    def ip_key(request: Request) -> str:
        """Rate-limit key using only the client IP."""
        return f"ip:{request.client.host if request.client else 'unknown'}"

    @staticmethod
    def ip_email_key(request: Request, email: str) -> str:
        """Rate-limit key combining client IP and normalized email."""
        ip = request.client.host if request.client else "unknown"
        return f"ip_email:{ip}:{email.lower().strip()}"

    # ------------------------------------------------------------------
    # Core check
    # ------------------------------------------------------------------
    def check(self, key: str) -> None:
        """Raise ``RateLimitError`` if *key* has exceeded the limit."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._hits[key]
            # Prune expired entries
            self._hits[key] = timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= self.max_requests:
                raise RateLimitError(
                    f"Too many requests. Try again in {self.window_seconds} seconds."
                )
            timestamps.append(now)

    # ------------------------------------------------------------------
    # FastAPI dependency (IP-only — use check() for IP+email)
    # ------------------------------------------------------------------
    def __call__(self, request: Request) -> None:
        """FastAPI ``Depends`` callable using IP-only key."""
        self.check(self.ip_key(request))

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def cleanup(self) -> None:
        """Remove fully-expired keys.  Call periodically if memory matters."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            empty_keys = [
                k for k, v in self._hits.items() if not any(t > cutoff for t in v)
            ]
            for k in empty_keys:
                del self._hits[k]


# ---------------------------------------------------------------------------
# Shared instances
# ---------------------------------------------------------------------------
login_limiter = RateLimiter(max_requests=5, window_seconds=60)
signup_limiter = RateLimiter(max_requests=3, window_seconds=60)
forgot_password_limiter = RateLimiter(max_requests=3, window_seconds=60)
