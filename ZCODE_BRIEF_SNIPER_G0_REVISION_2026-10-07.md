# ZCode brief — sniper filter G0 revision before approval (HYP-PM-0016) (2026-10-07)

**Category:** Research (P-M). **Planner review of G0 `72b4bd5`** (`research/sniper-filter-2026-10`).
**Verdict: NOT APPROVED as frozen.**

What's sound:
- the sidecar verifies, and all 12 PIT tests pass
- the population and census match G1FIX
- the bar reproduction is right

What's wrong: `g1_run.py` has defects that would make the single G1 run unreadable or open to
discretion. No outcome has been read, so this is a **disclosed pre-approval revision**:
- fix in place on the same branch
- write a new sidecar
- record the old sidecar hash in `PREDECLARATION.md` §11 "Revision 1"

It is not a re-run.

## Required fixes

**R1. The selection threshold is computed on subsets, so every window starts cold.**
`select_mask(scores[c][test_mask], …)` (and the same for validation and PBO) only sees setups inside
the subset. The first test months therefore get no trailing-250 history from validation: they fall
back, or go unselected. §5 says the threshold uses the scores of *the filled setups in the trailing
250 sessions*, whatever the split.

Fix: compute `select_mask` **once per configuration on the full score series** (every scored
setup, 2016 onward), then index into val, test and PBO. Add a test: the selection of a setup in the
first test month equals its selection computed on the full series.

**R2. The PBO matrix is mostly NaN.**
Scores exist only for prediction years ≥ 2016 (M0 included, because it is assigned inside the
refit loop). The "TRAIN+VAL months" matrix therefore has about 180 all-NaN rows. `pbo_cscv` doesn't
handle NaN: the Sharpe falls to 0, every configuration ties, and PBO is meaningless.

Fix: the PBO matrix = the 4 configurations' monthly selected-mean-R over the **validation months
only** (2016-01..2021-09, about 69 months, where all four have out-of-sample scores). Drop any month
where a configuration has no selection, and record the count. Freeze `n_splits` so that each split
has ≥ 2 rows (16 is fine at 69). Assert that there are no NaN entries before calling `pbo_cscv`.
Amend §7.5.

**R3. The pass decision must be computed, not hand-written.**
The RESULT must contain, for each configuration, booleans for conditions 1–5 and a final
`passes`.
- **Condition 4 uses the validation-chosen M1 only.** The unchosen M1 is reported but can't pass.
- `h1` and `h2` must each be > 0 (condition 3).
- Condition 5 is one grid-level PBO that applies to all configurations.
- The VERDICT copies these flags; it doesn't re-judge them.

**R4. The "also report" list isn't implemented.** It is mandatory in §7. Add to the RESULT:
1. a year-by-year table per configuration (2016 → latest): n all, n selected, mean R selected, mean
   R all, difference
2. per-feature R-quintile spreads (the univariate diagnostic) on the validation and test periods,
   reported separately
3. the robustness row: the headline (condition 1 and 2 numbers) recomputed with fill-bar exits
   (hold 0, exit on the fill bar) dropped
4. win rate (already there)

**R5. A point-in-time leak in the reference set: fill status isn't known at s.**
Ranks (§3) and the selection threshold (§5) use "filled E-SN setups with setup day in the trailing
250 sessions before s". But whether a setup at s′ < s gets filled can be decided **after** s: fills
are watched for 20 sessions. So the reference set at s includes setups whose fill hadn't happened
yet.

There's a second problem in the same place: `add_ranks` and `select_mask` take "prior" to mean
earlier *rows* in mergesort order (`hi = i`). Same-day setups (equal `pos`) therefore rank against
each other in an arbitrary, order-dependent way.

Fix:
- The reference set at s = setups with **setup pos < p(s)** (strictly earlier days, never the same
  day) **and fill bar index < p(s)**. The fill index is `f[0]` from `fill_limit`, carried in
  `_snipe_trade`, so the fill is known by the close of s−1.
- Add PIT tests:
  - a setup with s′ < s that fills after s is excluded from s's rank and threshold window
  - two same-day setups get identical reference sets, whatever their row order

**R6. The fingerprint check doesn't stop the run, and it will drift.**
§2 says drift "stops the run", but `g1_run.py` only records the fingerprint after the run. The live
DB also gains a bar every day, so a whole-DB fingerprint will no longer equal `f42275e3…` at G1.

Fix: either
- make a read-only **snapshot** of the DB now (SQLite backup API into the scratch area, not the
  repo), and record its sha256 and the snapshot fingerprint in the predeclaration, or
- use a fingerprint limited to the panel horizon (≤ 2026-10-06), if `E.dataset_fingerprint`
  supports it.

Check the fingerprint **before** any outcome is computed, and `SystemExit` on a mismatch.

**R7. Replace the IHSG feature: it's constant for most of the sample.**
There is no IHSG bar before 2021-07, so `ihsg_above_ma200` is 0.0 for all of training and most of
validation. It's a dead feature that then switches on, untrained, in test.

Fix: replace it with `mkt_above_ma200`: an **equal-weight market index** built from the panel (the
daily mean close-to-close return of the owner-screen-eligible universe, cumulated), 1.0 if above its
200-session MA at s. It's point in time and has full history. Add it to the truncation test. Keep
the feature count at 10.

**R8. The deflation bar is unresolved: the owner decides, and the default is the stricter one.**
`origin/research/broad-search-v2-zcode` `recount/RECOUNT_W0` and `CENSUS_NOTE.md` give census
**N = 561** (bar 3.2745). Hardening carries 276 (≈ 3.06). Neither recount is ratified.
- Freeze the **primary** pass bar at the stricter count: N = 561 + 4 = 565, computed exactly with
  `emax_abs_z` (≈ 3.28).
- Report the 280-count bar (3.07) as a secondary line ("would pass under the hardening count").
- If the owner rules otherwise before approval, the planner amends this line.

State in the HANDOFF which one the predeclaration freezes.

## Process

1. Same branch `research/sniper-filter-2026-10`. Edit `PREDECLARATION.md` (add §11 "Revision 1",
   listing R1–R8 and the old sidecar hash `PREDECLARATION.sha256` @ `72b4bd5`), `sniper_filter.py`,
   `g1_run.py` and the tests.
2. **Still read no outcomes.** A dry run of `g1_run.py` on a **synthetic** panel, with fake R, to
   prove the RESULT schema (pass flags, year table, quintiles, robustness row, PBO with no NaN) is
   allowed and encouraged. Don't run it on the real panel.
3. Rerun the census (counts only) if the population or reference-set definition changed the counts.
4. Write a new sidecar, update `HANDOFF_G0.md` (§ "Revision 1: what changed"), push, and **STOP**
   for approval.

Then continue with **Task 3**: `ZCODE_BRIEF_MECHANISM_INVENTORY_B_2026-10-07.md` plus its amendment
(commits `e1aee99`, `2cec4db` on local `ops/hardening-2026-07-10`). Push and stop.

## Task 2 (structural events), reviewed: accepted

Ranking accepted: **A (tender offers, pooled)** and **D (dividend ex-dates)** go forward. B depends
on sourcing the LQ45 / IDX30 history; C, E and F are skipped. Under D-070, each of A and D still
needs its **mechanism D-entry filed before any G0**. Task 3's combined ranking produces those drafts.
Don't start a G0 for A or D yet.

## Hard constraints

- No outcomes before approval.
- Research-side only. Production tree untouched. Read-only DB. Never print secrets.
- No registry or DECISION_LOG edits. No force-push. `logs/TELEGRAM_OFF` stays.
