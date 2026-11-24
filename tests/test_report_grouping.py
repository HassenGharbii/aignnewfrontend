"""The same accident arrives as several reports (re-sent by another unit, or
followed up citing the earlier number): they must count as one event, showing
the latest version, with the others kept as its history. Made-up data only."""

from app import crud, grouping, models, worker

TRAFFIC = "أحداث مرورية"
THEFT = "جرائم السرقات"
TEXT = "حادث مرور اصطدام بين سيارتين على الطريق الوطنية رقم 1"


def _report(db, ref, text=TEXT, time="2026-11-20T01:00:00", category=TRAFFIC, deaths=0, **fields):
    crud.upsert_raw_event(db, {"reference": ref, "event_summary": text, "time": time, "source": f"unit {ref}", "actor": "SOC_Manager"})
    db.add(
        models.ProcessedEvent(
            reference=ref,
            status="done",
            data={
                "التصنيف": {"الصنف_الرئيسي": category},
                "تفاصيل_الحادث": {"عدد_الوفيات": deaths, "عدد_الإصابات": 1},
            },
            **fields,
        )
    )
    db.commit()
    return crud.get_processed(db, ref)


def _main_refs(db):
    return sorted(p.reference for p, _raw in crud.list_done_with_raw(db))


def _group_of(db, ref):
    return crud.get_processed(db, ref).group_ref


# --- citation parsing ---------------------------------------------------------


def test_cited_numbers_reads_the_usual_wordings():
    assert grouping.cited_numbers("ملخص الحدث : تبعا للإعلام عدد 126417 بتاريخ 21/11/2026") == ["126417"]
    assert grouping.cited_numbers("تبعا لاعلامنا عدد 120001 و الاعلام عدد 120002 حول") == ["120001", "120002"]
    assert grouping.cited_numbers("تبعا لبطاقة الإشعار الفوري عدد 099999 المتعلقة") == ["099999"]


def test_cited_numbers_ignores_other_numbers():
    assert grouping.cited_numbers("اصطدام بين عدد 03 سيارات و عدد 120001 من المترجلين") == []
    assert grouping.cited_numbers("تبعا للإعلام عدد 000000") == []
    assert grouping.cited_numbers(None) == []


# --- rule (a): identical text -------------------------------------------------


def test_identical_reports_become_one_event_shown_once(db_session):
    _report(db_session, "110100-0001-120001", time="2026-11-20T01:01:00")
    _report(db_session, "110000-0002-120002", time="2026-11-20T02:44:00")
    grouping.group_all(db_session)
    assert _group_of(db_session, "110100-0001-120001") == _group_of(db_session, "110000-0002-120002")
    assert _main_refs(db_session) == ["110000-0002-120002"]  # the latest one


def test_different_texts_stay_separate(db_session):
    _report(db_session, "110100-0001-120001")
    _report(db_session, "110100-0002-120002", text="حادث آخر مختلف تماما")
    grouping.group_all(db_session)
    assert _main_refs(db_session) == ["110100-0001-120001", "110100-0002-120002"]


def test_identical_text_in_another_category_is_not_merged(db_session):
    _report(db_session, "110100-0001-120001")
    _report(db_session, "110100-0002-120002", category=THEFT)
    grouping.group_all(db_session)
    assert _main_refs(db_session) == ["110100-0001-120001", "110100-0002-120002"]


# --- rule (b): citation ---------------------------------------------------------


def test_follow_up_chain_becomes_one_event(db_session):
    _report(db_session, "240000-0001-120001", text="حادث مرور جرح سائق", time="2026-11-20T08:00:00")
    _report(db_session, "240000-0002-120002", text="تبعا للإعلام عدد 120001 توفي الجريح", time="2026-11-21T08:00:00", deaths=1)
    _report(db_session, "240000-0003-120003", text="تبعا للإعلام عدد 120002 تم الدفن", time="2026-11-22T08:00:00", deaths=1)
    grouping.group_all(db_session)
    groups = {_group_of(db_session, r) for r in ("240000-0001-120001", "240000-0002-120002", "240000-0003-120003")}
    assert groups == {"240000-0001-120001"}  # named after the earliest report
    assert _main_refs(db_session) == ["240000-0003-120003"]


def test_ambiguous_citation_is_not_linked(db_session):
    _report(db_session, "110100-0001-120001", text="حادث أول")
    _report(db_session, "220100-0005-120001", text="حادث ثان")
    _report(db_session, "330100-0009-120009", text="تبعا للإعلام عدد 120001 تحيين")
    grouping.group_all(db_session)
    assert len(_main_refs(db_session)) == 3


