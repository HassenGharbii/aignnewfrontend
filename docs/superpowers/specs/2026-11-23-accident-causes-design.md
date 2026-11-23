# Accident causes from the official list — design

Date: 2026-11-23 · Status: approved

## Why

The dashboard's "cause" (chart «أسباب/أنواع الحوادث», filter «سبب/نوع الحادث»,
table column, Word/Excel reports) is really the accident *type* — the
sub-category from `subcategory.txt`. The causes the police state in each report
(«الأسباب المحتملة») are never extracted. The user has the official list of 19
causes (`اسباب الحوادث.pdf`, kept out of git) and wants every accident tagged
with causes from that list only.

## Goals

- Each traffic event gets `أسباب_الحادث`: one or more causes, always from the
  19. There is no "not stated" option (user decision: an escape value would let
  the model drift away from the list).
- The real causes **replace** the type in the cause chart, the cause filter,
  the table column and the reports' "by cause" section (user picked option B).
- Existing events get causes without manual work.

## Non-goals

- Editing causes by hand in the edit form (later).
- Showing the official codes (01–19) in the UI — names only; the file keeps
  the official order.
- Changing the type classification itself; `sub_category` stays in the data.

## Anti-goals

- A value outside the list — impossible by construction (enum).
- Accepted trade-off: when a report states no cause, the model must still pick
  the closest one from the accident description, so those picks are inferred,
  not quoted.

## Approaches considered

1. **Add the field to the existing extraction call** — enum-constrained, no
   extra model call; the worker's existing startup backfill fills old events.
   Gap: hand-edited events (`is_edited`) are skipped. **Chosen.**
2. Separate cause-only model call with its own backfill — covers edited events,
   but one more model call per event on an already slow worker.
3. Keyword matching on «الأسباب المحتملة», no model — instant, but reports
   paraphrase ("عدم ترك أولوية المرور" vs "عدم احترام الأولوية") and misses
   would be silent.

## Design

**List** — `accident_causes.txt` at the repo root, one cause per line in the
official order (01→19), spelled as in the PDF with correct hamzas (e.g.
«عدم احترام الأولوية»). User-confirmed corrections of PDF typos: 11 is «اختراق الضوء
الأحمر» (running a red light; the PDF's «احتراق» means "burning") and 14 is
«إهمال حدث». The prompt explains «إهمال حدث» as the user defined it: a guardian
neglecting a minor (usually a child) who then got involved in the accident. Copied into the image by the `Dockerfile` like
`subcategory.txt`. *(my call)*

**Extraction** (`app/pipeline.py`) — `EXTRACTION_SCHEMA` gains a required
`أسباب_الحادث`: array of strings, enum = the 19 only, unique items,
1–5 items. Guided decoding makes off-list values impossible. Prompt rule: take
causes only from what the report states (usually «الأسباب المحتملة»), map
paraphrases to the closest list entry (e.g. «الإفراط في السرعة» → «السرعة»),
list every stated cause; when none is stated, pick the single closest cause
from how the accident is described.

**Storage** — `worker.build_record` and `pipeline.build_event_record` copy it
to `data["أسباب_الحادث"]`. No DB migration (it lives in the JSON column).

**API** (`app/serialize.py`) — dashboard rows get `causes: string[]`; events
without the field (not yet re-processed, or hand-edited) get `[]`, shown as
«غير محدد» in the UI only — this is missing data, not a model answer.
*(my call)*

**Frontend**
- `CauseDonut` counts `causes`; an event with two causes counts once under each.
  Title «أسباب الحوادث», subtitle notes that one accident can have several causes.
- `FilterBar` / `FiltersContext`: the «سبب/نوع الحادث» group becomes «سبب الحادث»,
  options from `causes`, an event matches if any of its causes is selected.
- `EventsTable` column and CSV/Excel column «السبب/النوع» → «الأسباب»
  (comma-joined).
- `reportData.byCause` counts `causes` (Word «توزيع الحوادث حسب الأسباب» and
  Excel «حسب السبب» follow automatically).
- `EventDetailModal` shows the causes; it keeps showing the type, labelled
  «نوع الحادث», since that's the only place type remains visible. *(my call)*

**Rollout** — deploy, then restart the worker with `BACKFILL_ON_START=true`
(the default): every non-edited event is re-extracted and gains causes. This
re-runs the whole backlog through vLLM, as every worker restart already does.

## Testing

- Unit: the schema enum equals `accident_causes.txt` exactly (19 entries);
  serialization defaults missing causes to `[]`.
- Prompt check against the real model on a few reports (the Gafsa report should
  give «السرعة» + «عدم احترام الأولوية»; a report with no causes section should
  still give one plausible cause from the list) — needs vLLM, run where it's available.
- Local preview with sample data, as done for the people-search fix.

## Left to the builder

Exact prompt wording, chart/filter styling, and how many items the filter
shows before collapsing.
