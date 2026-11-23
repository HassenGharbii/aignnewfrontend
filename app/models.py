from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from .db import Base


class RawEvent(Base):
    """The event exactly as returned by the source API, one row per reference."""

    __tablename__ = "raw_events"

    id = Column(Integer, primary_key=True)
    reference = Column(String, unique=True, nullable=False, index=True)
    source = Column(String)
    target = Column(String)
    subject = Column(String)
    address = Column(String, nullable=True)
    event_place = Column(String)
    event_summary = Column(Text)
    # sha256 of event_summary as last received; a different value on re-fetch = corrected report.
    summary_hash = Column(String(64), nullable=True)
    status = Column(String)
    sender_mail = Column(String, nullable=True)
    event_time = Column(String)  # kept as the raw ISO string from the source API
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    processed = relationship("ProcessedEvent", back_populates="raw_event", uselist=False)


class ProcessedEvent(Base):
    """The classify+extract result for a reference. Never overwritten by the worker
    once it exists, so a user's PATCH edits survive future poll cycles."""

    __tablename__ = "processed_events"

    id = Column(Integer, primary_key=True)
    reference = Column(String, ForeignKey("raw_events.reference"), unique=True, nullable=False, index=True)
    data = Column(JSON, nullable=True)
    classification_model = Column(String)
    extraction_model = Column(String)
    status = Column(String, default="done", nullable=False)  # done | failed | skipped
    error = Column(Text, nullable=True)
    attempts = Column(Integer, default=0, server_default="0", nullable=False)  # consecutive failures
    is_edited = Column(Boolean, default=False, nullable=False)
    # sha256 of the raw text `data` was extracted from; differs from raw_events.summary_hash
    # when the source sent a corrected version that has not been re-extracted yet.
    source_hash = Column(String(64), nullable=True)
    # Reports of the same accident share group_ref (the earliest one's reference);
    # only the is_main one is counted by the dashboard. See app/grouping.py.
    group_ref = Column(String, nullable=True, index=True)
    is_main = Column(Boolean, default=True, server_default="true", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    raw_event = relationship("RawEvent", back_populates="processed")


class PollState(Base):
    """Single-row table tracking the `start` param to use on the next poll."""

    __tablename__ = "poll_state"

    id = Column(Integer, primary_key=True)
    next_start = Column(String, nullable=False)
    last_polled_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
