# ZCode brief — price-learning cross-sectional ranking model (2026-10-06)

**Task 1 of 2 in the owner's queue.** Task 2, exits and position management, is briefed after this
one reports.
**Category:** Research (P-M). **Owner-requested 2026-10-06.**
**Branch:** create `research/ml-rank-2026-10` from `origin/research/new-order-2026-09-30` (062999d).
Push only that branch.
**Separate from Broad search v2.** That has its own reviewer and branch
(`research/broad-search-v2-zcode`). Do not touch it, and do not count this work inside it.

## Why

Six months of P-M work tested 266+ candidates; almost all were price patterns, and all were null or
anti-edges. The one durable price result is risk-based: volatility exclusion
(FWD-PM-VOLEX-001, in forward test). No one has tested whether a **learning model on price and volume
only** can rank stocks cross-sectionally better than a simple rule.

The honest prior is that it ends up close to "low volatility plus momentum". The value is in finding
that out cleanly, under the same governance as everything else.

## Mode: two gates, and you stop at each

- **G0, predeclare and freeze.** Write the predeclaration, the drivers and the PIT (point-in-time)
  tests. Run the tests, which read no outcomes. Freeze everything (sha256), push and **stop**. No
  model is fit on returns before G0 is approved.
- **G1, single run.** Only after the owner, via the planner, approves G0: one run, one RESULT, one
  VERDICT. Then stop for review. Re-running with changed settings after seeing results is forbidden;
  any fix after G1 is a new, disclosed, re-frozen run that counts as a new trial.

## Specification (draft it into the predeclaration; you may tighten, not loosen)

**Data**
- `research.rulecard.data.load_extended_ohlcv(issuance=True)`, 2000→latest final bar.
- Record the dataset fingerprint and the git commit via `research/tracking.py`.

**Universe at each rebalance**
- Top 150 by 60-day average turnover (ADV60), close ≥ 50, traded on at least 18 of 20 sessions.
- This is the same universe as the 2026-09/10 pattern studies.

**Rebalance and portfolio**
- Monthly, on the first session of each month.
- Features use data through the prior session's close only.
- Hold one month, entering at the open of the first session.
- Book: long-only top quintile, equal weight. Also report the top 30 names.

**Features** (price and volume only, each a cross-sectional rank in [0, 1]; list them all in the
predeclaration; ≤ 15 in total):
- returns over 5, 21, 63 and 126 sessions, and 12-month-minus-1-month momentum
- Parkinson-60 volatility (from daily highs and lows)
- 20-day realized volatility
- the maximum daily return over 21 sessions (a "lottery" measure)
- distance to the 52-week high
- log ADV20
- ADV20 / ADV120 (volume trend)
- 252-day beta to IHSG
- idiosyncratic volatility relative to IHSG
- ATR14 / close

**Target**
- The cross-sectional rank of the next month's open-to-open return.

**Models** (a fixed, small grid; ≤ 6 configurations in total across M1 and M2; list them in the
predeclaration):
- **M0, baseline (no learning):** the equal-weight average of two ranks, low Parkinson-60 volatility
  and 12-1 momentum.
- **M1:** ridge regression on the ranks (2–3 alpha values).
- **M2:** `sklearn` `HistGradientBoostingRegressor`, shallow: max_depth ≤ 3 and early stopping off
  (2–3 configurations). LightGBM is not installed; do not add dependencies.

**Splits** (walk-forward, refit yearly on an expanding window):
- Train from 2001.
- **Validation: 2016-01 to 2021-09.** The single configuration of M1 and of M2 is chosen here on mean
  monthly rank IC (Spearman correlation between predicted rank and realized return rank).
- **Test: 2021-10 to the latest complete month,** read once at G1.
- **Embargo:** the training labels for a refit at year Y end at least one full month before the first
  prediction month.

**Costs**
- 0.60% round trip, charged on actual monthly turnover.

**Benchmarks** (both, per D-065 §3):
- the equal-weight liquid base book: the same universe, all names
- IHSG

## Statistics and pass bar (fixed at G0)

**Report** for M0, M1 and M2, on validation and on test:
- mean monthly rank IC and its t
- top-quintile return net of costs minus the equal-weight base book, with Newey-West t (lag 3)
- hit rate
- turnover
- the worst 12 months
- a **year-by-year table, mandatory**

**Overfitting:**
- PBO (probability of backtest overfitting) via `research/statistics.py::pbo_cscv`, over the full
  configuration grid's monthly validation returns.
- Deflated Sharpe ratio, at the multiplicity N then in force.

**A model PASSES only if all of these hold on the TEST period:**
1. Net top-quintile excess over the equal-weight base book is > 0, with Newey-West t ≥ the deflation
   bar at the current N. That bar is 3.06 at N=266; compute the exact value at G0 with the repo's
   method and freeze it.
2. It beats M0, paired monthly differences t ≥ 2. Otherwise the learning adds nothing.
3. PBO < 0.5.
4. The result is not carried by one calendar year (leave-one-year-out stays > 0).
5. Positive versus IHSG too (reported, not gating).

**If only M0 passes, that is a valid finding.** It says the simple rule is the edge; report it as
such.

## Governance (draft, do not file)

**Hypothesis**
- This is a new mechanism, "learned combination of price/volume features", which no existing family
  covers.
- Draft a registration as **HYP-PM-0015** and a family proposal (e.g. `Price-Learning {L1}`) in
  `docs/research_programs/P-M/ml_rank/REGISTRATION_DRAFT.md`.
- Draft the matching DECISION_LOG entry text too.
- **Do not edit `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md` or `DECISION_LOG.md`.** The owner
  files them at G0. Families widen only by a formal amendment and are never narrowed (D-028).

**Code and boundaries**
- Code lives under `research/` or `docs/research_programs/P-M/ml_rank/`, research-side only.
- No production imports (`tests/test_architecture_boundary.py`), and no writes to production or
  fence tables.
- Seeds fixed and recorded.
- Run `pytest` on any test you add, plus the boundary tests.

**PIT tests at G0** (they read no outcomes):
- (a) Every feature at rebalance date D must be bit-identical when the panel is truncated at D.
- (b) Training labels never overlap the prediction month (embargo check).
- (c) The universe at D uses only data up to D−1.

## Deliverables

**G0: commit, push, stop.**
- `docs/research_programs/P-M/ml_rank/` containing:
  - `PREDECLARATION.md` and its `.sha256`
  - the driver(s)
  - the PIT test file
  - `REGISTRATION_DRAFT.md`
  - `HANDOFF_G0.md`: what is frozen, the deflation bar used, the configuration grid, and the
    estimated runtime

**G1, after approval: commit, push, stop.**
- `RESULT_<utc>.json`
- `VERDICT.md`, with the year-by-year table, the PBO and the comparison to M0
- `HANDOFF_G1.md`

## Hard constraints

- No production changes. No service restarts. `logs/TELEGRAM_OFF` stays.
- Do not touch `~/jurnal26` or `research/broad-search-v2-zcode`.
- Never print secrets.
- Work from the research DB snapshot or read-only connections (`data.db.connect(read_only=True)`).
