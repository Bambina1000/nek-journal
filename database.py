import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Read the database path from environment variable
DB_PATH = os.environ.get("DATABASE_PATH", "./journal.db")

# Ensure the directory exists (with fallback)
db_dir = os.path.dirname(DB_PATH)
if db_dir:
    try:
        os.makedirs(db_dir, exist_ok=True)
        print(f"✅ Database directory: {db_dir}")
    except Exception as e:
        # Fallback to local file
        DB_PATH = "./journal.db"
        print(f"⚠️  Using fallback database: {DB_PATH}")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()