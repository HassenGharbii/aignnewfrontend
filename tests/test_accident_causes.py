from types import SimpleNamespace

from app import config
from app.pipeline import (
    ACCIDENT_CAUSES,
    EXTRACTION_SCHEMA,
    build_event_record,
    build_extraction_prompt,
    load_accident_causes,
    normalize_causes,
)
from app.worker import build_record


def test_list_has_the_19_official_causes():
    causes = load_accident_causes(config.ACCIDENT_CAUSES_FILE)
    assert len(causes) == 19
    assert causes[0] == "السرعة"
    assert causes[10] == "اختراق الضوء الأحمر"
    assert causes[13] == "إهمال حدث"
    assert causes[18] == "انفلاق عجلة"


def test_loader_ignores_blank_lines_and_bom(tmp_path):
    f = tmp_path / "causes.txt"
    f.write_text("﻿السرعة\n\n المداهمة \n", encoding="utf-8")
    assert load_accident_causes(f) == ["السرعة", "المداهمة"]


def test_schema_enum_is_exactly_the_list():
    assert EXTRACTION_SCHEMA["properties"]["أسباب_الحادث"] == {
        "type": "array",
        "items": {"type": "string", "enum": ACCIDENT_CAUSES},
        "minItems": 1,
        "maxItems": 5,
    }
    assert "أسباب_الحادث" in EXTRACTION_SCHEMA["required"]


def test_prompt_mentions_field_and_source():
    prompt = build_extraction_prompt("x", "y")
    assert "أسباب_الحادث" in prompt
    assert "الأسباب المحتملة" in prompt
    # User-defined meaning: a guardian's neglect of a minor caught up in the accident.
    assert "إهمال حدث" in prompt and "قاصر" in prompt


def test_normalize_dedupes_and_drops_unknown():
    assert normalize_causes(["السرعة", "شيء آخر", "السرعة", "المداهمة"]) == ["السرعة", "المداهمة"]
    assert normalize_causes(None) == []


def test_builders_store_causes():
    extraction = {"أسباب_الحادث": ["السرعة", "السرعة"]}
    assert build_event_record({}, {}, extraction)["أسباب_الحادث"] == ["السرعة"]
    raw = SimpleNamespace(
        reference="r", source=None, event_time=None, subject=None, event_place=None, event_summary=None
    )
    assert build_record(raw, "أحداث مرورية", {}, extraction)["أسباب_الحادث"] == ["السرعة"]
