from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

from app.models import InstrumentType, LedgerEntryType


class AmountRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=4)
    description: str | None = Field(None, max_length=255)


class HoldingResponse(BaseModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    symbol: str
    name: str
    instrument_type: InstrumentType
    quantity: int
    average_cost: Decimal

    model_config = ConfigDict(from_attributes=True)


class PortfolioValuation(BaseModel):
    cash_balance: Decimal
    holdings_value: Decimal
    total_portfolio_value: Decimal
    invested_cost: Decimal
    realized_pnl: Decimal  # Realized PnL is from Trades, but we can pass it in if computed
    unrealized_pnl: Decimal
    total_pnl: Decimal


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    opening_balance: Decimal
    cash_balance: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioDetailResponse(PortfolioResponse):
    valuation: PortfolioValuation
    holdings: list[HoldingResponse]


class CashLedgerEntryResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    trade_id: uuid.UUID | None
    entry_type: LedgerEntryType
    amount: Decimal
    balance_after: Decimal
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PortfolioSnapshotResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    snapshot_date: date
    cash_balance: Decimal
    holdings_value: Decimal
    total_portfolio_value: Decimal
    invested_cost: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
