# Evidence — P0.E1.S1.T2

**Date:** 2026-07-23
**Trace tag:** [H-8]

## Objective
Expand `tests/test_scanner_vpin_gate.py` (created in P0.E1.S1.T1) to prove the corrected VPIN gate under the full required behaviour matrix, not just the two scenarios T1 needed to demonstrate its own fix.

## Required behaviour matrix — coverage

| # | Case | Test | Result |
|---|---|---|---|
| 1 | VPIN enabled, DB available, PASS → proceeds | `test_vpin_pass_lets_candidate_reach_downstream_processing` | proceeds past the gate — proven via a `calc_vol_ratio` spy, not just an empty-result absence of evidence |
| 2 | VPIN enabled, DB available, FAIL → blocked | `test_vpin_fail_blocks_candidate_before_downstream_processing` | blocked before downstream — same spy technique, proves the block is real, not incidental |
| 3 | VPIN enabled, DB unavailable → blocked + alarm | `test_vpin_fails_closed_and_alarms_on_db_unavailable` (T1) | blocked, exactly one alarm, `notify=False` |
| 4 | VPIN enabled, eval exception → blocked + alarm | `test_vpin_fails_closed_and_alarms_on_calc_error` (T1, strengthened this task) | blocked, exactly one alarm, **and** the opened connection is confirmed closed (no leak) |
| 5 | VPIN disabled → legacy preserved | `test_vpin_disabled_never_calls_calc_vpin_multi` (T1) | `calc_vpin_multi` never called |

Cross-cutting, also required by this task:
- **No silent pass:** `test_vpin_no_longer_raises_nameerror_on_db_unavailable` (T1) — regression for the root cause itself.
- **Exactly one alarm:** asserted via `len(alarm_calls) == 1` in cases 3 and 4; extended in the new determinism test (below) to exactly-one-per-run across repeated runs.
- **No resource leaks:** case 4 (new this task) and the existing PASS-path check (T1) both assert the gate's own connection was closed.
- **Determinism:** new `test_vpin_gate_is_deterministic_across_repeated_runs` — same mocks, two calls to `scan_momentum_signals()`, identical disposition and identical alarm payload both times.

## Isolation achieved (no real DB/scheduler/network)
- Database: `db_connect` monkeypatched to a `_FakeConn` stub or a controlled-raise function.
- Scheduler-adjacent gates (`is_trading_day`, `is_blackout_day`, sector scores, macro overlay): monkeypatched to fixed pass-through values — none of them are the VPIN gate, so their real behavior isn't the thing under test.
- Alarm emission: `engine.fail_open_alarm.fail_closed_alarm` replaced with a spy list — asserts call count, `source`, ticker-bearing detail string, and `notify=False`.
- Candidate disposition: proven two ways — the coarse way (empty `signals` result, used by the DB-unavailable/calc-error/disabled cases, where result emptiness is unambiguous because there's no OHLCV data to reach otherwise) and the precise way (a `calc_vol_ratio` spy with a >=25-row df, used by the PASS/FAIL cases specifically because those are the two cases where "empty result" alone is ambiguous about whether the candidate was blocked at the VPIN gate or simply had no further data).

## Test output (named tests)
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/tjies/workspace/projects/5001
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.3.0, langsmith-0.10.9, respx-0.23.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 9 items

tests/test_scanner_vpin_gate.py .........                                [100%]

============================== 9 passed in 0.52s ===============================
```

## Old-implementation-fails / new-implementation-passes proof
Ran the full 9-test file against the pre-fix `scheduler/scanner.py` (`git show 03e1ed3:scheduler/scanner.py`, the last commit before T1's fix, temporarily swapped in and restored via `git checkout --` afterward — working tree verified byte-identical to the committed fix post-restore):

```
tests/test_scanner_vpin_gate.py ..FFF..FF                                [100%]
5 failed, 4 passed in 0.61s
```

5 failures, all against the exact audited defect (captured in every failing test's log): `WARNING root:scanner.py:418 [scan_momentum] VPIN filter error [TESTVPIN]: name '_db_connect' is not defined`. Failing tests: `test_vpin_fails_closed_and_alarms_on_db_unavailable`, `test_vpin_fails_closed_and_alarms_on_calc_error`, `test_vpin_passes_strong_buy_signal_and_closes_connection`, `test_vpin_fail_blocks_candidate_before_downstream_processing` (new this task), `test_vpin_gate_is_deterministic_across_repeated_runs` (new this task).

The 4 tests that pass against the old code do so for an understood, non-alarming reason, not because they fail to exercise the bug: the old except-path had no `continue`, so it fails *open* (lets every candidate through regardless of VPIN outcome) rather than crashing the whole scan — `test_vpin_pass_lets_candidate_reach_downstream_processing` (row 1, PASS→proceeds) is trivially satisfied by a gate that always lets everything through; `test_vpin_disabled_never_calls_calc_vpin_multi` and `test_vpin_no_longer_raises_nameerror_on_db_unavailable` only assert non-crash / not-called, which old code also happens to satisfy. The block/alarm/leak/determinism assertions — the ones that actually distinguish "fixed" from "broken" — are exactly the ones that fail on old code.

## Regression run (full suite)
```
1208 passed, 1 skipped in 23.37s
```
Prior baseline (after T1) was 1,205 passed / 1 skipped / 0 failed; +3 from this task's new tests, 0 regressions.

## Gate-script output
```
[PASS] QG-1 full test suite
    ... 1208 passed, 1 skipped in ...s
[PASS] QG-4 schema drift
    N/A — no schema module yet (Phase 1 deliverable, P1.E1.S1)
[PASS] QG-9 grep-audits (phase-appropriate)
    PENDING — implemented by P0.E1.S2.T4 (scripts/audits/an8_unregistered_jobs.py not yet present)
[PASS] QG-5 evidence presence
    4 done-task card(s) checked, all have evidence artifacts

GATE: PASS
```
(exact numbers captured at commit time below)

## Verification commands
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q tests/test_scanner_vpin_gate.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/pre_merge_gate.py
```
