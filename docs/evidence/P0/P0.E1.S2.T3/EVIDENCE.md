# Evidence — P0.E1.S2.T3

**Date:** 2026-07-26
**Trace tag:** [H-2, AN-8]

## Investigation (before coding)

| Function | Where defined | Callers found | Registered? | Own docstring time | Superseded by another registered job? |
|---|---|---|---|---|---|
| `daily_fetch_report` | `scheduler/reports.py:33` | `scheduler/__init__.py` (module-level re-export only) | No — confirmed, matches audit H-2 | none stated | No — `run_ohlcv_coverage_check` (17:00) checks OHLCV *coverage-thinness* only (alert-on-anomaly); it does not report `stockbit_flow`/`broker_flow` ticker counts, average records/ticker, or a routine (always-sent) status. `run_market_health_report` (08:45) reports VPIN/breadth/technicals — unrelated content. No overlap found. |
| `flow_broker_report` | `scheduler/reports.py:303` | `scheduler/__init__.py` (re-export); referenced in `scheduler/jobs.py:305`'s `run_news_fetch` docstring ("Spike detection... is consumed by flow_broker_report") and in `tests/test_scheduler_foreign_snapshot_removal.py` (P0.E1.S2.T2, explicitly noting this function's registration is out of that task's scope) | No — confirmed, matches audit H-2 | **"Report at 17:15"** (own docstring, verbatim) | No — `run_eod_trade_plan` (16:40) is the agent-firm ranked trade plan across long sources; distinct content from this function's flow-sentiment/divergence/news-spike/foreign-accumulation digest. `run_premover_eod` (16:30) is deterministic auto-trade evaluation, not a report. |
| `auto_trade_status_report` | `scheduler/reports.py:466` | `scheduler/__init__.py` (re-export only) | No — confirmed, matches audit H-2 | **"Report at 09:00"** (own docstring, verbatim) | No — `open_trades_status_report` (route-triggered, not scheduled) reports *currently open* trades with live P&L; this function reports the last 10 `paper_trades` rows (open or closed) since yesterday, as an activity digest, not a live snapshot. Different content and different trigger mechanism. |
| `open_trades_status_report` (4th export, **not in scope**) | `scheduler/reports.py:132` | `routes/backtest.py:942-943` (real, live route) | N/A — reachable via route, not audit H-2's target | — | — |

### `auto_trade_status_report` — is there a live auto-trade feature behind it?

Traced `auto_trade_from_premover` end to end: `paper_trade.py` stores the mode (`off`/`shadow`/`enforce`) in `paper_config`, exposed via `routes/backtest.py`'s GET/POST endpoints; `run_premover_eod` (registered, 16:30 WIB, `scheduler/jobs.py`) is the job that reads the mode and, when `enforce` and a setup would-trade, calls `paper_trade.open_trade(...)` directly — this **does** write `paper_trades` autonomously. `run_premover_eod`'s own per-setup Telegram summary is deliberately suppressed same-day (`# Telegram suppressed per config` in its body). `auto_trade_status_report`'s 09:00-next-morning digest is the natural, designed complement to that same-day suppression — not a duplicate, and not describing a dead feature.

**Scope caveat found (not fixed — see DEBT-001):** the report's SQL (`SELECT ... FROM paper_trades WHERE entry_date >= yesterday`) selects every `paper_trades` row opened in the window, not only rows `run_premover_eod` opened. Under present conditions this is not *wrong* (auto-trade-from-premover is the only path shown writing `paper_trades` autonomously in this codebase — other entries are the operator's manual/agent-firm trades, which the operator already knows they made), but the report's "🤖 Auto-Trade Status" framing would misrepresent those rows if a second automated writer appears. Filed as DEBT-001; not fixed here (content-scope change, not a wiring decision — out of T3's register-or-delete remit, ER-2).

## Decision: Option A (register) for all three

1. None of the three duplicates content already produced by a registered job (table above).
2. Two of the three name their own intended time in-docstring — used verbatim, no guesswork.
3. The third (`daily_fetch_report`) has no stated time; its data sources (`ohlcv`, `stockbit_flow`, `broker_flow`) are only fully populated for the day after the 20:15 broker-flow fetch and the 21:00 reconciliation pass, so 21:05 was chosen (IMPL-DEC-005).
4. All three already have complete, working implementations (each builds a message and calls `send_telegram`, matching the pattern of every other registered report/job in this file) — deleting working, non-duplicated code would discard information the operator has never had a chance to receive, which the audit itself flags as the worse outcome ("a documented output that silently doesn't exist is worse than no output").

`open_trades_status_report` is untouched — it was never audit H-2's target (real route caller found) and this task adds no scheduler registration for it.

## Fix

- `scheduler/__init__.py`:
  - Added `scheduler.add_job(daily_fetch_report, ...)` at 21:05 WIB, `mon-fri`, id `daily_fetch_report`.
  - Added `scheduler.add_job(flow_broker_report, ...)` at 17:15 WIB, `mon-fri`, id `flow_broker_report`.
  - Added `scheduler.add_job(auto_trade_status_report, ...)` at 09:00 WIB, `mon-fri`, id `auto_trade_status_report`.
  - Added three startup banner `print()` lines matching the existing per-job idiom.
  - No changes to `scheduler/reports.py` — all three functions are registered as-is; the DEBT-001 content-scope question is explicitly not fixed in this diff.

