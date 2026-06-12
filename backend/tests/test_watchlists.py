import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models import Instrument, Watchlist, WatchlistItem


def test_create_and_get_watchlist(client: TestClient, db_session, test_user_headers, test_user):
    # Create watchlist
    res = client.post(
        "/api/v1/watchlists",
        headers=test_user_headers,
        json={"name": "My Tech Stocks"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "My Tech Stocks"
    assert data["user_id"] == str(test_user.id)
    watchlist_id = data["id"]
    
    # Get watchlists
    res = client.get("/api/v1/watchlists", headers=test_user_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1
    
    # Get specific watchlist
    res = client.get(f"/api/v1/watchlists/{watchlist_id}", headers=test_user_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "My Tech Stocks"

def test_duplicate_watchlist_name(client: TestClient, db_session, test_user_headers):
    # Create first
    res = client.post(
        "/api/v1/watchlists",
        headers=test_user_headers,
        json={"name": "Dup List"}
    )
    assert res.status_code == 200
    
    # Create duplicate
    res = client.post(
        "/api/v1/watchlists",
        headers=test_user_headers,
        json={"name": "Dup List"}
    )
    assert res.status_code == 409

def test_add_remove_watchlist_item(client: TestClient, db_session, test_user_headers):
    # Find an instrument
    res_search = client.get("/api/v1/instruments/search?query=RELIANCE", headers=test_user_headers)
    instruments = res_search.json()
    assert len(instruments) > 0
    instrument_id = instruments[0]["id"]
    
    # Create watchlist
    res_wl = client.post(
        "/api/v1/watchlists",
        headers=test_user_headers,
        json={"name": "Add Remove List"}
    )
    watchlist_id = res_wl.json()["id"]
    
    # Add item
    res_add = client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        headers=test_user_headers,
        json={"instrument_id": instrument_id}
    )
    assert res_add.status_code == 200
    assert res_add.json()["instrument"]["id"] == instrument_id
    
    # Add duplicate item
    res_dup = client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        headers=test_user_headers,
        json={"instrument_id": instrument_id}
    )
    assert res_dup.status_code == 409
    
    # Verify it is in the list
    res_get = client.get(f"/api/v1/watchlists/{watchlist_id}", headers=test_user_headers)
    assert len(res_get.json()["items"]) == 1
    
    # Remove item
    res_del = client.delete(
        f"/api/v1/watchlists/{watchlist_id}/items/{instrument_id}",
        headers=test_user_headers
    )
    assert res_del.status_code == 204
    
    # Verify removed
    res_get_after = client.get(f"/api/v1/watchlists/{watchlist_id}", headers=test_user_headers)
    assert len(res_get_after.json()["items"]) == 0

def test_watchlist_ownership(client: TestClient, db_session, test_user_headers, test_user, setup_test_users):
    other_client = setup_test_users[1][0]
    
    # Create watchlist with user 1
    res = client.post(
        "/api/v1/watchlists",
        headers=test_user_headers,
        json={"name": "Private List"}
    )
    watchlist_id = res.json()["id"]
    
    # Try to access with user 2
    res_other = other_client.get(f"/api/v1/watchlists/{watchlist_id}")
    assert res_other.status_code == 404
