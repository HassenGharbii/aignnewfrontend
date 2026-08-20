from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
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
    data = Column(JSONB, nullable=True)
    classification_model = Column(String)
    extraction_model = Column(String)
    status = Column(String, default="done", nullable=False)  # done | failed
    error = Column(Text, nullable=True)
    is_edited = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    raw_event = relationship("RawEvent", back_populates="processed")


class PollState(Base):
    """Single-row table tracking the `start` param to use on the next poll."""

    __tablename__ = "poll_state"

    id = Column(Integer, primary_key=True)
    next_start = Column(String, nullable=False)
    last_polled_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