## Test output (named tests)
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q tests/test_scheduler_report_registration.py -v
```
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/tjies/workspace/projects/5001
configfile: pytest.ini
plugins: anyio-4.14.2, asyncio-1.3.0, langsmith-0.10.9, respx-0.23.1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 8 items

tests/test_scheduler_report_registration.py ........                     [100%]

============================== 8 passed in 0.62s ===============================
```

New tests (`tests/test_scheduler_report_registration.py`, 8):
- Each of the three functions is registered under the expected job id, targets the correct function object, and fires at the expected hour/minute/day_of_week.
- `open_trades_status_report` remains unregistered (confirms this task didn't overreach into the out-of-scope 4th export).
- No duplicate job ids anywhere in the scheduler, and none of the three new ids is double-registered.
- `flow_broker_report` is scheduled strictly after its two data sources (17:00 news fetch, 16:15 screener EOD).
- `daily_fetch_report` is scheduled strictly after its two data sources (20:15 broker flow fetch, 21:00 OHLCV reconciliation).
- Sanity: the exact three H-2-named functions are the wired targets, and the 4th export's identity is unchanged.

## Old-implementation-fails / new-implementation-passes proof
Ran the 8 new tests against the pre-fix `scheduler/__init__.py` (`git stash push -- scheduler/__init__.py`, then `git stash pop` — working tree confirmed restored to the fix):
```
6 failed, 2 passed in 0.45s
```
The 6 failures are exactly the ones that assert registration exists (three per-function registration tests, no-duplicate-ids, and the two ordering tests, which need the job to exist before its trigger time can be compared) — each fails against pre-fix code for the expected reason (`add_job` was never called). The 2 that pass either way test facts unaffected by this change: `open_trades_status_report` was already unregistered before this task and stays that way, and the sanity check on function identity is true regardless of scheduler wiring.

## Regression run (full suite)
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q
```
```
1230 passed, 1 skipped in 25.30s
```
Prior baseline (after P0.E1.S2.T2) was 1,222 passed / 1 skipped / 0 failed; +8 from this task's new tests, 0 regressions.

## Gate-script output

**Cold-review correction (2026-07-26):** the run pasted below was captured mid-implementation, before this task card's final status-line wording was settled, and was stale by the time the task was first presented as complete — a finding from this task's own cold review. Re-run post-fix, with the task card correctly reading `**Status:** done` (no substring ambiguity):
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python scripts/pre_merge_gate.py
```
```
[PASS] QG-1 full test suite
    1230 passed, 1 skipped in 24.37s
[PASS] QG-4 schema drift
    N/A — no schema module yet (Phase 1 deliverable, P1.E1.S1)
[PASS] QG-9 grep-audits (phase-appropriate)
    PENDING — implemented by P0.E1.S2.T4 (scripts/audits/an8_unregistered_jobs.py not yet present)
[PASS] QG-5 evidence presence
    7 done-task card(s) checked, all have evidence artifacts

GATE: PASS
```
7 is the correct, legitimate count (6 done cards existing before this task + T3 itself, now genuinely done with evidence) — not a repeat of the substring artifact the original (now-superseded) run below exhibited.

*Original run, captured before the task-card wording fix — kept for the audit trail, not as current evidence:*
```
[PASS] QG-1 full test suite
    1230 passed, 1 skipped in 24.03s
[PASS] QG-4 schema drift
    N/A — no schema module yet (Phase 1 deliverable, P1.E1.S1)
[PASS] QG-9 grep-audits (phase-appropriate)
    PENDING — implemented by P0.E1.S2.T4 (scripts/audits/an8_unregistered_jobs.py not yet present)
[PASS] QG-5 evidence presence
    6 done-task card(s) checked, all have evidence artifacts

GATE: PASS
```
This "6" was captured while `TASK-CARD.md` still read `not-started`, so it correctly excluded T3 at that moment — it was not itself wrong, it was simply never re-verified against the final wording before being cited as this task's evidence, which cold review flagged as a Major finding (evidence bundle must reflect the artifact it's evidence for).

## Decision entries filed
- `IMPL-DEC-005` — registration time choice for `daily_fetch_report` (21:05 WIB).
- `DEBT-001` — `auto_trade_status_report` query not scoped to auto-trade-originated rows; payoff task **`P0.E1.S2.T5`** assigned (PLAN-001 §18 changelog, 2026-07-26).
- `DEBT-002` — (filed during cold review) `auto_trade_status_report` mixes naive/WIB-aware `datetime.now()`; same payoff task `P0.E1.S2.T5`.

## Verification commands
```
export PATH=$HOME/.local/node/bin:$PATH
.venv/bin/python -m pytest -q tests/test_scheduler_report_registration.py -v
.venv/bin/python -m pytest -q
.venv/bin/python scripts/pre_merge_gate.py
```
