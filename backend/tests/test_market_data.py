import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.schemas.market_data import QuoteResponse, CandleResponse
from app.services.market_data import MarketDataProvider


class MockProvider(MarketDataProvider):
    async def get_quote(self, instrument_id: str, yahoo_symbol: str, local_symbol: str) -> QuoteResponse:
        return QuoteResponse(
            instrument_id=uuid.UUID(instrument_id),
            symbol=local_symbol,
            price=Decimal("150.50"),
            open=Decimal("150.00"),
            previous_close=Decimal("149.00"),
            volume=1000,
            fetch_timestamp=datetime.now(timezone.utc),
            is_stale=False
        )

    async def get_quotes(self, items: list[dict[str, str]]) -> list[QuoteResponse]:
        res = []
        for item in items:
            res.append(QuoteResponse(
                instrument_id=uuid.UUID(item["instrument_id"]),
                symbol=item["symbol"],
                price=Decimal("150.50"),
                open=Decimal("150.00"),
                previous_close=Decimal("149.00"),
                volume=1000,
                fetch_timestamp=datetime.now(timezone.utc),
                is_stale=False
            ))
        return res

    async def get_historical_candles(self, yahoo_symbol: str, interval: str, period: str) -> list[CandleResponse]:
        return [
            CandleResponse(
                timestamp=datetime.now(timezone.utc),
                open=Decimal("150.00"),
                high=Decimal("155.00"),
                low=Decimal("149.00"),
                close=Decimal("152.00"),
                volume=5000
            )
        ]


@pytest.fixture(autouse=True)
def mock_market_provider(monkeypatch):
    import app.routes.market_data
    import app.routes.watchlists
    
    mock = MockProvider()
    monkeypatch.setattr(app.routes.market_data, "market_data_provider", mock)
    monkeypatch.setattr(app.routes.watchlists, "market_data_provider", mock)
    
    # Also clear cache
    from app.services.market_data import quote_cache
    quote_cache._cache.clear()


def test_get_instrument_quote(client: TestClient, db_session, test_user_headers):
    # Find an instrument
    res_search = client.get("/api/v1/instruments/search?query=RELIANCE", headers=test_user_headers)
    instruments = res_search.json()
    assert len(instruments) > 0
    instrument_id = instruments[0]["id"]
    
    res = client.get(f"/api/v1/market-data/quotes/{instrument_id}", headers=test_user_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "RELIANCE"
    assert float(data["price"]) == 150.5
    assert data["is_stale"] is False

def test_get_watchlist_quotes(client: TestClient, db_session, test_user_headers):
    # Find an instrument
    res_search = client.get("/api/v1/instruments/search?query=RELIANCE", headers=test_user_headers)
    instrument_id = res_search.json()[0]["id"]
    
    # Create watchlist and add instrument
    res_wl = client.post("/api/v1/watchlists", headers=test_user_headers, json={"name": "Quote List"})
    watchlist_id = res_wl.json()["id"]
    
    client.post(f"/api/v1/watchlists/{watchlist_id}/items", headers=test_user_headers, json={"instrument_id": instrument_id})
    
    # Fetch quotes
    res_quotes = client.get(f"/api/v1/watchlists/{watchlist_id}/quotes", headers=test_user_headers)
    assert res_quotes.status_code == 200
    quotes = res_quotes.json()
    assert len(quotes) == 1
    assert quotes[0]["symbol"] == "RELIANCE"
    assert float(quotes[0]["price"]) == 150.5

def test_get_historical_candles(client: TestClient, db_session, test_user_headers):
    res_search = client.get("/api/v1/instruments/search?query=RELIANCE", headers=test_user_headers)
    instrument_id = res_search.json()[0]["id"]
    
    res = client.get(f"/api/v1/market-data/historical/{instrument_id}?interval=1d&period=1mo", headers=test_user_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert float(data[0]["open"]) == 150.0
    assert float(data[0]["close"]) == 152.0
