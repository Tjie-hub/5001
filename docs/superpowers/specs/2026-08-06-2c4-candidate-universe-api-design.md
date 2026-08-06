# Task 2C-4 — Candidate Universe APIs + Legacy Migration Decision

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2C, Task 4 of 4 —
final task before the freeze). Builds on the frozen v1 foundation and 2C-1/2C-2/2C-3.

## Step 1 — Consumer audit (required before any decision)

| Route | Frontend | Scheduler | Agent Firm | Docs | Tests | Verdict |
|---|---|---|---|---|---|---|
| `GET /api/screener/results` | **YES** — `templates/workspace.html:1780`, `fetch('/api/screener/results')` | no | no | no | no | **Active consumer** |
| `GET /api/screener/reversal` | no | no | no | no | no | **No consumer** |
| `GET /api/premover/watchlist` | no | no | no | no | no (only a self-referential status message in its own sibling route) | **No consumer** |
| `POST /api/premover/run` | no | no | no | no | no | **No consumer**, but a write/trigger action — see below |

Grepped for literal path references across `*.py`/`*.js`/`*.html`, `docs/`, `*.md`, and `tests/`
(full repo). `test_premover_auto_trade.py` was checked directly — it tests `/api/paper/
premover_mode` (a different, unrelated paper-trading toggle route), not these.

## Migration decision (per-route, per the brief's own rule)

- **`/api/screener/results` — active consumer → KEEP.** `templates/workspace.html` calls it
  directly; removing it breaks a real page. `GET /api/v1/candidates/screening` is added
  alongside it, calling the exact same `screener.db.get_screen_results(date)` — zero
  duplication, two URLs. Migration plan: once a v1-native frontend consumer exists (tracked
  under Phase 2C/2D more broadly, not this task), point `workspace.html` at the v1 endpoint and
  retire the legacy one then — not now, since that's a frontend change outside this task's
  scope ("do not refactor unrelated modules").
- **`/api/screener/reversal` — no consumer → MIGRATE, remove legacy.** Its logic (persisted-
  table-if-available else live-scan-of-latest, `?date=`/`?direction=` filters) lived entirely
  inline in the route, not in a service function — extracted into
  `screener.reversal_filter.get_current_watchlist()` (new, see below) as part of the move, not
  duplicated across two files.
- **`/api/premover/watchlist` — no consumer → MIGRATE, remove legacy.** Already a clean call
  to `engine.premover_detector.get_watchlist()`; the v1 route calls the same function verbatim.
- **`POST /api/premover/run` — out of scope, left untouched regardless of consumer count.** A
  write/trigger action (starts a background scan), not a candidate-universe *read* artifact —
  this task's Data Contract is read-only ("Return business objects only"; "do not introduce new
  persistence"). Migrating triggers isn't part of Watchlist/Snapshot/Report/Candidate Universe
  scope. Its sibling GET route's removal doesn't affect it; its own `security/route_policy.py`
  OPERATOR entry stays.

## What "Candidate Universe" actually is — four distinct sources, one namespace

Per the original [Business Output Audit](2026-08-06-2c-business-apis-audit.md),
`candidate_watchlist_snapshot` (`engine.watchlist_report`) is the canonical pre-firm candidate
universe — the one with `record_snapshot`/`diff_snapshot`, matching the brief's suggested
`current`/`{date}` shape (the same shape 2C-1 already established for watchlist_snapshot). The
consumer audit surfaced three *additional*, narrower candidate sources that don't share that
shape (no diff concept, different tables) — kept as clearly separate, named sub-resources under
the same `/api/v1/candidates/*` namespace rather than forced into a shape they don't fit
("adjust endpoint names if the audit reveals a better fit").

### `diff` dropped from scope — structural finding, not a narrowing choice

