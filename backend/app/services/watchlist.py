import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import ConflictError, NotFoundError
from app.models import Instrument, Watchlist, WatchlistItem


def get_user_watchlist_or_404(db: Session, watchlist_id: uuid.UUID, user_id: uuid.UUID) -> Watchlist:
    """Fetch a watchlist and ensure it belongs to the user."""
    watchlist = db.execute(
        select(Watchlist)
        .options(joinedload(Watchlist.items).joinedload(WatchlistItem.instrument))
        .where(Watchlist.id == watchlist_id)
    ).unique().scalar_one_or_none()
    
    if watchlist is None or watchlist.user_id != user_id:
        raise NotFoundError("Watchlist not found.")
        
    return watchlist


def create_watchlist(db: Session, *, user_id: uuid.UUID, name: str) -> Watchlist:
    watchlist = Watchlist(user_id=user_id, name=name)
    db.add(watchlist)
    try:
        db.commit()
        db.refresh(watchlist)
    except IntegrityError:
        db.rollback()
        raise ConflictError("A watchlist with this name already exists.")
    return watchlist


def get_user_watchlists(db: Session, user_id: uuid.UUID) -> list[Watchlist]:
    return list(db.execute(
        select(Watchlist)
        .options(joinedload(Watchlist.items).joinedload(WatchlistItem.instrument))
        .where(Watchlist.user_id == user_id)
        .order_by(Watchlist.name)
    ).unique().scalars().all())


def add_instrument_to_watchlist(db: Session, *, watchlist_id: uuid.UUID, user_id: uuid.UUID, instrument_id: uuid.UUID) -> WatchlistItem:
    # Verify ownership
    get_user_watchlist_or_404(db, watchlist_id, user_id)
    
    # Verify instrument exists
    instrument = db.execute(select(Instrument).where(Instrument.id == instrument_id)).scalar_one_or_none()
    if not instrument:
        raise NotFoundError("Instrument not found.")
        
    item = WatchlistItem(watchlist_id=watchlist_id, instrument_id=instrument_id)
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
        # Load instrument relationship for response
        item.instrument = instrument
    except IntegrityError:
        db.rollback()
        raise ConflictError("Instrument is already in this watchlist.")
        
    return item


def remove_instrument_from_watchlist(db: Session, *, watchlist_id: uuid.UUID, user_id: uuid.UUID, instrument_id: uuid.UUID) -> None:
    # Verify ownership
    get_user_watchlist_or_404(db, watchlist_id, user_id)
    
    item = db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.watchlist_id == watchlist_id, WatchlistItem.instrument_id == instrument_id)
    ).scalar_one_or_none()
    
    if not item:
        raise NotFoundError("Instrument not found in watchlist.")
        
    db.delete(item)
    db.commit()

def delete_watchlist(db: Session, *, watchlist_id: uuid.UUID, user_id: uuid.UUID) -> None:
    watchlist = get_user_watchlist_or_404(db, watchlist_id, user_id)
    db.delete(watchlist)
    db.commit()
