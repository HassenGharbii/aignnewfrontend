import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models
from app.api import app
from app.db import SessionLocal, engine, init_db

DEFAULT_CATEGORY = "أحداث مرورية"
DEFAULT_SUB_CATEGORY = "حادث مرور"


@pytest.fixture(scope="session", autouse=True)
def _schema():
    init_db()


@pytest.fixture(autouse=True)
def _clean_tables(_schema):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE processed_events, raw_events RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_UNSET = object()


@pytest.fixture
def make_event(db_session):
    def _make(
        reference,
        category=DEFAULT_CATEGORY,
        sub_category=DEFAULT_SUB_CATEGORY,
        status="done",
        data_override=_UNSET,
    ):
        if data_override is _UNSET:
            data = {"التصنيف": {"الصنف_الرئيسي": category, "الصنف_الفرعي": sub_category}}
        else:
            data = data_override
        db_session.add(
            models.RawEvent(
                reference=reference,
                subject=f"subject {reference}",
                event_summary=f"summary {reference}",
                event_time="2026-01-01T00:00:00",
            )
        )
        db_session.flush()
        db_session.add(models.ProcessedEvent(reference=reference, data=data, status=status))
        db_session.commit()

    return _make
