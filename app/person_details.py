"""Deterministic extraction of a named person's identity details from the raw
report text.

The LLM extraction only returns a name and a free-form "الرخصة" field per
driver, and the small model often leaves it empty even when the report states
the national ID card ("ب ت و 12345678") verbatim. These details follow a fixed
police-report phrasing, so we read them with regexes from the text that follows
the person's name, up to the next person mentioned. Nothing is guessed: a field
the text doesn't state stays None.
"""

import re
from datetime import date

_TATWEEL = "ـ"

# Phrases that introduce another person — the end of the current person's segment.
_NEXT_PERSON = re.compile(r"المدعو|المدعوة|المسماة|المسمى|يرافقه|ترافقه|يرافقها|ترافقها")
_SEGMENT_MAX = 400

_CIN = re.compile(
    r"(?:ب\s*\.?\s*ت\s*\.?\s*و|بطاقة\s+(?:ال)?تعريف(?:\s+(?:ال)?وطنية)?)"
    r"\s*\.?\s*(?:عدد|رقم)?\s*:?\s*(\d{8})(?!\d)"
)
_LICENSE = re.compile(r"رخصة\s+(?:ال)?سياقة\s*(?:عدد|رقم)?\s*:?\s*(\d[\d/]*\d)")
_BIRTH = re.compile(
    r"مولود(ة)?\s+(?:في|بتاريخ)\s*:?\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{4})"
)
_OCCUPATION = re.compile(
    r"(?:مهنته|مهنتها)\s*:?\s*(.+?)"
    r"(?=\s+(?:صاحب|صاحبة|يعمل|تعمل|رتبته|رتبتها|رقم|قاطن|قاطنة|مولود|مولودة)\b|[،,.:؛]|$)"
)


def _normalize(text: str) -> str:
    # "المدعو/ فلان" → "المدعو فلان", but keep numbers like "23168/20" intact.
    text = re.sub(r"(?<!\d)/|/(?!\d)", " ", text.replace(_TATWEEL, ""))
    return re.sub(r"\s+", " ", text).strip()


def _segment_after(text: str, name: str) -> str | None:
    idx = text.find(name)
    if idx < 0:
        return None
    rest = text[idx + len(name) : idx + len(name) + _SEGMENT_MAX]
    stop = _NEXT_PERSON.search(rest)
    return rest[: stop.start()] if stop else rest


def _reference_date(event_time: str | None) -> date | None:
    if not event_time:
        return None
    try:
        return date.fromisoformat(event_time[:10])
    except ValueError:
        return None


def person_details(text: str | None, name: str, event_time: str | None = None) -> dict:
    """Return {cin, license, gender, age_range, occupation}; each None when the
    report doesn't state it for this person."""
    details = {"cin": None, "license": None, "gender": None, "age_range": None, "occupation": None}
    name = _normalize(name or "")
    if not text or not name:
        return details
    segment = _segment_after(_normalize(text), name)
    if not segment:
        return details

    if m := _CIN.search(segment):
        details["cin"] = m.group(1)
    if m := _LICENSE.search(segment):
        details["license"] = m.group(1)
    if m := _OCCUPATION.search(segment):
        occupation = m.group(1).strip()
        if occupation and len(occupation) <= 60:
            details["occupation"] = occupation
    if m := _BIRTH.search(segment):
        details["gender"] = "female" if m.group(1) else "male"
        day, month, year = int(m.group(2)), int(m.group(3)), int(m.group(4))
        ref = _reference_date(event_time)
        try:
            born = date(year, month, day)
        except ValueError:
            born = None
        if born and ref and ref >= born:
            age = ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))
            details["age_range"] = f"{age} سنة"
        else:
            details["age_range"] = f"مواليد {year}"
    return details
