"""Core cryptographic utilities — password hashing, JWTs, opaque tokens.

No business logic lives here.  Every function is a pure input→output
transformation suitable for unit-testing in isolation.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.config import get_settings

_ph = PasswordHasher()


# ---------------------------------------------------------------------------
# Password hashing (Argon2id)
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    """Return an Argon2id hash of *plain*."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` when *plain* matches *hashed*, ``False`` otherwise."""
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError):
        return False


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------
def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    """Create a signed JWT access token.

    Returns ``(token_string, expires_in_seconds)``.
    """
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.jwt_access_expire_minutes)
    now = datetime.now(timezone.utc)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.

    Returns the payload dict.  Raises ``jwt.InvalidTokenError`` subclasses
    on failure (callers should map to ``UnauthorizedError``).
    """
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "role", "exp", "iat", "jti"]},
    )


# ---------------------------------------------------------------------------
# Opaque tokens (refresh, email-verification, password-reset)
# ---------------------------------------------------------------------------
def generate_token() -> tuple[str, str]:
    """Generate a cryptographically-random URL-safe token.

    Returns ``(raw_token, sha256_hex_hash)``.
    The *raw_token* is sent to the client; only the *hash* is stored in the DB.
    """
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    """Return the SHA-256 hex digest of *raw*."""
    return hashlib.sha256(raw.encode()).hexdigest()
