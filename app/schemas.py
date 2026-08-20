from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProcessedEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference: str
    data: dict[str, Any] | None
    status: str
    error: str | None
    is_edited: bool
    classification_model: str | None
    extraction_model: str | None
    created_at: datetime
    updated_at: datetime


class ProcessedEventUpdate(BaseModel):
    data: dict[str, Any]


class RawEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference: str
    source: str | None
    target: str | None
    subject: str | None
    address: str | None
    event_place: str | None
    event_summary: str | None
    status: str | None
    sender_mail: str | None
    event_time: str | None
    fetched_at: datetime


class PollResult(BaseModel):
    fetched: int
    processed: int
    failed: int
    error: str | None = None
