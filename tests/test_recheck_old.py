"""Reports whose figures were extracted from an older text than the one we now hold
(a correction overwrote the raw text before version tracking existed)."""

from app import config, crud, models, worker
from app.recheck_old import recheck_old
from app.serialize import event_summary_hash

OLD = "نص الحادث قبل التصحيح"
NEW = "نص الحادث بعد التصحيح"
TRAFFIC = "أحداث مرورية"


def _report(db, ref, extracted_from, current, category=TRAFFIC, **fields):
    crud.upsert_raw_event(db, {"reference": ref, "event_summary": current, "time": "2026-11-23T10:00:00"})
    data = {"التصنيف": {"الصنف_الرئيسي": category}}
    if extracted_from is not None:
        data["النص_الأصلي"] = extracted_from
    db.add(
        models.ProcessedEvent(
            reference=ref, data=data, status="done", source_hash=event_summary_hash(current), **fields
        )
    )
    db.commit()


def _picked(db):
    return sorted(r.reference for r in worker.fetch_unclassified(db, 50))


def test_stale_traffic_report_is_queued_for_reextraction(db_session):
    _report(db_session, "A", extracted_from=OLD, current=NEW)
    result = recheck_old(db_session)
    assert result == {"checked": 1, "stale": 1}
    assert _picked(db_session) == ["A"]


def test_report_in_sync_is_left_alone(db_session):
    _report(db_session, "A", extracted_from=NEW, current=NEW)
    assert recheck_old(db_session) == {"checked": 1, "stale": 0}
    assert _picked(db_session) == []


def test_edited_and_textless_reports_are_skipped(db_session):
    _report(db_session, "A", extracted_from=OLD, current=NEW, is_edited=True)
    _report(db_session, "B", extracted_from=None, current=NEW)
    assert recheck_old(db_session) == {"checked": 0, "stale": 0}
    assert _picked(db_session) == []


def test_other_categories_only_when_asked(db_session):
    _report(db_session, "A", extracted_from=OLD, current=NEW, category="جرائم السرقات")
    assert recheck_old(db_session) == {"checked": 0, "stale": 0}
    assert recheck_old(db_session, all_categories=True) == {"checked": 1, "stale": 1}
    assert _picked(db_session) == ["A"]


def test_dry_run_changes_nothing(db_session):
    _report(db_session, "A", extracted_from=OLD, current=NEW)
    assert recheck_old(db_session, dry_run=True) == {"checked": 1, "stale": 1}
    assert _picked(db_session) == []


def test_queued_report_gets_fresh_attempts(db_session):
    _report(db_session, "A", extracted_from=OLD, current=NEW, attempts=config.MAX_CLASSIFY_ATTEMPTS)
    recheck_old(db_session)
    assert crud.get_processed(db_session, "A").attempts == 0
    assert _picked(db_session) == ["A"]
