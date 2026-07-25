import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Read from environment variable
DATABASE_URL = os.environ.get("SUPABASE_DATABASE_URL")

# Fallback to local SQLite for development (if env var is missing)
if not DATABASE_URL:
    DB_PATH = os.environ.get("DATABASE_PATH", "./journal.db")
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()