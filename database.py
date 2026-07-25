import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Turso connection details
TURSO_DATABASE_URL = os.environ.get("TURSO_DB_URL", "libsql://nek-journal-bambina1000.aws-us-west-2.turso.io")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicm8iLCJpYXQiOjE3ODQ5NDA1MjEsImlkIjoiMDE5Zjk2YmQtZTAwMS03NzY5LWIzNjUtODhmNDcyN2M4OTc0Iiwia2lkIjoiMVJnTnY0aEYycXFlbko4TU1Zd1FfT1RVM0NoZkVDdzNLdFRiOXg4YVIzYyIsInJpZCI6IjJmZjY0ZWQ3LWMzNzAtNGVlZi1hOTliLTFiN2FhNGFkODdlOSJ9.xAdDoKKJ7VIlYwf1n8UMsVvRCoEKBZ0GyJ0lw4jrfiAeIMax-ljnsSGunbgrc4yFgQ-Ng6jnxmYFjN3XezxaDA")

# Create the engine using the libsql dialect
engine = create_engine(
    TURSO_DATABASE_URL,
    connect_args={
        "auth_token": TURSO_AUTH_TOKEN,
    },
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()