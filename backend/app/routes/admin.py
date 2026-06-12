import uuid
import csv
from io import StringIO
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.core.deps import CurrentAdmin
from app.db import get_db
from app.models import (
    User, Portfolio, Trade, Order, CashLedgerEntry, PortfolioSnapshot, 
    AdminLog, LedgerEntryType, UserRole, Holding
)
from app.schemas.admin import (
    AdminStatsResponse, AdminLogResponse, SuspendUserRequest, AdjustBalanceRequest
)
from app.schemas.auth import UserResponse
from app.schemas.portfolio import PortfolioResponse, CashLedgerEntryResponse
from app.schemas.trading import TradeResponse, OrderResponse

router = APIRouter()

def create_admin_log(db: Session, actor_id: uuid.UUID, target_user_id: uuid.UUID | None, action: str, target_type: str, target_id: str | None, reason: str, before: dict | None, after: dict | None):
    log = AdminLog(
        actor_user_id=actor_id,
        target_user_id=target_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        before_data=before,
        after_data=after
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


import time
from app.services.market_data import market_data_provider

@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(
    admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    active_users = db.execute(select(func.count()).select_from(User).where(User.is_suspended == False)).scalar() or 0
    suspended_users = db.execute(select(func.count()).select_from(User).where(User.is_suspended == True)).scalar() or 0
    total_portfolios = db.execute(select(func.count()).select_from(Portfolio)).scalar() or 0
    total_trades = db.execute(select(func.count()).select_from(Trade)).scalar() or 0
    
    return AdminStatsResponse(
        active_users=active_users,
        suspended_users=suspended_users,
        total_portfolios=total_portfolios,
        total_trades=total_trades
    )

@router.get("/market-data/health")
async def get_market_data_health(
    admin: CurrentAdmin,
):
    start_time = time.time()
    try:
        # Fetch quote for a reliably existing symbol to test Yahoo Finance
        quote = await market_data_provider.get_quote("dummy_id", "RELIANCE.NS", "RELIANCE")
        latency_ms = (time.time() - start_time) * 1000
        return {
            "provider_status": "OK",
            "quote_fetch_success": True,
            "response_latency_ms": round(latency_ms, 2),
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "provider_status": "ERROR",
            "quote_fetch_success": False,
            "error_message": str(e),
            "response_latency_ms": round(latency_ms, 2),
            "timestamp": datetime.now(UTC).isoformat()
        }


@router.get("/users", response_model=list[UserResponse])
def get_users(
    admin: CurrentAdmin,
    query: str | None = None,
    db: Session = Depends(get_db)
):
    stmt = select(User)
    if query:
        stmt = stmt.where(User.email.ilike(f"%{query}%") | User.display_name.ilike(f"%{query}%"))
    users = db.execute(stmt).scalars().all()
    return users


@router.get("/users/{user_id}", response_model=dict[str, Any])
def get_user_details(
    user_id: uuid.UUID,
    admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    portfolio = db.execute(select(Portfolio).where(Portfolio.user_id == user_id)).scalar_one_or_none()
    pf_data = None
    
    holdings = []
    orders = []
    trades = []
    ledger = []
    snapshots = []
    
    if portfolio:
        pf_data = {
            "id": portfolio.id,
            "cash_balance": portfolio.cash_balance,
            "total_invested": sum((h.quantity * h.average_cost for h in db.execute(select(Holding).where(Holding.portfolio_id == portfolio.id)).scalars()), Decimal(0)),
            "realized_pnl": sum((t.realized_pnl for t in db.execute(select(Trade).where(Trade.portfolio_id == portfolio.id)).scalars()), Decimal(0))
        }
        
        # We don't have a specific holding table in this schema without snapshots or ledger reconstruction?
        # Actually in the existing code, holdings are calculated dynamically. Let's return raw orders/trades.
        orders = db.execute(select(Order).where(Order.portfolio_id == portfolio.id).order_by(desc(Order.created_at)).limit(20)).scalars().all()
        trades = db.execute(select(Trade).where(Trade.portfolio_id == portfolio.id).order_by(desc(Trade.created_at)).limit(20)).scalars().all()
        ledger = db.execute(select(CashLedgerEntry).where(CashLedgerEntry.portfolio_id == portfolio.id).order_by(desc(CashLedgerEntry.created_at)).limit(20)).scalars().all()
        snapshots = db.execute(select(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio.id).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(10)).scalars().all()
        
    return {
        "user": UserResponse.model_validate(user).model_dump(),
        "portfolio": pf_data,
        "orders": [OrderResponse.model_validate(o).model_dump() for o in orders],
        "trades": [TradeResponse.model_validate(t).model_dump() for t in trades],
        "ledger": [CashLedgerEntryResponse.model_validate(l).model_dump() for l in ledger],
        "snapshots": [{
            "date": s.snapshot_date.isoformat(),
            "cash_balance": s.cash_balance,
            "holdings_value": s.holdings_value,
            "total_portfolio_value": s.total_portfolio_value,
            "total_pnl": s.total_pnl
        } for s in snapshots]
    }


@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: uuid.UUID,
    req: SuspendUserRequest,
    admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_suspended:
        raise HTTPException(status_code=400, detail="User already suspended")
    
    user.is_suspended = True
    user.suspended_at = datetime.now(UTC)
    
    create_admin_log(
        db, admin.id, user.id, "SUSPEND", "USER", str(user.id), req.reason,
        {"is_suspended": False}, {"is_suspended": True}
    )
    
    return {"message": "User suspended"}


@router.post("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: uuid.UUID,
    req: SuspendUserRequest,
    admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_suspended:
        raise HTTPException(status_code=400, detail="User is not suspended")
    
    user.is_suspended = False
    user.suspended_at = None
    
    create_admin_log(
        db, admin.id, user.id, "REACTIVATE", "USER", str(user.id), req.reason,
        {"is_suspended": True}, {"is_suspended": False}
    )
    
    return {"message": "User reactivated"}


@router.post("/portfolios/{portfolio_id}/adjust-balance")
def adjust_balance(
    portfolio_id: uuid.UUID,
    req: AdjustBalanceRequest,
    admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    portfolio = db.execute(select(Portfolio).where(Portfolio.id == portfolio_id)).scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
    before_balance = portfolio.cash_balance
    new_balance = before_balance + req.amount
    
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Balance adjustment would result in negative cash")
        
    portfolio.cash_balance = new_balance
    
    ledger_entry = CashLedgerEntry(
        portfolio_id=portfolio.id,
        entry_type=LedgerEntryType.ADMIN_ADJUSTMENT,
        amount=req.amount,
        balance_after=new_balance,
        description=f"Admin Adjustment: {req.reason}"
    )
    db.add(ledger_entry)
    
    create_admin_log(
        db, admin.id, portfolio.user_id, "ADJUST_BALANCE", "PORTFOLIO", str(portfolio.id), req.reason,
        {"cash_balance": float(before_balance)}, {"cash_balance": float(new_balance)}
    )
    
    return {"message": "Balance adjusted", "new_balance": new_balance}


@router.get("/logs", response_model=list[AdminLogResponse])
def get_admin_logs(
    admin: CurrentAdmin,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    logs = db.execute(select(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit)).scalars().all()
    return logs


@router.get("/export/{entity}")
def export_csv(
    entity: str,
    admin: CurrentAdmin,
    db: Session = Depends(get_db)
):
    output = StringIO()
    writer = csv.writer(output)
    
    if entity == "users":
        users = db.execute(select(User)).scalars().all()
        writer.writerow(["ID", "Email", "Role", "Is Suspended", "Created At"])
        for u in users:
            writer.writerow([str(u.id), u.email, u.role.value, u.is_suspended, u.created_at.isoformat()])
            
    elif entity == "trades":
        trades = db.execute(select(Trade)).scalars().all()
        writer.writerow(["ID", "Portfolio ID", "Instrument ID", "Side", "Quantity", "Price", "Created At"])
        for t in trades:
            writer.writerow([str(t.id), str(t.portfolio_id), str(t.instrument_id), t.side.value, t.quantity, t.execution_price, t.created_at.isoformat()])
            
    elif entity == "admin_logs":
        logs = db.execute(select(AdminLog)).scalars().all()
        writer.writerow(["ID", "Actor ID", "Action", "Target Type", "Target ID", "Reason", "Created At"])
        for l in logs:
            writer.writerow([str(l.id), str(l.actor_user_id), l.action, l.target_type, str(l.target_id), l.reason, l.created_at.isoformat()])
    else:
        raise HTTPException(status_code=400, detail="Invalid export entity")
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity}_export.csv"}
    )
