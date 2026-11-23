# Accident Causes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tag every traffic event with one or more causes from the official 19-item list and make those causes the dashboard's cause chart, filter, table column and report breakdown.

**Architecture:** The list lives in `accident_causes.txt`. The existing single extraction call gains an enum-constrained `أسباب_الحادث` array, stored in the event's JSON. The serializer exposes it as `causes: string[]`, and the frontend swaps every `sub_category`-as-cause usage for `causes`.

**Tech Stack:** FastAPI + SQLAlchemy (Python 3.12), vLLM guided JSON (xgrammar), React + TypeScript + Recharts, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-11-23-accident-causes-design.md`

## Global Constraints

- Allowed causes are exactly these 19 strings, in this order (one per line in `accident_causes.txt`):
  `السرعة`, `عدم احترام الأولوية`, `السهو وعدم الانتباه`, `عدم ملازمة اليمين`, `السياقة في حالة سكر`, `المجاوزة الممنوعة`, `السير ليلا بدون إنارة`, `عدم احترام علامة قف`, `السير في اتجاه محجر`, `السير إلى الوراء`, `اختراق الضوء الأحمر`, `المداهمة`, `تغيير الاتجاه`, `إهمال حدث`, `عبور السكة`, `السياقة بدون رخصة`, `شق الطريق دون انتباه`, `محاولة الصعود أو النزول`, `انفلاق عجلة`.
- There is no "not stated" value in the schema. The model always picks 1–5 causes from the list.
- Missing data (events not re-processed yet, or hand-edited) is `causes: []` in the API, displayed as `غير محدد`. The model must never be able to output it.
- The JSON key is `أسباب_الحادث` (top-level in the extraction output and in the stored record). The API field is `causes`.
- `sub_category` stays in the data and the API. It's only removed from the cause chart, filter, table column and reports. It stays visible in the event detail modal as `نوع الحادث: …`.
- `اسباب الحوادث.pdf` must never be committed (`*.pdf` is in `.gitignore`).
- Tests that need no DB run with `--noconftest` (the conftest exits without `TEST_DATABASE_URL`). Python with the backend deps: `$VENV/Scripts/python` where `VENV` is the session's scratchpad venv (`py -3.14 -m venv` + `pip install -r requirements.txt pytest`).

## Review Focus

1. **The model returns the same cause twice.** `uniqueItems` is left out of the schema because xgrammar support for it is uncertain. `normalize_causes` must dedupe while keeping order. Test in Task 1.
2. **Stored data with a value outside the list** (a hand edit or an older schema). It must be dropped, not shown as a new chart slice. `normalize_causes` filters it in the builders; the serializer filters out non-strings. Tests in Tasks 1 and 2.
3. **Old events without the key**, which is every event until the worker restarts. They must render as `غير محدد` in the donut and an empty table cell, and not crash the filter. Test in Task 2, checked in the Task 4 preview.
4. **An event with two causes.** In the donut, filter and report it counts once under each cause; percentages are of events, so they can add up to more than 100%. Checked in the Task 4 preview.
5. **The causes file has a trailing newline, blank lines or a BOM.** The loader must return exactly 19 clean strings. Test in Task 1.

---

### Task 1: Causes list, extraction schema, prompt, record builders

**Files:**
- Create: `accident_causes.txt`
- Modify: `app/config.py` (next to `SUBCATEGORY_FILE`), `app/pipeline.py` (`EXTRACTION_SCHEMA`, `EXTRACTION_INSTRUCTIONS`, `build_event_record`), `app/worker.py` (`build_record`), `Dockerfile` (the `COPY subcategory.txt …` line), `.gitignore` (already edited, commit it)
- Test: `tests/test_accident_causes.py`

**Interfaces:**
- Produces: `config.ACCIDENT_CAUSES_FILE: Path` (env `ACCIDENT_CAUSES_FILE`, default `accident_causes.txt`); `pipeline.load_accident_causes(path) -> list[str]`; `pipeline.ACCIDENT_CAUSES: list[str]`; `pipeline.normalize_causes(values) -> list[str]`; stored record key `"أسباب_الحادث": list[str]`.

- [ ] **Step 1: Write the failing tests** in `tests/test_accident_causes.py`:
  - `test_list_has_the_19_official_causes`: `load_accident_causes(config.ACCIDENT_CAUSES_FILE)` has `len == 19`, `[0] == "السرعة"`, `[10] == "اختراق الضوء الأحمر"`, `[13] == "إهمال حدث"`, `[18] == "انفلاق عجلة"`.
  - `test_loader_ignores_blank_lines_and_bom(tmp_path)`: the file `"﻿السرعة\n\n المداهمة \n"` gives `["السرعة", "المداهمة"]`.
  - `test_schema_enum_is_exactly_the_list`: `EXTRACTION_SCHEMA["properties"]["أسباب_الحادث"] == {"type": "array", "items": {"type": "string", "enum": ACCIDENT_CAUSES}, "minItems": 1, "maxItems": 5}`, and `"أسباب_الحادث" in EXTRACTION_SCHEMA["required"]`.
  - `test_prompt_mentions_field_and_source`: `build_extraction_prompt("x", "y")` contains `"أسباب_الحادث"` and `"الأسباب المحتملة"`.
  - `test_normalize_dedupes_and_drops_unknown`: `normalize_causes(["السرعة", "شيء آخر", "السرعة", "المداهمة"]) == ["السرعة", "المداهمة"]`; `normalize_causes(None) == []`.
  - `test_builders_store_causes`: `build_event_record({...}, {}, {"أسباب_الحادث": ["السرعة", "السرعة"]})["أسباب_الحادث"] == ["السرعة"]`, and the same for `worker.build_record(SimpleNamespace(reference="r", source=None, event_time=None, subject=None, event_place=None, event_summary=None), "أحداث مرورية", {}, {...})`.

- [ ] **Step 2: Run, expect failures** (ImportError on `load_accident_causes`)
  Run: `$VENV/Scripts/python -m pytest --noconftest -q tests/test_accident_causes.py`

- [ ] **Step 3: Implement**
  - Write `accident_causes.txt` with the 19 strings from Global Constraints, in order.
  - Add `ACCIDENT_CAUSES_FILE` to `config.py`, following the pattern of `SUBCATEGORY_FILE`.
  - In `pipeline.py`: add `load_accident_causes` (read with `utf-8-sig`, strip each line, skip empty ones) and `ACCIDENT_CAUSES = load_accident_causes(config.ACCIDENT_CAUSES_FILE)`. Add the schema property exactly as in the test and append it to the top-level `required`. Add `normalize_causes` (keep the first occurrence, drop anything not in `ACCIDENT_CAUSES`, treat non-list as `[]`).
  - Append a `- أسباب_الحادث:` paragraph to `EXTRACTION_INSTRUCTIONS` before the final "أعد النتيجة…" line. It must say: choose only from the schema's list; take the causes from what the report states, usually in the «الأسباب المحتملة» section; map paraphrases to the closest entry (example «الإفراط في السرعة» → «السرعة», «عدم ترك أولوية المرور» → «عدم احترام الأولوية»); list every stated cause without repeating one; if the report states no cause, choose the single closest cause from how the accident is described.
  - Both `build_event_record` and `worker.build_record` add `"أسباب_الحادث": normalize_causes(extraction.get("أسباب_الحادث"))` (worker imports it from `.pipeline`).
  - Add `accident_causes.txt` to the Dockerfile `COPY subcategory.txt …` line.

- [ ] **Step 4: Run, expect PASS** (same command, 6 passed). Also re-run `tests/test_person_details.py` (5 passed).

- [ ] **Step 5: Commit** `accident_causes.txt app/config.py app/pipeline.py app/worker.py Dockerfile .gitignore tests/test_accident_causes.py docs/superpowers/specs/2026-11-23-accident-causes-design.md docs/superpowers/plans/2026-11-23-accident-causes.md`. Message: "Extract accident causes from the official 19-item list". Do not `git add docs/` wholesale: the rest of `docs/` is the user's untracked material.

### Task 2: Expose `causes` from the API

**Files:**
- Modify: `app/serialize.py` (`to_dashboard_event` return dict)
- Test: `tests/test_accident_causes.py` (append)

**Interfaces:**
- Consumes: stored `data["أسباب_الحادث"]` from Task 1.
- Produces: each dashboard row / `/api/events` item has `causes: list[str]`.

- [ ] **Step 1: Write the failing tests**
  - `test_row_exposes_causes`: `to_dashboard_event(processed, raw)` with `processed.data = {"أسباب_الحادث": ["السرعة", 3, "المداهمة"]}` gives `row["causes"] == ["السرعة", "المداهمة"]`.
  - `test_row_without_causes_is_empty_list`: `data = {}` gives `row["causes"] == []`; `data = None` also gives `[]`.
  Build `processed` and `raw` as `SimpleNamespace` with the attributes `to_dashboard_event` reads (`id, data, status, created_at=None, updated_at=None`; `event_summary, event_time, source, target, subject, event_place`).
- [ ] **Step 2: Run, expect FAIL** (`KeyError: 'causes'`).
- [ ] **Step 3: Implement**: add `"causes"` to the returned dict, keeping only `str` items from `data.get("أسباب_الحادث") or []`. Do not filter against the list here: Task 1 already normalizes at write time, and the serializer must not depend on the causes file.
- [ ] **Step 4: Run, expect PASS** (8 passed in the file).
- [ ] **Step 5: Commit**: "Expose accident causes on dashboard events".

### Task 3: Frontend uses causes instead of the type

**Files:**
- Modify: `src/api/types.ts` (`RawEvent`), `src/context/FiltersContext.tsx`, `src/components/FilterBar.tsx:83-89,144-147`, `src/components/charts/CauseDonut.tsx`, `src/components/table/EventsTable.tsx:48-51,77-82`, `src/components/table/EventDetailModal.tsx:46-50`, `src/lib/reportData.ts:152`, `src/lib/generateReportExcel.ts:24,50`

**Interfaces:**
- Consumes: `RawEvent.causes: string[]` from Task 2.
- Produces: `FiltersState.causes: Set<string>` and `toggleCause(v: string)` replace `subCategories` / `toggleSubCategory` everywhere (rename; no other consumers exist; check with `grep -rn "subCategories\|toggleSubCategory" src`, which must return nothing afterwards). Display constant `UNKNOWN_CAUSE = 'غير محدد'`, exported from `src/lib/causes.ts` (new, one line) so the donut and the table use the same text.

- [ ] **Step 1: Types and filtering**
  - `RawEvent.causes: string[]`.
  - `FiltersContext`: rename the filter state and toggle. An event passes when `filters.causes.size === 0` or some `e.causes` entry is in `filters.causes` (exact `has`, since values come from a fixed list). Add `...e.causes` to `searchHaystack`.
- [ ] **Step 2: FilterBar**: options are `countGrouped(allEvents.flatMap((e) => e.causes)).map(([name]) => name)`, label `سبب الحادث`, rendered when `causes.length > 0`.
- [ ] **Step 3: CauseDonut**
  - Title `أسباب الحوادث`; subtitle `قد يكون للحادث أكثر من سبب · اضغط عنصرًا للتصفية`.
  - Count each distinct cause once per event. An event with `causes.length === 0` counts once as `UNKNOWN_CAUSE`. `pct` = count / number of filtered events.
  - The `UNKNOWN_CAUSE` and `أخرى` rows are not clickable. Other rows call `toggleCause`.
- [ ] **Step 4: Table, CSV, detail modal**
  - Column and CSV header `الأسباب`, value `e.causes.join('، ')`. The table cell is truncated to 30 and shows `—` when empty.
  - The detail modal shows each cause as a pill. The existing `sub_category` pill text becomes `نوع الحادث: {sub_category}`.
- [ ] **Step 5: Reports**
  - `reportData.byCause` counts distinct causes per event, the same way `byPartyType` does (lines 118-128), and skips events with none.
  - Excel column header `الأسباب`, key `causes`, value joined with `'، '`.
- [ ] **Step 6: Verify the build**: rebuild the web image of the isolated preview stack (Task 4 setup): `docker compose -f <scratchpad>/sample/docker-compose.yml build web`. Expected: `npm run build` succeeds (this is the TypeScript check; Node isn't installed on the host).
- [ ] **Step 7: Commit**: "Show official accident causes in the cause chart, filter, table and reports".

### Task 4: Preview with sample data and a real-model check

**Files:**
- Modify: `<scratchpad>/sample/seed.py` (scratchpad only, not committed)

- [ ] **Step 1: Seed three cases**: the two Gafsa events with `"أسباب_الحادث": ["السرعة", "عدم احترام الأولوية"]`, plus one more traffic event with no `أسباب_الحادث` key (the old-data case). Rebuild and start: `docker compose up -d --build` in `<scratchpad>/sample`, then run the seed in the api container.
- [ ] **Step 2: API check**: `curl -s localhost:9921/api/events?limit=10` shows `causes` with both values on the Gafsa events and `[]` on the third.
- [ ] **Step 3: UI check** (http://localhost:5183, by the user if no browser tool is available):
  - The donut shows `السرعة` 67%, `عدم احترام الأولوية` 67% and `غير محدد` 33%.
  - Clicking `السرعة` filters to 2 events.
  - The «سبب الحادث» filter lists the 2 causes.
  - The table column shows `السرعة، عدم احترام الأولوية`.
  - The detail modal shows both pills plus `نوع الحادث: حادث مرور`.
  - The Excel export has the «الأسباب» column.
- [ ] **Step 4: Real model check**, on the machine with vLLM (GPU), after deploying:
  - Run `python -m app.debug_extract <reference of a report with «الأسباب المحتملة»> <reference of one without>`.
  - Expected: `أسباب_الحادث` holds list values only, matches the stated causes for the first report, and has exactly one plausible cause for the second.
  - Report the outputs to the user before restarting the worker for the backfill.
