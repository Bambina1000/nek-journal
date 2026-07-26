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


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    starting_balance = Column(Float, default=0.0)
    broker = Column(String, nullable=True)
    account_type = Column(String, nullable=True)
    status = Column(String, default="Active")
    purchase_cost = Column(Float, default=0.0)
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