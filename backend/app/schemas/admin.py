import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import UserResponse

class AdminStatsResponse(BaseModel):
    active_users: int
    suspended_users: int
    total_portfolios: int
    total_trades: int

class AdminLogResponse(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    target_user_id: uuid.UUID | None = None
    action: str
    target_type: str
    target_id: str | None = None
    reason: str
    before_data: dict | None = None
    after_data: dict | None = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SuspendUserRequest(BaseModel):
    reason: str = Field(..., min_length=1)

class AdjustBalanceRequest(BaseModel):
    amount: Decimal
    reason: str = Field(..., min_length=1)
