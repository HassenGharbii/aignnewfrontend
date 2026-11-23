"""Add accident causes to traffic events processed before the causes feature.

Asks the model for أسباب_الحادث only and merges the answer into the stored
JSON. Every other field (place, parties, category...) is left exactly as it
is, so hand-edited events get causes too. Only "done" events in the traffic
category are touched; unclassified and other-category rows are not.

Resumable: events that already have causes are skipped, so it can be stopped
and run again. Take a database backup before the first real run.

Run with:
    python -m app.backfill_causes --dry-run --limit 5   # print, save nothing
    python -m app.backfill_causes                       # all traffic events
"""

import argparse
import time
from typing import Callable, Iterable

from . import config, crud
from .db import SessionLocal
from .pipeline import (
    CAUSES_INSTRUCTIONS,
    EXTRACTION_SCHEMA,
    JSON_ONLY,
    log,
    normalize_causes,
    vllm_chat_json,
)

CAUSES_KEY = "أسباب_الحادث"

CAUSES_SCHEMA = {
    "type": "object",
    "properties": {CAUSES_KEY: EXTRACTION_SCHEMA["properties"][CAUSES_KEY]},
    "required": [CAUSES_KEY],
}


def build_causes_prompt(event_summary: str, subject: str) -> str:
    # Same report prefix as build_extraction_prompt, so vLLM's prefix cache applies.
    return (
        f"نص الحدث:\n{event_summary}\n\n"
        f"عنوان الحدث: {subject}\n\n"
        "أنت محلل بيانات لأحداث المرور. حدد أسباب الحادث من النص أعلاه:\n\n"
        f"{CAUSES_INSTRUCTIONS}{JSON_ONLY}"
    )


def extract_causes(event_summary: str, subject: str) -> list[str]:
    answer = vllm_chat_json(config.EXTRACTION_MODEL, build_causes_prompt(event_summary, subject), CAUSES_SCHEMA)
    return normalize_causes(answer.get(CAUSES_KEY))


def needs_causes(pair) -> bool:
    processed, raw = pair
    return CAUSES_KEY not in (processed.data or {}) and bool((raw.event_summary or "").strip())


def backfill(
    pairs: Iterable,
    extract: Callable[[str, str], list[str]],
    save: Callable[[object, dict], None],
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    targets = [p for p in pairs if needs_causes(p)]
    if limit is not None:
        targets = targets[:limit]
    total = len(targets)
    log(f"[causes] {total} traffic event(s) without causes{' (dry run)' if dry_run else ''}")

    updated = failed = 0
    started = time.monotonic()
    for i, (processed, raw) in enumerate(targets, 1):
        try:
            causes = normalize_causes(extract(raw.event_summary, raw.subject or ""))
        except Exception as exc:  # one bad call must not stop a 4k-event run
            failed += 1
            log(f"[causes] {i}/{total} {processed.reference} FAILED: {exc}")
            continue
        if not causes:
            failed += 1
            log(f"[causes] {i}/{total} {processed.reference} FAILED: no valid cause in answer")
            continue
        if dry_run:
            log(f"[causes] {i}/{total} {processed.reference} -> {causes} (not saved)")
            continue
        # A new dict, not an in-place edit: SQLAlchemy only sees reassignment of a JSON column.
        save(processed, {**(processed.data or {}), CAUSES_KEY: causes})
        updated += 1
        rate = i / max(time.monotonic() - started, 1e-9)
        log(f"[causes] {i}/{total} {processed.reference} -> {causes} ({rate:.2f}/s, failed={failed})")

    log(f"[causes] done: total={total} updated={updated} failed={failed}")
    return {"total": total, "updated": updated, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print the causes, save nothing")
    parser.add_argument("--limit", type=int, default=None, help="process at most N events")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        pairs = crud.list_done_with_raw(db, config.CATEGORY, main_only=False)

        def save(processed, data):
            processed.data = data
            db.commit()  # per event, so a stopped run keeps what it finished

        backfill(pairs, extract=extract_causes, save=save, dry_run=args.dry_run, limit=args.limit)
    finally:
        db.close()


if __name__ == "__main__":
    main()
