# Task 2C-2 — Snapshot APIs

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2C, Task 2 of 4).
Builds on the frozen v1 foundation, frozen Workstream 2B, the
[Business Output Audit](2026-08-06-2c-business-apis-audit.md), and 2C-1's Watchlist APIs.

## What "Snapshots" means here, distinct from 2C-1's "Watchlists"

2C-1 already exposes `watchlist_snapshot` **content** (`current`/`history`/`{date}`/`diff`) for
one strategy at a time. If `/api/v1/snapshots` did the same thing again, it would be a pure
duplicate — the task explicitly asks to simplify rather than ship that. Instead:

**`/api/v1/snapshots*` is a metadata/inventory layer across every snapshot-producing table,
not a second way to fetch watchlist content.** It answers "what snapshot artifacts exist in
this system, and how big are they" — not "what's in one." Two tables currently produce
date-keyed snapshots:

- `watchlist_snapshot` (`engine.trade_plan`) — per `(date, strategy)`.
- `candidate_watchlist_snapshot` (`engine.watchlist_report`) — per `date` only (single unified
  pre-firm universe, no strategy split).

`persistent_watchlist` is excluded (not date-keyed — current-state-only, already fully served
by 2C-1's `/api/v1/watchlists/persistent`); `regime_watchlist` is excluded (per the audit,
scanner input, not a snapshot artifact).

## `/api/v1/snapshots/history` is redundant — dropped, not built

The brief's own instruction: if one suggested endpoint is redundant with another, simplify and
document rather than ship duplicates. `/api/v1/snapshots` (no date filter) already returns
every inventory row across every date — that *is* "the history." A separate `/history` endpoint
would return the identical payload under a different name. **Dropped.** Two endpoints instead
of three: `GET /api/v1/snapshots` (optionally filtered) and `GET /api/v1/snapshots/{date}`.

## New read-only helpers (metadata only — no content-reading functions added here)

- `engine.trade_plan.list_snapshot_inventory(conn) -> list[dict]` — `{strategy, date,
  ticker_count}` per `(strategy, date)`, every strategy, via `GROUP BY strategy, date` over
  `watchlist_snapshot`. Distinct from 2C-1's `list_snapshot_dates` (single-strategy, dates
  only, no counts) — genuinely new, not a duplicate of it.
- `engine.watchlist_report.list_snapshot_inventory(conn) -> list[dict]` — `{date,
  ticker_count}` per date, via `GROUP BY date` over `candidate_watchlist_snapshot`.

Both are pure aggregate `SELECT`s over tables their own modules already own. No writer
(`record_snapshot` in either module, `diff_watchlist`, `diff_snapshot`) is touched.

## Endpoints

- `GET /api/v1/snapshots?type=watchlist|candidate_universe&strategy=eod|premarket` — every
  inventory row from both sources, tagged `{"type": "watchlist"|"candidate_universe",
  "strategy": "eod"|"premarket"|null, "date", "ticker_count"}`, newest first. `type`/`strategy`
  narrow the already-computed combined list (no new SQL capability — a Python filter over what
  the two aggregate queries already returned). Empty list (not 404) when nothing exists yet —
  an empty inventory is a valid state.
- `GET /api/v1/snapshots/{date}?type=&strategy=` — the same rows, filtered to one date. `404
  NO_SNAPSHOT_DATA` if that date has no snapshot of any type.
- Both: `VIEWER`.

## Data contract

Metadata only — `{type, strategy, date, ticker_count}` per row. No ticker-level content (that's
2C-1's job for watchlists, 2C-4's for candidate universe) and no Telegram/HTML formatting
anywhere in the response.

## Explicitly out of scope

Snapshot *content* retrieval (already 2C-1 for watchlists; candidate-universe content is
2C-4's), `regime_watchlist`, and any new filter beyond `type`/`strategy` (no pagination exists
on either underlying query, matching the brief's "only if already supported by the service").
