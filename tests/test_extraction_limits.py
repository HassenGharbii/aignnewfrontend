"""The model once wrote «سيارة خفيفة» into أنواع_الأطراف_المتورطة until it hit
max_tokens, and the truncated JSON failed to parse. Lists must be bounded."""

from types import SimpleNamespace

from app.pipeline import EXTRACTION_SCHEMA, PARTY_TYPES, build_event_record
from app.worker import build_record

PARTIES = EXTRACTION_SCHEMA["properties"]["الأطراف"]["properties"]["أنواع_الأطراف_المتورطة"]


def test_party_types_list_is_bounded():
    assert PARTIES["maxItems"] == len(PARTY_TYPES)


def test_keywords_list_is_bounded():
    assert EXTRACTION_SCHEMA["properties"]["كلمات_مفتاحية"]["maxItems"] == 6


EXTRACTION = {
    "كلمات_مفتاحية": ["مخالفات", "المرور", "مخالفات"],
    "الأطراف": {"السائقون": [{"الاسم": "س"}], "أنواع_الأطراف_المتورطة": ["سيارة خفيفة", "دراجة نارية", "سيارة خفيفة"]},
}


def _check(record):
    assert record["كلمات_مفتاحية"] == ["مخالفات", "المرور"]
    assert record["الأطراف"]["أنواع_الأطراف_المتورطة"] == ["سيارة خفيفة", "دراجة نارية"]
    assert record["الأطراف"]["السائقون"] == [{"الاسم": "س"}]


def test_builders_drop_repeated_items():
    _check(build_event_record({}, {}, EXTRACTION))
    raw = SimpleNamespace(reference="r", source=None, event_time=None, subject=None, event_place=None, event_summary=None)
    _check(build_record(raw, "أحداث مرورية", {}, EXTRACTION))
