import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentVerifiedUser
from app.db import get_db
from app.schemas.market_data import InstrumentResponse
from app.services.instrument import get_instrument, search_instruments
from app.core.errors import NotFoundError

router = APIRouter()


@router.get("/search", response_model=list[InstrumentResponse])
def search(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, le=100),
    user: CurrentVerifiedUser = None,
    db: Session = Depends(get_db),
):
    """Search for instruments in the database."""
    instruments = search_instruments(db, query, limit)
    return instruments


@router.get("/{instrument_id}", response_model=InstrumentResponse)
def get_single_instrument(
    instrument_id: uuid.UUID,
    user: CurrentVerifiedUser = None,
    db: Session = Depends(get_db),
):
    """Get instrument details by ID."""
    instrument = get_instrument(db, instrument_id)
    if not instrument:
        raise NotFoundError("Instrument not found.")
    return instrument
