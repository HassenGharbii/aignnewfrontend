import math

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlalchemy.orm import Session

from . import config, crud, models, schemas, serialize
from .db import Base, SessionLocal, engine, get_db

app = FastAPI(title="Morour Traffic Events API")

# Wide open for now since this runs on a trusted internal network alongside the
# dashboard — tighten to the actual frontend origin before exposing this beyond it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Ops API — reference-keyed, for inspecting/correcting individual records
# (Postman/curl/scripts, not the dashboard below).
# ---------------------------------------------------------------------------
@app.get("/events", response_model=list[schemas.ProcessedEventOut])
def list_events(
    limit: int = Query(50, le=500),
    offset: int = 0,
    subcategory: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.ProcessedEvent).order_by(desc(models.ProcessedEvent.created_at))
    if status:
        query = query.filter(models.ProcessedEvent.status == status)
    results = query.all()
    if subcategory:
        results = [
            r for r in results
            if ((r.data or {}).get("التصنيف") or {}).get("الصنف_الفرعي") == subcategory
        ]
    return results[offset : offset + limit]


@app.get("/events/{reference}", response_model=schemas.ProcessedEventOut)
def get_event(reference: str, db: Session = Depends(get_db)):
    processed = crud.get_processed(db, reference)
    if processed is None:
        raise HTTPException(404, "processed event not found")
    return processed


@app.get("/events/{reference}/raw", response_model=schemas.RawEventOut)
def get_raw_event(reference: str, db: Session = Depends(get_db)):
    raw = db.query(models.RawEvent).filter_by(reference=reference).first()
    if raw is None:
        raise HTTPException(404, "raw event not found")
    return raw


@app.patch("/events/{reference}", response_model=schemas.ProcessedEventOut)
def update_event(reference: str, update: schemas.ProcessedEventUpdate, db: Session = Depends(get_db)):
    """Partial update: only the keys present in `data` are merged in (recursively
    for nested objects), so a caller can send just {"تفاصيل_الحادث": {"عدد_الوفيات": 1}}
    without resending the whole record."""
    processed = crud.get_processed(db, reference)
    if processed is None:
        raise HTTPException(404, "processed event not found")
    processed.data = crud.deep_merge(processed.data or {}, update.data)
    processed.is_edited = True
    db.commit()
    db.refresh(processed)
    return processed


@app.post("/events/poll", response_model=schemas.PollResult)
def trigger_poll():
    """Run one poll cycle immediately instead of waiting for the worker's interval."""
    from . import worker

    db = SessionLocal()
    try:
        return worker.poll_once(db)
    finally:
        db.close()


@app.post("/admin/reset-poll-state")
def reset_poll_state(start: str, db: Session = Depends(get_db)):
    """Force the worker's next poll to (re)start from this timestamp. Needed
    because START_DATE in .env only seeds poll_state the very first time the
    worker ever runs — after that, poll_state in the database takes over and
    ignores .env entirely, so changing START_DATE later has no effect on its
    own. `start` must be an ISO datetime, e.g. 2026-08-18T00:00:00."""
    crud.get_or_create_poll_state(db, start)
    crud.update_poll_state(db, start)
    return {"next_start": start}


# ---------------------------------------------------------------------------
# Dashboard API — flat, numeric-id, paginated shape consumed by the
# traffic-incidents-dashboard frontend (src/api/*). Everything here is
# computed from the same processed_events rows as the ops API above; nothing
# is stored twice.
#
# Filtering/pagination happens in Python after loading all "done" rows rather
# than in SQL, since the interesting fields (region, severity, sub_category)
# live inside JSONB and are derived, not stored columns. Fine at the volume
# this feed produces (a police reporting stream, not a firehose) — revisit
# with real columns/indexes if that stops being true.
# ---------------------------------------------------------------------------
def _dashboard_rows(db: Session) -> list[dict]:
    return [serialize.to_dashboard_event(processed, raw) for processed, raw in crud.list_done_with_raw(db)]


