"""Group the reports that describe the same accident into one event.

The source sends one accident as several reports, each under its own reference:
re-sent by another unit with the same text, or followed up by a report citing
the earlier one's number («تبعا للإعلام عدد NNNNNN», NNNNNN = the third part of
its reference). Each processed report gets:

- group_ref: the reference of the earliest report of its event;
- is_main: True for the one report that stands for the event in the dashboard
  (a hand-edited one if any, else the latest by event_time).

Nothing is deleted; the other reports are the event's versions. Grouping is
recomputed from scratch each time, so running it again changes nothing.

Run with:
    python -m app.group_reports --dry-run   # counts only
    python -m app.group_reports             # save
"""

import re
from datetime import datetime, timedelta

from sqlalchemy import func

from . import models
from .crud import CATEGORY_EXPR
from .pipeline import log

# A citation word (إعلام / إشعار, any prefix or suffix), then «عدد» within a short
# stretch without digits, then exactly six digits.
_CITATION_RE = re.compile(r"[اإأ](?:علام|شعار)\S*[^0-9]{0,40}?عدد\s*(\d{6})(?!\d)")
NOT_NUMBERED = "000000"
OPENING_CHARS = 200
NEAR_WINDOW = timedelta(hours=24)


def cited_numbers(text: str | None) -> list[str]:
    if not text:
        return []
    out = []
    for number in _CITATION_RE.findall(text):
        if number != NOT_NUMBERED and number not in out:
            out.append(number)
    return out


def central_number(reference: str) -> str | None:
    parts = reference.split("-")
    if len(parts) != 3 or parts[2] == NOT_NUMBERED:
        return None
    return parts[2]


class _Groups:
    def __init__(self, refs):
        self.parent = {r: r for r in refs}

    def find(self, ref):
        while self.parent[ref] != ref:
            self.parent[ref] = self.parent[self.parent[ref]]
            ref = self.parent[ref]
        return ref

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _parse_time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _link_near_copies(db, groups: _Groups, by_ref: dict) -> None:
    """A district's draft re-sent hours later by its governorate with small
    corrections: same first OPENING_CHARS characters, within NEAR_WINDOW.
    Live check (2026-11-23): such pairs arrive minutes to ~8 hours apart, while
    different accidents sharing a standard opening were days apart."""
    P, R = models.ProcessedEvent, models.RawEvent
    opening = func.md5(func.left(R.event_summary, OPENING_CHARS))
    rows = (
        db.query(P.reference, opening.label("opening"))
        .join(R, R.reference == P.reference)
        .filter(P.status == "done", R.approved.is_(True), func.length(R.event_summary) >= OPENING_CHARS)
        .all()
    )
    buckets = {}
    for reference, key in rows:
        row = by_ref[reference]
        when = _parse_time(row.event_time)
        if when is not None:
            buckets.setdefault((row.category, key), []).append((when, reference))
    for items in buckets.values():
        items.sort()
        for (t1, ref1), (t2, ref2) in zip(items, items[1:]):
            if t2 - t1 <= NEAR_WINDOW:
                groups.union(ref1, ref2)


def _order(row):
    return (row.event_time or "", row.id)


def group_all(db, dry_run: bool = False) -> dict:
    P, R = models.ProcessedEvent, models.RawEvent
    # Approved reports only: an operator copy must never become an event's main report.
    done = (P.status == "done") & R.approved.is_(True)
    rows = (
        db.query(
            P.id, P.reference, P.is_edited, P.group_ref, P.is_main,
            R.summary_hash, R.event_time, CATEGORY_EXPR.label("category"),
        )
        .join(R, R.reference == P.reference)
        .filter(done)
        .all()
    )
    by_ref = {row.reference: row for row in rows}
    groups = _Groups(by_ref)

    # (a) identical text, same category
    first_with_text = {}
    for row in rows:
        key = (row.category, row.summary_hash)
        if row.summary_hash is None:
            continue
        if key in first_with_text:
            groups.union(first_with_text[key], row.reference)
        else:
            first_with_text[key] = row.reference

    # (b) citation of exactly one stored report of the same category
    by_number = {}
    for row in rows:
        number = central_number(row.reference)
        if number:
            by_number.setdefault(number, []).append(row.reference)
    citing = (
        db.query(P.reference, R.event_summary)
        .join(R, R.reference == P.reference)
        .filter(done, R.event_summary.op("~")("[اإأ](علام|شعار)"))
        .all()
    )
    for reference, text in citing:
        for number in cited_numbers(text):
            matches = by_number.get(number, [])
            if len(matches) != 1 or matches[0] == reference:
                continue
            if by_ref[matches[0]].category == by_ref[reference].category:
                groups.union(matches[0], reference)

    # (c) same opening, same category, sent within NEAR_WINDOW of the previous one
    _link_near_copies(db, groups, by_ref)

    members = {}
    for row in rows:
        members.setdefault(groups.find(row.reference), []).append(row)

    changes = []
    for group in members.values():
        group_ref = min(group, key=_order).reference
        edited = [r for r in group if r.is_edited]
        main = max(edited or group, key=_order)
        for row in group:
            is_main = row.reference == main.reference
            if row.group_ref != group_ref or row.is_main != is_main:
                changes.append({"id": row.id, "group_ref": group_ref, "is_main": is_main})

    result = {"reports": len(rows), "events": len(members), "merged": len(rows) - len(members)}
    if not dry_run and changes:
        db.bulk_update_mappings(P, changes)
        db.commit()
    log(f"[group] reports={result['reports']} events={result['events']} merged={result['merged']} "
        f"updated={0 if dry_run else len(changes)}{' (dry run)' if dry_run else ''}")
    return result
