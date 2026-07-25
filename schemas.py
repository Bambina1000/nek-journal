from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AccountBase(BaseModel):
    name: str
    starting_balance: float = 0.0
    broker: Optional[str] = None
    account_type: Optional[str] = None
    status: str = "Active"
    purchase_cost: float = 0.0

class AccountCreate(AccountBase): pass

class AccountResponse(AccountBase):
    id: int
    created_at: datetime
    class Config: orm_mode = True

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    starting_balance: Optional[float] = None
    broker: Optional[str] = None
    account_type: Optional[str] = None
    status: Optional[str] = None
    purchase_cost: Optional[float] = None

class TradeCreate(BaseModel):
    pair: str
    direction: str
    setup_type: str
    entry_price: float
    exit_price: float
    position_size: float
    risk_reward: float
    pnl: float
    emotion_before: str
    followed_plan: str
    mistakes: Optional[str] = None
    notes: Optional[str] = None
    before_image: Optional[str] = None
    after_image: Optional[str] = None
    confidence: Optional[int] = None
    session: Optional[str] = None
    account_id: Optional[int] = None
    stop_loss: Optional[float] = None          # NEW
    take_profit: Optional[float] = None        # NEW

class TradeResponse(TradeCreate):
    id: int
    created_at: datetime
    account: Optional[AccountResponse] = None
    class Config: orm_mode = True

class TradeUpdate(BaseModel):
    pair: Optional[str] = None
    direction: Optional[str] = None
    setup_type: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    position_size: Optional[float] = None
    risk_reward: Optional[float] = None
    pnl: Optional[float] = None
    emotion_before: Optional[str] = None
    followed_plan: Optional[str] = None
    mistakes: Optional[str] = None
    notes: Optional[str] = None
    before_image: Optional[str] = None
    after_image: Optional[str] = None
    confidence: Optional[int] = None
    session: Optional[str] = None
    account_id: Optional[int] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None