# Evidence — P0.E1.S1.T1

**Date:** 2026-07-23
**Trace tag:** [H-8, AN-5]

## Root cause (confirmed against source, matches Audit §4 H-8)
`scheduler/scanner.py:410` — `_vpin_conn = _db_connect(DB_PATH)`. `_db_connect` was never defined in the module (the real import is `from data.db import connect as db_connect`). Every call with `filter_vpin=1` raised `NameError`, caught by a bare `except Exception` that logged a warning **without `continue`**, so the ticker fell through and passed the VPIN gate regardless of its actual VPIN signal — the filter was a silent no-op.

## Fix
`scheduler/scanner.py` VPIN block (was lines 404-418, now 404-427):
1. `_db_connect(DB_PATH)` → `db_connect(DB_PATH)` (the name that actually exists) — removes the NameError.
2. Connection close wrapped in `try/finally` — the original `_vpin_conn.close()` ran unconditionally after the calc call with no protection; once the NameError is fixed, a `calc_vpin_multi` exception would otherwise leak the now-successfully-opened connection.
3. `except Exception as _ve:` now calls `fail_closed_alarm("vpin_gate", ..., notify=False)` and `continue`s — fail-closed per AN-5 ("A gate that cannot evaluate blocks the candidate and records why"), matching the `notify=False` per-ticker convention already used at the liquidity_gate fail-open site (scanner.py ~line 1376) to avoid Telegram spam inside the per-ticker loop.
4. Removed the dead `import sqlite3 as _sqlite3` line that sat inside the same 3 lines being rewritten (module already imports `sqlite3` at top-level; this local alias was never referenced anywhere).

`engine/fail_open_alarm.py`: added `fail_closed_alarm` / `format_fail_closed_alarm`, mirroring the existing `fail_open_alarm` plumbing (WARNING log + best-effort Telegram, never raises) but with an accurate "🛑 FAIL-CLOSED" message — reusing `fail_open_alarm` as-is would have mislabeled a blocked candidate as an admitted one. See `docs/EXEC-DECISIONS.md` IMPL-DEC-004.

## Test output (named tests)
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/tjies/workspace/projects/5001
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.3.0, langsmith-0.10.9, respx-0.23.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 14 items

tests/test_scanner_vpin_gate.py ......                                   [ 42%]
tests/test_fail_open_alarm.py ........                                   [100%]

============================== 14 passed in 0.51s ==============================
```

New tests (`tests/test_scanner_vpin_gate.py`, 6): VPIN disabled never calls `calc_vpin_multi` (legacy off-switch preserved) · no NameError on DB-unavailable (regression for the root cause) · fails closed + alarms on DB-unavailable · fails closed + alarms on a `calc_vpin_multi` error (proves the fix isn't narrowly scoped to one call site) · passes an accepted signal and closes its connection (no leak on the success path) · blocks a rejected signal with no alarm (legacy non-error block path untouched).

New tests (`tests/test_fail_open_alarm.py`, +4): `format_fail_closed_alarm` says FAIL-CLOSED not FAIL-OPEN · logs at WARNING · notifies via Telegram best-effort · swallows notifier errors without raising.

**Bug-catching sanity check:** ran the 6 new scanner tests against the pre-fix `scheduler/scanner.py` (`git stash push -- scheduler/scanner.py`) — 3 failed, with the captured log line reproducing the exact audited defect verbatim: `WARNING root:scanner.py:418 [scan_momentum] VPIN filter error [TESTVPIN]: name '_db_connect' is not defined`. Confirms the new tests actually exercise and catch H-8, not just re-describe it.

## Regression run (full suite)
```
1205 passed, 1 skipped in 23.06s
```
Baseline was 1195 passed / 1 skipped / 0 failed (bring-up, `docs/EXEC-DECISIONS.md` IMPL-DEC-001); +10 from this task's new tests (6 scanner + 4 fail_open_alarm), 0 regressions.

## Gate-script output
```
[PASS] QG-1 full test suite
    ... 1205 passed, 1 skipped in 23.19s
[PASS] QG-4 schema drift
    N/A — no schema module yet (Phase 1 deliverable, P1.E1.S1)
[PASS] QG-9 grep-audits (phase-appropriate)
    PENDING — implemented by P0.E1.S2.T4 (scripts/audits/an8_unregistered_jobs.py not yet present)
[PASS] QG-5 evidence presence
    2 done-task card(s) checked, all have evidence artifacts

GATE: PASS
```
(First run before this file existed correctly reported `[FAIL] QG-5` for this exact task — see task card history; re-run after this file was added passes, confirming QG-5 enforces evidence-before-done, not just a check that always passes.)

## Verification commands
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q tests/test_scanner_vpin_gate.py tests/test_fail_open_alarm.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/pre_merge_gate.py
```
