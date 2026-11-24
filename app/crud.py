from sqlalchemy import func
from sqlalchemy.orm import Session

from .serialize import event_summary_hash
from . import config, models

# Must match the expression index created in db.init_db (same function, same argument
# order) or Postgres cannot use the index.
CATEGORY_EXPR = func.json_extract_path_text(models.ProcessedEvent.data, "التصنيف", "الصنف_الرئيسي")


def is_approved(event: dict) -> bool:
    return event.get("actor") == config.APPROVED_ACTOR


def sort_oldest_first(events: list) -> list:
    """The source lists newest first. Storing in that order would leave the OLDEST
    version of a reference in raw_events; oldest first makes the newest win."""
    return sorted(events, key=lambda e: e.get("time") or "")


def upsert_raw_event(db: Session, event: dict, commit: bool = True) -> models.RawEvent:
    reference = event.get("reference")
    raw = db.query(models.RawEvent).filter_by(reference=reference).first()
    if raw is None:
        raw = models.RawEvent(reference=reference)
        db.add(raw)
    elif raw.approved and not is_approved(event):
        # An operator copy never replaces the approved version.
        return raw
    raw.actor = event.get("actor")
    raw.approved = is_approved(event)
    raw.source = event.get("source")
    raw.target = event.get("target")
    raw.subject = event.get("subject")
    raw.address = event.get("address")
    raw.event_place = event.get("event_place")
    raw.event_summary = event.get("event_summary")
    raw.summary_hash = event_summary_hash(raw.event_summary)
    raw.status = event.get("status")
    raw.sender_mail = event.get("senderMail")
    raw.event_time = event.get("time")
    if commit:
        db.commit()
        db.refresh(raw)
    else:
        db.flush()
    return raw


def get_processed(db: Session, reference: str) -> models.ProcessedEvent | None:
    return db.query(models.ProcessedEvent).filter_by(reference=reference).first()


def save_processed_event(
    db: Session,
    reference: str,
    data: dict | None,
    status: str,
    error: str | None,
    classification_model: str,
    extraction_model: str,
) -> models.ProcessedEvent:
    processed = get_processed(db, reference)
    if processed is None:
        processed = models.ProcessedEvent(reference=reference)
        db.add(processed)
    processed.data = data
    processed.status = status
    processed.error = error
    processed.classification_model = classification_model
    processed.extraction_model = extraction_model
    db.commit()
    db.refresh(processed)
    return processed


def list_done_with_raw(
    db: Session, category: str | None = None, main_only: bool = True
) -> list[tuple[models.ProcessedEvent, models.RawEvent]]:
    """main_only: one row per event (see app/grouping.py), as the dashboard counts them."""
    query = (
        db.query(models.ProcessedEvent, models.RawEvent)
        .join(models.RawEvent, models.RawEvent.reference == models.ProcessedEvent.reference)
        .filter(models.ProcessedEvent.status == "done", models.RawEvent.approved.is_(True))
    )
    if main_only:
        query = query.filter(models.ProcessedEvent.is_main.is_(True))
    if category:
        query = query.filter(CATEGORY_EXPR == category)
    # id tie-breaker: clients page across separate requests, and equal created_at
    # values must not reorder between pages.
    return query.order_by(models.ProcessedEvent.created_at.desc(), models.ProcessedEvent.id.desc()).all()


def get_or_create_poll_state(db: Session, default_start: str) -> models.PollState:
    state = db.query(models.PollState).filter_by(id=1).first()
    if state is None:
        state = models.PollState(id=1, next_start=default_start)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def update_poll_state(db: Session, next_start: str) -> None:
    state = db.query(models.PollState).filter_by(id=1).first()
    state.next_start = next_start
    db.commit()


def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge overlay into base, returning a new dict. Used so a PATCH
    can update e.g. just تفاصيل_الحادث.عدد_الوفيات without resending the whole record."""
    result = dict(base or {})
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
