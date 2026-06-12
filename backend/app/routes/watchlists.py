import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentVerifiedUser
from app.db import get_db
from app.schemas.market_data import QuoteResponse
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemResponse,
    WatchlistResponse,
)
from app.services.market_data import market_data_provider, quote_cache
from app.services.watchlist import (
    add_instrument_to_watchlist,
    create_watchlist,
    get_user_watchlist_or_404,
    get_user_watchlists,
    remove_instrument_from_watchlist,
)

router = APIRouter()


@router.post("", response_model=WatchlistResponse)
def create_new_watchlist(
    data: WatchlistCreate,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Create a new watchlist."""
    return create_watchlist(db, user_id=user.id, name=data.name)


@router.get("", response_model=list[WatchlistResponse])
def get_watchlists(
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """List all watchlists for the current user."""
    return get_user_watchlists(db, user_id=user.id)


@router.get("/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(
    watchlist_id: uuid.UUID,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Get details of a specific watchlist."""
    return get_user_watchlist_or_404(db, watchlist_id, user.id)


@router.post("/{watchlist_id}/items", response_model=WatchlistItemResponse)
def add_item_to_watchlist(
    watchlist_id: uuid.UUID,
    data: WatchlistItemCreate,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Add an instrument to a watchlist."""
    return add_instrument_to_watchlist(
        db, 
        watchlist_id=watchlist_id, 
        user_id=user.id, 
        instrument_id=data.instrument_id
    )


@router.delete("/{watchlist_id}/items/{instrument_id}", status_code=204)
def remove_item_from_watchlist(
    watchlist_id: uuid.UUID,
    instrument_id: uuid.UUID,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Remove an instrument from a watchlist."""
    remove_instrument_from_watchlist(
        db, 
        watchlist_id=watchlist_id, 
        user_id=user.id, 
        instrument_id=instrument_id
    )


@router.get("/{watchlist_id}/quotes", response_model=list[QuoteResponse])
async def get_watchlist_quotes(
    watchlist_id: uuid.UUID,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Fetch live quotes for all instruments in a watchlist using batch retrieval."""
    watchlist = get_user_watchlist_or_404(db, watchlist_id, user.id)
    
    if not watchlist.items:
        return []
        
    items_to_fetch = []
    responses = []
    
    # Check cache first
    for item in watchlist.items:
        inst_id_str = str(item.instrument.id)
        cached = quote_cache.get(inst_id_str)
        if cached:
            responses.append(cached)
        else:
            items_to_fetch.append({
                "instrument_id": inst_id_str,
                "yahoo_symbol": item.instrument.yahoo_symbol,
                "symbol": item.instrument.symbol
            })
            
    # Fetch missing quotes in batch
    if items_to_fetch:
        batch_responses = await market_data_provider.get_quotes(items_to_fetch)
        for resp in batch_responses:
            quote_cache.set(str(resp.instrument_id), resp)
            responses.append(resp)
            
    return responses
