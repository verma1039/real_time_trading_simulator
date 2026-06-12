import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db import SessionLocal
from app.models import Instrument, InstrumentType, User, UserRole
from app.core.security import get_password_hash

def seed_db():
    db = SessionLocal()
    try:
        # Seed initial instruments if they don't exist
        print("Seeding instruments...")
        instruments = [
            {"symbol": "RELIANCE", "yahoo_symbol": "RELIANCE.NS", "exchange": "NSE", "name": "Reliance Industries", "instrument_type": InstrumentType.EQUITY},
            {"symbol": "TCS", "yahoo_symbol": "TCS.NS", "exchange": "NSE", "name": "Tata Consultancy Services", "instrument_type": InstrumentType.EQUITY},
            {"symbol": "HDFCBANK", "yahoo_symbol": "HDFCBANK.NS", "exchange": "NSE", "name": "HDFC Bank", "instrument_type": InstrumentType.EQUITY},
            {"symbol": "INFY", "yahoo_symbol": "INFY.NS", "exchange": "NSE", "name": "Infosys", "instrument_type": InstrumentType.EQUITY},
            {"symbol": "ICICIBANK", "yahoo_symbol": "ICICIBANK.NS", "exchange": "NSE", "name": "ICICI Bank", "instrument_type": InstrumentType.EQUITY},
        ]
        
        for inst in instruments:
            exists = db.query(Instrument).filter_by(symbol=inst["symbol"]).first()
            if not exists:
                new_inst = Instrument(
                    symbol=inst["symbol"],
                    yahoo_symbol=inst["yahoo_symbol"],
                    exchange=inst["exchange"],
                    name=inst["name"],
                    instrument_type=inst["instrument_type"],
                    is_active=True,
                    is_tradeable=True
                )
                db.add(new_inst)
                print(f"Added instrument: {inst['symbol']}")
        db.commit()

        # Seed admin user
        print("Seeding initial admin user...")
        admin_email = os.environ.get("ADMIN_INITIAL_EMAIL")
        admin_password = os.environ.get("ADMIN_INITIAL_PASSWORD")

        if admin_email and admin_password:
            admin_user = db.query(User).filter_by(email=admin_email).first()
            if not admin_user:
                new_admin = User(
                    email=admin_email,
                    hashed_password=get_password_hash(admin_password),
                    display_name="System Admin",
                    role=UserRole.ADMIN,
                    is_verified=True,
                    is_suspended=False
                )
                db.add(new_admin)
                db.commit()
                print(f"Admin user created: {admin_email}")
            else:
                print(f"Admin user {admin_email} already exists.")
        else:
            print("ADMIN_INITIAL_EMAIL or ADMIN_INITIAL_PASSWORD not set. Skipping admin creation.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
