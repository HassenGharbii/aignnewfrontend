"""Standalone background worker: pulls raw_events rows already sitting in the
database that have no successful classification yet, classifies each one into
a top-level category (and a sub-category within it, where known) using a
small Ollama model, and writes the result into processed_events.

This is independent of app/worker.py's API-polling loop — it only reads/writes
the database, never touching app/worker.py, app/pipeline.py, app/config.py,
app/api.py or .env.example. The set of top-level categories the classifier can
choose from comes from categories.json (the declared list); sub-categories,
where they've been defined, still come from subcategory.txt — a category
missing from subcategory.txt is classified with no sub-category.

Run with: python -m app.category_worker
"""

import json
import os
import re
import time

from sqlalchemy.orm import Session

from . import config, models
from .db import Base, SessionLocal, engine
from .pipeline import classify_subcategory, extract_details, ollama_chat_json


def log(*args):
    print(*args, flush=True)


POLL_INTERVAL_SECONDS = config.POLL_INTERVAL_SECONDS
# How many unclassified rows to pull from the database per cycle.
BATCH_SIZE = int(os.getenv("CATEGORY_WORKER_BATCH_SIZE", "20"))

CATEGORIES_FILE = config.BASE_DIR / "categories.json"

_CATEGORY_BLOCK_RE = re.compile(r'"([^"]+)"\s*:\s*\[(.*?)\]', re.DOTALL)
_STRING_RE = re.compile(r'"([^"]+)"')


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


def classify_once(db: Session) -> dict:
    categories = load_categories()
    category_map = load_category_map()
    rows = fetch_unclassified(db, BATCH_SIZE)

    classified_count = 0
    failed_count = 0
    for raw in rows:
        summary = (raw.event_summary or "").strip()
        if not summary:
            continue

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
            save(db, raw.reference, data=None, status="failed", error=str(exc))
            failed_count += 1
            continue

        save(db, raw.reference, data=record, status="done", error=None)
        classified_count += 1

    log(f"[category-worker] pulled={len(rows)} classified={classified_count} failed={failed_count}")
    return {"pulled": len(rows), "classified": classified_count, "failed": failed_count}


def main():
    Base.metadata.create_all(bind=engine)
    log(f"[category-worker] starting, polling the database every {POLL_INTERVAL_SECONDS}s")
    while True:
        db = SessionLocal()
        try:
            classify_once(db)
        except Exception as exc:
            log(f"[category-worker] cycle failed: {exc}")
        finally:
            db.close()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
