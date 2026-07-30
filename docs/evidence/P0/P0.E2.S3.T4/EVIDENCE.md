# Evidence — P0.E2.S3.T4

**Date:** 2026-07-30
**Trace tag:** [L-4]
**Branch:** implemented directly on `master` (single-session, operator-directed continuation — see Time-gate note)

## Verification (before coding)

- `docs/PLAN-001-Implementation-Master-Plan.md` §3, line 83: "T4: holiday
  fail-open note logged `[L-4]`" — confirms this is the correct, and
  final, Phase 0 task.
- `docs/EXEC-STATUS.md` §7 "Next up": `P0.E2.S3.T4 — holiday fail-open
  note logged [L-4] (last Phase 0 task)` — confirmed.
- `git log --oneline -5` showed `P0.E2.S3.T3` (`a224454`) as `HEAD`, no
  intervening work; `git status` showed no `p0/e2-s3-t4-*` branch and no
  stray uncommitted work touching `scheduler/jobs.py` or
  `scheduler/reports.py`. No discrepancy found.
- The pre-existing task-card scaffold independently confirms scope: "Log
  a note when a holiday check fails open, instead of failing silently" —
  matches what was built.
- Traced `[L-4]` to the original audit:
  `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md` line 308: "**L-4:**
  `_holiday_skip` fails open (calendar import error → job runs on
  holidays; ohlcv gets purged later but `stockbit_flow`/`daily_screen`
  keep junk holiday rows)."
- Read `scheduler/jobs.py` in full before changing anything, per the
  operator's explicit instruction, not just the `_holiday_skip` function
  in isolation.

## Root-cause analysis

**Why the audit flagged this:** `_holiday_skip(fn_name)` wraps its
calendar check in `try: ... except Exception: pass`, then unconditionally
`return False`. If `from engine.calendar_filter import is_trading_day`
raises (a broken import — syntax error, missing module) or
`is_trading_day()` itself raises for any reason, the exception is
discarded with **no logging at all**, and the function returns `False` —
"not a holiday, proceed" — even though the check that would have proven
that never actually completed. The caller (every job listed below) then
runs its full body as if today were a normal trading day. The audit's own
consequence note — "ohlcv gets purged later but `stockbit_flow`/
`daily_screen` keep junk holiday rows" — describes a real downstream
asymmetry: some tables have a later cleanup/reconciliation pass that
removes bad holiday-written rows, others don't, so a fail-open event
leaves permanent junk data in those tables with no record that it
happened.

**Every code path that can trigger the fail-open condition:** two
independent, unrelated definitions of `_holiday_skip` exist — confirmed
by `grep -rn "_holiday_skip" --include="*.py" .` before writing any code,
not assumed:
- `scheduler/jobs.py:59` — 12 call sites in the same file:
  `run_flow_fetch`, `run_broker_flow_fetch`, `run_ohlcv_reconciliation`,
  `run_token_health_check`, `run_ohlcv_coverage_check`, `run_news_fetch`,
  `run_premover_eod`, `run_hourly_risk_bundle`, `run_eod_risk_summary`,
  `run_market_health_report`, `run_premarket_firm_scan`,
  `run_eod_trade_plan`.
- `scheduler/reports.py:19` — an **independent** copy (not imported from
  `jobs.py`, has its own separate `except Exception: pass`), with 4 call
  sites: `daily_fetch_report`, `open_trades_status_report`,
  `flow_broker_report`, `auto_trade_status_report`.
- Both had the identical fail-open shape; the fix had to be applied to
  both, not just one, to actually close the audit finding.

**Confirmed out of scope (a different pattern, not L-4):**
`scheduler/scanner.py`'s `scan_momentum_signals` (line 250) and
`scheduled_multi_strategy_scan` (line 1237) also call
`is_trading_day()`, but with **no try/except at all** — a broken
calendar import there propagates as an uncaught exception (fail-loud /
crash), not a silent fail-open. This is architecturally different from
`_holiday_skip`'s pattern and is not what L-4 describes; left untouched,
per "do not redesign calendar ownership or scheduling."

**Whether existing logging/monitoring already covers part of this:**
checked directly — it does not. The pre-fix `except Exception: pass` in
both copies is a bare pass with zero logging; nothing else in the
codebase logs or alerts on this specific failure mode. This confirms the
task is additive, not duplicative of existing coverage — same finding
pattern as `P0.E2.S3.T3`'s "nothing already covers this" check.

## Implementation

Both `_holiday_skip` copies changed identically in shape:
```diff
-    except Exception:
-        pass
+    except Exception as e:
+        logging.warning(f"[{fn_name}] holiday check failed ({e}) — failing open, job will run")
     return False
```
- **`scheduler/jobs.py`**: uses the module's existing top-level `logging`
  import (already present, used throughout the file) — no new import.
