"""FastAPI dependencies for route protection.

Usage::

    @router.get("/protected")
    def protected(user: CurrentVerifiedUser):
        ...

    @router.get("/admin-only")
    def admin_only(user: CurrentAdmin):
        ...
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db import get_db
from app.models import User

import jwt as pyjwt

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Core dependency: extract and validate JWT → load User
# ---------------------------------------------------------------------------
def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ] = None,
    db: Session = Depends(get_db),
) -> User:
    """Decode the access JWT and return the corresponding ``User``.

    Raises ``UnauthorizedError`` on any failure.
    """
    if credentials is None:
        raise UnauthorizedError("Missing authentication token.")

    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired.")
    except pyjwt.InvalidTokenError:
        raise UnauthorizedError("Invalid authentication token.")

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise UnauthorizedError("Invalid authentication token.")
        
    import uuid
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError("Invalid authentication token.")

    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if user is None:
        raise UnauthorizedError("User not found.")

    return user


# ---------------------------------------------------------------------------
# Stricter dependencies
# ---------------------------------------------------------------------------
def require_verified_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the current user has a verified email and is not suspended."""
    if not user.is_email_verified:
        raise ForbiddenError("Please verify your email first.")
    if user.is_suspended:
        raise ForbiddenError("Your account has been suspended.")
    return user


def require_admin(
    user: Annotated[User, Depends(require_verified_user)],
) -> User:
    """Ensure the current user is a verified admin."""
    if user.role.value != "ADMIN":
        raise ForbiddenError("Admin access required.")
    return user


# ---------------------------------------------------------------------------
# Type aliases for clean route signatures
# ---------------------------------------------------------------------------
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentVerifiedUser = Annotated[User, Depends(require_verified_user)]
CurrentAdmin = Annotated[User, Depends(require_admin)]
