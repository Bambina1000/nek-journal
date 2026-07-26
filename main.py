from fastapi import FastAPI, Depends, HTTPException, File, Form, UploadFile, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import models, schemas
from database import engine, get_db
import os
import shutil
import csv
import io
import json
import re
from collections import Counter

# ---------- RATE LIMITING ----------
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# ---------- ENVIRONMENT VARIABLES ----------
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-use-64-characters")
if SECRET_KEY == "change-this-in-production-use-64-characters":
    print("⚠️  WARNING: Using default SECRET_KEY. Set environment variable for production.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 1 day

# Email config
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# CORS allowed origins – split by comma
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://your-app.onrender.com,http://localhost:8000").split(",")
# Trim whitespace
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NEK Journal", version="2.0.0")

# ---------- RATE LIMITER ----------
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# ---------- CORS (restricted) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- AUTH HELPERS ----------
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# ---------- AUTH ENDPOINTS ----------
@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    hashed = get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=schemas.Token)
@limiter.limit("5/minute")   # rate limit login attempts
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    return current_user


# ---------- ACCOUNT ENDPOINTS ----------
@app.post("/accounts/", response_model=schemas.AccountResponse)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    db_account = models.Account(**account.dict(), user_id=current_user.id)
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.get("/accounts/", response_model=list[schemas.AccountResponse])
def get_accounts(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Account).filter(models.Account.user_id == current_user.id).all()

