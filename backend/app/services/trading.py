import uuid
from decimal import Decimal
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.market_sessions import is_market_open
from app.models import (
    CashLedgerEntry,
    Holding,
    Instrument,
    LedgerEntryType,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Portfolio,
    Trade,
)
from app.schemas.trading import OrderCreateRequest, OrderSimulateResponse
from app.services.market_data import market_data_provider


class TradingService:
    def __init__(self, db: Session):
        self.db = db
        self.market_provider = market_data_provider

    def _calculate_execution_price(self, quote_price: Decimal, side: OrderSide) -> Decimal:
        spread = Decimal("0.001") # 0.1% spread
        if side == OrderSide.BUY:
            return quote_price * (Decimal("1") + spread)
        else:
            return quote_price * (Decimal("1") - spread)

    def _calculate_charges(self, gross_amount: Decimal) -> Tuple[Decimal, Decimal, Decimal]:
        """Returns (brokerage, taxes, other_charges)"""
        brokerage = min(gross_amount * Decimal("0.0005"), Decimal("20.00"))
        taxes = gross_amount * Decimal("0.0002")
        other_charges = Decimal("0")
        return brokerage, taxes, other_charges

    async def _get_and_validate_instrument_quote(self, instrument_id: uuid.UUID) -> Tuple[Instrument, Decimal, bool]:
        instrument = self.db.get(Instrument, instrument_id)
        if not instrument:
            raise HTTPException(status_code=404, detail="Instrument not found")
        if not instrument.is_active or not instrument.is_tradeable:
            raise HTTPException(status_code=400, detail="Instrument is not tradeable")
            
        quote = await self.market_provider.get_quote(
            instrument_id=str(instrument.id),
            yahoo_symbol=instrument.yahoo_symbol,
            local_symbol=instrument.symbol
        )
        return instrument, quote.price, quote.is_stale

    async def simulate_market_order(self, portfolio_id: uuid.UUID, request: OrderCreateRequest) -> OrderSimulateResponse:
        instrument, quote_price, is_stale = await self._get_and_validate_instrument_quote(request.instrument_id)
        
        execution_price = self._calculate_execution_price(quote_price, request.side)
        gross_amount = execution_price * request.quantity
        
        brokerage, taxes, other_charges = self._calculate_charges(gross_amount)
        total_charges = brokerage + taxes + other_charges
        
        sufficient_funds = None
        sufficient_holdings = None
        
        portfolio = self.db.get(Portfolio, portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
            
        if request.side == OrderSide.BUY:
            net_amount = gross_amount + total_charges
            sufficient_funds = portfolio.cash_balance >= net_amount
        else:
            net_amount = gross_amount - total_charges
            holding = self.db.execute(
                select(Holding).where(
                    Holding.portfolio_id == portfolio_id,
                    Holding.instrument_id == request.instrument_id
                )
            ).scalar_one_or_none()
            sufficient_holdings = holding is not None and holding.quantity >= request.quantity

        return OrderSimulateResponse(
            instrument_id=request.instrument_id,
            side=request.side,
            quantity=request.quantity,
            quote_price=quote_price,
            execution_price=execution_price,
            gross_amount=gross_amount,
            brokerage=brokerage,
            taxes=taxes,
            other_charges=other_charges,
            total_charges=total_charges,
            net_amount=net_amount,
            is_market_open=is_market_open(),
            is_quote_stale=is_stale,
            sufficient_funds=sufficient_funds,
            sufficient_holdings=sufficient_holdings,
        )

    async def execute_market_order(self, portfolio_id: uuid.UUID, request: OrderCreateRequest) -> Order:
        # 1. Idempotency Check (fast path before fetching quote)
        existing_order = self.db.execute(
            select(Order).where(
                Order.portfolio_id == portfolio_id,
                Order.idempotency_key == request.idempotency_key
            )
        ).scalar_one_or_none()
        if existing_order:
            return existing_order

        # 2. Market Open Check
        if not is_market_open():
            raise HTTPException(status_code=400, detail="Market is closed")

        # 3. Get Quote & Validate
        instrument, quote_price, is_stale = await self._get_and_validate_instrument_quote(request.instrument_id)
        if is_stale:
            raise HTTPException(status_code=400, detail="Market data is stale, cannot execute order")

        # 4. Pricing & Spread
        execution_price = self._calculate_execution_price(quote_price, request.side)
        gross_amount = execution_price * request.quantity
        brokerage, taxes, other_charges = self._calculate_charges(gross_amount)
        total_charges = brokerage + taxes + other_charges

        # 5. Atomic Transaction execution
        try:
            # Create Order record initially
            order = Order(
                portfolio_id=portfolio_id,
                instrument_id=request.instrument_id,
                idempotency_key=request.idempotency_key,
                side=request.side,
                order_type=OrderType.MARKET,
                status=OrderStatus.PENDING,
                quantity=request.quantity,
                quote_price=quote_price,
            )
            self.db.add(order)
            self.db.flush()

            # Lock Portfolio
            portfolio = self.db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id).with_for_update()
            ).scalar_one_or_none()
            if not portfolio:
                raise HTTPException(status_code=404, detail="Portfolio not found")

            # Lock Holding
            holding = self.db.execute(
                select(Holding).where(
                    Holding.portfolio_id == portfolio_id,
                    Holding.instrument_id == request.instrument_id
                ).with_for_update()
            ).scalar_one_or_none()

            # Validate execution
            if request.side == OrderSide.BUY:
                net_amount = gross_amount + total_charges
                if portfolio.cash_balance < net_amount:
                    order.status = OrderStatus.REJECTED
                    order.rejection_reason = "Insufficient funds"
                    self.db.commit()
                    raise HTTPException(status_code=400, detail="Insufficient funds")
                
                # Update Holding
                if not holding:
                    holding = Holding(
                        portfolio_id=portfolio_id,
                        instrument_id=request.instrument_id,
                        quantity=request.quantity,
                        average_cost=execution_price
                    )
                    self.db.add(holding)
                else:
                    total_old_cost = holding.quantity * holding.average_cost
                    holding.quantity += request.quantity
                    holding.average_cost = (total_old_cost + gross_amount) / holding.quantity
                
                realized_pnl = Decimal("0")

            else: # SELL
                net_amount = gross_amount - total_charges
                if not holding or holding.quantity < request.quantity:
                    order.status = OrderStatus.REJECTED
                    order.rejection_reason = "Insufficient holdings"
                    self.db.commit()
                    raise HTTPException(status_code=400, detail="Insufficient holdings")

                # Decrease Holding
                holding.quantity -= request.quantity
                
                # Realized P&L
                realized_pnl = ((execution_price - holding.average_cost) * request.quantity) - total_charges

            # Create Trade
            trade = Trade(
                order_id=order.id,
                portfolio_id=portfolio_id,
                instrument_id=request.instrument_id,
                side=request.side,
                quantity=request.quantity,
                execution_price=execution_price,
                gross_amount=gross_amount,
                brokerage=brokerage,
                taxes=taxes,
                other_charges=other_charges,
                total_charges=total_charges,
                realized_pnl=realized_pnl,
                quote_timestamp=order.created_at # Approximate
            )
            self.db.add(trade)
            self.db.flush()

            # Process Cash and Ledger
            if request.side == OrderSide.BUY:
                portfolio.cash_balance -= net_amount
                self.db.add(CashLedgerEntry(
                    portfolio_id=portfolio_id,
                    trade_id=trade.id,
                    entry_type=LedgerEntryType.TRADE_BUY,
                    amount=-net_amount,
                    balance_after=portfolio.cash_balance,
                    description=f"Bought {request.quantity} shares of {instrument.symbol}"
                ))
            else:
                portfolio.cash_balance += net_amount
                self.db.add(CashLedgerEntry(
                    portfolio_id=portfolio_id,
                    trade_id=trade.id,
                    entry_type=LedgerEntryType.TRADE_SELL,
                    amount=net_amount,
                    balance_after=portfolio.cash_balance,
                    description=f"Sold {request.quantity} shares of {instrument.symbol}"
                ))

            # Mark Order Filled
            from app.models import utc_now
            order.status = OrderStatus.FILLED
            order.executed_at = utc_now()
            
            # Flush changes before snapshot
            self.db.flush()

            # Upsert Daily Snapshot (synchronous, within transaction)
            # Fetch existing snapshot for today if any
            from sqlalchemy import func
            from app.models import PortfolioSnapshot
            from datetime import date
            
            today = date.today()
            snapshot = self.db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .where(PortfolioSnapshot.snapshot_date == today)
            ).scalar_one_or_none()

            # Evaluate net worth (requires flushed holdings/cash)
            from app.services.portfolio import calculate_portfolio_valuation
            # We need to pass portfolio, holdings, and current_prices
            holdings_list = self.db.execute(select(Holding).where(Holding.portfolio_id == portfolio_id)).scalars().all()
            val_result = calculate_portfolio_valuation(portfolio, holdings_list, {request.instrument_id: execution_price})
            
            if snapshot:
                snapshot.cash_balance = val_result.cash_balance
                snapshot.holdings_value = val_result.holdings_value
                snapshot.total_portfolio_value = val_result.total_portfolio_value
                snapshot.invested_cost = val_result.invested_cost
                snapshot.realized_pnl = val_result.realized_pnl
                snapshot.unrealized_pnl = val_result.unrealized_pnl
                snapshot.total_pnl = val_result.total_pnl
            else:
                snapshot = PortfolioSnapshot(
                    portfolio_id=portfolio_id,
                    snapshot_date=today,
                    cash_balance=val_result.cash_balance,
                    holdings_value=val_result.holdings_value,
                    total_portfolio_value=val_result.total_portfolio_value,
                    invested_cost=val_result.invested_cost,
                    realized_pnl=val_result.realized_pnl,
                    unrealized_pnl=val_result.unrealized_pnl,
                    total_pnl=val_result.total_pnl
                )
                self.db.add(snapshot)

            # Final Commit
            self.db.commit()
            self.db.refresh(order)
            return order

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            import traceback
            tb = traceback.format_exc()
            raise HTTPException(status_code=500, detail=tb)

    def get_orders(self, portfolio_id: uuid.UUID) -> list[Order]:
        return self.db.execute(
            select(Order).where(Order.portfolio_id == portfolio_id).order_by(Order.created_at.desc())
        ).scalars().all()

    def get_trades(self, portfolio_id: uuid.UUID) -> list[Trade]:
        return self.db.execute(
            select(Trade).where(Trade.portfolio_id == portfolio_id).order_by(Trade.created_at.desc())
        ).scalars().all()
