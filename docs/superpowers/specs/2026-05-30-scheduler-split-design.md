# R5a — scheduler.py Split Design

**Date:** 2026-05-30  
**Scope:** Convert `scheduler.py` (1887 lines) into a Python package `scheduler/` with five focused sub-modules. Zero logic changes — pure structural refactor.

---

## Problem

`scheduler.py` has grown to 1887 lines covering four distinct concerns: shared fetch utilities, data fetch jobs, signal scanning, and monitoring reports. All module-level state (three cache dicts) lives alongside APScheduler job registrations and 15+ job functions. The file is hard to navigate and impossible to test in isolation.

---

## Architecture

### Package structure

```
scheduler/
  __init__.py   — start_scheduler() + all APScheduler CronTrigger registrations
  state.py      — _regime_clf_cache, _sector_scores_cache, _last_trades_state
  utils.py      — get_all_tickers, fetch_latest, _load_ohlcv_bulk, send_suspension_resume_alerts
  jobs.py       — run_flow_fetch, run_broker_flow_fetch, run_foreign_snapshot, run_news_fetch
  scanner.py    — _get_sector_scores_cached, _sector_verdict, scan_momentum_signals,
                  daily_signal_scan, scheduled_multi_strategy_scan
  reports.py    — daily_fetch_report, open_trades_status_report, flow_broker_report,
                  auto_trade_status_report
```

### Dependency graph (no cycles)

```
scheduler/__init__.py
  ├── scheduler/jobs.py      → scheduler/utils.py, scheduler/state.py
  ├── scheduler/scanner.py   → scheduler/utils.py, scheduler/state.py
  └── scheduler/reports.py  → scheduler/utils.py, scheduler/state.py

scheduler/utils.py   — no internal imports
scheduler/state.py   — no imports
```

### Module responsibilities

**`state.py`**  
Holds the three module-level cache dicts that were previously defined at the top of `scheduler.py`:
- `_regime_clf_cache: dict` — cached regime classifier per ticker
- `_sector_scores_cache: dict` — cached sector scores with TTL timestamp
- `_last_trades_state: dict` — previous open-trades snapshot for delta detection

Sub-modules that need a cache import it directly: `from scheduler.state import _sector_scores_cache`.

**`utils.py`**  
Shared fetch helpers used by more than one sub-module:
- `get_all_tickers(conn)` — returns list of active ticker strings
- `fetch_latest(conn, ticker)` — returns latest OHLCV row for a ticker
- `_load_ohlcv_bulk(conn, tickers, date)` — bulk OHLCV load for scan jobs
- `send_suspension_resume_alerts(conn)` — suspension detector + Telegram alert

**`jobs.py`**  
Scheduled data-ingestion job functions (each is registered as a CronTrigger in `__init__.py`):
- `run_flow_fetch()`
- `run_broker_flow_fetch()`
- `run_foreign_snapshot()`
- `run_news_fetch()`

All import from `scheduler.utils` and `scheduler.state` as needed.

**`scanner.py`**  
Signal scanning logic:
- `_get_sector_scores_cached(conn)` — reads/writes `_sector_scores_cache`
- `_sector_verdict(scores, ticker)` — pure helper, no DB
- `scan_momentum_signals(conn, tickers, date)` — momentum signal scanner
- `daily_signal_scan()` — orchestrates the daily EOD scan job
- `scheduled_multi_strategy_scan()` — multi-strategy scan job

**`reports.py`**  
Monitoring and report job functions:
- `daily_fetch_report()`
- `open_trades_status_report()`
- `flow_broker_report()`
- `auto_trade_status_report()`

**`__init__.py`**  
Contains only `start_scheduler()`. Imports job functions from the four sub-modules and registers them with APScheduler using WIB (Asia/Jakarta) CronTriggers — identical to the current `start_scheduler()` at lines 1698–1888 of `scheduler.py`.

---

## Migration Strategy

1. Create `scheduler/` directory.
2. Move functions into sub-modules one file at a time, in dependency order:
   - `state.py` first (no deps)
   - `utils.py` second (no internal deps)
   - `jobs.py`, `scanner.py`, `reports.py` (depend on state + utils)
   - `__init__.py` last (depends on all four)
3. Delete `scheduler.py`.
4. Run full test suite after each sub-module is created to catch import errors early.

**Callers unchanged:**  
`app.py` does `from scheduler import start_scheduler` — works because `__init__.py` exports it.  
No other file imports from `scheduler.py` directly (verified by grep).

---

## Testing

- No new tests required — this is a pure structural refactor with zero logic changes.
- Full test suite (`venv/bin/pytest`) must be green before and after each sub-module move.
- Final gate: 173 tests pass, Flask app starts cleanly, APScheduler registers all jobs without error.

---

## Out of Scope

- `app.py` split — deferred to R5b (separate spec)
- Any logic changes to scheduler functions
- New scheduler features or job additions
- Test coverage improvements for scheduler functions
