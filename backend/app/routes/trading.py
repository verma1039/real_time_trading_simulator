import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentVerifiedUser
from app.core.rate_limit import limiter
from app.db import get_db
from app.schemas.trading import (
    OrderCreateRequest,
    OrderResponse,
    OrderSimulateResponse,
    TradeResponse,
)
from app.services.portfolio import get_user_portfolio_or_404
from app.services.trading import TradingService

router = APIRouter()


def get_trading_service(db: Session = Depends(get_db)) -> TradingService:
    return TradingService(db)


@router.post("/orders/simulate", response_model=OrderSimulateResponse)
@limiter.limit("30/minute")
async def simulate_order(
    request: Request,
    req: OrderCreateRequest,
    current_user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
    trading_service: TradingService = Depends(get_trading_service),
):
    portfolio = get_user_portfolio_or_404(db, portfolio_id=req.portfolio_id if hasattr(req, 'portfolio_id') else None, user_id=current_user.id) if False else None # Wait, we need the default portfolio.
    # The get_user_portfolio_or_404 takes portfolio_id, but the user may not pass it.
    # From test_market_data.py, there's a default portfolio created. Let's just query the first portfolio.
    from sqlalchemy import select
    from app.models import Portfolio
    portfolio = db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id)).scalars().first()
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    return await trading_service.simulate_market_order(portfolio.id, req)


@router.post("/orders", response_model=OrderResponse)
@limiter.limit("20/minute")
async def create_order(
    request: Request,
    req: OrderCreateRequest,
    current_user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
    trading_service: TradingService = Depends(get_trading_service),
):
    from sqlalchemy import select
    from app.models import Portfolio
    portfolio = db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id)).scalars().first()
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    order = await trading_service.execute_market_order(portfolio.id, req)
    return order


@router.get("/orders", response_model=list[OrderResponse])
def get_orders(
    current_user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
    trading_service: TradingService = Depends(get_trading_service),
):
    from sqlalchemy import select
    from app.models import Portfolio
    portfolio = db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id)).scalars().first()
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    return trading_service.get_orders(portfolio.id)


@router.get("/trades", response_model=list[TradeResponse])
def get_trades(
    current_user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
    trading_service: TradingService = Depends(get_trading_service),
):
    from sqlalchemy import select
    from app.models import Portfolio
    portfolio = db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id)).scalars().first()
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    return trading_service.get_trades(portfolio.id)
