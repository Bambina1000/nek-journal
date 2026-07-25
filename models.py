from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

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
    created_at = Column(DateTime, default=datetime.utcnow)
    before_image = Column(String, nullable=True)
    after_image = Column(String, nullable=True)
    confidence = Column(Integer, nullable=True)
    session = Column(String, nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    account = relationship("Account", back_populates="trades")

    # NEW: stop_loss and take_profit
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)