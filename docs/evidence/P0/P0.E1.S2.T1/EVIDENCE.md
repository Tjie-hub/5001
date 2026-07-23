# Evidence — P0.E1.S2.T1

**Date:** 2026-07-23
**Trace tag:** [H-1]

## Root cause (confirmed against source, matches Audit §4 H-1)
`scheduler/jobs.py` fully implements `run_hourly_risk_bundle` and `run_eod_risk_summary` (each holiday-guarded via `_holiday_skip`, each delegating to a well-formed, idempotent `engine/risk_alert.py` function). `scheduler/__init__.py` imports both (lines 51-52) but never calls `scheduler.add_job(...)` for either — grep-verified before the fix: zero occurrences of `run_hourly_risk_bundle` or `run_eod_risk_summary` inside any `add_job(...)` call. RED/ORANGE/YELLOW alerts were written to `market_risk_log` with `sent=0` by `route_risk_alert` (called from `scheduler/scanner.py`'s multi-strategy scan) and simply accumulated, never delivered.

## Decision: Option A (register), not Option B (delete)
Justification, from existing documentation:
- `engine/risk_alert.py` module docstring (design intent, predates this task): `"RED: logged to market_risk_log; bundled hourly by scheduler"`, `"ORANGE: logged to market_risk_log; EOD summary only"`.
- Audit H-1 **Fix** text: `"Register the two jobs (hourly during session + EOD)."`
- The implementation itself is correct and idempotent (`get_pending_risk_alerts` filters `sent=0`; `mark_alerts_sent` flips them after a successful send) — nothing about it is obsolete or broken, it was simply never wired up.

No third option was considered or needed — the evidence unambiguously supports registration.

## Fix
`scheduler/__init__.py`:
1. New loop, `hour in range(9, 16)`, registers `run_hourly_risk_bundle` at `:10` each hour (09:10-15:10, mon-fri) — mirrors the *exact* existing idiom already used for `_run_open_trade_monitor`'s hourly loop two blocks above it (same `range(9, 16)`, same day-of-week), offset 5 minutes later than the `:05` slot shared by `scheduled_multi_strategy_scan` and `_run_open_trade_monitor` (the jobs that write to `market_risk_log` via `route_risk_alert`) to avoid a same-minute write-then-read race — the same defensive-offset pattern already used elsewhere in this exact file (`_run_screener_eod` at 16:15 vs. the 16:05 flow fetch; `eod_trade_plan` at 16:40 after 16:15+16:30).
2. New single registration for `run_eod_risk_summary` at `16:10` mon-fri — after the session's last risk-scoring pass (14:35 scan / 15:05 trade monitor), in the existing "EOD family" time band, not colliding with any existing job minute.
3. Two new print lines in the startup summary, matching the pre-existing convention that every registered job gets one.

No changes to `scheduler/jobs.py` or `engine/risk_alert.py` — both were already correct. `run_foreign_snapshot` (also flagged by H-1, also currently unregistered) is explicitly **not** touched — it is P0.E1.S2.T2's separate, not-yet-started task.

## Test output (named tests)
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/tjies/workspace/projects/5001
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.3.0, langsmith-0.10.9, respx-0.23.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 8 items

tests/test_scheduler_risk_alert_registration.py ........                 [100%]

============================== 8 passed in 0.31s ===============================
```

New tests (`tests/test_scheduler_risk_alert_registration.py`, 8):
- **Registration:** `run_hourly_risk_bundle` registered at all 7 session hours (09:10-15:10) · `run_eod_risk_summary` registered exactly once at 16:10 · no duplicate job ids anywhere in the scheduler · the risk-bundle's minute doesn't collide with the market_risk_log writer's minute (race-avoidance proof) · sanity check that the two functions targeted are the exact two the audit named (not `run_foreign_snapshot`, which stays out of scope).
- **Idempotence** (pre-existing `engine.risk_alert` behavior, now actually exercised in production for the first time): `send_hourly_risk_bundle` called twice sends once (RED) · `send_eod_risk_summary` called twice sends once (ORANGE+YELLOW bundled) · `send_hourly_risk_bundle` does not steal ORANGE/YELLOW rows from the EOD summary.

**Bug-catching sanity check:** ran the 8 new tests against the pre-fix `scheduler/__init__.py` (temporarily restored via `git stash push -- scheduler/__init__.py`, then `git stash pop`, working tree verified restored) — the 2 registration-existence tests failed (`AssertionError: missing hourly_risk_bundle job for hour 9`, `assert None is not None` for `eod_risk_summary`), the other 6 (idempotence + sanity checks, which don't depend on scheduler wiring) passed either way, as expected.

## Regression run (full suite)
```
1216 passed, 1 skipped in 24.48s
```
Prior baseline (after P0.E1.S1.T2) was 1,208 passed / 1 skipped / 0 failed; +8 from this task's new tests, 0 regressions.

## Gate-script output
```
GATE: PASS
```
(QG-1 full suite 1,216 passed/1 skipped/0 failed; QG-4 N/A pre-Phase-1; QG-9 PENDING — the full "zero imported-but-unregistered jobs" grep-audit is P0.E1.S2.T4's deliverable, this task is one of the two jobs it will later verify; QG-5 evidence present for all done tasks.)

## Verification commands
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q tests/test_scheduler_risk_alert_registration.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/pre_merge_gate.py
```