Unlike `trade_plan.diff_watchlist` (2C-1) — whose "current" side only needs already-persisted
`ticker`/`confidence`/`sources`, so a persisted snapshot can be re-hydrated into its `ranked`
argument — `watchlist_report.diff_snapshot`'s "current" side **always recomputes**
`candidate_score(c)` from the live `candidates` argument (`current = {c["ticker"]:
candidate_score(c) for c in candidates}`), and `candidate_score()` reads `c["conviction"]` and
`c["vol_ratio"]` directly (`KeyError` if absent). `candidate_watchlist_snapshot` persists only
the *already-computed* `score` column — `conviction`/`vol_ratio`/`premkt_conf` (the raw scoring
inputs) are never stored anywhere. There is no way to reconstruct a valid `candidates` argument
from persisted data alone, so `diff_snapshot()` cannot be called against a past date the way
`diff_watchlist()` could. Writing a second comparison purely over stored `score` values would
duplicate `diff_snapshot`'s set-difference/movement-threshold algorithm outside the function
that owns it — exactly what this task rules out ("do not duplicate business rules" / "if a
metric is not already tracked, omit it rather than introducing new engine logic": the raw
per-candidate scoring inputs simply aren't tracked). **`GET /api/v1/candidates/diff` is
therefore not implemented in this task.** `current`/`{date}` (read-only content, no
recomputation) are unaffected and ship as designed below.

## New read-only helpers (two)

- `engine.watchlist_report.get_snapshot(conn, date_str) -> list[dict]` — the persisted
  `candidate_watchlist_snapshot` rows for one date, rank order. Same shape/purpose as 2C-1's
  `trade_plan.get_snapshot` (a straight `SELECT`), added because `watchlist_report.py` had a
  writer (`record_snapshot`) and an inventory reader (`list_snapshot_inventory`, 2C-2) but no
  content reader yet.
- `screener.reversal_filter.get_current_watchlist(db_path) -> tuple[str | None, list[dict]]` —
  moves the legacy route's branching (persisted `reversal_watchlist` for the latest `scan_date`
  if the table has rows, else a live `scan_reversals()` of the latest `daily_screen` date) into
  the module that already owns `scan_reversals`/`run_scan`. This is the route's *existing*
  logic relocated, not new business logic, and not a second copy — the legacy route is deleted
  in the same change.

## Endpoints

- `GET /api/v1/candidates?strategy=` *(none — candidate_watchlist_snapshot has no strategy
  axis, unlike watchlist_snapshot)* — current pre-firm candidate universe. `404
  NO_CANDIDATE_DATA` if nothing has ever been snapshotted.
- `GET /api/v1/candidates/{date}` — that date's snapshot. `404 NO_CANDIDATE_DATA` if none.
  (No `diff` endpoint — see the structural finding above.)
- `GET /api/v1/candidates/screening?date=` (default today) — `screener.db.get_screen_results()`
  verbatim. Empty list (not 404) for a date with no rows — a quiet day is valid, not missing.
- `GET /api/v1/candidates/reversal-watchlist?date=&direction=` — `date` omitted uses
  `get_current_watchlist()`'s persisted-or-live fallback (the migrated legacy default
  behavior); `date` given calls `run_scan(date)` directly, matching the legacy contract exactly.
  `direction` filters `long`/`short` client-side exactly as the legacy route did.
- `GET /api/v1/candidates/premover-watchlist?min_score=&days=&pattern_type=` —
  `engine.premover_detector.get_watchlist()` verbatim, same defaults (`min_score=50, days=5`).
- All five: `VIEWER` (matches every legacy entry being replaced — none were more restrictive).

## Data contract

Structured JSON only, `sources`/`reasons` JSON-decoded where the underlying table stores them
as text, no HTML/console formatting anywhere (none existed in these routes to begin with — the
legacy screener/premover routes were already pure JSON).

## Explicitly out of scope

`POST /api/premover/run` (write action, see above), any change to `screener.db`,
`screener.reversal_filter`'s scan algorithm, or `engine.premover_detector`'s scoring/detection
logic — every function called here already existed and is called unchanged.
