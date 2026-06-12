"""Central API v1 router.

All feature routers are included here and the single `api_v1` router
is mounted on the FastAPI app in main.py under the /api/v1 prefix.
"""

from fastapi import APIRouter

from app.routes import auth, portfolio, instruments, market_data, watchlists, trading

api_v1 = APIRouter()

api_v1.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1.include_router(portfolio.router, prefix="/portfolios", tags=["portfolio"])
api_v1.include_router(instruments.router, prefix="/instruments", tags=["instruments"])
api_v1.include_router(market_data.router, prefix="/market-data", tags=["market_data"])
api_v1.include_router(watchlists.router, prefix="/watchlists", tags=["watchlists"])
api_v1.include_router(trading.router, prefix="/trading", tags=["trading"])
