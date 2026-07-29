# Evidence — P0.E1.S2.T4

**Date:** 2026-07-26
**Trace tag:** [AN-8]

Full methodology, per-candidate findings, and follow-up recommendation are in `AUDIT-REPORT.md` (this task's primary deliverable). This file carries the standard test/regression/gate evidence.

## Deliverable

`scripts/audits/an8_unregistered_jobs.py` — reproducible repository-wide AN-8 grep-audit. Checks all 37 names re-exported from `scheduler/__init__.py` (across `scheduler.utils`, `scheduler.scanner`, `scheduler.jobs`, `scheduler.reports`). A candidate passes if registered (`scheduler.add_job`), externally referenced anywhere else in the repo, or explicitly allowlisted with a dated reason and a follow-up task citation.

## Test output (named tests)
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q tests/test_an8_audit.py -v
```
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/tjies/workspace/projects/5001
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.3.0, langsmith-0.10.9, respx-0.23.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 6 items

tests/test_an8_audit.py ......                                           [100%]

============================== 6 passed in 0.19s ===============================
```

New tests (`tests/test_an8_audit.py`, 6), against synthetic repos so the audit tool's own detection logic is tested independently of the real, large, slow-changing scheduler package:
- A registered job is classified clean.
- An externally-called helper is classified clean.
- A genuinely orphaned function is flagged.
- An allowlisted orphan is clean (audit passes) but remains visible in the report, not silently hidden.
- **Self-reference regression test:** a function whose own docstring mentions its own name must still be flagged if nothing else references it — this test caught a real bug in the first implementation (§4 of AUDIT-REPORT.md) before it shipped.
- **Integration check:** running the real audit module against the actual repository asserts it currently passes (36 clean + 1 allowlisted-with-citation), so a future accidental regression in either the audit logic or the allowlist is caught by CI, not discovered manually.

## Bug caught by this task's own test suite, then fixed
The first implementation of `_has_external_reference` only excluded the literal `def name(` line within a function's own defining file — a self-referential docstring or comment elsewhere in that same function's body would have been miscounted as "external reference." `tests/test_an8_audit.py::test_own_def_line_does_not_count_as_external_reference` failed against that implementation:
```
FAILED tests/test_an8_audit.py::test_own_def_line_does_not_count_as_external_reference
assert False
+  where False = any(<generator object ...>)
1 failed, 5 passed in 0.22s
```
Fixed by excluding the function's whole body span (its `def` line through the line before the next top-level `def`/`class`, or EOF) rather than only the single `def` line. Re-run after the fix: 6 passed. Re-ran the real-repo audit before and after the fix — identical result both times (36 clean + `run_vpin_backfill`), confirming the fix didn't change behavior against the actual codebase, only against the synthetic case it was built to catch.

## Regression run (full suite)
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q
```
```
1236 passed, 1 skipped in 23.85s
```
Prior baseline (after P0.E1.S2.T3) was 1,230 passed / 1 skipped / 0 failed; +6 from this task's new tests, 0 regressions.

## Gate-script output
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python scripts/pre_merge_gate.py
```
```
[PASS] QG-1 full test suite
    1236 passed, 1 skipped in 23.85s
[PASS] QG-4 schema drift
    N/A — no schema module yet (Phase 1 deliverable, P1.E1.S1)
[PASS] QG-9 grep-audits (phase-appropriate)
    AN-8 audit: 37 candidate(s) clean, 0 violation(s)
    ... (36 registered/externally-referenced + 1 allowlisted — full list in AUDIT-REPORT.md §3)
    AN-8: PASS — zero unwired capabilities
[PASS] QG-5 evidence presence
    7 done-task card(s) checked, all have evidence artifacts

GATE: PASS
```
QG-9 flips from `PENDING` (placeholder, per `IMPL-DEC-003`) to a real, enforced check for the first time — no edit to `scripts/pre_merge_gate.py` was needed, since its `check_grep_audits()` already auto-detects the audit script's existence and runs it once present.

## Decision entries filed
- `DEBT-003` — `run_vpin_backfill` is an unwired capability (new AN-8 finding); payoff task `P0.E1.S2.T6` assigned (PLAN-001 §18 changelog, 2026-07-26).

## Verification commands
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python scripts/audits/an8_unregistered_jobs.py
.venv/bin/python -m pytest -q tests/test_an8_audit.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/pre_merge_gate.py
```
