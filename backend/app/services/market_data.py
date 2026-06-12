import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol

import anyio
import yfinance as yf

from app.core.market_sessions import is_market_open
from app.schemas.market_data import CandleResponse, QuoteResponse

logger = logging.getLogger(__name__)


class MarketDataProvider(Protocol):
    async def get_quote(self, instrument_id: str, yahoo_symbol: str, local_symbol: str) -> QuoteResponse:
        ...

    async def get_quotes(self, items: list[dict[str, str]]) -> list[QuoteResponse]:
        """items is a list of dicts: {'instrument_id': ..., 'yahoo_symbol': ..., 'symbol': ...}"""
        ...

    async def get_historical_candles(self, yahoo_symbol: str, interval: str, period: str) -> list[CandleResponse]:
        ...


class YahooFinanceProvider(MarketDataProvider):
    def _is_stale(self, fetch_time: datetime, source_time: datetime | None) -> bool:
        if not source_time:
            return True
        # If market is closed, it's not "stale" in the sense of being outdated
        if not is_market_open(fetch_time):
            return False
            
        # If market is open, it's stale if older than 15 mins (typical YF delay) + 5 mins buffer = 20 mins
        diff = fetch_time - source_time
        return diff.total_seconds() > 1200

    def _fetch_quote_sync(self, instrument_id: str, yahoo_symbol: str, local_symbol: str) -> QuoteResponse:
        ticker = yf.Ticker(yahoo_symbol)
        info = ticker.fast_info
        
        # fast_info provides last_price, previous_close, open, etc.
        # it doesn't provide the exact trade timestamp reliably, we approximate with fetch_timestamp
        fetch_ts = datetime.now(timezone.utc)
        
        try:
            price = Decimal(str(info.last_price))
            # fast_info might raise AttributeError if symbol is invalid or no data
        except Exception:
            # Fallback to history if fast_info fails (some symbols don't have fast_info populated)
            hist = ticker.history(period="1d")
            if hist.empty:
                raise ValueError(f"No data found for symbol {yahoo_symbol}")
            row = hist.iloc[-1]
            price = Decimal(str(row["Close"]))
            
        open_price = Decimal(str(info.open)) if hasattr(info, 'open') and info.open else None
        prev_close = Decimal(str(info.previous_close)) if hasattr(info, 'previous_close') and info.previous_close else None
        vol = int(info.last_volume) if hasattr(info, 'last_volume') and info.last_volume else None
        
        is_stale = self._is_stale(fetch_ts, fetch_ts) # Approximate source_time as fetch_ts for now unless YF gives it
        
        return QuoteResponse(
            instrument_id=instrument_id,
            symbol=local_symbol,
            price=price,
            open=open_price,
            previous_close=prev_close,
            volume=vol,
            fetch_timestamp=fetch_ts,
            is_stale=is_stale
        )

    async def get_quote(self, instrument_id: str, yahoo_symbol: str, local_symbol: str) -> QuoteResponse:
        return await anyio.to_thread.run_sync(
            self._fetch_quote_sync, instrument_id, yahoo_symbol, local_symbol
        )

    def _fetch_quotes_batch_sync(self, items: list[dict[str, str]]) -> list[QuoteResponse]:
        if not items:
            return []
            
        yahoo_symbols = [item["yahoo_symbol"] for item in items]
        space_separated = " ".join(yahoo_symbols)
        
        tickers = yf.Tickers(space_separated)
        fetch_ts = datetime.now(timezone.utc)
        
        results = []
        for item in items:
            ysym = item["yahoo_symbol"]
            ticker = tickers.tickers.get(ysym)
            if not ticker:
                continue
                
            try:
                info = ticker.fast_info
                price = Decimal(str(info.last_price))
                open_price = Decimal(str(info.open)) if hasattr(info, 'open') and info.open else None
                prev_close = Decimal(str(info.previous_close)) if hasattr(info, 'previous_close') and info.previous_close else None
                vol = int(info.last_volume) if hasattr(info, 'last_volume') and info.last_volume else None
                
                results.append(QuoteResponse(
                    instrument_id=item["instrument_id"],
                    symbol=item["symbol"],
                    price=price,
                    open=open_price,
                    previous_close=prev_close,
                    volume=vol,
                    fetch_timestamp=fetch_ts,
                    is_stale=self._is_stale(fetch_ts, fetch_ts)
                ))
            except Exception as e:
                logger.warning(f"Failed to fetch batch quote for {ysym}: {e}")
                
        return results

    async def get_quotes(self, items: list[dict[str, str]]) -> list[QuoteResponse]:
        return await anyio.to_thread.run_sync(
            self._fetch_quotes_batch_sync, items
        )

    def _fetch_historical_sync(self, yahoo_symbol: str, interval: str, period: str) -> list[CandleResponse]:
        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(period=period, interval=interval)
        
        candles = []
        for ts, row in hist.iterrows():
            # Convert pandas timestamp to standard python datetime in UTC
            dt = ts.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
                
            candles.append(CandleResponse(
                timestamp=dt,
                open=Decimal(str(row["Open"])),
                high=Decimal(str(row["High"])),
                low=Decimal(str(row["Low"])),
                close=Decimal(str(row["Close"])),
                volume=int(row["Volume"])
            ))
        return candles

    async def get_historical_candles(self, yahoo_symbol: str, interval: str, period: str) -> list[CandleResponse]:
        return await anyio.to_thread.run_sync(
            self._fetch_historical_sync, yahoo_symbol, interval, period
        )


# Simple TTLCache for Quotes
from datetime import timedelta

class QuoteCache:
    def __init__(self, ttl_seconds: int = 15):
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: dict[str, tuple[datetime, QuoteResponse]] = {}

    def get(self, instrument_id: str) -> QuoteResponse | None:
        if instrument_id in self._cache:
            cached_time, response = self._cache[instrument_id]
            if datetime.now(timezone.utc) - cached_time <= self.ttl:
                return response
            else:
                del self._cache[instrument_id]
        return None

    def set(self, instrument_id: str, response: QuoteResponse) -> None:
        self._cache[instrument_id] = (datetime.now(timezone.utc), response)

    def invalidate(self, instrument_id: str) -> None:
        self._cache.pop(instrument_id, None)


# Global instances
market_data_provider = YahooFinanceProvider()
quote_cache = QuoteCache(ttl_seconds=15)
