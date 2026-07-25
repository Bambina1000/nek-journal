from fastapi import FastAPI, Depends, HTTPException, File, Form, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas
from database import engine, get_db
import os
import shutil
import csv
import io
from datetime import datetime

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NEK Journal", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# ---------- ACCOUNT ENDPOINTS (unchanged) ----------
@app.post("/accounts/", response_model=schemas.AccountResponse)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    db_account = models.Account(**account.dict())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.get("/accounts/", response_model=list[schemas.AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    return db.query(models.Account).all()

@app.put("/accounts/{account_id}", response_model=schemas.AccountResponse)
def update_account(account_id: int, account: schemas.AccountUpdate, db: Session = Depends(get_db)):
    db_account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    for key, value in account.dict(exclude_unset=True).items():
        setattr(db_account, key, value)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    db_account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(db_account)
    db.commit()
    return {"message": "Account deleted"}

# ---------- TRADE ENDPOINTS ----------
@app.post("/trades/", response_model=schemas.TradeResponse)
async def create_trade(
    pair: str = Form(...),
    direction: str = Form(...),
    setup_type: str = Form(...),
    position_size: float = Form(...),
    entry_price: float = Form(...),
    exit_price: float = Form(...),
    risk_reward: float = Form(...),
    pnl: float = Form(...),
    emotion_before: str = Form(...),
    followed_plan: str = Form(...),
    mistakes: str = Form(None),
    notes: str = Form(None),
    confidence: int = Form(None),
    session: str = Form(None),
    account_id: int = Form(None),
    stop_loss: float = Form(None),
    take_profit: float = Form(None),
    before_image: UploadFile = File(None),
    after_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    before_path = after_path = None
    if before_image and before_image.filename:
        ext = os.path.splitext(before_image.filename)[1]
        filename = f"before_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(before_image.file, buffer)
        before_path = f"/static/uploads/{filename}"
    if after_image and after_image.filename:
        ext = os.path.splitext(after_image.filename)[1]
        filename = f"after_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(after_image.file, buffer)
        after_path = f"/static/uploads/{filename}"

    trade_data = {
        "pair": pair,
        "direction": direction,
        "setup_type": setup_type,
        "position_size": position_size,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "risk_reward": risk_reward,
        "pnl": pnl,
        "emotion_before": emotion_before,
        "followed_plan": followed_plan,
        "mistakes": mistakes,
        "notes": notes,
        "before_image": before_path,
        "after_image": after_path,
        "confidence": confidence,
        "session": session,
        "account_id": account_id,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
    }
    db_trade = models.Trade(**trade_data)
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    db_trade = db.query(models.Trade).filter(models.Trade.id == db_trade.id).first()
    return db_trade

@app.get("/trades/", response_model=list[schemas.TradeResponse])
def get_trades(db: Session = Depends(get_db)):
    return db.query(models.Trade).all()

@app.put("/trades/{trade_id}", response_model=schemas.TradeResponse)
def update_trade(trade_id: int, trade: schemas.TradeUpdate, db: Session = Depends(get_db)):
    db_trade = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
    if not db_trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    for key, value in trade.dict(exclude_unset=True).items():
        setattr(db_trade, key, value)
    db.commit()
    db.refresh(db_trade)
    return db_trade

@app.delete("/trades/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    db_trade = db.query(models.Trade).filter(models.Trade.id == trade_id).first()
    if not db_trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(db_trade)
    db.commit()
    return {"message": "Trade deleted"}

@app.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    trades = db.query(models.Trade).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Pair", "Direction", "Setup", "Entry", "Exit",
        "Size", "R:R", "P&L", "Emotion", "Plan",
        "Mistakes", "Notes", "Date", "Account", "Confidence", "Session",
        "Stop Loss", "Take Profit"
    ])
    for t in trades:
        account_name = t.account.name if t.account else ""
        writer.writerow([
            t.id, t.pair, t.direction, t.setup_type, t.entry_price, t.exit_price,
            t.position_size, t.risk_reward, t.pnl, t.emotion_before, t.followed_plan,
            t.mistakes, t.notes, t.created_at.isoformat(), account_name, t.confidence, t.session,
            t.stop_loss, t.take_profit
        ])
    output.seek(0)
    response = StreamingResponse(output, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=trades_export.csv"
    return response

@app.get("/stats/")
def get_stats(db: Session = Depends(get_db)):
    trades = db.query(models.Trade).all()
    if not trades:
        return {"total": 0, "win_rate": 0, "profit_factor": 0, "by_strategy": [], "monthly": []}
    total = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    win_rate = len(wins)/total if total else 0
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = gross_profit/gross_loss if gross_loss else 0
    strategies = {}
    for t in trades:
        strategies[t.setup_type] = strategies.get(t.setup_type, 0) + t.pnl
    monthly = {}
    for t in trades:
        key = t.created_at.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + t.pnl
    return {
        "total": total,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "by_strategy": [{"strategy": k, "pnl": v} for k, v in strategies.items()],
        "monthly": [{"month": k, "pnl": v} for k, v in monthly.items()]
    }