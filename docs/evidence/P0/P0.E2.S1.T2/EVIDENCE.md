# Evidence — P0.E2.S1.T2

**Date:** 2026-07-30
**Trace tag:** [H-3]
**Branch:** `p0/e2-s1-t2-freshness-guard`

## Investigation

Audit finding H-3: neither scan loop (`scheduler/scanner.py`'s
`scan_momentum_signals` and `scheduled_multi_strategy_scan`) nor the
intraday monitor (`monitor.py`'s `_check_trade` and `_evaluate_swing_trend`)
checked a ticker's last OHLCV bar date before treating it as tradeable. A
feed gap, suspension, or token death would silently leave a stale bar in
`ohlcv`, and every downstream consumer evaluated it as if it were the
current session — a scanner could fire an entry signal off a week-old bar,
and the monitor could evaluate SL/TP/trailing/time-stop logic against a
price that hasn't moved in days, producing exits (or non-exits) that don't
reflect the ticker's real state.

Per the task card, this is the deliberately minimal Phase 0 guard: skip +
count + one aggregate warning per run/cycle. The full per-ticker Certifier
freshness flag (versioned thresholds, `per_ticker_flags`) is out of scope —
Phase 1 (PLAN-001 P1.E4.S1).

## Deliverable

- `engine/freshness.py` (new) — `is_fresh(last_date, as_of=None,
  max_age_sessions=1)`: true iff `last_date` is within `max_age_sessions`
  IDX trading sessions of `as_of` (default today), counted via
  `engine.calendar_filter.is_trading_day` so weekends/holidays never count
  against a ticker (a Friday bar is still fresh the following Monday).
  `None` is never fresh; a future-dated bar (clock skew) is treated as
  fresh, not stale — this guard's job is catching lagging data, not
  validating future dates.
- `scheduler/scanner.py` — `is_fresh()` called immediately after the
  pre-existing `len(df) < N` history-length guard, at all three sites that
  read a ticker's last bar before treating it as current: `scan_momentum_signals`
  (`< 25`), `scheduled_multi_strategy_scan`'s adaptive-selection loop
  (`< 20`), and its SELL/distribution loop shares the same `ohlcv_map` (no
  second read — see Test-coverage scope decision below for what this loop's
  guard has and hasn't been proven by). Each site increments a local
  `stale_skipped` counter and logs one aggregate WARNING per run when
  nonzero — same visibility shape as `IMPL-DEC-006`'s coverage-fallback
  guard, reused here rather than re-decided.
- `monitor.py` — `is_fresh()` called in `_check_trade` (right after
  `_latest_bar` returns) and `_evaluate_swing_trend` (right after the
  `len(df) < 55` guard); both return their normal "no action" shape plus a
  `stale: True` key instead of evaluating exit/trail logic against the
  stale bar. `check_all_open_trades` checks `result.get('stale')` for both
  the swing-trend and non-swing branches, skips closing/persisting/alerting
  for that trade, and logs one aggregate WARNING (`N/M open trade(s)
  skipped this cycle (stale last bar)`) when any were skipped.
- Test files:
  - `tests/test_freshness_guard.py` (new, 9 tests) — unit tests of
    `is_fresh()`: same-day, 1-session boundary (fresh), 2-session boundary
    (stale), weekend crossing, missing date, future date, string-date
    input, `max_age_sessions=0` edge, inclusive-boundary check.
  - `tests/test_scanner_freshness_guard.py` (new, 4 tests) — drives the real
    `scan_momentum_signals` end-to-end with every other filter switched off
    (same idiom as `tests/test_scanner_vpin_gate.py`): fresh last bar
    reaches downstream (spy on `calc_vol_ratio`, the first call after the
    guard); stale last bar is skipped before downstream, aggregate warning
    logged; 1-session-old boundary still fresh; 2-session-old boundary
    stale.
  - `tests/test_monitor_kernel_exits.py` — existing fixtures switched from
    fixed 2026-06 calendar dates to today-relative offsets (`_d(offset)`),
    since the new guard requires each test's last bar to be fresh relative
    to whenever the suite actually runs; day-gaps (entry-to-bar, SMA/
    time-stop bar counts) preserved exactly, only the reference point
    moved. Added `test_check_trade_skips_evaluation_on_stale_bar`: a bar 2
    sessions stale, priced straight through the stored SL, is *not* closed
    — proves the guard actually blocks evaluation rather than merely being
    present.
  - `tests/test_monitor_freshness_guard.py` (new, 3 tests) —
    `_evaluate_swing_trend` stale-skip and fresh-control cases; an
    integration test on `check_all_open_trades` (both a stale non-swing and
    a stale swing-trend trade) proving `close_trade` is never called and
    exactly one aggregate warning (`"2/2"`) is logged.
  - `tests/test_nr7_live_pipeline_e2e.py`, `tests/test_scanner_vpin_gate.py`
    — pre-existing fixtures updated to use a today-dated bar, for the same
    reason as `test_monitor_kernel_exits.py` above (both drive real
    `monitor._check_trade` / `scanner.scan_momentum_signals` code paths
    that now sit behind the freshness guard).

## Test-coverage scope decision

`scheduled_multi_strategy_scan`'s freshness guard is **not** driven
end-to-end the way `scan_momentum_signals`'s is. See `IMPL-DEC-007`:
`scan_momentum_signals` returns immediately after its ticker loop, so the
real function can be run to completion in a test; `scheduled_multi_strategy_scan`
unconditionally continues past its loop into flow-fetch, signal
persistence, a second (SELL/distribution) scan pass, and a full-universe
watchlist pass, none of which this task touches. Building a harness for all
of that would be disproportionate to a task explicitly framed as
"deliberately minimal." Confidence in that call site instead rests on
direct inspection confirming it is textually the same 4-line guard, in the
same position relative to the same `len(df) < N` check, as the one proven
correct by `tests/test_scanner_freshness_guard.py`.

## Test output (named tests, new/changed files)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && ./.venv/bin/python -m pytest -q tests/test_freshness_guard.py tests/test_scanner_freshness_guard.py tests/test_monitor_freshness_guard.py tests/test_monitor_kernel_exits.py tests/test_nr7_live_pipeline_e2e.py tests/test_scanner_vpin_gate.py tests/test_monitor_exit_review.py tests/test_bearish_signal_path.py'
```
```
.........................................................                [100%]
57 passed in 0.83s
```
(Post-cold-review count: 42 pre-fix + 4 new `scan_distribution_signals`
freshness tests + 11 `test_bearish_signal_path.py` tests whose fixtures the
fix required updating — see "Cold review" below.)

## Regression run (full suite)

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python -m pytest -q'
```
```
1269 passed, 1 skipped in 24.03s
```
Baseline (branched from `master` after P0.E2.S1.T1) was 1,248 passed/1
skipped/0 failed; +17 from this task's original new tests (9 in
`test_freshness_guard.py` + 4 in `test_scanner_freshness_guard.py` + 3 in
`test_monitor_freshness_guard.py` + 1 new test in the pre-existing
`test_monitor_kernel_exits.py`), +4 more from the cold-review fix (new
`scan_distribution_signals` freshness tests) = 1,269. The other pre-existing
files (`test_monitor_kernel_exits.py`'s other tests, `test_nr7_live_pipeline_e2e.py`,
`test_scanner_vpin_gate.py`, `test_bearish_signal_path.py`) had only their
fixture dates changed, not their test count. 0 regressions, 0 failures.

Note: a first run without `~/.local/node/bin` on `PATH` showed 4 failures
in `tests/test_value_format.py` (`FileNotFoundError: node`) — this is the
pre-existing, already-filed environment gap from `IMPL-DEC-001`; the
user-space Node install from that decision is still present on disk
(`~/.local/node`, confirmed `node --version` → `v22.14.0`) but was not on
`PATH` for this session's non-interactive shell. Not a regression from this
task; re-running with the documented `PATH` addition confirms 0 failures.

## Gate-script output

```
wsl.exe -d Ubuntu -- bash -lc 'cd /home/tjies/workspace/projects/5001 && export PATH="$HOME/.local/node/bin:$PATH" && ./.venv/bin/python scripts/pre_merge_gate.py'
```
```
[PASS] QG-1 full test suite — 1269 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 37 clean, 0 violations, 0 allowlisted (unaffected by this task; no scheduler-job surface touched)
[PASS] QG-5 evidence presence — 8 done-task card(s) checked, all have evidence

GATE: PASS
```
(Re-run post-cold-review-fix; matches the 1,269 regression count above.)

## Architectural invariant check (ADR-001 §"LLM agent firm remains advisory")

This task touches `engine/freshness.py` (new, pure deterministic date/
calendar math — no LLM, no `engine/agent_firm/` import), `monitor.py`, and
`scheduler/scanner.py`. Grepped the diff for any reference to
`engine.agent_firm`, `firm.py`, or LLM/prompt code — none. The guard sits
strictly upstream of and outside the one existing Agent Firm touchpoint in
`monitor.py` (`_agent_confirms_exit`, called only from
`check_all_open_trades`'s swing-trend branch on `R3_ADX_FADE`/
`R4_DISTRIBUTION` closes): a stale trade now short-circuits with `continue`
*before* `_evaluate_swing_trend` ever runs, so Agent Firm is never invoked
on a stale-bar trade at all, and when it is invoked (fresh trade, kernel
already decided CLOSE), its role is unchanged — confirm or veto a
deterministic decision, fail-open on error, never originate a fact or
decision itself. Production Engine (the scan loops, the exit kernel, the
freshness guard) remains the sole source of what's fresh, what closed, and
why; Agent Firm's only touchpoint continues to be a downstream veto on an
already-computed deterministic decision.

## Documentation delta

None. Not operator-facing (no Telegram message text changed, no ops
checklist references scan/monitor freshness) and not contract-changing
(the guard adds a skip path; it does not change any existing schema or
public function signature).

## Decision entries filed

- `IMPL-DEC-007` — test-coverage scope for `scheduled_multi_strategy_scan`'s
  freshness guard (relies on pattern-equivalence with the tested
  `scan_momentum_signals` guard, not independent end-to-end proof).

## Self-review (EXEC-001 §3.1 step 3, checklist §5.1/§5.2/§5.4)

- Diff does only what the task card says: the guard, at the three call
  sites the intent names ("scan loops + monitor"), plus the tests needed to
  prove it and the fixture-date fixes those tests' pre-existing neighbors
  needed to keep passing under the new guard. No drive-by changes.
- No FROZEN surface touched; Phase 0 stays legacy-only.
- No new dependency, framework, or plugin point (ER-12) — `is_fresh()` is a
  small pure function reusing the existing `engine.calendar_filter` module.
- Error-path direction is fail-closed on uncertain data (skip a stale bar,
  don't evaluate it), matching the polarity established by
  `P0.E1.S1.T1`'s VPIN guard and `P0.E2.S1.T1`'s coverage-fallback guard.
- Task exists verbatim in PLAN-001 §3 (`P0.E2.S1.T2 ... [H-3]`); no
  forward-phase work smuggled in (ER-2) — the full Certifier-based flag is
  explicitly left to Phase 1 in both the task card and `engine/freshness.py`'s
  own module docstring.

## Cold review (EXEC-001 §4)

**Performed 2026-07-30, as an independent reviewer pass.** Scope verified:
diff isolated to `engine/freshness.py` (new), the three named call sites in
`monitor.py`/`scheduler/scanner.py`, and their tests/fixtures — no FROZEN
surface, no forward-phase work smuggled in.

**1 Major finding, fixed before merge.** `EVIDENCE.md`'s own §Deliverable
claimed `scheduled_multi_strategy_scan`'s "SELL/distribution loop shares
the same `ohlcv_map` (no second read)" and therefore needed no separate
guard. Reading `scheduler/scanner.py` directly (not trusting the prose)
showed this is false: `scan_distribution_signals()` (`scanner.py:1171`) is
an independent function, called separately at `scanner.py:1501`, with its
own `ohlcv_map.get(ticker)` read driven by its own `stockbit_flow` DB query
— not the adaptive-selection loop's already-guarded ticker set. It read
`df['close'].iloc[-1]`/`iloc[-5]` and could fire a SELL/distribution signal
off a stale bar with **zero freshness check** — the exact H-3 failure mode
this task exists to close, on a call site the bundle believed (incorrectly)
was already covered.

**Fix:** `is_fresh()` guard added to `scan_distribution_signals()`'s loop
(skip + count + one aggregate `[scan_distribution] N ticker(s) skipped
this run (stale last bar)` warning — same idiom as the other three sites).
4 new named tests added to `tests/test_scanner_freshness_guard.py`
(fresh/stale/both session boundaries), driving the real function
end-to-end — this call site now has direct integration coverage, superior
to the pattern-equivalence-only confidence `IMPL-DEC-007` documents for its
sibling call site. `tests/test_bearish_signal_path.py`'s pre-existing
`scan_distribution_signals` fixtures used a fixed 2026-06-05 OHLCV date,
now stale relative to the new guard regardless of `trade_date`; its
`_make_ohlcv()` helper was switched to end on the real current date (same
idiom as this task's other fixture-date fixes). `IMPL-DEC-007` updated with
a correction note (§8 append-only). Full suite and gate script re-run after
the fix — see updated output below.

Adversarial checks beyond the shipped tests: confirmed `scan_distribution_signals`
is reachable from `scheduled_multi_strategy_scan` unconditionally (not
gated behind the adaptive-selection loop finding anything), confirmed no
other direct `ohlcv_map` read exists in `scheduler/scanner.py` outside the
four now-guarded sites (`grep -n "ohlcv_map\(\.get\|\[\)" scheduler/scanner.py`
against the full call graph), and confirmed the boundary tests
(`ONE_SESSION_AGO`/`TWO_SESSIONS_AGO`) use the same IDX-calendar-aware
helper as the already-proven `scan_momentum_signals` tests rather than a
new, unverified date computation.

No other findings. Functional correctness of the three originally-shipped
guard sites was independently re-derived from source (not re-read from the
bundle's prose): each `is_fresh()` call sits immediately after the
pre-existing history-length guard at its site, `continue`/early-return
shape matches the surrounding function's existing control flow, and
`check_all_open_trades`'s `stale` branch is checked before any
persist/close/alert call, not after.

**Time-gate note:** as with T5/T6/P0.E2.S1.T1, this cold review occurred in
the same continuous session as the original implementation — EXEC-001
§4.1's "next working session" time-gate was not literally satisfied; the
operator explicitly directed continuation in this session.
