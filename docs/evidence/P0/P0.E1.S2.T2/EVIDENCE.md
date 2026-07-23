# Evidence — P0.E1.S2.T2

**Date:** 2026-07-23
**Trace tag:** [H-1]

## Investigation (before coding)

| Question | Finding |
|---|---|
| Where defined | `scheduler/jobs.py` (was lines 302-340) |
| Import/reference sites | `scheduler/__init__.py` (module-level import only) + the function's own internals. Grep across the entire repo before the fix: only `scheduler/__init__.py`, `scheduler/jobs.py`, and historical (non-code) design docs from 2026-05-30/06-04 predating this program — nothing else calls it. |
| Scheduler registration | Not registered (`add_job`) — confirmed, matches audit H-1. |
| Documentation of purpose | Its own docstring: `"14:30 WIB — Pre-close foreign accumulation watchlist alert... Sends top 5 buy + top 5 sell tickers"`. But the body never calls `send_telegram` — it builds `msg` and then only prints `"... — no alert"`. Audit's own account: `"its send_telegram call was removed but the job kept its 14:30 docstring"` — i.e. a completed, deliberate deprecation with a stale docstring, not a bug. |
| Downstream consumers | None. Writes nothing to the DB; return value unused (function returns `None` implicitly); nothing imports it except the scheduler package. |
| Does it write data required elsewhere | No. |
| Does another scheduler job already do this work | **Yes** — `scheduler/reports.py::flow_broker_report` computes the identical thing: same function (`flow_filter.get_top_foreign_accumulation`), same `top_n=9999`, same top-5-buy/top-5-sell split, with an explicit in-code comment `"Foreign accumulation top 5 — appended to evening report"`. Unlike `run_foreign_snapshot`, `flow_broker_report` still calls `send_telegram(msg)` at the end of its body — it is a complete, correct implementation. |

## Decision: Option B (delete)

Evidence supports removal, not registration:
1. The alert path was **deliberately** disabled (send call removed), not accidentally broken — reviving it would be un-deprecating something, not fixing an oversight.
2. Its content is **already superseded** by `flow_broker_report`'s broader "evening report" (which also covers bullish/neutral/divergence signals and news-spike attention). Registering `run_foreign_snapshot` alongside `flow_broker_report` (once H-2/P0.E1.S2.T3 registers that, separately) would permanently duplicate the same foreign-flow content across two Telegram messages — exactly the kind of redundant alert path the audit and EXEC-001 (ER-12 thinness) both discourage.
3. No downstream consumer depends on it; deleting it has zero data or contract impact.

`flow_broker_report` itself is untouched — its registration status is H-2's scope (`scheduler/reports.py`, three functions, owned by P0.E1.S2.T3), not this task's.

## Fix
- `scheduler/jobs.py`: deleted the `run_foreign_snapshot` function body in full (its two local imports, `datetime as dt` and `flow_filter.get_top_foreign_accumulation`, were function-scoped and are removed with it — no module-level import became orphaned).
- `scheduler/__init__.py`: removed `run_foreign_snapshot` from the `from scheduler.jobs import (...)` re-export list. No `add_job` line ever existed for it, so nothing else changes.
- `tests/test_scheduler_risk_alert_registration.py`: updated one stale comment (from P0.E1.S1.T1) that referenced `run_foreign_snapshot` as "still out of scope" — it's now removed, not merely out of scope; direct, necessary consequence of this deletion, not unrelated cleanup.

## Test output (named tests)
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/tjies/workspace/projects/5001
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.3.0, langsmith-0.10.9, respx-0.23.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 14 items

tests/test_scheduler_foreign_snapshot_removal.py ......                  [ 42%]
tests/test_scheduler_risk_alert_registration.py ........                 [100%]

============================== 14 passed in 0.39s ===============================
```

New tests (`tests/test_scheduler_foreign_snapshot_removal.py`, 6):
- Symbol no longer exists on `scheduler.jobs` or the `scheduler` package.
- No source-level reference to the string `run_foreign_snapshot` remains anywhere under `scheduler/` (whole-file substring scan, not just imports).
- AST-level check: no dangling `_holiday_skip("run_foreign_snapshot")` call, and `scheduler/jobs.py` still parses cleanly (no fragment left behind).
- `start_scheduler()` still registers cleanly with no job referencing the removed function, and no duplicate job ids.
- The shared data function `flow_filter.get_top_foreign_accumulation` is still importable — no collateral damage to what `flow_broker_report` depends on.
- `flow_broker_report`'s superseding foreign-accumulation block is still present and untouched — confirms this task didn't reach into H-2/T3's file.

## Old-implementation-fails / new-implementation-passes proof
Ran the 6 new tests against the pre-fix `scheduler/jobs.py` + `scheduler/__init__.py` (`git stash push -- scheduler/jobs.py scheduler/__init__.py`, then `git stash pop` — working tree confirmed restored to the fix):
```
tests/test_scheduler_foreign_snapshot_removal.py FFF...                  [100%]
3 failed, 3 passed in 0.42s
```
The 3 failures are exactly the ones that assert removal (symbol-exists check, source-scan, AST dangling-call check) — each fails against pre-fix code for the expected reason (the function is still there). The 3 that pass either way test things unaffected by this specific change (scheduler still boots; the shared data function and the successor report are untouched) — correct, since those facts are true both before and after this task.

## Regression run (full suite)
```
1222 passed, 1 skipped in 23.15s
```
Prior baseline (after P0.E1.S2.T1) was 1,216 passed / 1 skipped / 0 failed; +6 from this task's new tests, 0 regressions.

## Gate-script output
```
GATE: PASS
```
(QG-1 full suite 1,222 passed/1 skipped/0 failed; QG-4 N/A pre-Phase-1; QG-9 PENDING — full "zero imported-but-unregistered jobs" grep-audit is P0.E1.S2.T4's deliverable; this task closes one more of the six named jobs; QG-5 evidence present for all done tasks.)

## Verification commands
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q tests/test_scheduler_foreign_snapshot_removal.py tests/test_scheduler_risk_alert_registration.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/pre_merge_gate.py
```