@app.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    categories = {row["category"] for row in _dashboard_rows(db) if row["category"]}
    return sorted(categories) or [config.CATEGORY]


@app.get("/api/stats/summary")
def stats_summary(db: Session = Depends(get_db)):
    rows = _dashboard_rows(db)

    by_category: dict[str, dict] = {}
    for row in rows:
        category = row["category"] or config.CATEGORY
        bucket = by_category.setdefault(category, {"category": category, "count": 0, "sub_categories": {}})
        bucket["count"] += 1
        sub = row["sub_category"] or "غير مصنف"
        bucket["sub_categories"][sub] = bucket["sub_categories"].get(sub, 0) + 1

    events_by_category = [
        {
            "category": b["category"],
            "count": b["count"],
            "sub_categories": [
                {"sub_category": name, "count": count} for name, count in b["sub_categories"].items()
            ],
        }
        for b in by_category.values()
    ]

    recent = sorted(rows, key=lambda r: r["created_at"] or "", reverse=True)[:10]
    recent_events = [
        {
            "event_title": r["event_title"],
            "category": r["category"],
            "event_time": r["event_time"],
            "region": r["region"],
        }
        for r in recent
    ]

    return {
        "total_events": len(rows),
        "events_by_category": events_by_category,
        "recent_events": recent_events,
    }


@app.get("/api/events")
def list_dashboard_events(
    limit: int = Query(50, le=2000),
    offset: int = 0,
    category: str | None = None,
    sub_category: str | None = None,
    region: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    rows = _dashboard_rows(db)

    if category:
        rows = [r for r in rows if r["category"] == category]
    if sub_category:
        rows = [r for r in rows if r["sub_category"] == sub_category]
    if region:
        rows = [r for r in rows if r["region"] == region]
    if search:
        needle = search.strip().lower()
        rows = [
            r
            for r in rows
            if needle
            in " ".join(
                filter(None, [r["event_title"], r["event_summary"], r["sub_category"]])
            ).lower()
        ]

    total_items = len(rows)
    page = rows[offset : offset + limit]
    total_pages = max(1, math.ceil(total_items / limit)) if limit else 1
    current_page = (offset // limit) + 1 if limit else 1

    return {
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": current_page,
        "data": page,
    }


@app.get("/people/search")
def people_search(
    query: str | None = None,
    cin: str | None = None,
    region: str | None = None,
    category: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    rows = _dashboard_rows(db)
    if region:
        rows = [r for r in rows if r["region"] == region]
    if category:
        rows = [r for r in rows if r["category"] == category]
    if status:
        rows = [r for r in rows if r["event_status"] == status]
    if severity:
        rows = [r for r in rows if r["severity"] == severity]

    processed_by_id = {row["id"]: row for row in rows}
    all_done = crud.list_done_with_raw(db)

    people_by_key: dict[str, dict] = {}
    for processed, _raw in all_done:
        row = processed_by_id.get(processed.id)
        if row is None:
            continue  # filtered out above
        for person in serialize.extract_people(processed, row):
            name = person["name"]
            cin_value = person["cin"]
            if query and query.strip().lower() not in name.lower():
                continue
            if cin and cin.strip() not in cin_value:
                continue
            key = cin_value or name or f"anon-{processed.id}"
            bucket = people_by_key.setdefault(
                key,
                {
                    "cin": cin_value,
                    "name": name,
                    "nickname": None,
                    "gender": None,
                    "age_range": None,
                    "phone": None,
                    "address": None,
                    "occupation": None,
                    "criminal_record": None,
                    "risk_level": None,
                    "event_count": 0,
                    "last_seen": None,
                    "history": [],
                },
            )
            bucket["event_count"] += 1
            bucket["history"].append(person["record"])
            if not bucket["last_seen"] or (person["record"]["event_datetime"] or "") > bucket["last_seen"]:
                bucket["last_seen"] = person["record"]["event_datetime"]

    results = list(people_by_key.values())[offset : offset + limit]
    return {"count": len(people_by_key), "results": results}
