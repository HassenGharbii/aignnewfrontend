"""Background loop: poll the source events API on an interval, store every raw
event seen, and run classify+extract on any reference that hasn't been processed
yet. Existing processed_events rows are never overwritten here, so a user's PATCH
edits (via the API) are never clobbered by a later poll cycle.
"""

import json
import time
from datetime import datetime, timedelta

import requests

from . import config, crud, pipeline
from .db import Base, SessionLocal, engine


def log(*args):
    print(*args, flush=True)


def fetch_events(start: str) -> list:
    if config.USE_SAMPLE_DATA:
        log(f"[data] USE_SAMPLE_DATA=true -> reading {config.SAMPLE_DATA_FILE}")
        return json.loads(config.SAMPLE_DATA_FILE.read_text(encoding="utf-8"))

    url = f"{config.API_BASE_URL}{config.EVENTS_PATH}"
    params = {config.START_PARAM: start, config.CATEGORY_PARAM: config.CATEGORY}
    log(f"[api] GET {url} params={params}")
    resp = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def poll_once(db) -> dict:
    subcategories = pipeline.load_subcategories(config.SUBCATEGORY_FILE, config.CATEGORY)
    state = crud.get_or_create_poll_state(db, config.DEFAULT_START_DATE)

    try:
        events = fetch_events(state.next_start)
    except requests.RequestException as exc:
        log(f"[api] request failed: {exc}")
        return {"fetched": 0, "processed": 0, "failed": 0, "error": str(exc)}

    processed_count = 0
    failed_count = 0
    latest_time = None

    for event in events:
        reference = event.get("reference")
        if not reference:
            continue

        crud.upsert_raw_event(db, event)

        event_time = event.get("time")
        if event_time and (latest_time is None or event_time > latest_time):
            latest_time = event_time

        if crud.get_processed(db, reference) is not None:
            continue  # already processed (or edited by a user) - never redo it

        try:
            record = pipeline.process_event(event, subcategories)
        except Exception as exc:
            log(f"[error] reference={reference}: {exc}")
            crud.save_processed_event(
                db, reference, data=None, status="failed", error=str(exc),
                classification_model=config.CLASSIFICATION_MODEL,
                extraction_model=config.EXTRACTION_MODEL,
            )
            failed_count += 1
            continue

        if record is None:
            continue

        crud.save_processed_event(
            db, reference, data=record, status="done", error=None,
            classification_model=config.CLASSIFICATION_MODEL,
            extraction_model=config.EXTRACTION_MODEL,
        )
        processed_count += 1

    if latest_time:
        next_start = (
            datetime.fromisoformat(latest_time) - timedelta(minutes=config.POLL_OVERLAP_MINUTES)
        ).isoformat()
        crud.update_poll_state(db, next_start)

    log(f"[poll] fetched={len(events)} processed={processed_count} failed={failed_count}")
    return {"fetched": len(events), "processed": processed_count, "failed": failed_count, "error": None}


def main():
    Base.metadata.create_all(bind=engine)
    log(f"[worker] starting, polling every {config.POLL_INTERVAL_SECONDS}s")
    while True:
        db = SessionLocal()
        try:
            poll_once(db)
        except Exception as exc:
            log(f"[worker] poll cycle failed: {exc}")
        finally:
            db.close()
        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
