# stockbit_flow_bars Backfill — Correctness Fix & Regression Record (2026-08-21)

**Date:** 2026-08-21 (09:00–09:25 WIB) · **Authority:** operator tasking *"FIX THE BACKFILL
CORRECTNESS BUG NOW"* (Research Edge scope only). **Constraints honored:** no OFI, no cont_k,
no HYP-PM-0002 statistic or power analysis, no hypothesis registration, no 309-day launch.
HYP-PM-0002 parameters, universe definition, thresholds, registration state, and power
assumptions are untouched.

---

## 1. The bug — original incorrect predicate

The bars backfill runners (`scratchpad/backfill_history.py`,
`scratchpad/backfill_flow_5liquid.py`) decided "this (ticker, date) cell is already done"
with a query against the **summary** table:

```sql
SELECT 1 FROM stockbit_flow WHERE ticker=? AND trade_date=?
```

**Why that is wrong for a `stockbit_flow_bars` backfill:** `stockbit_flow` can exist while
`stockbit_flow_bars` is missing. Concretely, the certified July 2026 summary backfill
(122 dates × 79 IDX80 names, via `backfill_stockbit_flow_gap.py`, which by design writes
ONLY `stockbit_flow`) left every one of those cells with an activity-bearing summary row and
**zero bar rows**. Under the old predicate each such cell tested "complete" and was skipped
permanently — a full backfill would have reported success while handing back a panel with
the largest IDX80 names systematically absent.

**Blast radius:** the 2026-08-20 bounded soak (30 minutes) proved **9,577** ticker/date cells
in the 309-day window (2025-01-02 → 2026-04-27) would be silently skipped while still missing
bars, including historical IDX80 bars (tasked figure). The fix session's own bounded
measurement of the same defect class recorded **9,341** cells
(`tools/flow_bars_gap.py` docstring; two passes at slightly different DB states — same
conclusion, thousands of cells). After the 2025-01-06 fixture recovery (−79) the count stood
at **9,262**; after the 2026-08-21 resume test (−4 more on 2025-01-07) it stands at
**9,258**. Direction and magnitude are unambiguous in every pass.

## 2. Corrected completion criterion

`tools/flow_bars_gap.py` (new module, both runners now call it):

A (ticker, trade_date) cell is **complete** iff either

1. `stockbit_flow_bars` has ≥1 row for it — the bars were actually fetched; **or**
2. its `stockbit_flow` summary row records a *genuinely empty session*
   (`COALESCE(buy_lot,0)=0 AND sell_lot=0 AND buy_freq=0 AND sell_freq=0`) — a
   successfully-queried session with zero traded bars.

Everything else — including **activity-bearing summary with no bars** (the defect) and
**never-fetched cells** — is **incomplete** and must be (re)fetched. `stockbit_flow` alone is
never again accepted as evidence that bars exist. No sentinel/fake bar rows are written for
empty sessions. Safety basis: across the whole window, "zero-activity summary" and "no bars"
agree exactly (0 disagreements), so the empty-session shortcut cannot mask a real gap.

Regression tests: `tests/test_flow_bars_gap.py` — 13 cases including the defect case
(activity summary, no bars ⇒ INCOMPLETE), null-column safety, bars-wins, other-date
non-satisfaction, order preservation. **13/13 pass** (server venv, 2026-08-21).

The only remaining summary-table predicate in a backfill is
`backfill_stockbit_flow_gap.py:117` — correct there, because that script's deliverable IS
the summary table.

## 3. Regression fixture — 2025-01-06 (contract A–G)

Soak-era state (verified read-only against the pre-fix DB snapshot, local copy frozen
2026-08-15): universe 958 active tickers; on 2025-01-06 exactly **79 IDX80** names carried
activity-bearing `stockbit_flow` rows with **zero** `stockbit_flow_bars`; 0 bars on the date.
(Tasking additionally described flow coverage for all 958; the snapshot shows the summary
backfill had populated 79 IDX80 rows at soak time — the full-universe summary rows for the
date were completed by the fixture fetch itself, below.)

