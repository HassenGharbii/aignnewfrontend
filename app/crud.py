from sqlalchemy.orm import Session

from . import models


def upsert_raw_event(db: Session, event: dict) -> models.RawEvent:
    reference = event.get("reference")
    raw = db.query(models.RawEvent).filter_by(reference=reference).first()
    if raw is None:
        raw = models.RawEvent(reference=reference)
        db.add(raw)
    raw.source = event.get("source")
    raw.target = event.get("target")
    raw.subject = event.get("subject")
    raw.address = event.get("address")
    raw.event_place = event.get("event_place")
    raw.event_summary = event.get("event_summary")
    raw.status = event.get("status")
    raw.sender_mail = event.get("senderMail")
    raw.event_time = event.get("time")
    db.commit()
    db.refresh(raw)
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


def list_done_with_raw(db: Session) -> list[tuple[models.ProcessedEvent, models.RawEvent]]:
    return (
        db.query(models.ProcessedEvent, models.RawEvent)
        .join(models.RawEvent, models.RawEvent.reference == models.ProcessedEvent.reference)
        .filter(models.ProcessedEvent.status == "done")
        .order_by(models.ProcessedEvent.created_at.desc())
        .all()
    )


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
