"""Database engine và session configuration cho PostgreSQL (hệ thống ICTU Tower).
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(override=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ictu_tower"
)

# SQLAlchemy 2.0+ mặc định tìm 'psycopg' (v3). 
# Chuẩn hóa về 'postgresql+psycopg2://' để dùng đúng thư viện psycopg2-binary đã cài.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

# Tạo SQLAlchemy engine
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    engine = None
    SessionLocal = None
    print(f"[Database Error] Không thể khởi tạo engine: {e}")

Base = declarative_base()


def get_db():
    """Dependency cung cấp session DB cho từng request FastAPI."""
    if SessionLocal is None:
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
