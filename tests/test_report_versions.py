"""A corrected report comes back under the same reference with a new text: it must
be re-extracted, without reprocessing unchanged reports or overwriting edits."""

from sqlalchemy import text

from app import config, crud, models, worker
from app.db import engine, init_db
from app.serialize import event_summary_hash

OLD = "نص الحادث الأول"
NEW = "نص الحادث بعد التصحيح"


def _event(ref="R-1-000001", summary=OLD, time="2026-11-23T10:00:00"):
    return {"reference": ref, "event_summary": summary, "subject": "بشأن حادث مرور", "time": time, "actor": "SOC_Manager"}


def _done(db, ref="R-1-000001", summary=OLD, **fields):
    """A report already received and extracted from `summary`."""
    crud.upsert_raw_event(db, _event(ref, summary))
    db.add(
        models.ProcessedEvent(
            reference=ref,
            data={"عنوان": "قديم"},
            status="done",
            source_hash=event_summary_hash(summary),
            **fields,
        )
    )
    db.commit()


def _picked(db):
    return [r.reference for r in worker.fetch_unclassified(db, 50)]


def test_upsert_stores_the_text_hash(db_session):
    raw = crud.upsert_raw_event(db_session, _event())
    assert raw.summary_hash == event_summary_hash(OLD)


def test_changed_text_is_picked_for_reextraction(db_session):
    _done(db_session)
    crud.upsert_raw_event(db_session, _event(summary=NEW))
    assert _picked(db_session) == ["R-1-000001"]


def test_unchanged_text_is_not_picked(db_session):
    _done(db_session)
    crud.upsert_raw_event(db_session, _event(summary=OLD))
    assert _picked(db_session) == []


def test_hand_edited_report_is_never_overwritten(db_session):
    _done(db_session, is_edited=True)
    crud.upsert_raw_event(db_session, _event(summary=NEW))
    assert _picked(db_session) == []


def test_changed_report_stops_after_max_attempts(db_session):
    _done(db_session, attempts=config.MAX_CLASSIFY_ATTEMPTS)
    crud.upsert_raw_event(db_session, _event(summary=NEW))
    assert _picked(db_session) == []


def _fake_model(monkeypatch, fail=False):
    def classify_category(summary, subject, categories):
        if fail:
            raise RuntimeError("vllm timeout")
        return {"الصنف_الرئيسي": "أحداث مرورية", "نسبة_الثقة": 0.9}

    monkeypatch.setattr(worker, "classify_category", classify_category)
    monkeypatch.setattr(worker, "extract_details", lambda s, t, reference=None: {"أسباب_الحادث": ["السرعة"]})


def test_reextraction_replaces_data_and_records_the_hash(db_session, monkeypatch):
    _fake_model(monkeypatch)
    _done(db_session)
    raw = crud.upsert_raw_event(db_session, _event(summary=NEW))
    assert worker.classify_row(db_session, raw, ["أحداث مرورية"], {}) is True
    processed = crud.get_processed(db_session, "R-1-000001")
    assert processed.source_hash == event_summary_hash(NEW)
    assert processed.data["أسباب_الحادث"] == ["السرعة"]
    assert _picked(db_session) == []


def test_failed_reextraction_keeps_old_data_and_counts_the_attempt(db_session, monkeypatch):
    _fake_model(monkeypatch, fail=True)
    _done(db_session)
    raw = crud.upsert_raw_event(db_session, _event(summary=NEW))
    assert worker.classify_row(db_session, raw, ["أحداث مرورية"], {}) is False
    processed = crud.get_processed(db_session, "R-1-000001")
    db_session.refresh(processed)
    assert processed.status == "done"
    assert processed.data == {"عنوان": "قديم"}
    assert processed.attempts == 1


def test_init_db_fills_hashes_of_existing_rows_without_reprocessing(db_session):
    _done(db_session)
    with engine.begin() as conn:
        conn.execute(text("UPDATE raw_events SET summary_hash = NULL"))
        conn.execute(text("UPDATE processed_events SET source_hash = NULL"))
    init_db()
    db_session.expire_all()
    raw = db_session.query(models.RawEvent).one()
    processed = db_session.query(models.ProcessedEvent).one()
    assert raw.summary_hash == event_summary_hash(OLD)
    assert processed.source_hash == raw.summary_hash
    assert _picked(db_session) == []


def test_recheck_refetches_the_window_without_moving_the_poll_position(db_session, monkeypatch):
    _done(db_session)
    crud.get_or_create_poll_state(db_session, "2026-11-23T12:00:00")
    asked = []

    def fake_fetch(start):
        asked.append(start)
        return [_event(summary=NEW), _event(ref="R-2-000002", summary="جديد")]

    monkeypatch.setattr(worker, "fetch_events", fake_fetch)
    monkeypatch.setattr(config, "RECHECK_WINDOW_HOURS", 48)
    result = worker.recheck_recent(db_session)

    assert asked == ["2026-11-21T12:00:00"]
    assert result == {"fetched": 2, "changed": 1, "new": 1}
    assert crud.get_or_create_poll_state(db_session, "x").next_start == "2026-11-23T12:00:00"
    assert sorted(_picked(db_session)) == ["R-1-000001", "R-2-000002"]


def test_recheck_due(monkeypatch):
    monkeypatch.setattr(config, "RECHECK_INTERVAL_SECONDS", 3600)
    assert worker.recheck_due(None, 100.0) is True
    assert worker.recheck_due(100.0, 3699.0) is False
    assert worker.recheck_due(100.0, 3700.0) is True
    monkeypatch.setattr(config, "RECHECK_INTERVAL_SECONDS", 0)
    assert worker.recheck_due(None, 100.0) is False
