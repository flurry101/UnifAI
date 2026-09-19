import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# We reuse the existing psycopg URL structure.
# SQLAlchemy 2.0 uses postgresql+psycopg2 or postgresql+psycopg.
# Given we have psycopg 3 installed, we use postgresql+psycopg.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Please configure DATABASE_URL in your .env file."
    )

if SQLALCHEMY_DATABASE_URL.startswith(("http://", "https://")):
    raise ValueError(
        f"Invalid DATABASE_URL: '{SQLALCHEMY_DATABASE_URL}'. "
        "It looks like a Supabase HTTPS Project URL was provided instead of a PostgreSQL connection URI.\n"
        "Expected PostgreSQL connection format:\n"
        "  postgresql://postgres:[PASSWORD]@db.<project-ref>.supabase.co:5432/postgres\n"
        "or connection pooler format:\n"
        "  postgresql://postgres.<project-ref>:[PASSWORD]@aws-0-<region>.pooler.supabase.com:6543/postgres"
    )

if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
