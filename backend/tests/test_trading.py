import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import CashLedgerEntry, Holding, LedgerEntryType, Order, OrderStatus, Trade


@pytest.fixture(autouse=True)
def mock_trading_dependencies(monkeypatch):
    import app.services.trading
    
    # Mock is_market_open to always be true
    monkeypatch.setattr(app.services.trading, "is_market_open", lambda: True)

    # Mock Market Data Provider
    from tests.test_market_data import MockProvider
    
    mock_provider = MockProvider()
    monkeypatch.setattr(app.services.trading, "market_data_provider", mock_provider)


def test_simulate_order(client: TestClient, test_user_headers):
    # Find instrument
    res_search = client.get("/api/v1/instruments/search?query=RELIANCE", headers=test_user_headers)
    instrument_id = res_search.json()[0]["id"]

    # Simulate BUY
    payload = {
        "instrument_id": instrument_id,
        "side": "BUY",
        "quantity": 10,
        "idempotency_key": "sim-buy-1"
    }
    res = client.post("/api/v1/trading/orders/simulate", headers=test_user_headers, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["side"] == "BUY"
    assert data["quantity"] == 10
    # Price is 150.50. BUY spread is +0.1%, so 150.50 * 1.001 = 150.6505
    assert float(data["execution_price"]) == 150.6505
    assert float(data["gross_amount"]) == 1506.505
    import pytest
    assert float(data["brokerage"]) == pytest.approx(1506.505 * 0.0005)
    assert float(data["taxes"]) == pytest.approx(1506.505 * 0.0002) # 0.301301
    assert data["sufficient_funds"] is True


def test_execute_buy_order_insufficient_funds(client: TestClient, test_user_headers):
    res_search = client.get("/api/v1/instruments/search?query=RELIANCE", headers=test_user_headers)
    instrument_id = res_search.json()[0]["id"]

    payload = {
        "instrument_id": instrument_id,
        "side": "BUY",
        "quantity": 1000,
        "idempotency_key": "buy-fail-1"
    }
    res = client.post("/api/v1/trading/orders", headers=test_user_headers, json=payload)
    if res.status_code == 500:
        print("TRACEBACK FROM SERVER: ", res.json())
    assert res.status_code == 400
    assert res.json()["detail"] == "Insufficient funds"


def test_execute_buy_and_sell_order(client: TestClient, test_user_headers, db_session):
    # Find instrument
    res_search = client.get("/api/v1/instruments/search?query=RELIANCE", headers=test_user_headers)
    instrument_id = res_search.json()[0]["id"]

    # Deposit funds
    res_portfolio = client.get("/api/v1/portfolios", headers=test_user_headers)
    portfolio_id = res_portfolio.json()[0]["id"]
    client.post(f"/api/v1/portfolios/{portfolio_id}/deposits", headers=test_user_headers, json={"amount": 10000.0, "description": "Test deposit"})

    # BUY 10 shares
    payload_buy = {
        "instrument_id": instrument_id,
        "side": "BUY",
        "quantity": 10,
        "idempotency_key": "buy-success-1"
    }
    res_buy = client.post("/api/v1/trading/orders", headers=test_user_headers, json=payload_buy)
    assert res_buy.status_code == 200
    order_data = res_buy.json()
    assert order_data["status"] == "FILLED"
    order_id = order_data["id"]

    # Verify Holdings
    res_portfolio = client.get(f"/api/v1/portfolios/{portfolio_id}", headers=test_user_headers)
    portfolio_data = res_portfolio.json()
    
    assert float(portfolio_data["cash_balance"]) < 110000.0
    holdings = portfolio_data["holdings"]
    assert len(holdings) == 1
    assert holdings[0]["instrument_id"] == str(instrument_id)
    assert holdings[0]["quantity"] == 10
    assert float(holdings[0]["average_cost"]) == 150.6505

    # Verify Idempotency on BUY
    res_buy_2 = client.post("/api/v1/trading/orders", headers=test_user_headers, json=payload_buy)
    assert res_buy_2.status_code == 200
    assert res_buy_2.json()["id"] == order_id # Same order returned

    # Verify trades
    res_trades = client.get("/api/v1/trading/trades", headers=test_user_headers)
    trades = res_trades.json()
    assert len(trades) == 1
    assert trades[0]["order_id"] == order_id
    assert trades[0]["side"] == "BUY"

    # SELL 5 shares
    payload_sell = {
        "instrument_id": instrument_id,
        "side": "SELL",
        "quantity": 5,
        "idempotency_key": "sell-success-1"
    }
    res_sell = client.post("/api/v1/trading/orders", headers=test_user_headers, json=payload_sell)
    assert res_sell.status_code == 200
    sell_order = res_sell.json()
    assert sell_order["status"] == "FILLED"
    
    # Sell Price is 150.50. SELL spread is -0.1%, so 150.50 * 0.999 = 150.3495
    # The Realized P&L should be negative because we sold lower than we bought.
    # Diff: 150.3495 - 150.6505 = -0.301 per share. Total for 5 shares = -1.505. Then minus charges.

    # Verify Holdings
    res_portfolio_2 = client.get(f"/api/v1/portfolios/{portfolio_id}", headers=test_user_headers)
    holdings_2 = res_portfolio_2.json()["holdings"]
    assert holdings_2[0]["quantity"] == 5 # Reduced by 5
    # Average cost must NOT change
    assert float(holdings_2[0]["average_cost"]) == 150.6505

    # Verify snapshots updated
    from app.models import PortfolioSnapshot
    snapshots = db_session.execute(select(PortfolioSnapshot)).scalars().all()
    assert len(snapshots) >= 1
