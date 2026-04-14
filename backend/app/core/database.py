import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

# Default to SQLite for local fallback, but expect the Cloud URL in production.
# Replace '<YOUR-PASSWORD>' with your actual Supabase Database Password.
DEFAULT_URL = "postgresql://postgres.spbmkcmcdtqebammaarf:<YOUR-PASSWORD>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_URL)

# SQLite requires 'check_same_thread', PostgreSQL does not.
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
