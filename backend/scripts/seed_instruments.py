import os
import sys

# Add the project root to the path so we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Instrument, InstrumentType

NIFTY_50 = [
    ("RELIANCE", "RELIANCE.NS", "NSE", "Reliance Industries Limited"),
    ("TCS", "TCS.NS", "NSE", "Tata Consultancy Services Limited"),
    ("HDFCBANK", "HDFCBANK.NS", "NSE", "HDFC Bank Limited"),
    ("ICICIBANK", "ICICIBANK.NS", "NSE", "ICICI Bank Limited"),
    ("BHARTIARTL", "BHARTIARTL.NS", "NSE", "Bharti Airtel Limited"),
    ("INFY", "INFY.NS", "NSE", "Infosys Limited"),
    ("ITC", "ITC.NS", "NSE", "ITC Limited"),
    ("HINDUNILVR", "HINDUNILVR.NS", "NSE", "Hindustan Unilever Limited"),
    ("LT", "LT.NS", "NSE", "Larsen & Toubro Limited"),
    ("SBIN", "SBIN.NS", "NSE", "State Bank of India"),
    ("BAJFINANCE", "BAJFINANCE.NS", "NSE", "Bajaj Finance Limited"),
    ("KOTAKBANK", "KOTAKBANK.NS", "NSE", "Kotak Mahindra Bank Limited"),
    ("AXISBANK", "AXISBANK.NS", "NSE", "Axis Bank Limited"),
    ("M&M", "M&M.NS", "NSE", "Mahindra & Mahindra Limited"),
    ("TATOMOTORS", "TATAMOTORS.NS", "NSE", "Tata Motors Limited"),
    ("MARUTI", "MARUTI.NS", "NSE", "Maruti Suzuki India Limited"),
    ("SUNPHARMA", "SUNPHARMA.NS", "NSE", "Sun Pharmaceutical Industries Limited"),
    ("ASIANPAINT", "ASIANPAINT.NS", "NSE", "Asian Paints Limited"),
    ("HCLTECH", "HCLTECH.NS", "NSE", "HCL Technologies Limited"),
    ("TITAN", "TITAN.NS", "NSE", "Titan Company Limited"),
    ("BAJAJFINSV", "BAJAJFINSV.NS", "NSE", "Bajaj Finserv Limited"),
    ("NTPC", "NTPC.NS", "NSE", "NTPC Limited"),
    ("ONGC", "ONGC.NS", "NSE", "Oil & Natural Gas Corporation Limited"),
    ("POWERGRID", "POWERGRID.NS", "NSE", "Power Grid Corporation of India Limited"),
    ("ULTRACEMCO", "ULTRACEMCO.NS", "NSE", "UltraTech Cement Limited"),
    ("WIPRO", "WIPRO.NS", "NSE", "Wipro Limited"),
    ("JSWSTEEL", "JSWSTEEL.NS", "NSE", "JSW Steel Limited"),
    ("TATASTEEL", "TATASTEEL.NS", "NSE", "Tata Steel Limited"),
    ("HINDALCO", "HINDALCO.NS", "NSE", "Hindalco Industries Limited"),
    ("GRASIM", "GRASIM.NS", "NSE", "Grasim Industries Limited"),
    ("LTIM", "LTIM.NS", "NSE", "LTIMindtree Limited"),
    ("DRREDDY", "DRREDDY.NS", "NSE", "Dr. Reddy's Laboratories Limited"),
    ("ADANIENT", "ADANIENT.NS", "NSE", "Adani Enterprises Limited"),
    ("ADANIPORTS", "ADANIPORTS.NS", "NSE", "Adani Ports and Special Economic Zone Limited"),
    ("INDUSINDBK", "INDUSINDBK.NS", "NSE", "IndusInd Bank Limited"),
    ("NESTLEIND", "NESTLEIND.NS", "NSE", "Nestle India Limited"),
    ("EICHERMOT", "EICHERMOT.NS", "NSE", "Eicher Motors Limited"),
    ("BRITANNIA", "BRITANNIA.NS", "NSE", "Britannia Industries Limited"),
    ("APOLLOHOSP", "APOLLOHOSP.NS", "NSE", "Apollo Hospitals Enterprise Limited"),
    ("CIPLA", "CIPLA.NS", "NSE", "Cipla Limited"),
    ("DIVISLAB", "DIVISLAB.NS", "NSE", "Divi's Laboratories Limited"),
    ("BAJAJ-AUTO", "BAJAJ-AUTO.NS", "NSE", "Bajaj Auto Limited"),
    ("HEROMOTOCO", "HEROMOTOCO.NS", "NSE", "Hero MotoCorp Limited"),
    ("TRENT", "TRENT.NS", "NSE", "Trent Limited"),
    ("SHRIRAMFIN", "SHRIRAMFIN.NS", "NSE", "Shriram Finance Limited"),
    ("BEL", "BEL.NS", "NSE", "Bharat Electronics Limited"),
    ("BPCL", "BPCL.NS", "NSE", "Bharat Petroleum Corporation Limited"),
    ("COALINDIA", "COALINDIA.NS", "NSE", "Coal India Limited"),
    ("TATACONSUM", "TATACONSUM.NS", "NSE", "Tata Consumer Products Limited"),
    ("TECHM", "TECHM.NS", "NSE", "Tech Mahindra Limited"),
]

def seed_instruments(db: Session):
    print("Seeding NIFTY 50 instruments...")
    count = 0
    for symbol, yahoo_symbol, exchange, name in NIFTY_50:
        instrument = Instrument(
            symbol=symbol,
            yahoo_symbol=yahoo_symbol,
            exchange=exchange,
            name=name,
            instrument_type=InstrumentType.EQUITY,
            is_active=True,
            is_tradeable=True
        )
        db.add(instrument)
        try:
            db.commit()
            count += 1
        except IntegrityError:
            db.rollback()
            print(f"Skipping {symbol} - already exists.")
            
    print(f"Successfully seeded {count} new instruments.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_instruments(db)
    finally:
        db.close()
