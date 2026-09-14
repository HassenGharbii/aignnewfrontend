"""Background worker.

On startup (unless BACKFILL_ON_START=false) it re-classifies every record
already in raw_events, skipping ones a user edited by hand (backfill_all).
Then it loops, one combined cycle per interval:

1. Fetch new events from the source events API, all categories, and store every
   one seen into raw_events (fetch_new_events).
2. Pull raw_events rows that have no processed_events row yet (or a failed one
   that wasn't user-edited), classify each into a top-level category (and a
   sub-category within it, where known), extract structured fields from
   event_summary using Ollama, and write the result into processed_events
   (classify_once).

The set of top-level categories the classifier can choose from comes from
categories.json (the declared list); sub-categories, where they've been
defined, still come from subcategory.txt — a category missing from
subcategory.txt is classified with no sub-category.

Run with: python -m app.worker
"""

import json
import os
import re
import time
from datetime import datetime, timedelta

import requests
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import config, crud, models
from .db import Base, SessionLocal, engine
from .pipeline import classify_subcategory, extract_details, ollama_chat_json


def log(*args):
    print(*args, flush=True)


POLL_INTERVAL_SECONDS = config.POLL_INTERVAL_SECONDS
# How many rows to pull from the database per query.
BATCH_SIZE = int(os.getenv("WORKER_BATCH_SIZE", "20"))
BACKFILL_ON_START = os.getenv("BACKFILL_ON_START", "true").strip().lower() in ("1", "true", "yes")

CATEGORIES_FILE = config.BASE_DIR / "categories.json"

_CATEGORY_BLOCK_RE = re.compile(r'"([^"]+)"\s*:\s*\[(.*?)\]', re.DOTALL)
_STRING_RE = re.compile(r'"([^"]+)"')

MAX_PAGES = 1000  # safety cap, not an expected ceiling


# ---------------------------------------------------------------------------
# Fetch new events from the source API into raw_events
# ---------------------------------------------------------------------------
def fetch_events(start: str) -> list:
    if config.USE_SAMPLE_DATA:
        log(f"[data] USE_SAMPLE_DATA=true -> reading {config.SAMPLE_DATA_FILE}")
        return json.loads(config.SAMPLE_DATA_FILE.read_text(encoding="utf-8"))

    url = f"{config.API_BASE_URL}{config.EVENTS_PATH}"
    all_events = []
    page = 1
    while page <= MAX_PAGES:
        # No category filter: the source category is usually empty, so the
        # classifier assigns it instead.
        params = {
            config.START_PARAM: start,
            "page": page,
            "page_size": config.EVENTS_PAGE_SIZE,
        }
        log(f"[api] GET {url} params={params}")
        resp = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_events.extend(batch)
        if len(batch) < config.EVENTS_PAGE_SIZE:
            break  # last page
        page += 1
    return all_events


def fetch_new_events(db: Session) -> dict:
    state = crud.get_or_create_poll_state(db, config.DEFAULT_START_DATE)

    try:
        events = fetch_events(state.next_start)
    except requests.RequestException as exc:
        log(f"[api] request failed: {exc}")
        return {"fetched": 0, "stored": 0, "error": str(exc)}

    stored_count = 0
    latest_time = None

    for event in events:
        reference = event.get("reference")
        if not reference:
            continue

        crud.upsert_raw_event(db, event)
        stored_count += 1

        event_time = event.get("time")
        if event_time and (latest_time is None or event_time > latest_time):
            latest_time = event_time

    if latest_time:
        next_start = (
            datetime.fromisoformat(latest_time) - timedelta(minutes=config.POLL_OVERLAP_MINUTES)
        ).isoformat()
        crud.update_poll_state(db, next_start)

    log(f"[fetch] fetched={len(events)} stored={stored_count}")
    return {"fetched": len(events), "stored": stored_count, "error": None}


# ---------------------------------------------------------------------------
# Classify + extract raw_events rows into processed_events
# ---------------------------------------------------------------------------
def load_categories() -> list[str]:
    """categories.json is the declared list of top-level categories the
    classifier is allowed to choose among."""
    return json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))


def load_category_map() -> dict[str, list[str]]:
    """subcategory.txt is a loose (trailing-comma) JSON fragment, so it's parsed
    with regex instead of json.loads. Returns {category: [subcategories]} for
    every top-level category block in the file — not every declared category
    necessarily has one yet."""
    text = config.SUBCATEGORY_FILE.read_text(encoding="utf-8")
    return {
        match.group(1): _STRING_RE.findall(match.group(2))
        for match in _CATEGORY_BLOCK_RE.finditer(text)
    }


