# Evidence — P0.E2.S1.T1

**Date:** 2026-07-30
**Trace tag:** [M-5]
**Branch:** `p0/e2-s1-t1-eod-coverage-date-guard`

## Investigation

`screener_jobs.run_eod`'s coverage-fallback path (`# ── Coverage fallback: insert
neutral entries for tickers without daily_screen data today`) exists to give
every ticker a `daily_screen` row for `trade_date`, even ones the intraday
scan pass didn't produce one for. Before this task, the per-ticker fallback
took `df.iloc[-1]` — the ticker's *most recent available* OHLCV bar — and
wrote it into `daily_screen` **stamped with `trade_date`**, with no check
that the bar itself was actually dated `trade_date`. A ticker whose OHLCV
history stopped days earlier (suspension, feed gap, delisting-in-progress)
would silently get a fabricated "today" row built from old data — exactly
the kind of dishonest baseline P0.E2 exists to close out before v2
shadowing starts (PLAN-001 §3, Phase 0 preamble).

Confirmed from the pre-fix diff (see `git show` below): the old code had
*zero* date-comparison logic between the `len(df) < 20` history-length check
and building the row — it went straight from "enough rows exist" to
"compute a row from the last one." There was no code path that could have
caught a stale-last-bar ticker; every test in this bundle that exercises the
`'stale'` branch is therefore a genuine new-behavior test, not a
already-passing assertion.

## Deliverable

- `screener/screener_jobs.py` — extracted the per-ticker fallback computation
  (previously inline in `run_eod`'s loop) into a module-level
  `_coverage_fallback_row(ticker, df, trade_date)` helper, unit-testable in
  isolation (mirrors the existing `_eod_calendar_cleanup` extraction in the
  same file). Added the date guard: `str(last['date']) != trade_date` now
  short-circuits to `(None, 'stale')` before any row is computed. The
  pre-existing `len(df) < 20` guard is unchanged (`'insufficient_history'`).
  `run_eod`'s loop now tallies a `stale_skipped` count alongside the
  pre-existing `fallback_ok` count, and logs one aggregate WARNING line when
  `stale_skipped > 0` (same shape as the pre-existing `fallback_ok` INFO
  line) — see `IMPL-DEC-006` for why aggregate-log over silent-skip or
  per-ticker-alarm.
- `tests/test_coverage_fallback_date_guard.py` (new, 4 tests).

## Test output (named tests)

```
wsl.exe -e bash -lc 'cd /home/tjies/workspace/projects/5001 && PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q tests/test_coverage_fallback_date_guard.py -v'
```
```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.0.3, pluggy-1.6.0
collected 4 items

tests/test_coverage_fallback_date_guard.py::test_stale_last_bar_is_skipped_not_reported_as_trade_date PASSED
tests/test_coverage_fallback_date_guard.py::test_fresh_last_bar_still_computes_a_row PASSED
tests/test_coverage_fallback_date_guard.py::test_insufficient_history_skipped_unchanged_from_prior_behavior PASSED
tests/test_coverage_fallback_date_guard.py::test_missing_ticker_dataframe_skipped PASSED

