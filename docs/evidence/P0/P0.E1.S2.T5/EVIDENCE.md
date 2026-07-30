# Evidence — P0.E1.S2.T5

**Date:** 2026-07-30
**Trace tag:** [DEBT-001, DEBT-002]

## Deliverable

`scheduler/reports.py::auto_trade_status_report` — two fixes, both confined to this one function:

1. **DEBT-001 (query scope):** the `paper_trades` query now requires a matching `premover_auto_log` row (`EXISTS` subquery on `ticker` + `entry_date`, `mode='enforce'`, `would_trade=1`) — i.e. a row `run_premover_eod`'s enforce-mode path actually opened via `open_trade()` (see `scheduler/jobs.py` lines 442-447). A `paper_trades` row opened through any other path (manual, other strategy) no longer appears under the "🤖 Auto-Trade Status" header. No schema change: `premover_auto_log` already exists and already records `mode`/`would_trade` per evaluation (`paper_trade.py::_log_premover_auto`).
2. **DEBT-002 (timezone):** `yesterday` is now computed via `datetime.now(WIB) - timedelta(days=1)`, matching every other date reference in `scheduler/reports.py` (`daily_fetch_report`, `flow_broker_report`, `open_trades_status_report` all use `dt.now(WIB)`/`datetime.now(WIB)`). Replaces the prior `datetime.now() - __import__('datetime').timedelta(days=1)` naive-time computation. `timedelta` is now imported locally in the function (matching the existing local-import convention at lines 38/64/76 of the same file) rather than via the `__import__` workaround.

## Test output (named tests)

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q tests/test_auto_trade_status_report.py tests/test_scheduler_report_registration.py -v
```
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
collected 13 items

tests/test_auto_trade_status_report.py .....                             [ 38%]
tests/test_scheduler_report_registration.py ........                     [100%]

============================== 13 passed in 0.32s ===============================
```

New tests (`tests/test_auto_trade_status_report.py`, 5), against an isolated DB with the real `paper_trades`/`premover_auto_log` schema (via `paper_trade.init_paper_table()`), `send_telegram` captured instead of sent, holiday guard bypassed:
- An enforce-mode, `would_trade=1` auto-trade is included (baseline correctness).
- A manual/other-path `paper_trades` row with no matching `premover_auto_log` row is excluded (DEBT-001).
- A `paper_trades` row matched only by a **shadow**-mode log entry is excluded (mode filter).
- A `paper_trades` row matched only by a `would_trade=0` log entry is excluded (would-trade filter).
- **DEBT-002 regression:** WIB-now and naive-now frozen to the same real instant but different calendar dates (as a UTC-clocked process would produce); a trade dated two days before WIB-now must be excluded under the WIB-correct cutoff — the pre-fix naive cutoff would have computed one day earlier and incorrectly included it.

## Fix verified to actually change behavior (self-review, not just line coverage)

Before committing, the fix was temporarily reverted to the pre-T5 code and the same 5 tests re-run: 4 of 5 failed (`test_excludes_manual_trade_with_no_matching_log_row`, `test_excludes_shadow_mode_log_entry`, `test_excludes_would_trade_false_log_entry`, `test_yesterday_cutoff_uses_wib_not_naive_now`), confirming each targets real, previously-present behavior rather than passing vacuously. Re-applied the fix; all 5 pass again. (Same discipline T4 itself used on its own self-reference bug.)

## Regression run (full suite)

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q
```
```
1241 passed, 1 skipped in 21.59s
```
Prior baseline (after P0.E1.S2.T4) was 1,236 passed / 1 skipped / 0 failed; +5 from this task's new tests, 0 regressions.

## Gate-script output

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python scripts/pre_merge_gate.py
```
```
[PASS] QG-1 full test suite
    1241 passed, 1 skipped in 21.87s
[PASS] QG-4 schema drift
    N/A — no schema module yet (Phase 1 deliverable, P1.E1.S1)
[PASS] QG-9 grep-audits (phase-appropriate)
    AN-8 audit: 37 candidate(s) clean, 0 violation(s) — unchanged by this task
    AN-8: PASS — zero unwired capabilities
[PASS] QG-5 evidence presence
    7 done-task card(s) checked, all have evidence artifacts

GATE: PASS
```

## Documentation delta

None. `auto_trade_status_report`'s content is not referenced by any `docs/ops/*` checklist (checked: no match for `auto_trade_status_report` under `docs/ops/`) — same situation T3/T4 found for this function's sibling reports. The behavior change is operator-visible (fewer/different rows in the 09:00 WIB Telegram message going forward) but there is no existing contract doc to amend.

## Decision entries filed

- `DEBT-001` — update filed (append-only, entry not edited per §8 rule); closes once this task is cold-reviewed and merged, not before.
- `DEBT-002` — update filed (append-only); closes once this task is cold-reviewed and merged, not before.

## Verification commands

```
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q tests/test_auto_trade_status_report.py -v
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q
PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python scripts/pre_merge_gate.py
```
