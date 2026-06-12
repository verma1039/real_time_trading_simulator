from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

IST_TZ = ZoneInfo("Asia/Kolkata")

# NSE/BSE Market Hours (Equities)
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)

# Static NSE/BSE holidays for the current year (e.g. 2026)
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 3),    # Holi (Estimated)
    date(2026, 3, 20),   # Eid-Ul-Fitr (Estimated)
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra (Estimated)
    date(2026, 11, 8),   # Diwali-Laxmi Pujan (Estimated)
    date(2026, 11, 24),  # Gurunanak Jayanti (Estimated)
    date(2026, 12, 25),  # Christmas
}

def is_market_open(dt_utc: datetime | None = None) -> bool:
    """Check if the Indian equity market is currently open."""
    dt = dt_utc or datetime.now(timezone.utc)
    ist_time = dt.astimezone(IST_TZ)
    
    # Check weekends (5 = Saturday, 6 = Sunday)
    if ist_time.weekday() >= 5:
        return False
        
    # Check static holiday calendar
    if ist_time.date() in NSE_HOLIDAYS_2026:
        return False
        
    # Check market hours
    current_time = ist_time.time()
    if not (MARKET_OPEN <= current_time <= MARKET_CLOSE):
        return False
        
    return True
