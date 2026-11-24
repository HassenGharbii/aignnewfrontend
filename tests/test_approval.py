"""Only the version approved by SOC_Manager counts. Operator copies (SOC1_OP1, ...)
stay in the database but are never classified, grouped or shown, and never
replace an approved version. Made-up data only."""

from app import crud, grouping, models, worker
from app.backfill_approval import backfill_approval
from app.serialize import event_summary_hash

TRAFFIC = "أحداث مرورية"
OPERATOR = "SOC1_OP1"
APPROVER = "SOC_Manager"


def _event(ref, summary="نص الحادث", time="2026-11-20T10:00:00", actor=APPROVER):
    return {"reference": ref, "event_summary": summary, "time": time, "actor": actor}


def _done(db, ref, summary="نص الحادث", actor=APPROVER):
    crud.upsert_raw_event(db, _event(ref, summary, actor=actor))
    db.add(
        models.ProcessedEvent(
            reference=ref,
            status="done",
            data={"التصنيف": {"الصنف_الرئيسي": TRAFFIC}},
            source_hash=event_summary_hash(summary),
        )
    )
    db.commit()


def _raw(db, ref):
    db.expire_all()
    return db.query(models.RawEvent).filter_by(reference=ref).one()


def _picked(db):
    return sorted(r.reference for r in worker.fetch_unclassified(db, 50))


# --- storing -------------------------------------------------------------------


def test_upsert_stores_actor_and_approval(db_session):
    crud.upsert_raw_event(db_session, _event("A", actor=APPROVER))
    crud.upsert_raw_event(db_session, _event("B", actor=OPERATOR))
    assert (_raw(db_session, "A").actor, _raw(db_session, "A").approved) == (APPROVER, True)
    assert (_raw(db_session, "B").actor, _raw(db_session, "B").approved) == (OPERATOR, False)


def test_operator_copy_never_replaces_the_approved_version(db_session):
    crud.upsert_raw_event(db_session, _event("A", summary="المصادق عليه"))
    crud.upsert_raw_event(db_session, _event("A", summary="نسخة العون", actor=OPERATOR))
    raw = _raw(db_session, "A")
    assert (raw.event_summary, raw.approved) == ("المصادق عليه", True)


def test_approved_version_replaces_an_operator_copy(db_session):
    crud.upsert_raw_event(db_session, _event("A", summary="نسخة العون", actor=OPERATOR))
    crud.upsert_raw_event(db_session, _event("A", summary="المصادق عليه"))
    raw = _raw(db_session, "A")
    assert (raw.event_summary, raw.approved) == ("المصادق عليه", True)


def test_newest_version_wins_although_the_source_lists_newest_first(db_session, monkeypatch):
    newest_first = [
        _event("A", summary="الأحدث", time="2026-11-20T12:00:00"),
        _event("A", summary="الأقدم", time="2026-11-20T09:00:00"),
    ]
    monkeypatch.setattr(worker, "fetch_events", lambda start: newest_first)
    worker.fetch_new_events(db_session)
    assert _raw(db_session, "A").event_summary == "الأحدث"


# --- hidden everywhere -----------------------------------------------------------


def test_classifier_skips_reports_that_are_not_approved(db_session):
    crud.upsert_raw_event(db_session, _event("A"))
    crud.upsert_raw_event(db_session, _event("B", actor=OPERATOR))
    assert _picked(db_session) == ["A"]


def test_dashboard_shows_approved_reports_only(db_session, client):
    _done(db_session, "A", summary="حادث أول")
    _done(db_session, "B", summary="حادث ثان", actor=OPERATOR)
    body = client.get("/api/events").json()
    assert body["total_items"] == 1
    assert [row["event_summary"] for row in body["data"]] == ["حادث أول"]
    assert [p.reference for p, _raw in crud.list_done_with_raw(db_session)] == ["A"]


def test_operator_copy_is_not_grouped_with_the_approved_report(db_session):
    # Same text would otherwise merge them, and the later one would become the main report.
    _done(db_session, "A", summary="حادث مرور بين سيارتين")
    _done(db_session, "B", summary="حادث مرور بين سيارتين", actor=OPERATOR)
    assert grouping.group_all(db_session) == {"reports": 1, "events": 1, "merged": 0}
    assert crud.get_processed(db_session, "A").is_main is True


# --- backfill over data already stored -------------------------------------------


def test_backfill_marks_matching_references_and_keeps_the_rest(db_session):
    _done(db_session, "A", summary="نص العون", actor=None)   # stored from /events, later approved with new text
    _done(db_session, "B", summary="نفس النص", actor=None)   # approved with the same text
    _done(db_session, "C", summary="لم يصادق عليه", actor=None)  # never approved
    approved = [
        _event("A", summary="نص المصادقة القديم", time="2026-11-20T09:00:00"),
        _event("A", summary="نص المصادقة", time="2026-11-20T11:00:00"),
        _event("B", summary="نفس النص"),
        _event("D", summary="لم يُخزّن بعد"),
    ]

    result = backfill_approval(db_session, approved)

    assert result == {
        "approved_versions": 3,
        "marked": 2,
        "already": 0,
        "text_changed": 1,
        "new": 1,
        "not_approved": 1,
    }
    assert _raw(db_session, "A").event_summary == "نص المصادقة"
    assert [r for r in ("A", "B", "C", "D") if _raw(db_session, r).approved] == ["A", "B", "D"]
    assert _raw(db_session, "C").event_summary == "لم يصادق عليه"  # nothing deleted
    # A's text changed -> re-extracted; D is new -> classified; B and C untouched.
    assert _picked(db_session) == ["A", "D"]


def test_backfill_dry_run_changes_nothing(db_session):
    _done(db_session, "A", actor=None)
    result = backfill_approval(db_session, [_event("A")], dry_run=True)
    assert (result["marked"], result["not_approved"]) == (1, 0)
    assert _raw(db_session, "A").approved is False
