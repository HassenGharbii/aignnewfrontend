# Rolling out accident causes on the live server

Adds `أسباب_الحادث` to the ~4k traffic events already processed, without
re-running the rest of the extraction and without touching unclassified or
other-category events. Run every command from the repo folder on the server.

## 1. Back up the database

```bash
docker compose exec -T db pg_dump -U morour -d morour -Fc > backup_before_causes_$(date +%F_%H%M).dump
ls -lh backup_before_causes_*.dump   # must not be 0 bytes
```

## 2. Turn off the worker's start-up re-processing

`BACKFILL_ON_START=true` re-runs the model on **every** event (all categories,
unclassified ones included) each time the worker starts. In `.env`:

```
BACKFILL_ON_START=false
```

## 3. Deploy

```bash
git pull
docker compose up -d --build api worker web
```

New events from now on get causes as part of the normal extraction.

## 4. Try it on a few events (saves nothing)

```bash
docker compose exec -T api python -m app.backfill_causes --dry-run --limit 10
```

Each line shows `reference -> [causes]`. Open a few of those reports in the
dashboard and check that the causes match what «الأسباب المحتملة» says.

## 5. Run it for all traffic events

```bash
nohup docker compose exec -T api python -m app.backfill_causes > backfill_causes.log 2>&1 &
tail -f backfill_causes.log
```

It saves after each event, so it is safe to stop (`Ctrl+C` on the `tail`,
then `pkill -f backfill_causes` or `docker compose restart api`) and run step 5
again: events that already have causes are skipped. Failed events (timeouts,
etc.) are logged as `FAILED` and are picked up by the next run.

The last line is the summary: `[causes] done: total=… updated=… failed=…`.

## Rolling back

**Remove only the causes**: keeps every event that arrived after the backup:

```bash
docker compose exec -T db psql -U morour -d morour -c \
  "UPDATE processed_events SET data = (data::jsonb - 'أسباب_الحادث')::json WHERE (data::jsonb) ? 'أسباب_الحادث';"
```

**Full restore** from the backup (loses anything written after step 1):

```bash
docker compose stop api worker
docker compose exec -T db pg_restore -U morour -d morour --clean --if-exists < backup_before_causes_<date>.dump
docker compose start api worker
```

## Re-extracting reports corrected before version tracking

Reports whose figures came from an older version of their text (a correction
overwrote the raw text under the same reference) are listed and queued with:

```bash
docker compose exec -T api python -m app.recheck_old --dry-run   # list only
docker compose exec -T api python -m app.recheck_old             # queue traffic reports
docker compose exec -T api python -m app.recheck_old --all-categories
```

The worker then re-extracts them on its normal cycles. Hand-edited reports are
never touched. Running it again is harmless.
