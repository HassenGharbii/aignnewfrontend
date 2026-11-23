# One event per accident: grouping report versions

Approved by the user on 2026-11-23.

## Why

The same accident reaches us as several reports, each under its own reference,
so the dashboard counts it 2-4 times. Live counts (traffic, done): 778 reports
are exact copies of each other (367 events, 411 extra copies); 87 reports cite
an earlier report's number. The user wants each accident treated as one event:
counted once, showing its final state, with earlier versions kept as history.

## Rules

Two processed reports of the same category belong to the same event when:

- **(a) identical text**: same `raw_events.summary_hash` (a report re-sent by
  another unit, e.g. district then region).
- **(b) citation**: one cites the other's number, «تبعا للإعلام عدد NNNNNN»,
  where NNNNNN is the third part of the earlier reference. Linked only when the
  number matches exactly one stored reference; chains are followed.
- **(c) nearly identical text**: off until the user has checked samples.

## Final state

- Every group has one **main** row (`processed_events.is_main`); all dashboard
  statistics, lists and the people search use main rows only.
- Main = a hand-edited member if any, else the member with the latest
  `event_time` (ties: highest id).
- Phase 1: the main row's own extraction is the event's figures.
- Phase 2 (later): for groups linked by citation, the model re-reads the
  original plus all follow-ups together and that combined result is shown.

## Storage

`processed_events.group_ref` (reference of the group's earliest member) and
`processed_events.is_main` (default true). Nothing is deleted. A single report
is its own group.

## Running

- `python -m app.group_reports [--dry-run]` groups every existing report once.
- The worker links each report right after it is classified.

## History in the app

`/api/events` rows get `versions`: the other members (reference, time, source,
deaths, injuries). The event detail shows them as a list.