# --- rule (c): same opening, sent within a day -------------------------------

OPENING = "ملخص الحدث : ليوم 07/11/2026 على الساعة 19:10 على مستوى الطريق الوطنية رقم 1 " * 3


def test_corrected_resend_within_a_day_is_merged(db_session):
    _report(db_session, "030200-0935-000000", text=OPENING + "جرح سائق", time="2026-11-07T19:16:16")
    _report(db_session, "030000-2574-116332", text=OPENING + "جرح سائقان", time="2026-11-07T20:54:15")
    grouping.group_all(db_session)
    assert _main_refs(db_session) == ["030000-2574-116332"]


def test_same_opening_days_apart_stays_separate(db_session):
    _report(db_session, "210000-1823-113598", text=OPENING + "حادث أول", time="2026-11-04T06:16:17")
    _report(db_session, "210100-4896-000000", text=OPENING + "حادث ثان", time="2026-11-07T20:46:33")
    grouping.group_all(db_session)
    assert len(_main_refs(db_session)) == 2


def test_short_texts_are_not_matched_by_opening(db_session):
    _report(db_session, "030200-0001-000000", text="حادث مرور أ", time="2026-11-07T19:00:00")
    _report(db_session, "030200-0002-000000", text="حادث مرور ب", time="2026-11-07T19:30:00")
    grouping.group_all(db_session)
    assert len(_main_refs(db_session)) == 2


# --- main row choice, idempotence, dry run -----------------------------------


def test_hand_edited_version_stays_the_main_one(db_session):
    _report(db_session, "110100-0001-120001", time="2026-11-20T01:00:00", is_edited=True)
    _report(db_session, "110000-0002-120002", time="2026-11-20T03:00:00")
    grouping.group_all(db_session)
    assert _main_refs(db_session) == ["110100-0001-120001"]


def test_group_all_twice_gives_the_same_result(db_session):
    _report(db_session, "110100-0001-120001", time="2026-11-20T01:00:00")
    _report(db_session, "110000-0002-120002", time="2026-11-20T03:00:00")
    first = grouping.group_all(db_session)
    second = grouping.group_all(db_session)
    assert first == second == {"reports": 2, "events": 1, "merged": 1}
    assert _main_refs(db_session) == ["110000-0002-120002"]


def test_dry_run_counts_without_saving(db_session):
    _report(db_session, "110100-0001-120001")
    _report(db_session, "110000-0002-120002")
    assert grouping.group_all(db_session, dry_run=True) == {"reports": 2, "events": 1, "merged": 1}
    db_session.expire_all()
    assert _main_refs(db_session) == ["110000-0002-120002", "110100-0001-120001"]


# --- worker: new reports join their event as they are classified ---------------


def test_worker_cycle_links_a_new_copy_to_its_event(db_session, monkeypatch):
    monkeypatch.setattr(worker, "classify_category", lambda s, t, c: {"الصنف_الرئيسي": TRAFFIC, "نسبة_الثقة": 0.9})
    monkeypatch.setattr(worker, "extract_details", lambda s, t, reference=None: {})
    monkeypatch.setattr(worker, "load_categories", lambda: [TRAFFIC])
    monkeypatch.setattr(worker, "load_category_map", lambda: {})
    _report(db_session, "110100-0001-120001", time="2026-11-20T01:00:00")
    crud.upsert_raw_event(
        db_session, {"reference": "110000-0002-120002", "event_summary": TEXT, "time": "2026-11-20T03:00:00", "actor": "SOC_Manager"}
    )
    assert worker.classify_once(db_session)["classified"] == 1
    assert _main_refs(db_session) == ["110000-0002-120002"]


# --- what the dashboard sees ---------------------------------------------------


def test_dashboard_counts_the_event_once_and_lists_its_versions(db_session, client):
    _report(db_session, "240000-0001-120001", text="حادث مرور جرح سائق", time="2026-11-20T08:00:00")
    _report(db_session, "240000-0002-120002", text="تبعا للإعلام عدد 120001 توفي الجريح", time="2026-11-21T08:00:00", deaths=1)
    grouping.group_all(db_session)

    assert client.get("/api/stats/summary").json()["total_events"] == 1
    page = client.get("/api/events").json()
    assert page["total_items"] == 1
    event = page["data"][0]
    assert event["details"]["تفاصيل_الحادث"]["عدد_الوفيات"] == 1
    assert event["versions"] == [
        {
            "reference": "240000-0001-120001",
            "event_time": "2026-11-20T08:00:00",
            "source": "unit 240000-0001-120001",
            "deaths": 0,
            "injuries": 1,
        }
    ]