============================== 4 passed in 0.72s ===============================
```

New tests, calling the extracted `_coverage_fallback_row` directly with
synthetic OHLCV frames (no DB needed — same idiom as
`tests/test_eod_purge.py`'s `_eod_calendar_cleanup` tests):
- Last bar dated before `trade_date` → `(None, 'stale')`, no row computed —
  the new guard behavior; against the pre-fix inline code this scenario
  would have produced a valid row instead (see Investigation above and the
  diff below).
- Last bar dated exactly `trade_date` → unchanged behavior, row computed
  with the same fields/values the pre-fix code produced.
- Fewer than 20 bars of history → `(None, 'insufficient_history')` —
  pre-existing guard, confirmed untouched by this task.
- No OHLCV history at all (`df=None`) → `(None, 'insufficient_history')`.

## Diff confirming the pre-fix code had no date check

```
$ git diff -- screener/screener_jobs.py
...
-                    df = grouped.get(ticker)
-                    if df is None or len(df) < 20:
-                        continue
-                    last = df.iloc[-1]
-                    avg_vol = df['volume'].tail(20).mean()
-                    vr = last['volume'] / avg_vol if avg_vol > 0 else None
...
+                    row, skip_reason = _coverage_fallback_row(ticker, grouped.get(ticker), trade_date)
+                    if row is None:
+                        if skip_reason == 'stale':
+                            stale_skipped += 1
+                        continue
```
(full diff captured in the branch commit) — the removed lines show the
direct jump from the history-length check straight to `df.iloc[-1]`, with no
date comparison anywhere in between.

## Empirical pre-fix/post-fix verification (independent of the diff read)

Rather than relying on reading the diff alone, extracted `master`'s verbatim
pre-fix inline block (`git show master:screener/screener_jobs.py`, lines
208-224) into a standalone script and ran it against the identical
stale-last-bar input used by
`test_stale_last_bar_is_skipped_not_reported_as_trade_date` (last bar
`2026-07-20`, `trade_date="2026-07-30"`):

```
$ .venv/bin/python /tmp/verify_pre_fix_behavior.py
OLD (pre-fix) logic result for a stale-last-bar ticker: {'close': 102, 'signal': 'neutral', 'last_date': '2026-07-20'}
CONFIRMED: pre-fix code produces a row from a stale bar with no date check.
Post-fix _coverage_fallback_row() on the identical input returns (None, 'stale') — see test file.
```

Confirms the guard is genuine new behavior: the pre-fix code would have
written `{close: 102, signal: 'neutral'}` into `daily_screen` under
`2026-07-30` from a bar 10 days stale; post-fix, the identical input is
skipped and counted in `stale_skipped` instead.

## Regression run (full suite)

```
wsl.exe -e bash -lc 'cd /home/tjies/workspace/projects/5001 && PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q'
```
```
1248 passed, 1 skipped in 22.89s
```
Baseline (branched from `master` after P0.E1.S2.T6) was 1,244 passed/1
skipped/0 failed; +4 from this task's new tests, 0 regressions, 0 failures.

## Gate-script output

```
wsl.exe -e bash -lc 'cd /home/tjies/workspace/projects/5001 && PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python scripts/pre_merge_gate.py'
```
```
[PASS] QG-1 full test suite — 1248 passed, 1 skipped
[PASS] QG-4 schema drift — N/A (Phase 1 deliverable)
[PASS] QG-9 grep-audits — AN-8: 37 clean, 0 violations, 0 allowlisted (unaffected by this task; no scheduler-job surface touched)
[PASS] QG-5 evidence presence — 7 done-task cards checked, all have evidence

GATE: PASS
```

## Documentation delta

None. Grepped `docs/ops/*.md` for any reference to the coverage-fallback
path or `daily_screen`; none exists, so there is no operator-facing
checklist to update (same conclusion reached for the equivalent check in
P0.E1.S2.T6's evidence).

## Decision entries filed

- `IMPL-DEC-006` — stale-skip visibility (aggregate log line, not silent or
  per-ticker) and the helper-extraction shape (mirrors `_eod_calendar_cleanup`),
  both OPEN-latitude implementation choices (EXEC-001 §7).

## Self-review (EXEC-001 §3.1 step 3, checklist §5.1/§5.2/§5.4)

- Diff does only what the task card says: the date guard, plus the
  extraction needed to make it independently testable. No drive-by changes
  — the pre-existing unused `import numpy as _np` inside the same `if
  missing:` block was left untouched (out of this task's scope).
- No FROZEN surface touched; Phase 0 stays legacy-only per PLAN-001 §3
  preamble — no v2 machinery introduced.
- No new dependency, framework, or plugin point (ER-12).
- Error-path direction is fail-closed on uncertain data (skip, don't
  fabricate), matching the polarity established by P0.E1.S1.T1's VPIN guard.
- Task exists verbatim in PLAN-001 §3 (`P0.E2.S1.T1 ... [M-5]`); no
  forward-phase work smuggled in (ER-2).

## Cold review (EXEC-001 §4)

**As reviewer role:** read the diff from the checklist (§5.1/§5.2/§5.4), not
from memory of writing it. Scope: isolated to `screener/screener_jobs.py`'s
coverage-fallback block + one new test file + decision/evidence docs; no
other module touched, no FROZEN surface, no forward-phase (Phase 1+) work.
Functional correctness independently re-derived from source (not assumed
from the task's own claim): confirmed by extracting and running the
verbatim pre-fix logic against the same stale-bar input the new tests use
(see "Empirical pre-fix/post-fix verification" above) — the pre-fix code
provably fabricates a row from a 10-day-stale bar; post-fix it is skipped.
All 4 new tests independently re-run, full suite re-run (1,248/1,
0 failed), gate script re-run (PASS). 0 findings.

**Process note (time-gate deviation, same pattern as P0.E1.S2.T5/T6):**
this cold review occurred in the same continuous session as the
implementation commit — EXEC-001 §4.1's "next working session / one sleep
or run-cycle" gate was not literally satisfied. The operator explicitly
directed single-session execution for this task in this session's
instructions and is aware of the deviation.

## Verification commands

```
wsl.exe -e bash -lc 'cd /home/tjies/workspace/projects/5001 && PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q tests/test_coverage_fallback_date_guard.py -v'
wsl.exe -e bash -lc 'cd /home/tjies/workspace/projects/5001 && PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python -m pytest -q'
wsl.exe -e bash -lc 'cd /home/tjies/workspace/projects/5001 && PATH="/home/tjies/.local/node/bin:/usr/bin:/bin:/home/tjies/.local/bin" .venv/bin/python scripts/pre_merge_gate.py'
```
