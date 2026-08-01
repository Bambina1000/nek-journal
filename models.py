from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    trades = relationship("Trade", back_populates="owner")
    accounts = relationship("Account", back_populates="owner")
    watchlist = relationship("WatchlistItem", back_populates="owner")
    report_settings = relationship("ReportSetting", back_populates="owner")
    weekly_reviews = relationship("WeeklyReview", back_populates="owner")  # new


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    starting_balance = Column(Float, default=0.0)
    broker = Column(String, nullable=True)
    account_type = Column(String, nullable=True)          # "Challenge", "Instant", "Real"
    status = Column(String, default="Active")            # Active, Inactive
    purchase_cost = Column(Float, default=0.0)
    peak_balance = Column(Float, default=0.0)

    # ---- NEW CHALLENGE TRACKING FIELDS ----
    phase = Column(String, nullable=True)                 # "Phase 1", "Phase 2", "Instant"
    profit_target_percent = Column(Float, default=8.0)    # e.g. 8% to pass
    max_drawdown_percent = Column(Float, default=8.0)     # maximum allowed drawdown
    daily_drawdown_percent = Column(Float, default=4.0)   # daily drawdown limit
    current_balance = Column(Float, nullable=True)        # computed from trades, stored for quick access
    challenge_status = Column(String, default="Active")   # "Active", "Passed", "Failed"

    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="accounts")
    trades = relationship("Trade", back_populates="account")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String, index=True)
    direction = Column(String)
    setup_type = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float)
    position_size = Column(Float)
    risk_reward = Column(Float)
    pnl = Column(Float)
    emotion_before = Column(String)
    followed_plan = Column(String)
    mistakes = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)  # overridden when frontend sends it
    before_image = Column(Text, nullable=True)   # store Base64 string
    after_image = Column(Text, nullable=True)    # store Base64 string
    confidence = Column(Integer, nullable=True)
    session = Column(String, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    status = Column(String, default="Closed")       # "Open" or "Closed"
    journal_entry = Column(Text, nullable=True)     # Long-form reflection

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    account = relationship("Account", back_populates="trades")
    owner = relationship("User", back_populates="trades")


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="watchlist")


class ReportSetting(Base):
    __tablename__ = "report_settings"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    frequency = Column(String, default="weekly")  # weekly, monthly
    last_sent = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="report_settings")


# ---------- NEW: Weekly Review Model ----------
class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"

    id = Column(Integer, primary_key=True, index=True)
    # The week this review covers – we store the Monday date (or Sunday) to identify the week.
    week_start = Column(DateTime, nullable=False, index=True)   # e.g. Monday 00:00
    # The actual review content
    review_text = Column(Text, nullable=True)                   # main reflection
    mistakes = Column(Text, nullable=True)                      # what went wrong
    wins = Column(Text, nullable=True)                          # what went right
    lessons = Column(Text, nullable=True)                       # key takeaways
    rating = Column(Integer, nullable=True)                     # e.g. 1-5 self‑rating for the week
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="weekly_reviews")