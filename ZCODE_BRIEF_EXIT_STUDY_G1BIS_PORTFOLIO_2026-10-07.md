# ZCode brief — exit study G1-bis: fix the portfolio simulation only (2026-10-07)

**Branch:** `research/exit-study-2026-10` (tip `0a19fcd`). Work in the existing worktree
`~/10 Projects/idx-walkforward-exitstudy`.
**Owner-approved 2026-10-07** ("give to zcode") after planner review of G1.

## Why

The trade-level results of G1 are valid and stand unchanged: per-trade net %, R, the paired t-values,
and the P4 recommendation's statistical leg. The **portfolio simulation in `assemble_portfolio` is
invalid**, for three reasons:

1. **Position arms aren't modelled.** P0–P4 produce identical portfolios (E1: CAGR 0.137,
   max DD −0.892, 43 taken). The second tranche, the averaging-down add, the pyramid add and the P4
   top-up never reach the portfolio.
2. **No cash or leverage limit.** Sizing to 1% risk with a tight structure stop gives huge positions,
   and cash goes negative. The result is drawdowns such as −15,579,810 (X0 E1), and only 43 of 2,253
   E1 trades taken.
3. **The recommendation rule's drawdown guard was therefore vacuous.** The "unstopped variants went
   bust" statement is a sizing artifact.

## Scope

A disclosed, single re-run of the **portfolio layer only**. Do not change the three frozen files
(`PREDECLARATION.md`, `exit_study.py`, `test_pit_exit_study.py`). Their sidecar must still verify
before and after the work.

## Step 1 — mini-freeze before running (new files only)

**Write `PORTFOLIO_FIX.md`** with this specification, then its sha256 in `PORTFOLIO_FIX.sha256`.
Commit the spec, its sidecar and the new code/test files, push the branch, and only then run.

**Specification:**
- **Equity book.** Start at 1.0. **Cash may never go negative.** Daily mark-to-market on closes. At
  most 10 open positions. Signals are processed in time order (the existing `t1`, ticker order).
- **Base size of a new position (first fill):**
  `qty = min(1% of equity / (entry − stop), 20% of equity / entry, cash / (entry × (1 + buy costs)))`.
  - Equity is cash plus mark-to-market at the prior close.
  - If the resulting notional is below 2% of equity, **skip** the signal and count it.
  - E-BRK uses its own frozen stop.
  - Arms without a stop (X0, X6) still size on the structure-stop distance; that's the same sizing
    the owner would use. **No position may exceed 20% of equity at entry.**
- **Legs, per the frozen arm definitions**, using each leg's actual fill day and price from the
  frozen trade simulation:
  - **P1:** half of qty at the zone-top fill, half at the zone-low fill if it fills.
  - **P2, P3, P4:** the add or top-up is **50% of the base qty**. Cap it so the position's total
    notional stays ≤ 30% of equity at the add's fill. Limit it to available cash (if cash is short,
    buy what the cash allows; if that is below 1% of equity, skip the add).
  - **P4:** the top-up sale happens on its own fill day and price.
  - All exits use the frozen trade's exit day, price and reason.
- **Costs per fill:** 0.15% buy + 0.20% slippage on buy notional; 0.25% on sale notional. Same as
  frozen.
- **Reported per population (E-SN, E-RND, E-BRK) × era × arm:**
  - CAGR, max drawdown, worst rolling 250 sessions
  - final equity
  - signals, taken, skipped (full / cash / tiny)
  - average gross exposure, % of days with 10 positions
- **Parity check (required):** for every trade the portfolio enters, the trade's own net % recomputed
  from its legs must equal the frozen G1 `net_pct` to within 1e-9, after scaling out the size.
  Report the count checked and the maximum difference. Any mismatch beyond 1e-9 → STOP and report;
  do not write a verdict.
- **Guard re-applied:** the frozen recommendation rule's drawdown leg — an arm's max DD is not worse
  than its baseline's by more than 20% relative — evaluated with the fixed portfolio, in both eras.
  - The statistical leg (paired t ≥ 2 both eras) is taken from G1 unchanged.
  - Output: the final recommendation per arm.

## Step 2 — single run

- Implement in new files: `portfolio_v2.py` and `g1bis_run.py`, plus `test_portfolio_v2.py` covering:
  - cash never negative
  - the 20% and 30% caps
  - leg sizing for P1 to P4
  - the skip rules
  - the parity check

  You may expose leg records from the frozen simulation **only by calling it**. If legs aren't
  exposed, reconstruct them from the frozen rules in `portfolio_v2.py`, with the parity check
  proving equivalence.
- Run once, read-only data, same dataset fingerprint as G1 (`f42275e3…`); disclose any drift.
- Write:
  - `RESULT_G1BIS_<utc>.json`
  - an **addendum section appended to `VERDICT.md`**, titled "G1-bis portfolio fix (2026-10-07)". It
    states that the G1 portfolio tables are invalid (do not delete them; mark them superseded),
    shows the new tables, gives the final recommendation per arm, and says explicitly whether P4
    deepens drawdowns.
  - an update to `PRACTICE_NOTE.md` (one dated paragraph)
  - `HANDOFF_G1BIS.md`
- Commit, push, STOP.

## Hard constraints

- Do not re-run or alter trade-level G1 results.
- No changes to the frozen trio. No touching `~/jurnal26`, the registries/DECISION_LOG, production or
  other branches.
- Read-only data. Never print secrets.
