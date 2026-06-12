from datetime import datetime
from decimal import Decimal
import uuid

from pydantic import BaseModel, ConfigDict, Field


class InstrumentResponse(BaseModel):
    id: uuid.UUID
    symbol: str
    yahoo_symbol: str
    exchange: str
    name: str
    instrument_type: str
    tick_size: Decimal
    is_active: bool
    is_tradeable: bool

    model_config = ConfigDict(from_attributes=True)


class QuoteResponse(BaseModel):
    instrument_id: uuid.UUID
    symbol: str
    price: Decimal
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    previous_close: Decimal | None = None
    volume: int | None = None
    source_timestamp: datetime | None = None
    fetch_timestamp: datetime
    is_stale: bool


class CandleResponse(BaseModel):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
