import pytest
from app.models import UserRole, AdminLog, CashLedgerEntry, LedgerEntryType

@pytest.fixture
def admin_user(setup_test_users, db_session):
    _, _, user = setup_test_users[1]
    user.role = UserRole.ADMIN
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_token(admin_user):
    from app.core.security import create_access_token
    token, _ = create_access_token(admin_user.id, admin_user.role.value)
    return token

@pytest.fixture
def test_user_token(test_user_headers):
    return test_user_headers["Authorization"].split(" ")[1]

@pytest.fixture
def default_portfolio(test_user, db_session):
    from app.models import Portfolio
    from sqlalchemy import select
    port = db_session.execute(select(Portfolio).where(Portfolio.user_id == test_user.id)).scalar_one_or_none()
    if not port:
        from app.services.portfolio import create_portfolio
        from decimal import Decimal
        port = create_portfolio(db_session, user_id=test_user.id, name="Default Portfolio", opening_balance=Decimal("100000.00"))
    return port

def test_admin_authorization(client, db_session, test_user_token):
    # Test user is not admin
    res = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {test_user_token}"})
    assert res.status_code == 403
    assert "Admin access required" in res.json()["error"]["message"]

def test_admin_endpoints(client, db_session, admin_token, admin_user, test_user):
    # Test market-data health
    res = client.get("/api/v1/admin/market-data/health", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "provider_status" in data
    assert "quote_fetch_success" in data

    # Test stats
    res = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["total_portfolios"] >= 0

    # Test users list
    res = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Test suspend user
    res = client.post(f"/api/v1/admin/users/{test_user.id}/suspend", json={"reason": "Suspicious activity"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    
    # Verify AdminLog
    logs = client.get("/api/v1/admin/logs", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert any(l["action"] == "SUSPEND" and l["target_id"] == str(test_user.id) for l in logs)

    # Test reactivate user
    res = client.post(f"/api/v1/admin/users/{test_user.id}/reactivate", json={"reason": "Cleared"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

def test_admin_adjust_balance(client, db_session, admin_token, test_user, default_portfolio):
    initial_balance = default_portfolio.cash_balance
    amount = 500.0

    res = client.post(f"/api/v1/admin/portfolios/{default_portfolio.id}/adjust-balance", json={"amount": amount, "reason": "Bonus"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    
    db_session.refresh(default_portfolio)
    assert float(default_portfolio.cash_balance) == float(initial_balance) + amount

    # Verify Ledger Entry
    ledger = client.get(f"/api/v1/admin/users/{test_user.id}", headers={"Authorization": f"Bearer {admin_token}"}).json()["ledger"]
    assert any(entry["entry_type"] == "ADMIN_ADJUSTMENT" and float(entry["amount"]) == float(amount) for entry in ledger)

    # Verify AdminLog
    logs = client.get("/api/v1/admin/logs", headers={"Authorization": f"Bearer {admin_token}"}).json()
    print("LOGS RETURNED:", logs)
    assert any(l["action"] == "ADJUST_BALANCE" and l["target_id"] == str(default_portfolio.id) for l in logs)

def test_admin_user_details(client, db_session, admin_token, test_user):
    res = client.get(f"/api/v1/admin/users/{test_user.id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "user" in data
    assert "portfolio" in data
    assert "orders" in data
    assert "trades" in data
    assert "ledger" in data
    assert "snapshots" in data
