import uuid
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Instrument


def search_instruments(db: Session, query: str, limit: int = 20) -> list[Instrument]:
    """Search for instruments by symbol or name."""
    search_term = f"%{query}%"
    
    instruments = db.execute(
        select(Instrument)
        .where(
            or_(
                Instrument.symbol.ilike(search_term),
                Instrument.name.ilike(search_term)
            ),
            Instrument.is_active == True
        )
        .limit(limit)
    ).scalars().all()
    
    return list(instruments)

def get_instrument(db: Session, instrument_id: uuid.UUID) -> Instrument | None:
    return db.execute(
        select(Instrument).where(Instrument.id == instrument_id)
    ).scalar_one_or_none()