- **`scheduler/reports.py`**: same — the module already has `import
  logging` at the top (used elsewhere in the file); the new warning line
  uses it directly. (The pre-existing `if not ok:` branch's own quirky
  `import logging as _log` local shadow-import is untouched — fixing
  that would be unrelated cleanup, out of this task's scope.)
- **Docstrings on both functions** extended with an `L-4` note explaining
  the fail-open behavior is unchanged, only now logged — direct,
  in-file documentation of the change, not a functional difference.

**Fail-open behavior preserved exactly, not converted to fail-closed:**
`return False` is untouched in both files — on a calendar-check failure,
every caller still runs its job body exactly as before. Only the
previously-silent `except` branch now also calls `logging.warning(...)`
before falling through to the same `return False`.

**No refactoring of the two independent copies into one shared
function.** Considered and rejected: the two functions have small
existing stylistic differences (the `reports.py` copy's `if not ok:`
branch logs via a local `_log.getLogger(__name__)` instead of the
bare `logging` module functions `jobs.py` uses) and 16 call sites across
two files import nothing from each other today. Consolidating them would
be a real, if small, architectural change to shared scheduler
infrastructure — explicitly out of scope ("do not redesign calendar
ownership or scheduling"; "keep the implementation minimal and
localized").

## Tests

New `tests/test_holiday_skip_fail_open.py`, 7 tests — both `_holiday_skip`
copies covered independently, since they are separate functions with
separate fixes:

**`scheduler.jobs._holiday_skip`:**
- `test_jobs_normal_trading_day_no_log_no_skip` — normal operation: no
  skip, **no log at all**, unchanged.
- `test_jobs_normal_holiday_skips_and_logs_info` — normal holiday
  behavior unchanged: still skips, still logs at INFO (the pre-existing
  line), not WARNING.
- `test_jobs_calendar_import_failure_fails_open_and_logs_warning` — **the
  regression case the audit describes**: `is_trading_day()` raising
  `ImportError` (simulating a broken calendar import) still returns
  `False` (fail-open preserved exactly) but now logs exactly one WARNING
  naming the job and the exception.
- `test_jobs_unexpected_exception_type_also_fails_open_and_logs` — not
  just `ImportError` — any exception from `is_trading_day()` itself
  takes the same fail-open-and-log path.

**`scheduler.reports._holiday_skip` (independent copy):**
- `test_reports_normal_trading_day_no_log_no_skip`
- `test_reports_normal_holiday_skips_and_logs_info`
- `test_reports_calendar_import_failure_fails_open_and_logs_warning` —
  confirms the fix was applied to *both* files, not just `jobs.py`.

Each fail-open test also asserts `len(caplog.records) == 1` (no
duplicate logging — the "no duplicate logging where inappropriate"
requirement) and each normal-trading-day test asserts
`caplog.records == []` (no log at all when nothing is wrong — the same
requirement from the other direction).

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && ./.venv/bin/python -m pytest -q tests/test_holiday_skip_fail_open.py -v'
```
```
collected 7 items
tests/test_holiday_skip_fail_open.py .......                             [100%]
7 passed in 0.51s
```

**Confirmed these tests would have failed pre-fix, not just post-fix:**
`git diff scheduler/jobs.py scheduler/reports.py` shows the only change
is `except Exception: pass` → `except Exception as e: logging.warning(...)`
— the pre-fix branch had zero logging, so
`test_*_calendar_import_failure_fails_open_and_logs_warning`'s
`assert len(caplog.records) == 1` would have failed against `caplog.records == []`
before this change (verified by reading the diff, not by reverting and
re-running, since the diff is a single unambiguous line-for-line swap
with no other variable involved).

## Regression run (full suite)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python -m pytest -q'
```
```
1307 passed, 1 skipped in 25.20s
```
Baseline (post-`P0.E2.S3.T3`) was 1,300 passed/1 skipped/0 failed; +7 from
`test_holiday_skip_fail_open.py`. 0 regressions, 0 failures. Targeted
subset run first: `tests/test_holiday_skip_fail_open.py
tests/test_scheduler_risk_alert_registration.py
tests/test_calendar_coverage_alarm.py tests/test_auto_trade_status_report.py
tests/scheduler/` (this task's own tests plus every existing test
touching scheduler job registration, calendar checks, or the four
`reports.py` functions this task's `_holiday_skip` copy gates) — 43
passed, run before the full suite.

## Gate-script output

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python scripts/pre_merge_gate.py'
```
```
[PASS] QG-1 full test suite — 1307 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 38 clean, 0 violations, 0 allowlisted (unaffected — no scheduler-job surface touched, only internal logging inside two existing helper functions)
[PASS] QG-5 evidence presence — 8 done-task card(s) checked, all have evidence

GATE: PASS
```

## Decision entries filed

None. No `§8`-classifiable event — a straightforward, minimal logging
addition with an unambiguous root cause already fully specified by the
original audit. The one judgment call (leave the two independent
`_holiday_skip` copies as two copies, don't consolidate) is documented
above under "Implementation" rather than filed as a numbered `IMPL-DEC`
entry — a scope boundary consistent with the threshold used throughout
this cycle (`P0.E2.S2.T2`, `P0.E2.S3.T1`, `P0.E2.S3.T2`, `P0.E2.S3.T3`).

## Self-review (EXEC-001 §3.1 step 3, checklist §5.1/§5.2/§5.4)

- Diff does only what the task card says: one `except` branch changed in
  each of two files, two docstrings extended, one new test file. No
  drive-by changes — every job body, every other `except Exception:`
  block in `scanner.py`/`jobs.py`/`reports.py` (confirmed via grep there
  are many, all unrelated to calendar/holiday checking), and the two
  fail-loud `is_trading_day()` call sites in `scanner.py` are untouched.
- No FROZEN surface touched; Phase 0 stays legacy-only.
- No new dependency (ER-12) — `logging` already imported in both files.
- Fail-open behavior explicitly preserved, not converted to fail-closed —
  the operator's own instruction, verified by the diff itself
  (`return False` unchanged in both files).
- No forward-phase work smuggled in (ER-2): did not redesign calendar
  ownership, did not consolidate the two `_holiday_skip` copies, did not
  touch the fail-loud pattern in `scanner.py`.
- Task exists verbatim in PLAN-001 §3 (`P0.E2.S3.T4 ... [L-4]`) and is
  confirmed the final Phase 0 task (no `P0.E2.S3.T5` or further Phase 0
  entries in PLAN-001 §3).

## Cold review (EXEC-001 §4)

**Performed 2026-07-30, as an independent reviewer pass**, against the
operator's explicit checklist:

- **Hidden fail-open paths:** grepped `scheduler/`, `engine/calendar_filter.py`
  for every `except Exception:` (23 hits across `scanner.py`/`jobs.py`/
  `reports.py`) and read each site's context — none besides the two
  `_holiday_skip` copies wrap a calendar check with a silent pass; the
  rest are unrelated (data-fetch retries, optional-field parsing, etc.)
  and out of L-4's specific scope, not touched.
- **Logging correctness:** the new warning includes both the failing
  job's name and the exception's string representation
  (`f"[{fn_name}] holiday check failed ({e}) — failing open, job will run"`),
  matching the exact message shape already used elsewhere in the same
  file (`run_scheduler_heartbeat`'s `logging.warning(f"[heartbeat] write
  failed: {e}")`) — consistent with established convention, not a new
  pattern. No full traceback (`logging.exception`) — matches that same
  existing convention rather than introducing a new, heavier logging
  style for this one function.
- **Log spam:** each `_holiday_skip` call logs at most once per
  invocation (mutually exclusive `if not ok:` vs. `except` branches, one
  log call each, never both — verified by both the code shape and the
  `len(caplog.records) == 1` test assertions). If the calendar were
  persistently broken, callers running on their normal cadence (including
  `run_hourly_risk_bundle`, the most frequent) would each independently
  warn on their own schedule — a moderate volume of warnings under a
  genuinely broken calendar, but this is the correct, intended escalation
  for an actual operational fault, not spam under normal conditions
  (confirmed: zero logging on the normal/no-exception path).
- **Startup/import edge cases:** the new log call sits inside the same
  `try/except` that already wraps the calendar import; no new import-time
  behavior. Full test suite (which imports `scheduler.jobs`/
  `scheduler.reports` extensively) ran clean.
- **Regression risk:** full suite (1,307/1,300 baseline) and gate both
  clean; 4 explicit regression tests confirm normal trading-day and
  normal-holiday behavior in both files is byte-for-byte unchanged (same
  return value, same — or no — log line as before).
- **Documentation consistency:** both `_holiday_skip` docstrings updated
  in-file to explain the L-4 note; the audit report remains the read-only
  historical record and is correctly left unedited, same treatment as
  every prior L-series task this cycle.

**0 findings.** No code changes required as a result of this review.

**Time-gate note:** as with every P0 task this cycle, this cold review
occurred in the same continuous session as the implementation; operator
explicitly directed continuation.
