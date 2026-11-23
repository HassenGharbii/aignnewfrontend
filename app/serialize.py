"""Flattens a (ProcessedEvent, RawEvent) pair into the shape the dashboard
frontend's `RawEvent` TS interface expects (see src/api/types.ts).

severity/priority/event_status have no real source-of-truth field — الحالة/
التدقيق were deliberately dropped from the extraction pipeline earlier because
the model kept hallucinating them. These are computed deterministically here
from the two numeric fields that HAVE been reliable in every test
(عدد_الوفيات/عدد_الإصابات), rather than fabricated. event_status in particular
only reflects our own pipeline state (processed vs failed), not any real
legal/administrative case status, since the source feed doesn't expose one.
"""

import hashlib
import re

from . import governorates
from .person_details import person_details

PRIORITY_BY_SEVERITY = {"حرج": 1, "مرتفع": 2, "متوسط": 3, "منخفض": 4}


def compute_severity(facts: dict) -> str:
    deaths = facts.get("عدد_الوفيات") or 0
    injuries = facts.get("عدد_الإصابات") or 0
    hazardous = bool(facts.get("مواد_خطرة_متسربة"))
    if deaths > 0:
        return "حرج"
    if injuries >= 3 or hazardous:
        return "مرتفع"
    if injuries >= 1:
        return "متوسط"
    return "منخفض"


def compute_priority(severity: str) -> int:
    return PRIORITY_BY_SEVERITY.get(severity, 4)


def compute_event_status(processing_status: str) -> str:
    return "مغلق" if processing_status == "done" else "قيد المعالجة"


def event_summary_hash(event_summary: str | None) -> str:
    return hashlib.sha256((event_summary or "").encode("utf-8")).hexdigest()


def to_dashboard_event(processed, raw) -> dict:
    data = processed.data or {}
    location = data.get("الموقع") or {}
    facts = data.get("تفاصيل_الحادث") or {}
    classification = data.get("التصنيف") or {}

    region = governorates.match_governorate(
        location.get("المعتمدية"),
        location.get("العمادة"),
        location.get("المنطقة"),
        raw.event_place,
        raw.source,
        raw.target,
    ) or (location.get("المنطقة") or raw.event_place or "غير محدد")

    severity = compute_severity(facts)
    created_at = processed.created_at.isoformat() if processed.created_at else None
    updated_at = processed.updated_at.isoformat() if processed.updated_at else None

    return {
        "id": processed.id,
        "event_summary": raw.event_summary,
        "event_summary_hash": event_summary_hash(raw.event_summary),
        "event_time": raw.event_time,
        "source": raw.source,
        "target": raw.target,
        "category": classification.get("الصنف_الرئيسي"),
        "sub_category": classification.get("الصنف_الفرعي"),
        "event_title": data.get("عنوان") or raw.subject,
        "event_status": compute_event_status(processed.status),
        "severity": severity,
        "priority": compute_priority(severity),
        "region": region,
        "details": data,
        "created_at": created_at,
        "updated_at": updated_at,
        "classification_scores": {"نسبة_الثقة": classification.get("نسبة_الثقة")},
        "sub_category_score": classification.get("نسبة_الثقة"),
    }


def extract_people(processed, row: dict) -> list[dict]:
    """Real fields only: name + license from the LLM, plus CIN, license,
    gender, age and occupation read verbatim from the report text (see
    person_details). Nothing is inferred: risk_level/criminal_record and any
    detail the report doesn't state stay empty — fabricating them for real,
    named individuals in real incident reports would be irresponsible."""
    data = processed.data or {}
    drivers = ((data.get("الأطراف") or {}).get("السائقون")) or []
    people = []
    for d in drivers:
        name = (d.get("الاسم") or "").strip()
        llm_id = (d.get("الرخصة") or "").strip()
        if not name and not llm_id:
            continue
        # The LLM's single "الرخصة" field holds either a license or a CIN
        # (8 digits); prefer what the report text states explicitly.
        details = person_details(row["event_summary"], name, row["event_time"])
        llm_is_cin = bool(re.fullmatch(r"\d{8}", llm_id))
        people.append({
            "name": name,
            "cin": details["cin"] or (llm_id if llm_is_cin else ""),
            "license": details["license"] or (llm_id if llm_id and not llm_is_cin else None),
            "gender": details["gender"],
            "age_range": details["age_range"],
            "occupation": details["occupation"],
            "record": {
                "record_id": processed.id,
                "created_at": row["created_at"],
                "event_category": row["category"],
                "event_sub_category": row["sub_category"],
                "event_region": row["region"],
                "event_severity": row["severity"],
                "event_title": row["event_title"],
                "event_summary": row["event_summary"],
                "event_datetime": row["event_time"],
                "event_location": (data.get("الموقع") or {}).get("العنوان"),
                "source_text": row["event_summary"],
                "person_status": None,
                "legal_state": None,
                "risk_level": None,
                "role_detail": "سائق",
                "injury_type": None,
            },
        })
    return people
