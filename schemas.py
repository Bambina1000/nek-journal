from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# ===== USER =====
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# ===== ACCOUNT =====
class AccountBase(BaseModel):
    name: str
    starting_balance: float = 0.0
    broker: Optional[str] = None
    account_type: Optional[str] = None      # "Challenge", "Instant", "Real"
    status: str = "Active"
    purchase_cost: float = 0.0
    # ---- NEW CHALLENGE FIELDS ----
    phase: Optional[str] = None             # "Phase 1", "Phase 2", "Instant"
    profit_target_percent: float = 8.0      # target profit percentage to pass
    max_drawdown_percent: float = 8.0       # maximum allowed drawdown
    daily_drawdown_percent: float = 4.0     # daily drawdown limit
    current_balance: Optional[float] = None # computed from trades
    challenge_status: Optional[str] = "Active"  # "Active", "Passed", "Failed"

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    starting_balance: Optional[float] = None
    broker: Optional[str] = None
    account_type: Optional[str] = None
    status: Optional[str] = None
    purchase_cost: Optional[float] = None
    phase: Optional[str] = None
    profit_target_percent: Optional[float] = None
    max_drawdown_percent: Optional[float] = None
    daily_drawdown_percent: Optional[float] = None
    current_balance: Optional[float] = None
    challenge_status: Optional[str] = None

# ===== TRADE =====
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
    before_image: Optional[str] = None   # Base64 string
    after_image: Optional[str] = None    # Base64 string
    confidence: Optional[int] = None
    session: Optional[str] = None
    account_id: Optional[int] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: Optional[str] = "Closed"
    journal_entry: Optional[str] = None
    created_at: Optional[datetime] = None

class TradeResponse(TradeCreate):
    id: int
    created_at: datetime
    account: Optional[AccountResponse] = None
    class Config:
        from_attributes = True

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
    status: Optional[str] = None
    journal_entry: Optional[str] = None
    created_at: Optional[datetime] = None

# ===== WATCHLIST =====
class WatchlistItemBase(BaseModel):
    symbol: str
    notes: Optional[str] = None

class WatchlistItemCreate(WatchlistItemBase):
    pass

class WatchlistItemResponse(WatchlistItemBase):
    id: int
    added_at: datetime
    class Config:
        from_attributes = True

# ===== REPORT SETTINGS =====
class ReportSettingBase(BaseModel):
    email: EmailStr
    frequency: str = "weekly"

class ReportSettingCreate(ReportSettingBase):
    pass

class ReportSettingResponse(ReportSettingBase):
    id: int
    last_sent: Optional[datetime] = None
    class Config:
        from_attributes = True

# ===== WEEKLY REVIEW (NEW) =====
class WeeklyReviewBase(BaseModel):
    week_start: datetime
    review_text: Optional[str] = ""
    mistakes: Optional[str] = ""
    wins: Optional[str] = ""
    lessons: Optional[str] = ""
    rating: Optional[int] = None          # e.g., 1-5

class WeeklyReviewCreate(WeeklyReviewBase):
    pass

class WeeklyReviewResponse(WeeklyReviewBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    class Config:
        from_attributes = True