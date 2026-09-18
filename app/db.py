from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from . import config

engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    """create_all only creates missing tables, never missing columns, so columns
    added to an existing table are added here."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE processed_events ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0")
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
