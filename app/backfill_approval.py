"""Mark the reports already stored as approved or not, without deleting anything.

raw_events was filled from the source's /events, which mixes operator copies
(SOC1_OP1, ...) with the version approved by SOC_Manager. This pulls the approved
versions (/approved_events?soc_manager=true) for the whole period and, for each
reference:

- marks it approved and stores the approved text (the newest approved version
  wins). When that text differs from what was extracted, the worker's normal loop
  re-extracts it (summary_hash != source_hash); unchanged reports are not touched;
- inserts it if it was never stored; the worker then classifies it.

References with no approved version stay approved=false: kept in the database,
but no longer classified, grouped or shown. Grouping is then redone over the
approved reports only. Hand-edited reports keep their edits (the worker never
re-extracts an edited record).

Run with:
    python -m app.backfill_approval --dry-run    # fetch and count, change nothing
    python -m app.backfill_approval              # apply
    python -m app.backfill_approval --start 2026-11-01T00:00:00
"""

import argparse

from . import config, crud, models
from .db import SessionLocal, init_db
from .grouping import group_all
from .pipeline import log
from .serialize import event_summary_hash
from .worker import fetch_events

PAGE_SIZE = 1000
COMMIT_EVERY = 1000


def latest_approved(events: list) -> dict:
    """reference -> its newest approved version."""
    latest = {}
    for event in crud.sort_oldest_first(events):
        if event.get("reference") and crud.is_approved(event):
            latest[event["reference"]] = event
    return latest


def backfill_approval(db, events: list, dry_run: bool = False) -> dict:
    latest = latest_approved(events)
    stored = {
        ref: (approved, summary_hash)
        for ref, approved, summary_hash in db.query(
            models.RawEvent.reference, models.RawEvent.approved, models.RawEvent.summary_hash
        )
    }

    counts = {"approved_versions": len(latest), "marked": 0, "already": 0, "text_changed": 0, "new": 0}
    pending = 0
    for reference, event in latest.items():
        before = stored.get(reference)
        if before is None:
            counts["new"] += 1
        else:
            was_approved, old_hash = before
            counts["already" if was_approved else "marked"] += 1
            if old_hash != event_summary_hash(event.get("event_summary")):
                counts["text_changed"] += 1
        if dry_run:
            continue
        crud.upsert_raw_event(db, event, commit=False)
        pending += 1
        if pending >= COMMIT_EVERY:
            db.commit()
            pending = 0
            log(f"[approval] {counts}")
    if not dry_run:
        db.commit()

    counts["not_approved"] = (
        db.query(models.RawEvent).filter(models.RawEvent.approved.is_(False)).count()
        if not dry_run
        else sum(1 for ref, (approved, _h) in stored.items() if not approved and ref not in latest)
    )
    log(f"[approval] done{' (dry run)' if dry_run else ''}: {counts}")
    if not dry_run:
        group_all(db)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default=config.DEFAULT_START_DATE, help="fetch approved versions from this time")
    parser.add_argument("--dry-run", action="store_true", help="count only, change nothing")
    args = parser.parse_args()

    init_db()
    log(f"[approval] fetching approved versions from {config.API_BASE_URL}{config.EVENTS_PATH} since {args.start}")
    events = fetch_events(args.start, page_size=PAGE_SIZE)
    log(f"[approval] fetched {len(events)} row(s)")
    db = SessionLocal()
    try:
        backfill_approval(db, events, dry_run=args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
