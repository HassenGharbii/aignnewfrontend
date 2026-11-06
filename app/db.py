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
        # Built in the same transaction as the ALTER TABLE above: its ACCESS EXCLUSIVE
        # lock serializes concurrent init_db calls (api and worker). Don't split this
        # out or use CONCURRENTLY without handling that race. The first start after
        # deploy blocks while the index builds.
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_processed_events_category ON processed_events "
                "(json_extract_path_text(data, 'التصنيف', 'الصنف_الرئيسي'))"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
