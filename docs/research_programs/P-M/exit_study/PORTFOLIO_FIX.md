# PORTFOLIO_FIX — G1-bis specification: fix the portfolio simulation only (2026-10-07)

**Authority:** brief `ZCODE_BRIEF_EXIT_STUDY_G1BIS_PORTFOLIO_2026-10-07.md` (fix/telegram-curation @
6dbcd3b), owner-approved 2026-10-07. **Scope:** a disclosed, single re-run of the PORTFOLIO layer
only. The three frozen artifacts (`PREDECLARATION.md`, `exit_study.py`,
`test_pit_exit_study.py`) and their sidecar are untouched and must verify before and after.
G1's trade-level results stand unchanged. **This mini-freeze covers four NEW files:**
`PORTFOLIO_FIX.md`, `portfolio_v2.py`, `test_portfolio_v2.py`, `g1bis_run.py` (hashes in
`PORTFOLIO_FIX.sha256`; verified before the run and at the final commit).

## Why the G1 portfolio layer is invalid (restated from the planner review)

1. Position arms were not modelled (P0–P4 produced identical portfolios — single-exit
   approximation). 2. No cash or leverage limit (1%-risk sizing on tight stops → negative cash,
   DD magnitudes like −15.6M, 43/2,253 trades taken). 3. The recommendation rule's drawdown
   guard was therefore vacuous; "unstopped variants went bust" was a sizing artifact.

## Specification (frozen)

- **Equity book.** Start 1.0. **Cash may never go negative.** Daily mark-to-market on closes.
  At most 10 open positions; a position occupies a slot from its entry day through its exit day
  (same-day exit frees the slot for a same-day entry, as in G1). Signals processed in `(t1,
  ticker)` order.
- **Base size of a new position (first fill):**
  `qty = min(1%·equity/(entry − stop), 20%·equity/entry, cash/(entry·(1 + buy costs)))`, with
  buy costs = 0.15% + 0.20% slippage. Equity = cash + mark-to-market **at the prior close**.
  E-BRK sizes on its own frozen stop; arms without a stop (X0, X6) still size on the
  structure-stop distance. No position may exceed 20% of equity at entry (enforced by the
  min-leg).
- **Skip rules and their labels.** If 10 positions are open → skip, count `full`. If the
  min-sized notional (`qty·entry`) is below 2% of equity → skip: count `cash` when the binding
  (smallest) leg is the cash leg, else `tiny` (the 1%-risk leg can itself be sub-2% when the
  stop is very deep). `qty ≤ 0` counts `tiny`.
- **Legs, per the frozen arm definitions.** `portfolio_v2.simulate_legs` reconstructs each
  trade's legs — entry, P1 second half, P2 add, P3 add, P4 top-up buy and top-up sale, exit —
  as a faithful transcription of the frozen `simulate_trade` day-loop (same same-day
  precedence, same gap rules, same arming rules, including the frozen bottom-of-loop P4 fill
  block). Canonical quantities are the frozen units (1.0 base, 0.5 adds); the portfolio scales
  them. Roles are tagged so the engine can size each leg class.
- **P1 second half:** half of the base qty at the zone-top fill and half at the zone-low fill
  (if it fills within the frozen cancel window); cash-limited (buy what cash allows, floor 0);
  no 30% cap and no skip floor — the halves ARE the position (declared convention).
- **P2 / P3 / P4 adds and the P4 top-up:** desired = 50% of base qty, capped so the position's
  total notional at the add's fill stays ≤ 30% of equity (equity at prior close), and limited
  to available cash; if the trimmed add notional is below 1% of equity, skip the add (counted).
  The P4 top-up sells on its own fill day and price (actual held top-up quantity), the rest
  exits with the core at the frozen exit day/price/reason.
- **Costs per fill:** 0.15% buy + 0.20% slippage on buy notional; 0.25% on sale notional (as
  frozen).
- **Reported per population (E-SN, E-RND, E-BRK) × era × arm:** CAGR (two conventions, below),
  max drawdown, worst rolling 250 sessions, final equity, signals, taken, skipped
  (full/cash/tiny), average gross exposure (mean of long-notional/equity at close over the
  era's own span), and % of era-span days with 10 open positions.
- **CAGR conventions (declared):** `cagr_full` annualizes over the full panel horizon
  (len(index)/250 — the G1 convention, for side-by-side comparability with the superseded
  tables); `cagr_era` annualizes over the era's own session span (E1: 2001-01..2021-09;
  E2: 2021-10..2026-09). Max DD / worst-250 are computed on the full-index curve (equity is
  flat outside the era, as in G1).
- **Parity check (required gate):** for EVERY trade of every population × era × arm, the
  canonical legs' net % must equal the frozen `simulate_trade`'s `net_pct` within 1e-9
  (net % is size-free), and exit day/reason must match. Report count checked and max
  difference. Any mismatch beyond 1e-9 → STOP; write no verdict.
- **Panel pinning (declared):** the run loads the panel and truncates it to dates ≤ 2026-10-06
  — G1's exact panel horizon — so the trade set is G1's. The DB fingerprint is recorded and
  any drift vs G1's `f42275e3…` is disclosed. Population counts must equal G1's exactly
  (E-SN 3,682 / E-RND 3,682 / E-BRK 5,141) or the run stops.
- **Guard re-applied:** the frozen `recommend()` is re-used verbatim, fed G1's unchanged
  trade-level `expectancy_R` and `paired_t_vs_base` (from `RESULT_20261006T142027Z.json`) and
  the G1-bis portfolio max-DD. The addendum states explicitly whether P4 deepens drawdowns vs
  P0 in either era.

Any change to these four files after this mini-freeze re-opens G1-bis.