| # | Check | Result |
|---|---|---|
| A | 79 IDX80 defect cells detected **incomplete** by new predicate | **PASS** — all 79 selected (plus 879 never-fetched = 958); old predicate would have skipped exactly those 79 |
| B | Fetch the missing bars | **DONE** 2026-08-20 20:32:31–21:18:59 WIB (prior session, fixed predicate live): 958 cells fetched ≈2.9 s/cell; 842 names wrote 282,070 bar rows; 116 wrote legitimately-empty summaries. **79/79 IDX80 recovered** |
| C | Completed cells skipped, no vendor calls | **PASS** — production `main()` re-run for the date with `fetch_flow` monkeypatched to raise: `wrote=0 skipped=958 no-data=0` in 0.1 s, **0 fetch attempts** |
| D | Legitimate zero-bar sessions remain complete | **PASS** — 116 empty-session cells among the 958 skipped (any misclassification would have tripped the neutered fetch); unit-tested |
| E | No duplicate ticker/date/session records | **PASS** — 0 duplicate flow rows, 0 duplicate bar rows, 0 duplicate `bar_time` within session (PKs `(ticker,trade_date)` / `(ticker,trade_date,bar_time)` also structurally forbid them) |
| F | `PRAGMA quick_check` | **PASS** — `ok` (4.36 GB live DB) |
| G | Exact before/after counts | flow rows 79 → **958**; bars tickers 0 → **842** (+116 empty = 958/958 complete); defect cells on date 79 → **0**; window defect 9,341 → **9,262** (−79, exact) |

No unrelated historical dates were touched by the fixture (single-date scope
`FLOW_DATE_FROM/TO`); integrity re-verified after every write phase.

## 4. Interruption / resume test (2025-01-07, budget-bounded)

Two bounded invocations of the production runner (`FLOW_TICKERS=ALL`, single date,
`BUDGET_S=90`):

- **Run 1:** `wrote=14 skip=0` → **"BUDGET hit mid-date … safe stop (last cell committed)"**.
  Durable per-cell commits; 13 bar cells + 1 legitimately-empty session (ABDA) stored.
- **Run 2 (restart):** `wrote=13 skip=14` — the 14 completed cells were skipped **based on
  bars state** (13 bars-backed + 1 empty-session), and the run resumed at the **next
  incomplete cell** (ADRO — an activity-summary-no-bars defect name, correctly treated as
  incomplete), then AKRA + 11 further names.
- **No duplicate writes:** all 13 run-1 bar cells bit-identical after run 2 (4,355 rows
  unchanged); 0 duplicate rows; `quick_check ok`; the empty session was skipped, not
  refetched.

## 5. 5-hour invocation boundary (architecture, no long job run)

`scratchpad/backfill_flow_5liquid.py` (the designated full-universe runner via
`FLOW_TICKERS=ALL`) now enforces:

- **max 5 h per invocation** — `HARD_CAP_S = 5*3600`; `BUDGET_S` (env) is clamped to it;
- **budget check inside the ticker/cell loop** (2026-08-21 fix — previously date-only,
  which could overshoot a 5 h deadline by most of a ~50 min full-universe date);
- **safe shutdown before the deadline** — `CELL_MARGIN_S=60` stops *starting* new cells near
  the boundary; the in-flight cell still fetches and commits;
- **durable per-cell commits** — `_write()` commits each cell (pre-existing);
- **checkpoint/report on exit** — always emits `PASS END` + `CHECKPOINT` lines with
  wrote/skipped/no-data and budget usage;
- **resume from DB state** — gaps recomputed per run via `tools.flow_bars_gap`; no cursor
  file; **no reliance on ticker ordering**; **no reliance on `stockbit_flow`** for completion.

Not run: any multi-hour job (per tasking). `scratchpad/backfill_history.py` (legacy IDX80
Jan–Apr 2026 campaign, ≈4.3 h total window) keeps its original loop; it is not the future
full-universe runner.

## 6. Planning figures (unchanged)

Measured planning estimates stand: **868 names ≈ 142 h / 5.9 days; 958 names ≈ 157 h /
6.5 days.** The obsolete 51–68 h estimate is NOT restored. Current window state
(2026-08-21, post-validation): 309 dates × 958 = 296,022 cells; 5,566 complete;
290,456 to fetch (of which 9,258 are old-bug defect cells); broad-coverage days in window: 1
(2025-01-06).

## 7. Day 1 launch command (recorded only — NOT executed)

```bash
cd /home/tjiesar/idx-walkforward-5001
FLOW_TICKERS=ALL FLOW_DATE_FROM=2025-01-02 FLOW_DATE_TO=2026-04-28 BUDGET_S=17400 \
  PYTHONPATH=. nohup venv/bin/python3 scratchpad/backfill_flow_5liquid.py \
  >> backfill_flow_bars_day1.log 2>&1 &
```

`BUDGET_S=17400` (4 h 50 m) stays inside the 5 h hard cap; each subsequent day re-issues the
same command and resumes purely from DB bars state. ~5,800 cells/invocation → ~33
invocations ≈ the 157 h / 6.5-day estimate at 958 names.

**Lineage:** [[STOCKBIT_FLOW_BARS_BACKFILL_STATE_2026-08-20]] ·
`STOCKBIT_FLOW_BARS_HYP_PM_0002_COVERAGE_AUDIT.md` · `tools/flow_bars_gap.py` ·
`tests/test_flow_bars_gap.py` · `STOCKBIT_FLOW_BACKFILL_FEASIBILITY.md`.
