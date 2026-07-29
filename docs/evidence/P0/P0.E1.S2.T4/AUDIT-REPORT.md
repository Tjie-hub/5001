# Repository Audit Report — P0.E1.S2.T4 (AN-8: unwired capability)

**Date:** 2026-07-26
**Trace tag:** [AN-8]
**Scope:** every function re-exported through `scheduler/__init__.py` — the complete set of scheduler-reachable capabilities, not only the 6 dead jobs the Audit originally named (H-1's `run_hourly_risk_bundle`/`run_eod_risk_summary`/`run_foreign_snapshot`, H-2's `daily_fetch_report`/`flow_broker_report`/`auto_trade_status_report`, all dispositioned by P0.E1.S2.T1/T2/T3).

## 1. Methodology

A candidate (any name re-exported from `scheduler.utils`, `scheduler.scanner`, `scheduler.jobs`, or `scheduler.reports` into `scheduler/__init__.py`) passes the audit if it is any of:

1. **Registered** — passed as the function argument to `scheduler.add_job(...)` inside `start_scheduler()`.
2. **Externally referenced** — the name appears anywhere else in the repository (a real call site, a route, a test, or another registered function's body), **excluding** its own function body in its defining file (a self-referential docstring/comment must not count as evidence of external use — see §4) and excluding the `scheduler/__init__.py` import line itself.
3. **Allowlisted** — an explicit, reasoned, dated exception citing a follow-up task (empty by default; this task added exactly one entry, for the one finding below).
4. **Formally retired** — deleted outright (not checked programmatically; there is nothing left to find).

`utils.telegram.send_telegram` (re-exported for backward-compatible import paths, per the file's own comment) is excluded from the candidate set — it is a general-purpose utility, not a job/report/check in AN-8's sense.

Implementation: `scripts/audits/an8_unregistered_jobs.py`. Reproducible via:
```
.venv/bin/python scripts/audits/an8_unregistered_jobs.py
```

## 2. Commands executed

```
.venv/bin/python scripts/audits/an8_unregistered_jobs.py
.venv/bin/python -m pytest -q tests/test_an8_audit.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/pre_merge_gate.py
```

Plus manual, per-candidate verification (`grep -rn '\bNAME\b' --include='*.py' .`, excluding `.venv`/`__pycache__`) for every one of the 37 candidates, cross-checked against the script's own output — see §3.

## 3. Findings

**37 candidates checked. 36 clean, 1 new finding.**

| Candidate | Disposition | Basis |
|---|---|---|
| `_run_open_trade_monitor`, `_run_screener_eod`, `_run_screener_intraday`, `auto_trade_status_report`, `daily_fetch_report`, `daily_signal_scan`, `flow_broker_report`, `run_broker_flow_fetch`, `run_eod_risk_summary`, `run_eod_trade_plan`, `run_flow_fetch`, `run_forward_test_cycle`, `run_hourly_risk_bundle`, `run_market_health_report`, `run_news_fetch`, `run_ohlcv_coverage_check`, `run_ohlcv_reconciliation`, `run_phase5_bull_watch`, `run_premarket_firm_scan`, `run_premover_eod`, `run_scheduler_heartbeat`, `run_token_health_check`, `run_vpin_daily_batch`, `scheduled_multi_strategy_scan` | Registered | Each appears as the function argument to `scheduler.add_job(...)` in `start_scheduler()` |
| `open_trades_status_report` | Externally referenced | `routes/backtest.py:942-943` — a real, live manual-trigger route (confirmed again by T3; unchanged) |
| `get_all_tickers`, `fetch_latest`, `_load_ohlcv_bulk`, `send_suspension_resume_alerts` | Externally referenced | Called throughout `scanner.py`, `jobs.py`, `research/`, `migrations/applied/`, and by each other (`fetch_latest` calls `send_suspension_resume_alerts` internally, and `fetch_latest` itself is called from `scanner.py:537` inside `daily_signal_scan`, which **is** registered — so the whole chain is reachable) |
| `calc_votes`, `check_fundamental`, `_detect_price_shock`, `_load_stockbit_token`, `check_keystats_freshness`, `scan_momentum_signals`, `get_ticker_best_strategies` | Externally referenced | Internal helpers called by registered scan functions in the same module, and/or called directly from `routes/backtest.py` (`check_fundamental`, `scan_momentum_signals`) |
| **`run_vpin_backfill`** | **NEW FINDING — unwired** | `scheduler/jobs.py:894`. Fully implemented (N-day historical VPIN backfill, complementary to the registered daily `run_vpin_daily_batch`). Imported into `scheduler/__init__.py`. Referenced **nowhere else in the repository** — no `add_job`, no route, no CLI entry point (`grep -rn 'backfill'` across every `.py` file surfaced only its own definition, its own print/log strings, and unrelated uses of the word "backfill" in other modules' comments — see raw grep in the task's implementation transcript). Not one of the Audit's originally-named 6 jobs. |

## 4. A defect in the audit tool itself, caught before it shipped

While building `scripts/audits/an8_unregistered_jobs.py`, its own test suite (`tests/test_an8_audit.py::test_own_body_line...`) caught a real bug: the first implementation only excluded the literal `def name(` line when checking a function's own defining file, so a self-referential docstring or comment elsewhere in that same function's body (e.g. "Mirrors scheduler._load_ohlcv_bulk" — a real pattern already present in `engine/suspension_detector.py`) would have been miscounted as "external reference," silently masking a genuinely orphaned function whose only self-mention happened to sit in its own docstring. Fixed by excluding the function's whole body span (its `def` line through the line before the next top-level `def`/`class`, or EOF), not just the single `def` line — verified by a fresh test run and re-confirmed against the real repository (same single finding, `run_vpin_backfill`, before and after the fix).

## 5. Justification for every exception

- **`run_vpin_backfill`** is the only allowlisted exception, added with a citation to its follow-up task (`P0.E1.S2.T6`, PLAN-001 §18 changelog) and a dated reason in `scripts/audits/an8_unregistered_jobs.py`'s `ALLOWLIST` dict. No other exceptions exist.

## 6. Zero unresolved H-2-class violations (with the one explicit exception noted)

- All 6 of the Audit's originally-named dead jobs (H-1 ×3, H-2 ×3): **dispositioned** (P0.E1.S2.T1/T2/T3, merged).
- All other scheduler-exported capabilities beyond those 6: **36 of 37 clean**, **1 documented, allowlisted, and handed to a follow-up task** (`run_vpin_backfill` → `P0.E1.S2.T6`).
- The audit script is now wired into `scripts/pre_merge_gate.py`'s QG-9 (which already auto-detected the script's existence per `IMPL-DEC-003` — no gate-script edit was needed) and will fail any future merge that introduces a new, undocumented unwired capability.

## 7. Recommended follow-up (not implemented here, per this task's scope)

- **`P0.E1.S2.T6`** — decide `run_vpin_backfill`'s fate. Location: `scheduler/jobs.py:894`. Impact: a working historical-backfill utility is currently unreachable by any means (scheduled, manual route, or CLI) — low operational risk today (nothing depends on it running), but it means recovering from a VPIN data gap wider than what the daily batch catches has no invocation path at all. Recommended investigation mirrors T1–T3's methodology: check whether a periodic schedule makes sense for a backfill tool (probably not — these are typically run on-demand), in which case the right "wiring" may be a documented manual invocation path (an ops runbook entry or a thin CLI wrapper) rather than a cron registration.