@app.put("/accounts/{account_id}", response_model=schemas.AccountResponse)
def update_account(account_id: int, account: schemas.AccountUpdate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    db_account = db.query(models.Account).filter(models.Account.id == account_id,
                                                 models.Account.user_id == current_user.id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    for key, value in account.dict(exclude_unset=True).items():
        setattr(db_account, key, value)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    db_account = db.query(models.Account).filter(models.Account.id == account_id,
                                                 models.Account.user_id == current_user.id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(db_account)
    db.commit()
    return {"message": "Account deleted"}


# ---------- TRADE ENDPOINTS (with Base64 & size limit) ----------
MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5 MB

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
        status: str = Form("Closed"),
        journal_entry: str = Form(None),
        created_at: str = Form(None),
        before_image: str = Form(None),
        after_image: str = Form(None),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Enforce image size limit
    if before_image and len(before_image) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Before image too large (max 5 MB)")
    if after_image and len(after_image) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="After image too large (max 5 MB)")

    # Parse created_at
    if created_at:
        try:
            parsed_dt = datetime.fromisoformat(created_at)
        except ValueError:
            parsed_dt = datetime.utcnow()
    else:
        parsed_dt = datetime.utcnow()

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
        "before_image": before_image,
        "after_image": after_image,
        "confidence": confidence,
        "session": session,
        "account_id": account_id,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "status": status,
        "journal_entry": journal_entry,
        "created_at": parsed_dt,
        "user_id": current_user.id,
    }
    db_trade = models.Trade(**trade_data)
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    db_trade = db.query(models.Trade).filter(models.Trade.id == db_trade.id).first()
    return db_trade

@app.get("/trades/", response_model=list[schemas.TradeResponse])
def get_trades(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Trade).filter(models.Trade.user_id == current_user.id).all()

@app.put("/trades/{trade_id}", response_model=schemas.TradeResponse)
async def update_trade(
    trade_id: int,
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
    status: str = Form("Closed"),
    journal_entry: str = Form(None),
    created_at: str = Form(None),
    before_image: str = Form(None),
    after_image: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Enforce size limit if images are being updated
    if before_image and len(before_image) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Before image too large (max 5 MB)")
    if after_image and len(after_image) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="After image too large (max 5 MB)")

    db_trade = db.query(models.Trade).filter(
        models.Trade.id == trade_id,
        models.Trade.user_id == current_user.id
    ).first()
    if not db_trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if before_image is not None:
        db_trade.before_image = before_image
    if after_image is not None:
        db_trade.after_image = after_image

    if created_at:
        try:
            parsed_dt = datetime.fromisoformat(created_at)
            db_trade.created_at = parsed_dt
        except ValueError:
            pass

    update_fields = {
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
        "confidence": confidence,
        "session": session,
        "account_id": account_id,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "status": status,
        "journal_entry": journal_entry,
    }
    for key, value in update_fields.items():
        setattr(db_trade, key, value)

    db.commit()
    db.refresh(db_trade)
    return db_trade

@app.delete("/trades/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_trade = db.query(models.Trade).filter(models.Trade.id == trade_id,
                                             models.Trade.user_id == current_user.id).first()
    if not db_trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(db_trade)
    db.commit()
    return {"message": "Trade deleted"}


# ---------- WATCHLIST ENDPOINTS ----------
@app.post("/watchlist/", response_model=schemas.WatchlistItemResponse)
def add_watchlist(item: schemas.WatchlistItemCreate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    db_item = models.WatchlistItem(**item.dict(), user_id=current_user.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/watchlist/", response_model=list[schemas.WatchlistItemResponse])
def get_watchlist(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.WatchlistItem).filter(models.WatchlistItem.user_id == current_user.id).all()

@app.delete("/watchlist/{item_id}")
def delete_watchlist(item_id: int, db: Session = Depends(get_db),
                     current_user: models.User = Depends(get_current_user)):
    item = db.query(models.WatchlistItem).filter(models.WatchlistItem.id == item_id,
                                                 models.WatchlistItem.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}


# ---------- BACKUP & RESTORE ----------
@app.get("/backup/")
def backup_data(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trades = db.query(models.Trade).filter(models.Trade.user_id == current_user.id).all()
    accounts = db.query(models.Account).filter(models.Account.user_id == current_user.id).all()
    watchlist = db.query(models.WatchlistItem).filter(models.WatchlistItem.user_id == current_user.id).all()
    data = {
        "trades": [t.__dict__ for t in trades],
        "accounts": [a.__dict__ for a in accounts],
        "watchlist": [w.__dict__ for w in watchlist]
    }
    for key in ["trades", "accounts", "watchlist"]:
        for item in data[key]:
            item.pop("_sa_instance_state", None)
            item.pop("user_id", None)
            item.pop("id", None)
    return data

@app.post("/restore/")
def restore_data(data: dict, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db.query(models.Trade).filter(models.Trade.user_id == current_user.id).delete()
    db.query(models.Account).filter(models.Account.user_id == current_user.id).delete()
    db.query(models.WatchlistItem).filter(models.WatchlistItem.user_id == current_user.id).delete()
    db.commit()

    for acc in data.get("accounts", []):
        acc["user_id"] = current_user.id
        db.add(models.Account(**acc))
    db.commit()

    account_map = {}
    for acc in data.get("accounts", []):
        old_name = acc["name"]
        new_acc = db.query(models.Account).filter(models.Account.user_id == current_user.id,
                                                  models.Account.name == old_name).first()
        if new_acc:
            account_map[acc.get("id")] = new_acc.id

    for t in data.get("trades", []):
        t.pop("id", None)
        t["user_id"] = current_user.id
        if t.get("account_id") in account_map:
            t["account_id"] = account_map[t["account_id"]]
        else:
            t["account_id"] = None
        db.add(models.Trade(**t))

    for w in data.get("watchlist", []):
        w.pop("id", None)
        w["user_id"] = current_user.id
        db.add(models.WatchlistItem(**w))

    db.commit()
    return {"message": "Data restored successfully"}


# ---------- REPORT SETTINGS ----------
@app.post("/report-settings/", response_model=schemas.ReportSettingResponse)
def set_report_settings(settings: schemas.ReportSettingCreate, db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user)):
    existing = db.query(models.ReportSetting).filter(models.ReportSetting.user_id == current_user.id).first()
    if existing:
        existing.email = settings.email
        existing.frequency = settings.frequency
    else:
        existing = models.ReportSetting(**settings.dict(), user_id=current_user.id)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing

@app.get("/report-settings/", response_model=schemas.ReportSettingResponse)
def get_report_settings(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    settings = db.query(models.ReportSetting).filter(models.ReportSetting.user_id == current_user.id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="No report settings found")
    return settings

def send_email_report(user_email: str, content: str):
    if not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP credentials not configured – email not sent.")
        return
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = user_email
    msg["Subject"] = "Your Weekly Trading Journal Report"
    msg.attach(MIMEText(content, "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, user_email, msg.as_string())

def generate_report(trades):
    html = "<h1>Weekly Trading Summary</h1>"
    if not trades:
        return "<p>No trades this week.</p>"
    total = len(trades)
    wins = len([t for t in trades if t.pnl > 0])
    losses = len([t for t in trades if t.pnl < 0])
    pnl = sum(t.pnl for t in trades)
    win_rate = (wins / total) * 100 if total else 0
    html += f"<p>Total Trades: {total} | Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%</p>"
    html += f"<p>Net P&L: ${pnl:.2f}</p>"
    pairs = [t.pair for t in trades]
    top_pairs = Counter(pairs).most_common(3)
    html += "<p>Top Traded Pairs: " + ", ".join([f"{p[0]} ({p[1]})" for p in top_pairs]) + "</p>"
    return html

def scheduled_email_job():
    from database import SessionLocal
    db = SessionLocal()
    try:
        today_weekday = datetime.utcnow().weekday()
        if today_weekday != 5:
            return
        users_with_reports = db.query(models.User).join(models.ReportSetting).all()
        for user in users_with_reports:
            settings = db.query(models.ReportSetting).filter(models.ReportSetting.user_id == user.id).first()
            if not settings or settings.frequency != 'weekly':
                continue
            today_str = datetime.utcnow().date().isoformat()
            if settings.last_sent and settings.last_sent.date().isoformat() == today_str:
                continue
            trades = db.query(models.Trade).filter(
                models.Trade.user_id == user.id,
                models.Trade.created_at > datetime.utcnow() - timedelta(days=7)
            ).all()
            report = generate_report(trades)
            try:
                send_email_report(settings.email, report)
                settings.last_sent = datetime.utcnow()
                db.commit()
                print(f"Sent weekly report to {settings.email}")
            except Exception as e:
                print(f"Failed to send email to {settings.email}: {e}")
    finally:
        db.close()

@app.post("/send-test-report/")
async def send_test_report(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = db.query(models.ReportSetting).filter(models.ReportSetting.user_id == current_user.id).first()
    if not settings:
        raise HTTPException(404, "No report settings found. Please set your email first.")
    if not settings.email:
        raise HTTPException(400, "No email address set in your report settings.")
    trades = db.query(models.Trade).filter(
        models.Trade.user_id == current_user.id,
        models.Trade.created_at > datetime.utcnow() - timedelta(days=7)
    ).all()
    report = generate_report(trades)
    try:
        send_email_report(settings.email, report)
        return {"message": "Test report sent successfully!"}
    except Exception as e:
        raise HTTPException(500, f"Failed to send: {str(e)}")


# ---------- STATS ----------
@app.get("/stats/")
def get_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trades = db.query(models.Trade).filter(models.Trade.user_id == current_user.id).all()
    if not trades:
        return {"total": 0, "win_rate": 0, "profit_factor": 0, "by_strategy": [], "monthly": []}
    total = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    win_rate = len(wins) / total if total else 0
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss else 0
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


# ---------- CSV EXPORT ----------
@app.get("/export/csv")
def export_csv(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trades = db.query(models.Trade).filter(models.Trade.user_id == current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Pair", "Direction", "Setup", "Entry", "Exit",
        "Size", "R:R", "P&L", "Emotion", "Plan",
        "Mistakes", "Notes", "Date", "Account", "Confidence", "Session",
        "Stop Loss", "Take Profit", "Status", "Journal Entry"
    ])
    for t in trades:
        account_name = t.account.name if t.account else ""
        writer.writerow([
            t.id, t.pair, t.direction, t.setup_type, t.entry_price, t.exit_price,
            t.position_size, t.risk_reward, t.pnl, t.emotion_before, t.followed_plan,
            t.mistakes, t.notes, t.created_at.isoformat(), account_name, t.confidence, t.session,
            t.stop_loss, t.take_profit, t.status, t.journal_entry
        ])
    output.seek(0)
    response = StreamingResponse(output, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=trades_export.csv"
    return response


# ---------- ROOT ----------
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")


# ---------- SCHEDULER ----------
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_email_job, "interval", hours=24)
scheduler.start()