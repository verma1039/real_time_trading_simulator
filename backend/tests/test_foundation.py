"""Foundation tests — schema registration, constraints, endpoints, error format."""

from app import models  # noqa: F401
from app.db import Base


# ---------------------------------------------------------------------------
# Schema registration
# ---------------------------------------------------------------------------
def test_mvp_schema_is_registered() -> None:
    assert set(Base.metadata.tables) == {
        "admin_logs",
        "cash_ledger",
        "email_verification_tokens",
        "holdings",
        "instruments",
        "login_sessions",
        "orders",
        "password_reset_tokens",
        "portfolio_snapshots",
        "portfolios",
        "trades",
        "users",
        "watchlist_items",
        "watchlists",
    }


# ---------------------------------------------------------------------------
# Constraint presence
# ---------------------------------------------------------------------------
def test_watchlist_ownership_constraints_are_present() -> None:
    watchlists = Base.metadata.tables["watchlists"]
    items = Base.metadata.tables["watchlist_items"]

    assert watchlists.c.user_id.nullable is False
    assert items.c.watchlist_id.nullable is False
    assert {fk.target_fullname for fk in watchlists.c.user_id.foreign_keys} == {"users.id"}
    assert {fk.target_fullname for fk in items.c.watchlist_id.foreign_keys} == {"watchlists.id"}

    watchlist_unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in watchlists.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    item_unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in items.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("user_id", "name") in watchlist_unique_columns
    assert ("watchlist_id", "instrument_id") in item_unique_columns


def test_snapshot_uniqueness_is_present() -> None:
    snapshots = Base.metadata.tables["portfolio_snapshots"]
    unique_column_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in snapshots.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("portfolio_id", "snapshot_date") in unique_column_sets


# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------
def test_health_endpoint(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body


# ---------------------------------------------------------------------------
# Error format
# ---------------------------------------------------------------------------
def test_unknown_route_returns_standard_error(client) -> None:
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"
    assert "message" in body["error"]


def test_method_not_allowed_returns_standard_error(client) -> None:
    response = client.delete("/health")
    assert response.status_code == 405
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"
