import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentVerifiedUser
from app.db import get_db
from app.models import CashLedgerEntry, Holding, Portfolio
from app.schemas.portfolio import (
    AmountRequest,
    CashLedgerEntryResponse,
    HoldingResponse,
    PortfolioDetailResponse,
    PortfolioResponse,
)
from app.services.portfolio import (
    calculate_portfolio_valuation,
    deposit_cash,
    get_user_portfolio_or_404,
    reset_portfolio,
    withdraw_cash,
)

router = APIRouter()


@router.get("/", response_model=list[PortfolioResponse])
def get_portfolios(
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Get all portfolios for the current user."""
    portfolios = db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id)
    ).scalars().all()
    return portfolios


@router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
def get_portfolio(
    portfolio_id: uuid.UUID,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Get a portfolio with its holdings and real-time valuation."""
    portfolio = get_user_portfolio_or_404(db, portfolio_id, user.id)
    
    # In Phase 3, we don't have real market prices, so pass empty dict.
    # The valuation service will gracefully fall back to average_cost.
    holdings = db.execute(
        select(Holding).where(Holding.portfolio_id == portfolio.id)
    ).scalars().all()
    
    valuation = calculate_portfolio_valuation(portfolio, list(holdings), {})
    
    # We need to map holdings to response.
    # Note: Holding model doesn't store 'symbol' or 'name' directly (it's in Instrument).
    # We need a join. Let's do a join query for the holdings.
    from app.models import Instrument
    holdings_with_instruments = db.execute(
        select(Holding, Instrument)
        .join(Instrument, Holding.instrument_id == Instrument.id)
        .where(Holding.portfolio_id == portfolio.id, Holding.quantity > 0)
    ).all()
    
    holdings_response = []
    for h, i in holdings_with_instruments:
        holdings_response.append(HoldingResponse(
            id=h.id,
            instrument_id=i.id,
            symbol=i.symbol,
            name=i.name,
            instrument_type=i.instrument_type,
            quantity=h.quantity,
            average_cost=h.average_cost
        ))

    return PortfolioDetailResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        name=portfolio.name,
        opening_balance=portfolio.opening_balance,
        cash_balance=portfolio.cash_balance,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
        valuation=valuation,
        holdings=holdings_response,
    )


@router.post("/{portfolio_id}/deposits", response_model=CashLedgerEntryResponse)
def deposit(
    portfolio_id: uuid.UUID,
    req: AmountRequest,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Deposit virtual cash into the portfolio."""
    # The service will check ownership via locking
    entry = deposit_cash(db, portfolio_id=portfolio_id, user_id=user.id, amount=req.amount, description=req.description)
    return entry


@router.post("/{portfolio_id}/withdrawals", response_model=CashLedgerEntryResponse)
def withdraw(
    portfolio_id: uuid.UUID,
    req: AmountRequest,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Withdraw virtual cash from the portfolio."""
    entry = withdraw_cash(db, portfolio_id=portfolio_id, user_id=user.id, amount=req.amount, description=req.description)
    return entry


@router.post("/{portfolio_id}/reset", response_model=PortfolioResponse)
def reset(
    portfolio_id: uuid.UUID,
    user: CurrentVerifiedUser,
    db: Session = Depends(get_db),
):
    """Reset the portfolio back to its opening balance and wipe all holdings."""
    portfolio = reset_portfolio(db, portfolio_id=portfolio_id, user_id=user.id)
    return portfolio


@router.get("/{portfolio_id}/ledger", response_model=list[CashLedgerEntryResponse])
def get_ledger(
    portfolio_id: uuid.UUID,
    user: CurrentVerifiedUser,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get the cash ledger history for a portfolio."""
    # Ensure it belongs to user
    get_user_portfolio_or_404(db, portfolio_id, user.id)
    
    entries = db.execute(
        select(CashLedgerEntry)
        .where(CashLedgerEntry.portfolio_id == portfolio_id)
        .order_by(CashLedgerEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    
    return entries
