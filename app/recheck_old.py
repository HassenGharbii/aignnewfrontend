"""Queue reports whose figures were extracted from an older version of their text.

Before version tracking, a correction re-sent under the same reference overwrote
raw_events.event_summary but the extraction was never redone. Every processed
record keeps the text it was extracted from in data["النص_الأصلي"], so those
reports are found exactly: saved text != current raw text. This sets their
source_hash to the hash of the saved text; the worker's normal loop then sees it
differ from raw_events.summary_hash and re-extracts them.

Hand-edited reports are never touched. Traffic only unless --all-categories.

Run with:
    python -m app.recheck_old --dry-run          # count and list, change nothing
    python -m app.recheck_old                    # queue stale traffic reports
    python -m app.recheck_old --all-categories   # every category
"""

import argparse

from sqlalchemy import func

from . import config, models
from .crud import CATEGORY_EXPR
from .db import SessionLocal
from .pipeline import log
from .serialize import event_summary_hash

SAVED_TEXT = func.json_extract_path_text(models.ProcessedEvent.data, "النص_الأصلي")


def recheck_old(db, all_categories: bool = False, dry_run: bool = False) -> dict:
    query = (
        db.query(models.ProcessedEvent, SAVED_TEXT)
        .join(models.RawEvent, models.RawEvent.reference == models.ProcessedEvent.reference)
        .filter(
            models.ProcessedEvent.status == "done",
            models.ProcessedEvent.is_edited.is_(False),
            SAVED_TEXT.isnot(None),
        )
    )
    if not all_categories:
        query = query.filter(CATEGORY_EXPR == config.CATEGORY)

    checked = query.count()
    stale = query.filter(SAVED_TEXT != models.RawEvent.event_summary).all()
    scope = "all categories" if all_categories else config.CATEGORY
    log(f"[recheck-old] {scope}: checked={checked} extracted_from_older_text={len(stale)}"
        f"{' (dry run)' if dry_run else ''}")

    for processed, saved_text in stale:
        if dry_run:
            log(f"[recheck-old] {processed.reference} would be re-extracted")
            continue
        processed.source_hash = event_summary_hash(saved_text)
        processed.attempts = 0
    if not dry_run and stale:
        db.commit()
        log(f"[recheck-old] queued {len(stale)} report(s); the worker re-extracts them on its next cycles")
    return {"checked": checked, "stale": len(stale)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="count and list, change nothing")
    parser.add_argument("--all-categories", action="store_true", help="not only traffic")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        recheck_old(db, all_categories=args.all_categories, dry_run=args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
