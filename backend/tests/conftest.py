"""Shared test fixtures.

Sets DATABASE_URL to an in-memory SQLite database before any app code
is imported — this ensures tests never touch a real PostgreSQL instance.
"""

import os

# Must be set before importing any app modules so get_settings()
# picks up the test database URL on first call.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-not-for-production"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app import models  # noqa: F401 — ensure all models are registered


# ---------------------------------------------------------------------------
# Provide a fresh in-memory SQLite database for each test
# ---------------------------------------------------------------------------
@pytest.fixture()
def db_session():
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestSession()
    
    # Seed test instruments
    from app.models import Instrument, InstrumentType
    session.add(Instrument(
        symbol="RELIANCE",
        yahoo_symbol="RELIANCE.NS",
        exchange="NSE",
        name="Reliance Industries Limited",
        instrument_type=InstrumentType.EQUITY,
        is_active=True,
        is_tradeable=True
    ))
    session.commit()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def clear_rate_limiters():
    from app.core.rate_limit import login_limiter, signup_limiter, forgot_password_limiter
    login_limiter._hits.clear()
    signup_limiter._hits.clear()
    forgot_password_limiter._hits.clear()


@pytest.fixture()
def client(db_session):
    """TestClient that injects the test db_session via dependency override."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def setup_test_users(client, db_session):
    import uuid
    from app.models import User
    from sqlalchemy import select
    
    def create_user_and_login():
        email = f"user_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "password123!"
        client.post("/api/v1/auth/signup", json={"email": email, "password": pwd})
        
        user = db_session.execute(select(User).where(User.email == email)).scalar_one()
        user.is_email_verified = True
        db_session.commit()
        
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        token = resp.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # New client instance for this user
        new_client = TestClient(app)
        new_client.headers.update(headers)
        
        return new_client, headers, user
        
    client1, headers1, user1 = create_user_and_login()
    client2, headers2, user2 = create_user_and_login()
    
    return (client1, headers1, user1), (client2, headers2, user2)

@pytest.fixture()
def test_user_headers(setup_test_users):
    _, headers1, _ = setup_test_users[0]
    return headers1

@pytest.fixture()
def test_user(setup_test_users):
    _, _, user1 = setup_test_users[0]
    return user1

@pytest.fixture()
def auth_client(setup_test_users):
    client1, _, _ = setup_test_users[0]
    return client1
