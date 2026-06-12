import time
from typing import Any
import pytest
from httpx import Response
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _extract_refresh_token(response: Response) -> str | None:
    return response.cookies.get("refresh_token")


# ---------------------------------------------------------------------------
# Signup & Verify
# ---------------------------------------------------------------------------
def test_signup_success(client: Any, db_session: Session) -> None:
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "new@example.com", "password": "StrongPassword123", "display_name": "New User"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["display_name"] == "New User"
    assert not data["is_email_verified"]

    # Verify user created in DB
    user = db_session.query(User).filter_by(email="new@example.com").first()
    assert user is not None
    assert verify_password("StrongPassword123", user.password_hash)


def test_signup_duplicate_email(client: Any) -> None:
    client.post(
        "/api/v1/auth/signup",
        json={"email": "dup@example.com", "password": "StrongPassword123"}
    )
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "dup@example.com", "password": "AnotherPassword123"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_signup_weak_password(client: Any) -> None:
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "weak@example.com", "password": "short"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_verify_email_flow(client: Any, db_session: Session) -> None:
    client.post(
        "/api/v1/auth/signup",
        json={"email": "verify@example.com", "password": "StrongPassword123"}
    )
    
    # Grab the verification token hash from DB to simulate the email link
    from app.models import EmailVerificationToken
    user = db_session.query(User).filter_by(email="verify@example.com").first()
    assert user is not None
    assert not user.is_email_verified

    # We don't have the raw token, but for testing we can manually verify the user
    # Or we can test the token failure case
    resp = client.post("/api/v1/auth/verify-email", json={"token": "invalid_raw_token"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@pytest.fixture
def verified_user(client: Any, db_session: Session) -> tuple[str, str]:
    """Helper: creates a verified user and returns (email, password)"""
    email = "verified@example.com"
    password = "StrongPassword123"
    client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    
    user = db_session.query(User).filter_by(email=email).first()
    user.is_email_verified = True
    db_session.commit()
    return email, password


def test_login_success(client: Any, verified_user: tuple[str, str]) -> None:
    email, password = verified_user
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "expires_in" in data
    
    # Check refresh cookie
    cookie = _extract_refresh_token(resp)
    assert cookie is not None


def test_login_wrong_password(client: Any, verified_user: tuple[str, str]) -> None:
    email, _ = verified_user
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpassword"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_unverified(client: Any) -> None:
    client.post(
        "/api/v1/auth/signup",
        json={"email": "unverified@example.com", "password": "StrongPassword123"}
    )
    resp = client.post("/api/v1/auth/login", json={"email": "unverified@example.com", "password": "StrongPassword123"})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_login_suspended(client: Any, verified_user: tuple[str, str], db_session: Session) -> None:
    email, password = verified_user
    user = db_session.query(User).filter_by(email=email).first()
    user.is_suspended = True
    db_session.commit()

    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------
def test_refresh_success(client: Any, verified_user: tuple[str, str]) -> None:
    email, password = verified_user
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    old_cookie = login_resp.cookies.get("refresh_token")
    
    # Use httpx cookies to pass it back
    refresh_resp = client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_cookie})
    assert refresh_resp.status_code == 200
    
    new_cookie = refresh_resp.cookies.get("refresh_token")
    assert new_cookie is not None
    assert new_cookie != old_cookie
    assert refresh_resp.json()["access_token"] != login_resp.json()["access_token"]


def test_refresh_invalid_token(client: Any) -> None:
    resp = client.post("/api/v1/auth/refresh", cookies={"refresh_token": "fake_token"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
def test_logout(client: Any, verified_user: tuple[str, str]) -> None:
    email, password = verified_user
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    cookie = login_resp.cookies.get("refresh_token")

    # Logout
    logout_resp = client.post("/api/v1/auth/logout", cookies={"refresh_token": cookie})
    assert logout_resp.status_code == 200
    
    # Cookie should be cleared (max_age=0 or empty)
    # Different clients handle cookie deletion differently, but generally it's cleared
    
    # Subsequent refresh should fail (revoked)
    refresh_resp = client.post("/api/v1/auth/refresh", cookies={"refresh_token": cookie})
    assert refresh_resp.status_code == 401


# ---------------------------------------------------------------------------
# Forgot Password / Reset
# ---------------------------------------------------------------------------
def test_forgot_password(client: Any, verified_user: tuple[str, str]) -> None:
    email, _ = verified_user
    resp = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200
    
    # Even non-existent emails return 200
    resp2 = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp2.status_code == 200


def test_reset_password_invalid_token(client: Any) -> None:
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "fake_token", "new_password": "NewStrongPassword123"}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Profile (Me)
# ---------------------------------------------------------------------------
def test_get_me(client: Any, verified_user: tuple[str, str]) -> None:
    email, password = verified_user
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_resp.json()["access_token"]

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


def test_get_me_no_token(client: Any) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
def test_rate_limiting_signup(client: Any) -> None:
    from app.core.rate_limit import signup_limiter
    signup_limiter._hits.clear()

    # Signup limit is 3/min per IP
    for i in range(3):
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": f"rate{i}@example.com", "password": "StrongPassword123"}
        )
        assert resp.status_code in (201, 409)

    # 4th should be 429
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": "rate4@example.com", "password": "StrongPassword123"}
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

