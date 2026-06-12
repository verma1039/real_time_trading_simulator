import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.market_data import InstrumentResponse, QuoteResponse


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WatchlistItemResponse(BaseModel):
    id: uuid.UUID
    instrument: InstrumentResponse
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchlistResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    items: list[WatchlistItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchlistItemCreate(BaseModel):
    instrument_id: uuid.UUID
