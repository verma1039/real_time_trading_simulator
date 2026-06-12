import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderSide, OrderStatus, OrderType


class OrderCreateRequest(BaseModel):
    instrument_id: uuid.UUID
    side: OrderSide
    quantity: int = Field(gt=0, description="Number of shares to trade")
    idempotency_key: str = Field(min_length=1, max_length=100)


class OrderSimulateResponse(BaseModel):
    instrument_id: uuid.UUID
    side: OrderSide
    quantity: int
    quote_price: Decimal
    execution_price: Decimal
    gross_amount: Decimal
    brokerage: Decimal
    taxes: Decimal
    other_charges: Decimal
    total_charges: Decimal
    net_amount: Decimal
    is_market_open: bool
    is_quote_stale: bool
    sufficient_funds: bool | None = None
    sufficient_holdings: bool | None = None


class OrderResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    instrument_id: uuid.UUID
    idempotency_key: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    quantity: int
    limit_price: Decimal | None = None
    quote_price: Decimal | None = None
    quote_timestamp: datetime | None = None
    quote_fetched_at: datetime | None = None
    rejection_reason: str | None = None
    executed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TradeResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    portfolio_id: uuid.UUID
    instrument_id: uuid.UUID
    side: OrderSide
    quantity: int
    execution_price: Decimal
    gross_amount: Decimal
    brokerage: Decimal
    taxes: Decimal
    other_charges: Decimal
    total_charges: Decimal
    realized_pnl: Decimal
    quote_timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
