# Task 2C-1 — Watchlist APIs

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2C, Task 1 of 4).
Builds on the frozen v1 foundation, frozen Workstream 2B, and the
[Business Output Audit](2026-08-06-2c-business-apis-audit.md).

## Naming: `strategy` as a query param, not a path segment

The audit's mapping table used `/api/v1/watchlists/{strategy}/{date}`; this task's brief
suggests the flatter `/api/v1/watchlists/current`, `/history`, `/{date}`, `/diff`. Reconciled
as: **`strategy` is a query parameter** (`?strategy=eod`, default `eod`), not a path segment.
`watchlist_snapshot` has exactly two live values for `strategy` (`eod`, `premarket` — CLAUDE.md
§Scheduler), so it's a filter dimension on one resource ("the watchlist"), not two separate
resource hierarchies — matching how `/api/v1/status/jobs/failed?since=` and
`/api/v1/status/jobs/history?limit=` already use query params for narrowing, not path segments,
elsewhere in this same API.

## Service reuse — extending, not duplicating

`engine/trade_plan.py` already owns `watchlist_snapshot` (`record_snapshot`, `diff_watchlist`,
`ensure_watchlist_snapshot_table`) but has no *read/list* functions — only write (snapshot) and
diff. Two small read functions are added to that same file (not a new module — this table
already has one canonical owner):

- `get_snapshot(conn, date_str, strategy) -> list[dict]` — the persisted rows for one
  `(date, strategy)`, `sources` JSON-decoded. A straight `SELECT`, no new business rule.
- `list_snapshot_dates(conn, strategy) -> list[str]` — `SELECT DISTINCT date ... ORDER BY date
  DESC`. Enumeration only, same table.

`engine/persistent_watchlist.py` similarly gets one read function, `list_watchlist(conn,
status=None)`, alongside its existing `update_watchlist`/`build_message`.

**No changes to `record_snapshot`, `diff_watchlist`, `update_watchlist`, or any writer.**

## `diff` — matches `diff_watchlist`'s existing semantics exactly, nothing wider

`diff_watchlist(conn, date_str, strategy, ranked)` diffs an in-memory `ranked` list against
*the most recent prior persisted snapshot* (`SELECT MAX(date) WHERE date < date_str`) — it has
no concept of "diff these two arbitrary dates against each other." The brief's Parameters
section mentions "comparison dates," but building genuine arbitrary-pair comparison would mean
reimplementing the added/removed/status/score-delta computation outside `diff_watchlist` (since
that function always auto-selects "most recent prior") — which is exactly the "do not duplicate
business rules" this task rules out, and "do not invent filtering that does not already exist"
rules out extending the service to support it.

**Decision: `/api/v1/watchlists/diff?date=X&strategy=eod` exposes `diff_watchlist`'s native
semantics only** — the diff between `date=X` and whatever preceded it, using `get_snapshot(X,
strategy)` (re-hydrated into the same dict shape `ranked` already has: `ticker`/`confidence`/
`sources`) as the `ranked` argument. This is equivalent to what the EOD/Premarket scheduler jobs
themselves compute for a settled day — persisted data instead of live scan data, same function,
same result. Arbitrary two-date comparison is out of scope for this task; flagged, not built.

## Endpoints

- `GET /api/v1/watchlists/current?strategy=eod` — rows for the latest date. `404
  NO_WATCHLIST_DATA` if the strategy has no snapshot at all.
- `GET /api/v1/watchlists/history?strategy=eod` — `{"strategy", "dates": [...], "count"}`, all
  dates with a snapshot, newest first.
- `GET /api/v1/watchlists/{date}?strategy=eod` — rows for that exact date. `404
  NO_WATCHLIST_DATA` if nothing was snapshotted that day.
- `GET /api/v1/watchlists/diff?date=X&strategy=eod` — `date` required. `404
  NO_WATCHLIST_DATA` if `date` itself has no snapshot; `200` with `"diff": null` (not an error)
  if `date` exists but has no prior snapshot to compare against — a legitimate state (first day
  ever, or after a gap), not a failure.
- `GET /api/v1/watchlists/persistent?status=active|removed|all` (default `active`) — from the
  audit's mapping table (same "watchlist" domain, no date-keying — one row per ticker,
  current state only). `200` with an empty list if the table has no rows yet (not a 404 — an
  empty persistent watchlist is a valid state, not "missing data").
- All five: `VIEWER`.

## Data contract

Structured JSON only — `sources` JSON-decoded to a real list, no Telegram HTML/markdown from
`build_message()`/`_build_diff_section()` anywhere in the response. Each watchlist row:
`{ticker, rank, confidence, conviction, confluence, sources}`. Each persistent-watchlist row:
`{ticker, first_added_date, last_seen_date, status, consecutive_days, total_appearances}`.

## Explicitly out of scope

Arbitrary two-date diff (see above), pagination (neither `get_snapshot` nor `list_watchlist`
has any today — brief says only support it "if already supported by the service"), and
`regime_watchlist` (bear dip-scout — per the audit, deferred as scanner input rather than a
business output).
