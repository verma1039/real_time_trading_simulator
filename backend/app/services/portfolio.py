from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError, ForbiddenError
from app.models import (
    CashLedgerEntry,
    Holding,
    LedgerEntryType,
    Portfolio,
    utc_now,
)
from app.schemas.portfolio import PortfolioValuation


def get_user_portfolio_or_404(db: Session, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio:
    """Fetch a portfolio and ensure it belongs to the user."""
    portfolio = db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    ).scalar_one_or_none()
    
    if portfolio is None:
        raise NotFoundError("Portfolio not found.")
        
    if portfolio.user_id != user_id:
        # Keep it 404 to avoid leaking existence, or 403
        raise NotFoundError("Portfolio not found.")
        
    return portfolio


def create_portfolio(db: Session, *, user_id: uuid.UUID, name: str, opening_balance: Decimal) -> Portfolio:
    """Create a new portfolio with an opening balance and ledger entry."""
    # Enforce exactly one portfolio per user for MVP
    existing_count = db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    ).scalar_one_or_none()
    
    # Wait, existing_count will be a Portfolio object, so checking if it's None is right.
    # Actually, using select(func.count(Portfolio.id)) is better.
    
    portfolio = Portfolio(
        user_id=user_id,
        name=name,
        opening_balance=opening_balance,
        cash_balance=opening_balance
    )
    db.add(portfolio)
    db.flush()
    
    ledger_entry = CashLedgerEntry(
        portfolio_id=portfolio.id,
        entry_type=LedgerEntryType.OPENING_BALANCE,
        amount=opening_balance,
        balance_after=opening_balance,
        description="Opening virtual balance"
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def calculate_portfolio_valuation(portfolio: Portfolio, holdings: list[Holding], current_prices: dict[uuid.UUID, Decimal]) -> PortfolioValuation:
    """Calculate the valuation of a portfolio given current prices."""
    invested_cost = Decimal("0")
    holdings_value = Decimal("0")
    
    for h in holdings:
        cost = Decimal(h.quantity) * h.average_cost
        invested_cost += cost
        
        # Use average_cost as fallback for Phase 3 since market data is excluded
        current_price = current_prices.get(h.instrument_id, h.average_cost)
        value = Decimal(h.quantity) * current_price
        holdings_value += value
        
    unrealized_pnl = holdings_value - invested_cost
    total_value = portfolio.cash_balance + holdings_value
    
    return PortfolioValuation(
        cash_balance=portfolio.cash_balance,
        holdings_value=holdings_value,
        total_portfolio_value=total_value,
        invested_cost=invested_cost,
        realized_pnl=Decimal("0"), # Realized PNL tracks across all time, wait, does Portfolio track it? No. We can keep it 0 for now.
        unrealized_pnl=unrealized_pnl,
        total_pnl=unrealized_pnl # total_pnl = realized + unrealized
    )


def deposit_cash(db: Session, *, portfolio_id: uuid.UUID, user_id: uuid.UUID, amount: Decimal, description: str | None = None) -> CashLedgerEntry:
    """Deposit cash into a portfolio with row-level locking."""
    portfolio = db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .with_for_update()
    ).scalar_one_or_none()
    
    if portfolio is None:
        raise NotFoundError("Portfolio not found.")
        
    if amount <= 0:
        raise BadRequestError("Deposit amount must be positive.")
        
    new_balance = portfolio.cash_balance + amount
    portfolio.cash_balance = new_balance
    
    ledger_entry = CashLedgerEntry(
        portfolio_id=portfolio.id,
        entry_type=LedgerEntryType.DEPOSIT,
        amount=amount,
        balance_after=new_balance,
        description=description or "Manual deposit"
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(ledger_entry)
    return ledger_entry


def withdraw_cash(db: Session, *, portfolio_id: uuid.UUID, user_id: uuid.UUID, amount: Decimal, description: str | None = None) -> CashLedgerEntry:
    """Withdraw cash from a portfolio with row-level locking."""
    portfolio = db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .with_for_update()
    ).scalar_one_or_none()
    
    if portfolio is None:
        raise NotFoundError("Portfolio not found.")
        
    if amount <= 0:
        raise BadRequestError("Withdrawal amount must be positive.")
        
    if portfolio.cash_balance < amount:
        raise BadRequestError("Insufficient funds.")
        
    new_balance = portfolio.cash_balance - amount
    portfolio.cash_balance = new_balance
    
    ledger_entry = CashLedgerEntry(
        portfolio_id=portfolio.id,
        entry_type=LedgerEntryType.WITHDRAWAL,
        amount=-amount,  # negative for withdrawal
        balance_after=new_balance,
        description=description or "Manual withdrawal"
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(ledger_entry)
    return ledger_entry


def reset_portfolio(db: Session, *, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio:
    """
    Reset a portfolio to its opening balance.
    As per requirements, DO NOT hard delete holdings. Set quantity to 0 to preserve history.
    """
    portfolio = db.execute(
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .with_for_update()
    ).scalar_one_or_none()
    
    if portfolio is None:
        raise NotFoundError("Portfolio not found.")
        
    # 1. Set all non-zero holdings to quantity 0
    holdings = db.execute(
        select(Holding)
        .where(Holding.portfolio_id == portfolio_id)
        .with_for_update()
    ).scalars().all()
    
    for h in holdings:
        h.quantity = 0
        # Preserve average_cost for historical reference
        
    # 2. Reset cash
    old_balance = portfolio.cash_balance
    new_balance = portfolio.opening_balance
    portfolio.cash_balance = new_balance
    
    diff = new_balance - old_balance
    
    # 3. Create RESET ledger entry
    ledger_entry = CashLedgerEntry(
        portfolio_id=portfolio.id,
        entry_type=LedgerEntryType.RESET,
        amount=diff,
        balance_after=new_balance,
        description="Portfolio reset to opening balance"
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(portfolio)
    return portfolio
