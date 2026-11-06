from sqlalchemy import text

from app.db import engine

TRAFFIC = "أحداث مرورية"
OTHER = "أحداث أخرى"


def _get(client, **params):
    resp = client.get("/api/events", params=params)
    assert resp.status_code == 200
    return resp.json()


def test_category_filter_returns_only_that_category(client, make_event):
    for i in range(3):
        make_event(f"t{i}", category=TRAFFIC)
    for i in range(2):
        make_event(f"o{i}", category=OTHER)
    body = _get(client, category=TRAFFIC, limit=2000)
    assert body["total_items"] == 3
    assert all(r["category"] == TRAFFIC for r in body["data"])


def test_no_category_returns_all_done_including_null_data(client, make_event):
    make_event("a", category=TRAFFIC)
    make_event("b", data_override=None)
    make_event("c", status="failed")
    assert _get(client)["total_items"] == 2


def test_null_or_missing_classification_excluded_with_category(client, make_event):
    make_event("a", data_override=None)
    make_event("b", data_override={})
    assert _get(client, category=TRAFFIC)["total_items"] == 0


def test_pagination_over_filtered_rows(client, make_event):
    for i in range(5):
        make_event(f"t{i}", category=TRAFFIC)
    body = _get(client, category=TRAFFIC, limit=2, offset=4)
    assert body["total_items"] == 5
    assert len(body["data"]) == 1


def test_sub_category_and_search_still_apply(client, make_event):
    make_event("a", sub_category="حادث دهس")
    make_event("b", sub_category="حادث تصادم")
    assert _get(client, category=TRAFFIC, sub_category="حادث دهس")["total_items"] == 1
    assert _get(client, category=TRAFFIC, search="حادث دهس")["total_items"] == 1


def test_patch_category_change_visible_immediately(client, make_event):
    make_event("a", category=TRAFFIC)
    assert _get(client, category=TRAFFIC)["total_items"] == 1
    resp = client.patch("/events/a", json={"data": {"التصنيف": {"الصنف_الرئيسي": OTHER}}})
    assert resp.status_code == 200
    assert _get(client, category=TRAFFIC)["total_items"] == 0


def test_category_index_exists():
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM pg_indexes WHERE indexname = 'ix_processed_events_category'")
        ).first()
    assert row is not None
