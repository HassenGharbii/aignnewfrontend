from types import SimpleNamespace

from app.backfill_causes import CAUSES_SCHEMA, backfill, build_causes_prompt, needs_causes
from app.pipeline import EXTRACTION_SCHEMA


def _pair(pid, data, summary="نص الحادث"):
    return (
        SimpleNamespace(id=pid, reference=f"R{pid}", data=data, is_edited=False),
        SimpleNamespace(event_summary=summary, subject="بشأن حادث مرور"),
    )


def test_schema_asks_for_causes_only():
    assert CAUSES_SCHEMA == {
        "type": "object",
        "properties": {"أسباب_الحادث": EXTRACTION_SCHEMA["properties"]["أسباب_الحادث"]},
        "required": ["أسباب_الحادث"],
    }


def test_prompt_starts_with_the_report_and_carries_cause_rules():
    prompt = build_causes_prompt("نص التقرير", "العنوان")
    # Same prefix as the extraction prompt, so vLLM can reuse its prefix cache.
    assert prompt.startswith("نص الحدث:\nنص التقرير\n\nعنوان الحدث: العنوان\n\n")
    assert "الأسباب المحتملة" in prompt and "إهمال حدث" in prompt


def test_needs_causes_only_when_missing_and_text_present():
    assert needs_causes(_pair(1, {})) is True
    assert needs_causes(_pair(1, None)) is True
    assert needs_causes(_pair(1, {"أسباب_الحادث": ["السرعة"]})) is False
    assert needs_causes(_pair(1, {}, summary="  ")) is False


def test_backfill_merges_causes_and_keeps_other_fields():
    pairs = [_pair(1, {"الموقع": {"المنطقة": "قفصة"}}), _pair(2, {"أسباب_الحادث": ["المداهمة"]})]
    saved = {}
    result = backfill(
        pairs,
        extract=lambda summary, subject: ["السرعة", "السرعة", "خارج القائمة"],
        save=lambda processed, data: saved.__setitem__(processed.id, data),
    )
    assert saved == {1: {"الموقع": {"المنطقة": "قفصة"}, "أسباب_الحادث": ["السرعة"]}}
    assert pairs[0][0].data == {"الموقع": {"المنطقة": "قفصة"}}  # not mutated in place
    assert result == {"total": 1, "updated": 1, "failed": 0}


def test_dry_run_saves_nothing():
    saved = []
    result = backfill([_pair(1, {})], extract=lambda s, t: ["السرعة"], save=lambda p, d: saved.append(p), dry_run=True)
    assert saved == []
    assert result == {"total": 1, "updated": 0, "failed": 0}


def test_failure_is_counted_and_the_run_continues():
    def extract(summary, subject):
        if summary == "bad":
            raise RuntimeError("vllm timeout")
        return ["السرعة"]

    saved = []
    pairs = [_pair(1, {}, summary="bad"), _pair(2, {})]
    result = backfill(pairs, extract=extract, save=lambda p, d: saved.append(p.id))
    assert saved == [2]
    assert result == {"total": 2, "updated": 1, "failed": 1}


def test_empty_model_answer_counts_as_failure():
    saved = []
    result = backfill([_pair(1, {})], extract=lambda s, t: ["خارج القائمة"], save=lambda p, d: saved.append(p))
    assert saved == []
    assert result == {"total": 1, "updated": 0, "failed": 1}


def test_limit_caps_the_number_of_events():
    saved = []
    pairs = [_pair(i, {}) for i in range(5)]
    result = backfill(pairs, extract=lambda s, t: ["السرعة"], save=lambda p, d: saved.append(p.id), limit=2)
    assert saved == [0, 1]
    assert result["total"] == 2