def classify_category(event_summary: str, subject: str, categories: list[str]) -> dict:
    schema = {
        "type": "object",
        "properties": {
            "الصنف_الرئيسي": {"type": "string", "enum": categories},
            "نسبة_الثقة": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["الصنف_الرئيسي", "نسبة_الثقة"],
    }
    prompt = (
        f"نص الحدث:\n{event_summary}\n\n"
        f"عنوان الحدث: {subject}\n\n"
        "أنت محلل مختص في تصنيف البلاغات الواردة من مصادر أمنية متنوعة.\n"
        "صنّف نص الحدث أعلاه ضمن إحدى الفئات الرئيسية المتاحة فقط، واختر الأقرب دلاليًا لمضمون النص.\n\n"
        "الفئات الرئيسية المتاحة:\n" + "\n".join(f"- {c}" for c in categories) + "\n\n"
        "أعد فقط كائن JSON بالصنف الرئيسي المختار (بنفس الصياغة الحرفية من القائمة أعلاه) ونسبة ثقة بين 0 و1."
    )
    return ollama_chat_json(config.CLASSIFICATION_MODEL, prompt, schema)


def build_record(raw: models.RawEvent, category: str, subcategory: dict, extraction: dict) -> dict:
    """Same shape as schemaextractevent.txt / pipeline.build_event_record, but
    tagged with whatever category the classifier actually picked instead of a
    fixed one."""
    return {
        "معرف_الحدث": raw.reference,
        "المصدر": raw.source,
        "الطوابع_الزمنية": {
            "وقت_الإنشاء": None,
            "وقت_التحديث": None,
            "وقت_الحدث": raw.event_time,
        },
        "التصنيف": {
            "الصنف_الرئيسي": category,
            "الصنف_الفرعي": subcategory.get("الصنف_الفرعي"),
            "نسبة_الثقة": subcategory.get("نسبة_الثقة"),
        },
        "عنوان": raw.subject,
        "كلمات_مفتاحية": extraction.get("كلمات_مفتاحية", []),
        "الموقع": {
            "العنوان": raw.event_place,
            "المنطقة": extraction.get("الموقع", {}).get("المنطقة"),
            "المعتمدية": extraction.get("الموقع", {}).get("المعتمدية"),
            "العمادة": extraction.get("الموقع", {}).get("العمادة"),
        },
        "الأطراف": extraction.get("الأطراف", {}),
        "تفاصيل_الحادث": extraction.get("تفاصيل_الحادث", {}),
        "النص_الأصلي": raw.event_summary,
    }


def fetch_unclassified(db: Session, limit: int) -> list[models.RawEvent]:
    """raw_events with no processed_events row yet, or a failed/non-edited one
    (transient errors get retried; a user's PATCH edit is never touched)."""
    return (
        db.query(models.RawEvent)
        .outerjoin(models.ProcessedEvent, models.ProcessedEvent.reference == models.RawEvent.reference)
        .filter(
            (models.ProcessedEvent.id.is_(None))
            | ((models.ProcessedEvent.status == "failed") & (models.ProcessedEvent.is_edited.is_(False)))
        )
        .order_by(models.RawEvent.fetched_at.asc())
        .limit(limit)
        .all()
    )


def save(db: Session, reference: str, data: dict | None, status: str, error: str | None) -> None:
    processed = db.query(models.ProcessedEvent).filter_by(reference=reference).first()
    if processed is None:
        processed = models.ProcessedEvent(reference=reference)
        db.add(processed)
    processed.data = data
    processed.status = status
    processed.error = error
    processed.classification_model = config.CLASSIFICATION_MODEL
    processed.extraction_model = config.EXTRACTION_MODEL
    db.commit()


def classify_row(db: Session, raw: models.RawEvent, categories: list[str], category_map: dict) -> bool | None:
    """Classify one raw_events row and save the result. Returns True on success,
    False on failure, None if skipped because event_summary is empty."""
    summary = (raw.event_summary or "").strip()
    if not summary:
        # Marked, not just skipped in memory: an unmarked row is pulled again
        # every cycle and occupies a batch slot forever.
        save(db, raw.reference, data=None, status="skipped", error="empty event_summary")
        return None

    subject = raw.subject or ""
    try:
        log(f"[classify] reference={raw.reference} model={config.CLASSIFICATION_MODEL}")
        category_result = classify_category(summary, subject, categories)
        category = category_result["الصنف_الرئيسي"]
        subcategories = category_map.get(category)
        if subcategories:
            subcategory = classify_subcategory(summary, subject, subcategories)
        else:
            # No sub-category list declared yet for this category (see
            # subcategory.txt) — classify at the category level only.
            subcategory = {"الصنف_الفرعي": None, "نسبة_الثقة": category_result.get("نسبة_الثقة")}
        extraction = extract_details(summary, subject, reference=raw.reference)
        record = build_record(raw, category, subcategory, extraction)
    except Exception as exc:
        log(f"[error] reference={raw.reference}: {exc}")
        existing = db.query(models.ProcessedEvent).filter_by(reference=raw.reference).first()
        # A failed re-classification must not wipe out a record that was already classified.
        if existing is None or existing.status != "done":
            save(db, raw.reference, data=None, status="failed", error=str(exc))
        return False

    save(db, raw.reference, data=record, status="done", error=None)
    return True


def classify_once(db: Session) -> dict:
    categories = load_categories()
    category_map = load_category_map()
    rows = fetch_unclassified(db, BATCH_SIZE)

    classified_count = 0
    failed_count = 0
    skipped_count = 0
    for raw in rows:
        outcome = classify_row(db, raw, categories, category_map)
        if outcome is True:
            classified_count += 1
        elif outcome is False:
            failed_count += 1
        else:
            skipped_count += 1

    log(
        f"[classify] pulled={len(rows)} classified={classified_count} "
        f"failed={failed_count} skipped={skipped_count}"
    )
    return {
        "pulled": len(rows),
        "classified": classified_count,
        "failed": failed_count,
        "skipped": skipped_count,
    }


def backfill_all(db: Session) -> dict:
    """Re-classify every raw_events row once, oldest id first, skipping records
    a user edited by hand. Pages by id so no row is picked up twice."""
    categories = load_categories()
    category_map = load_category_map()
    candidates = (
        db.query(models.RawEvent)
        .outerjoin(models.ProcessedEvent, models.ProcessedEvent.reference == models.RawEvent.reference)
        .filter(or_(models.ProcessedEvent.id.is_(None), models.ProcessedEvent.is_edited.is_(False)))
    )
    total = candidates.count()
    log(f"[backfill] re-classifying {total} record(s)")

    last_id = 0
    seen = classified = failed = skipped = 0
    while True:
        rows = (
            candidates.filter(models.RawEvent.id > last_id)
            .order_by(models.RawEvent.id.asc())
            .limit(BATCH_SIZE)
            .all()
        )
        if not rows:
            break
        for raw in rows:
            last_id = raw.id
            seen += 1
            outcome = classify_row(db, raw, categories, category_map)
            if outcome is True:
                classified += 1
            elif outcome is False:
                failed += 1
            else:
                skipped += 1
        log(f"[backfill] {seen}/{total} (classified={classified} failed={failed} skipped={skipped})")

    log(f"[backfill] done: total={total} classified={classified} failed={failed} skipped={skipped}")
    return {"total": total, "classified": classified, "failed": failed, "skipped": skipped}


# ---------------------------------------------------------------------------
# Combined cycle: fetch first, then classify what's now available
# ---------------------------------------------------------------------------
def run_cycle(db: Session) -> dict:
    fetch_result = fetch_new_events(db)
    classify_result = classify_once(db)
    result = {**fetch_result, **classify_result}
    log(
        f"[worker] cycle done: fetched={fetch_result['fetched']} stored={fetch_result['stored']} "
        f"pulled={classify_result['pulled']} classified={classify_result['classified']} "
        f"failed={classify_result['failed']} skipped={classify_result['skipped']}"
    )
    return result


def main():
    Base.metadata.create_all(bind=engine)

    if BACKFILL_ON_START:
        db = SessionLocal()
        try:
            backfill_all(db)
        except Exception as exc:
            log(f"[backfill] stopped early: {exc}")
        finally:
            db.close()

    log(f"[worker] starting, running fetch+classify every {POLL_INTERVAL_SECONDS}s")
    while True:
        db = SessionLocal()
        try:
            run_cycle(db)
        except Exception as exc:
            log(f"[worker] cycle failed: {exc}")
        finally:
            db.close()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
