"""Authentication HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import CurrentVerifiedUser, get_current_user
from app.core.errors import UnauthorizedError
from app.core.rate_limit import (
    forgot_password_limiter,
    login_limiter,
    signup_limiter,
)
from app.db import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    ChangePasswordRequest,
)
from app.services import auth as auth_service

router = APIRouter()

_REFRESH_COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = settings.jwt_refresh_expire_days * 24 * 60 * 60
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        expires=max_age,
        path="/api/v1/auth",  # Scoped tightly
        domain=None,
        secure=settings.environment == "production",
        httponly=True,
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        domain=None,
    )


def _get_refresh_token(request: Request) -> str:
    token = request.cookies.get(_REFRESH_COOKIE_NAME)
    if not token:
        raise UnauthorizedError("Missing refresh token.")
    return token


# ---------------------------------------------------------------------------
# Signup & Verify
# ---------------------------------------------------------------------------
@router.post("/signup", response_model=UserResponse, status_code=201)
def signup(
    req: SignupRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new unverified account and send a verification email."""
    signup_limiter(request)
    return auth_service.signup(
        db=db,
        email=req.email,
        password=req.password,
        display_name=req.display_name,
    )


@router.post("/verify-email", response_model=UserResponse)
def verify_email(
    req: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    """Verify an email address using a token."""
    return auth_service.verify_email(db=db, raw_token=req.token)


# ---------------------------------------------------------------------------
# Login / Refresh / Logout
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate and create a session.

    Sets an HttpOnly cookie with the refresh token and returns the access JWT.
    """
    # IP + Email rate limiting to prevent targeted attacks
    login_limiter.check(login_limiter.ip_email_key(request, req.email))

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    access_token, refresh_token, expires_in = auth_service.login(
        db=db,
        email=req.email,
        password=req.password,
        user_agent=user_agent,
        ip_address=ip,
    )

    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/refresh", response_model=TokenResponse)
def refresh_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Rotate the refresh token and issue a new access JWT."""
    old_refresh = _get_refresh_token(request)

    access_token, new_refresh, expires_in = auth_service.refresh_session(
        db=db, raw_refresh_token=old_refresh
    )

    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Revoke the current session."""
    try:
        token = _get_refresh_token(request)
        auth_service.logout(db=db, raw_refresh_token=token)
    except UnauthorizedError:
        pass  # Already missing or invalid, treat as logged out

    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out successfully.")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(
    response: Response,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Revoke ALL sessions for the current user."""
    count = auth_service.logout_all(db=db, user_id=user.id)
    _clear_refresh_cookie(response)
    return MessageResponse(message=f"Revoked {count} active sessions.")


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------
@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Request a password reset email."""
    forgot_password_limiter.check(forgot_password_limiter.ip_email_key(request, req.email))
    auth_service.request_password_reset(db=db, email=req.email)
    # Always return success to prevent email enumeration
    return MessageResponse(
        message="If an account exists, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    req: ResetPasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Reset password and revoke all active sessions."""
    auth_service.confirm_password_reset(
        db=db, raw_token=req.token, new_password=req.new_password
    )
    _clear_refresh_cookie(response)
    return MessageResponse(message="Password reset successfully. Please log in.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    req: ChangePasswordRequest,
    response: Response,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Change password for an authenticated user and revoke all active sessions."""
    auth_service.change_password(
        db=db, user_id=user.id, current_password=req.current_password, new_password=req.new_password
    )
    _clear_refresh_cookie(response)
    return MessageResponse(message="Password changed successfully. Please log in again.")


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    user: CurrentVerifiedUser,
):
    """Return the profile of the currently authenticated user."""
    return user
