import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

os.makedirs("database", exist_ok=True)

# We reuse the existing psycopg URL structure.
# SQLAlchemy 2.0 uses postgresql+psycopg2 or postgresql+psycopg.
# Given we have psycopg 3 installed, we use postgresql+psycopg.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/local.db")

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

try:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True
    )
    # Test connection
    with engine.connect() as test_conn:
        pass
except Exception:
    logger.exception("Database initialization failed")
    if os.getenv("DATABASE_URL") and os.getenv("ALLOW_SQLITE_FALLBACK") != "1":
        raise
    # Graceful fallback to local SQLite database when explicitly permitted or unconfigured.
    SQLALCHEMY_DATABASE_URL = "sqlite:///./database/local.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args=connect_args
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _migrate_columns():
    try:
        with engine.begin() as conn:
            for col, col_type in [("email", "TEXT"), ("auth_provider", "TEXT DEFAULT 'local'"), ("avatar_url", "TEXT")]:
                try:
                    conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {col} {col_type};")
                except Exception:
                    logger.exception("Column migration failed for %s", col)
    except Exception:
        logger.exception("Column migration transaction failed")

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
