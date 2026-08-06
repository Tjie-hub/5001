# Task 2C-3 — Forward-Testing Report APIs

**Status:** Approved 2026-08-06 (Production Engine Phase 2, Workstream 2C, Task 3 of 4).
Builds on the frozen v1 foundation, frozen Workstream 2B, the
[Business Output Audit](2026-08-06-2c-business-apis-audit.md), and 2C-1/2C-2.

## Audit confirmation

Per the brief's own Implementation Note, and confirmed here: `forward_testing/reporting.py` is
the **only** persisted, structured report subsystem in this codebase — everything the EOD/
Premarket jobs produce is already the Watchlist/Snapshot APIs (2C-1/2C-2), not a separate
report artifact (per the original audit's risk #1). No placeholder EOD/Premarket report
endpoints are added.

`forward_testing/reporting.py` cleanly separates data from presentation already:
`get_positions_opened_on`, `get_trades_closed_on`, `get_all_closed_trades`,
`get_active_candidate_count`, `win_loss_summary`, `best_worst_trades` are pure data functions
(module docstring: "Read-only... nothing here writes to the database"); `_fmt_*`,
`build_forward_test_message`, `build_forward_test_report` are presentation (HTML/Telegram
text) — **excluded entirely**, per this task's non-goals.

Existing tests: `tests/forward_testing/test_reporting.py` (all seven data functions above,
extensively). Existing consumer: `scheduler/jobs.py::run_forward_test_cycle` (nightly 18:30
WIB), which is also where the exact `run_date` convention this design reuses comes from
(`rd = run_date or datetime.now(WIB).strftime("%Y-%m-%d")`).

## Two new pure helpers (existence/inventory only — no new business logic)

Forward-test reports have no natural "does a report exist" signal in the data functions
themselves (`get_positions_opened_on` etc. happily return `[]` for any date, real or not —
there's no way to tell "genuinely no activity" from "nobody ran this job that day"). The one
already-written signal for "a report was actually generated" is the dedup guard
`run_forward_test_cycle` already writes: `_job_sentinel(job='forward_test_cycle', run_date)`
(created inline in `scheduler/jobs.py`, never read anywhere before this task). Two small reads
added to `forward_testing/reporting.py`:

- `report_exists(db_path, run_date) -> bool` — `SELECT 1 FROM _job_sentinel WHERE
  job='forward_test_cycle' AND run_date=?`.
- `latest_report_date(db_path) -> Optional[str]` — `SELECT MAX(run_date) FROM _job_sentinel
  WHERE job='forward_test_cycle'`.

## One new structured-data assembly function

`build_forward_test_data(db_path, run_date, repo=None) -> dict` — calls the exact same six
data functions, in the exact same order, with the exact same arguments as
`build_forward_test_report` already does, but returns a dict instead of calling
`build_forward_test_message`. This necessarily duplicates the *orchestration sequence* (which
functions to call, in what order) that already exists inside `build_forward_test_report` —
refactoring that function to share the sequence would mean modifying an existing,
working, tested report-generation function, which this task's own constraints rule out
("do not modify report generation"). The six *computations themselves* are called unchanged,
not duplicated — only the ~10-line call sequence is, the same trade-off already accepted in
2B-2 rather than touching `app.py`'s live Prometheus route.

## Endpoints

- `GET /api/v1/reports/{date}` — the structured report for one exact date. `404
  NO_REPORT_DATA` if `report_exists()` is false for that date (the forward-test cycle never
  ran that day — not the same as "ran with zero activity," which returns real zero-filled
  data).
- `GET /api/v1/reports` — the **most recent** report (`latest_report_date()`), not strictly
  "today" — mirrors 2C-1's `/watchlists/current` idiom (latest available, not date-of-request)
  rather than the scheduler job's own internal "today" default, since a bare `/reports` call
  before the nightly 18:30 WIB run would otherwise 404 all day for no useful reason. `404
  NO_REPORT_DATA` only if no forward-test report has ever been generated.
- Both: `VIEWER`.

## Data contract

`{date, new_positions, closed_trades, active_positions, active_candidates, win_loss,
best_trades, worst_trades}` — exactly `build_forward_test_data`'s return shape, exactly the
same six values `build_forward_test_message` already renders, none of them reformatted. Exit
reasons (SL/TP/TRAIL/TIME/STALE) pass through verbatim, per the module's own stated discipline.

## Explicitly out of scope

EOD/Premarket "report" endpoints (already covered by 2C-1/2C-2, per the audit and this task's
own Implementation Note), any Telegram/HTML rendering, and any new report category.
