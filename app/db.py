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
        conn.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS summary_hash VARCHAR(64)"))
        conn.execute(text("ALTER TABLE processed_events ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64)"))
        conn.execute(text("ALTER TABLE processed_events ADD COLUMN IF NOT EXISTS group_ref VARCHAR"))
        conn.execute(
            text("ALTER TABLE processed_events ADD COLUMN IF NOT EXISTS is_main BOOLEAN NOT NULL DEFAULT true")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_processed_events_group_ref ON processed_events (group_ref)")
        )
        # Existing rows start as not approved; app.backfill_approval marks the approved ones.
        conn.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS actor VARCHAR"))
        conn.execute(
            text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS approved BOOLEAN NOT NULL DEFAULT false")
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_raw_events_approved ON raw_events (approved)"))
        # Rows from before version tracking: assume their extraction matches the text
        # we hold now, so deploying this does not re-run the model on the whole backlog.
        # Same hex sha256 of the UTF-8 text as serialize.event_summary_hash. Only touches
        # NULLs, so after the first start it is a no-op.
        conn.execute(
            text(
                "UPDATE raw_events SET summary_hash = "
                "encode(sha256(convert_to(coalesce(event_summary, ''), 'UTF8')), 'hex') "
                "WHERE summary_hash IS NULL"
            )
        )
        conn.execute(
            text(
                "UPDATE processed_events p SET source_hash = r.summary_hash "
                "FROM raw_events r WHERE r.reference = p.reference AND p.source_hash IS NULL"
            )
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
