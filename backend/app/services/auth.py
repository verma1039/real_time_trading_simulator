"""Authentication business logic.

Every public function accepts a SQLAlchemy ``Session`` so callers own
the transaction boundary.  No FastAPI/HTTP concepts leak in here.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
)
from app.core.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import (
    EmailVerificationToken,
    LoginSession,
    PasswordResetToken,
    Portfolio,
    User,
    utc_now,
)
from app.services.email import send_password_reset_email, send_verification_email
from app.services.portfolio import create_portfolio

logger = logging.getLogger(__name__)

_VERIFICATION_TOKEN_HOURS = 48
_PASSWORD_RESET_TOKEN_HOURS = 1


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------
def signup(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str | None = None,
) -> User:
    """Create a new unverified user and send a verification email."""
    normalized_email = email.lower().strip()

    existing = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()

    if existing is not None:
        raise ConflictError("An account with this email already exists.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.add(user)
    db.flush()  # assign user.id

    # Create verification token
    raw_token, token_hash = generate_token()
    verification = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=_VERIFICATION_TOKEN_HOURS),
    )
    db.add(verification)
    db.commit()
    db.refresh(user)

    # Send asynchronously-safe email (blocking in this MVP)
    try:
        send_verification_email(normalized_email, raw_token)
    except Exception:
        logger.exception("Failed to send verification email to %s", normalized_email)
        # Don't fail signup if email delivery fails

    return user


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
def verify_email(db: Session, *, raw_token: str) -> User:
    """Mark a user's email as verified using the supplied token."""
    token_hash = hash_token(raw_token)

    record = db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash
        )
    ).scalar_one_or_none()

    if record is None:
        raise BadRequestError("Invalid verification token.")

    if record.used_at is not None:
        raise BadRequestError("This verification link has already been used.")

    record_expires_at = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    if record_expires_at < datetime.now(timezone.utc):
        raise BadRequestError("This verification link has expired.")

    record.used_at = utc_now()

    user = db.execute(
        select(User).where(User.id == record.user_id)
    ).scalar_one()
    user.is_email_verified = True

    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def login(
    db: Session,
    *,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, str, int]:
    """Authenticate a user and create a session.

    Returns ``(access_token, raw_refresh_token, expires_in_seconds)``.
    """
    normalized_email = email.lower().strip()
    settings = get_settings()

    user = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password.")

    if not user.is_email_verified:
        raise ForbiddenError("Please verify your email before logging in.")

    if user.is_suspended:
        raise ForbiddenError("Your account has been suspended.")

    # Enforce exactly one portfolio per user for MVP
    # Create the default portfolio automatically after first verified login if it does not exist.
    from sqlalchemy import func
    portfolio_count = db.execute(
        select(func.count(Portfolio.id)).where(Portfolio.user_id == user.id)
    ).scalar_one()

    if portfolio_count == 0:
        create_portfolio(db, user_id=user.id, name="Default Portfolio", opening_balance=Decimal("100000.00"))

    # Create session
    raw_refresh, refresh_hash = generate_token()
    session = LoginSession(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.jwt_refresh_expire_days),
    )
    db.add(session)
    db.commit()

    access_token, expires_in = create_access_token(user.id, user.role.value)
    return access_token, raw_refresh, expires_in


# ---------------------------------------------------------------------------
# Refresh session
# ---------------------------------------------------------------------------
def refresh_session(db: Session, *, raw_refresh_token: str) -> tuple[str, str, int]:
    """Rotate a refresh token and issue a new access token.

    Returns ``(access_token, new_raw_refresh_token, expires_in_seconds)``.
    """
    settings = get_settings()
    token_hash = hash_token(raw_refresh_token)
    now = datetime.now(timezone.utc)

    session = db.execute(
        select(LoginSession).where(LoginSession.refresh_token_hash == token_hash)
    ).scalar_one_or_none()

    if session is None or session.revoked_at is not None:
        raise UnauthorizedError("Invalid or expired session.")

    session_expires_at = session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
    if session_expires_at < now:
        raise UnauthorizedError("Invalid or expired session.")

    # Revoke old session
    session.revoked_at = utc_now()

    # Load user to check suspension
    user = db.execute(
        select(User).where(User.id == session.user_id)
    ).scalar_one()

    if user.is_suspended:
        db.commit()
        raise ForbiddenError("Your account has been suspended.")

    # Create new session
    new_raw, new_hash = generate_token()
    new_session = LoginSession(
        user_id=user.id,
        refresh_token_hash=new_hash,
        user_agent=session.user_agent,
        ip_address=session.ip_address,
        expires_at=now + timedelta(days=settings.jwt_refresh_expire_days),
    )
    db.add(new_session)
    db.commit()

    access_token, expires_in = create_access_token(user.id, user.role.value)
    return access_token, new_raw, expires_in


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
def logout(db: Session, *, raw_refresh_token: str) -> None:
    """Revoke a single session by its refresh token."""
    token_hash = hash_token(raw_refresh_token)

    session = db.execute(
        select(LoginSession).where(LoginSession.refresh_token_hash == token_hash)
    ).scalar_one_or_none()

    if session is not None and session.revoked_at is None:
        session.revoked_at = utc_now()
        db.commit()


def logout_all(db: Session, *, user_id: uuid.UUID) -> int:
    """Revoke every active session for the given user.

    Returns the number of sessions revoked.
    """
    now = utc_now()
    result = db.execute(
        update(LoginSession)
        .where(
            LoginSession.user_id == user_id,
            LoginSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()
    return result.rowcount  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Password reset — request
# ---------------------------------------------------------------------------
def request_password_reset(db: Session, *, email: str) -> None:
    """Send a password-reset link.  Silent on unknown emails (no enumeration)."""
    normalized_email = email.lower().strip()

    user = db.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()

    if user is None:
        return  # no user enumeration

    raw_token, token_hash = generate_token()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=_PASSWORD_RESET_TOKEN_HOURS),
    )
    db.add(reset)
    db.commit()

    try:
        send_password_reset_email(normalized_email, raw_token)
    except Exception:
        logger.exception("Failed to send password-reset email to %s", normalized_email)


# ---------------------------------------------------------------------------
# Password reset — confirm
# ---------------------------------------------------------------------------
def confirm_password_reset(db: Session, *, raw_token: str, new_password: str) -> None:
    """Reset a user's password and revoke all their sessions."""
    token_hash = hash_token(raw_token)

    record = db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
    ).scalar_one_or_none()

    if record is None:
        raise BadRequestError("Invalid password-reset token.")

    if record.used_at is not None:
        raise BadRequestError("This reset link has already been used.")

    record_expires_at = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
    if record_expires_at < datetime.now(timezone.utc):
        raise BadRequestError("This reset link has expired.")

    record.used_at = utc_now()

    user = db.execute(
        select(User).where(User.id == record.user_id)
    ).scalar_one()
    user.password_hash = hash_password(new_password)

    # Revoke all sessions (logout-all on password change)
    db.execute(
        update(LoginSession)
        .where(
            LoginSession.user_id == user.id,
            LoginSession.revoked_at.is_(None),
        )
        .values(revoked_at=utc_now())
    )

    db.commit()
