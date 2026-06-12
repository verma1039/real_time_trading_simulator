import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CashLedgerEntry, LedgerEntryType, Portfolio, User


def get_auth_client(client: TestClient, db: Session) -> tuple[TestClient, dict]:
    """Helper to register and login a user, returning the client with auth headers and user info."""
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "password123!"
    
    client.post("/api/v1/auth/signup", json={"email": email, "password": pwd})
    
    # Get user to manually verify email
    user = db.execute(select(User).where(User.email == email)).scalar_one()
    user.is_email_verified = True
    db.commit()
    
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    access_token = resp.json()["access_token"]
    
    client.headers["Authorization"] = f"Bearer {access_token}"
    return client, {"id": str(user.id), "email": user.email}


def test_default_portfolio_created(client: TestClient, db_session: Session):
    auth_client, user_info = get_auth_client(client, db_session)
    
    # Check if we can fetch it
    resp = auth_client.get("/api/v1/portfolios/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    
    portfolio = data[0]
    assert portfolio["name"] == "Default Portfolio"
    assert Decimal(str(portfolio["opening_balance"])) == Decimal("100000.00")
    assert Decimal(str(portfolio["cash_balance"])) == Decimal("100000.00")


def test_get_portfolio_details(client: TestClient, db_session: Session):
    auth_client, user_info = get_auth_client(client, db_session)
    resp = auth_client.get("/api/v1/portfolios/")
    p_id = resp.json()[0]["id"]
    
    resp = auth_client.get(f"/api/v1/portfolios/{p_id}")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["id"] == p_id
    assert "valuation" in data
    assert "holdings" in data
    assert Decimal(str(data["valuation"]["cash_balance"])) == Decimal("100000.00")
    assert Decimal(str(data["valuation"]["total_portfolio_value"])) == Decimal("100000.00")
    assert len(data["holdings"]) == 0


def test_deposit_and_withdraw(client: TestClient, db_session: Session):
    auth_client, user_info = get_auth_client(client, db_session)
    p_id = auth_client.get("/api/v1/portfolios/").json()[0]["id"]
    
    # Deposit
    resp = auth_client.post(f"/api/v1/portfolios/{p_id}/deposits", json={"amount": "5000.00", "description": "Bonus"})
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["balance_after"])) == Decimal("105000.00")
    
    # Withdraw
    resp = auth_client.post(f"/api/v1/portfolios/{p_id}/withdrawals", json={"amount": "2000.00", "description": "Rent"})
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["balance_after"])) == Decimal("103000.00")
    
    # Attempt overdraft
    resp = auth_client.post(f"/api/v1/portfolios/{p_id}/withdrawals", json={"amount": "200000.00"})
    assert resp.status_code == 400
    assert "Insufficient funds" in resp.text
    
    # Attempt negative deposit
    resp = auth_client.post(f"/api/v1/portfolios/{p_id}/deposits", json={"amount": "-100.00"})
    assert resp.status_code == 422  # Pydantic validation


def test_portfolio_reset_and_reconciliation(client: TestClient, db_session: Session):
    auth_client, user_info = get_auth_client(client, db_session)
    p_id = auth_client.get("/api/v1/portfolios/").json()[0]["id"]
    
    # Do some transactions
    auth_client.post(f"/api/v1/portfolios/{p_id}/deposits", json={"amount": "1000.00"})
    auth_client.post(f"/api/v1/portfolios/{p_id}/withdrawals", json={"amount": "500.00"})
    
    # Reset
    resp = auth_client.post(f"/api/v1/portfolios/{p_id}/reset")
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["cash_balance"])) == Decimal("100000.00")
    
    # Ledger reconciliation
    resp = auth_client.get(f"/api/v1/portfolios/{p_id}/ledger")
    assert resp.status_code == 200
    ledger = resp.json()
    
    # There should be 4 entries: OPENING, DEPOSIT, WITHDRAWAL, RESET
    assert len(ledger) == 4
    
    sum_amount = sum(Decimal(str(entry["amount"])) for entry in ledger)
    assert sum_amount == Decimal("100000.00")
    
    # The last applied entry (which is index 0 since it's desc) is RESET
    assert ledger[0]["entry_type"] == "RESET"
    assert Decimal(str(ledger[0]["balance_after"])) == Decimal("100000.00")


def test_authorization_bounds(client: TestClient, db_session: Session):
    client1, info1 = get_auth_client(client, db_session)
    p_id1 = client1.get("/api/v1/portfolios/").json()[0]["id"]
    
    client2, info2 = get_auth_client(TestClient(client.app), db_session)
    
    # Client 2 trying to fetch Client 1's portfolio
    resp = client2.get(f"/api/v1/portfolios/{p_id1}")
    assert resp.status_code == 404
    
    # Client 2 trying to withdraw from Client 1
    resp = client2.post(f"/api/v1/portfolios/{p_id1}/withdrawals", json={"amount": "10.00"})
    assert resp.status_code == 404


def test_get_snapshots(client: TestClient, db_session: Session):
    auth_client, user_info = get_auth_client(client, db_session)
    p_id = auth_client.get("/api/v1/portfolios/").json()[0]["id"]
    
    # Just verify the endpoint returns 200 and a list (even if empty, since we don't generate snapshots here)
    resp = auth_client.get(f"/api/v1/portfolios/{p_id}/snapshots")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


