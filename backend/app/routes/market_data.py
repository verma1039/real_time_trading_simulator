import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentVerifiedUser
from app.db import get_db
from app.schemas.market_data import BatchQuoteRequest, CandleResponse, QuoteResponse
from app.services.instrument import get_instrument
from app.services.market_data import market_data_provider, quote_cache
from app.core.errors import NotFoundError

router = APIRouter()


@router.get("/quotes/{instrument_id}", response_model=QuoteResponse)
async def get_quote(
    instrument_id: uuid.UUID,
    user: CurrentVerifiedUser = None,
    db: Session = Depends(get_db),
):
    """Fetch live quote for a specific instrument (with 15s cache)."""
    # Check cache first
    cached_quote = quote_cache.get(str(instrument_id))
    if cached_quote:
        return cached_quote

    instrument = get_instrument(db, instrument_id)
    if not instrument:
        raise NotFoundError("Instrument not found.")

    quote = await market_data_provider.get_quote(
        instrument_id=str(instrument.id),
        yahoo_symbol=instrument.yahoo_symbol,
        local_symbol=instrument.symbol
    )
    
    quote_cache.set(str(instrument_id), quote)
    return quote


@router.post("/quotes/batch", response_model=list[QuoteResponse])
async def get_quotes_batch(
    req: BatchQuoteRequest,
    user: CurrentVerifiedUser = None,
    db: Session = Depends(get_db),
):
    """Fetch live quotes for multiple instruments (with 15s cache)."""
    instrument_ids = req.instrument_ids
    if not instrument_ids:
        return []

    results = []
    missing_ids = []

    # Check cache first
    for iid in instrument_ids:
        cached_quote = quote_cache.get(str(iid))
        if cached_quote:
            results.append(cached_quote)
        else:
            missing_ids.append(iid)

    if not missing_ids:
        return results

    # Fetch missing from DB
    from app.models import Instrument
    from sqlalchemy import select
    instruments = db.execute(
        select(Instrument).where(Instrument.id.in_(missing_ids))
    ).scalars().all()

    if not instruments:
        return results

    items_to_fetch = [
        {
            "instrument_id": str(inst.id),
            "yahoo_symbol": inst.yahoo_symbol,
            "symbol": inst.symbol
        }
        for inst in instruments
    ]

    fetched_quotes = await market_data_provider.get_quotes(items=items_to_fetch)
    
    for quote in fetched_quotes:
        quote_cache.set(str(quote.instrument_id), quote)
        results.append(quote)

    return results


@router.get("/historical/{instrument_id}", response_model=list[CandleResponse])
async def get_historical_candles(
    instrument_id: uuid.UUID,
    interval: str = Query("1d", description="Valid intervals: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo"),
    period: str = Query("1mo", description="Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"),
    user: CurrentVerifiedUser = None,
    db: Session = Depends(get_db),
):
    """Fetch historical OHLCV data for charts."""
    instrument = get_instrument(db, instrument_id)
    if not instrument:
        raise NotFoundError("Instrument not found.")

    candles = await market_data_provider.get_historical_candles(
        yahoo_symbol=instrument.yahoo_symbol,
        interval=interval,
        period=period
    )
    return candles
