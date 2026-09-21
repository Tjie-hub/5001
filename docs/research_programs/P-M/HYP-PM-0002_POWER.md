# HYP-PM-0002 · Power / MDE Analysis (pre-registration)

> **Owner decision, 2026-08-20 (same session): WAIT FOR THE DATA WINDOW TO MATURE.** Registration is
> deferred, not abandoned. No parameter below was changed by this decision — see §9 for the
> data-maturity checkpoint added after this decision, appended without editing anything above it.

> **Purpose:** determine whether the pre-registered [[HYP-PM-0002_DRAFT|HYP-PM-0002]] design — fixed
> k∈{3,7,15}, primary k=7, ADV≥Rp5bn/day, 0.60% round-trip friction floor, `OFI_day` construction,
> the 62-day universe, the day-clustered observation unit, and the multiplicity denominator — can
> distinguish an economically meaningful effect from noise. **Pre-registration preparation, not
> experiment execution.** No parameter in the draft was changed to produce this result, and none
> will be changed as a result of it (owner instruction). **The OFI-vs-return relationship was NOT
> computed** and stays untouched — every input below is either (a) the 62-day coverage-derived
> formation-date set already fixed in the draft, (b) the ADV≥5bn universe rule already fixed in the
> draft, or (c) the *unconditional* distribution of raw k-day returns (a noise-floor nuisance
> parameter, not the tested effect — see §1.3 for why this doesn't violate no-peek).

**Date:** 2026-08-20 · **Script:** `run_hyp_pm_0002_power.py` (this directory; read-only on
`data/walkforward.db`, no DB writes, no prod code) · **Raw decomposition:**
`hyp_pm_0002_decomp.json` · **Status:** power computed — **NOT adequately powered under plausible
assumptions; see §6 verdict.**

---

## 0. Compute footprint (reported before running, per instruction)

Machine: 4 cores, 7.7GB RAM. **At run time the machine was under real memory pressure** — 210MB free,
3.6/4GB swap already in use — so the design deliberately avoided loading the 18.3M-row
`stockbit_flow_bars` table into pandas at all (every query against it was restricted to the 62
already-fixed dates via `WHERE trade_date IN (...)`, staying in SQLite). The only table materialized
into pandas was a date-and-ticker-restricted `ohlcv` slice (2026-03-02→2026-08-20, the minimum window
covering the 30-day ADV lookback and the k=15 exit lookahead): **100,817 rows, ~13MB**. No Monte
Carlo or bootstrap was needed — the estimator is closed-form (analytic variance decomposition + a
t-distribution power formula). Measured: **peak RSS 147MB, wall time 59s, zero swap activity caused
by this process.** Safe to run again at any time; nothing here approached the machine's limits.

## 1. Method

### 1.1 Effective sample size — the day-cluster count, not the ticker-day count

The draft's observation unit is `(ticker, formation_date)`, but its planned inference (§9 of the
draft, mirroring `EXP-PM-0001`'s `daily_stats()`) is **cluster-by-day**: aggregate to one
cross-sectional statistic per formation date, then run a t-test on that day-level series. **The
effective N for the primary test is therefore the day count, not the ~8,600 ticker-day observation
count** — pooling more tickers per day narrows the *within-day* estimate but does not by itself add
independent degrees of freedom to the day-level t-test, because same-day cross-sectional returns
share a common-day component (§1.2). This is the same discipline `EXP-PM-0001` applied (12.7M bars,
but inference run on the *daily* series).

Applying the draft's own horizon-tail trim (§7 of the draft) to the 62 coverage-derived formation
dates:

| k (trading days) | usable formation dates (post-trim) | median cross-sectional universe/day |
|---|---|---|
| 3 | **58** | 214 |
| **7 (primary)** | **56** | **202** |
| 15 | **47** | 186 |

(Universe sizes were computed from the draft's own rule — ADV≥Rp5bn/day recomputed per date, ∩
flow-reporting that day, ∩ not suspended through the exit date — applied for real, not assumed. As
a sanity check, the resulting ~186–214-ticker universe lands almost exactly on
`research/regime/collect.py`'s independently-documented "canonical 187-ticker liquidity-filtered
set" — a real cross-check that the liquidity rule is behaving as intended, not a coincidence to lean
on for anything beyond that.)

### 1.2 Variance decomposition — common day-factor vs. idiosyncratic noise

For each k, the *unconditional* k-day log return `r_{i,t,k} = logp(t+k) − logp(t)` was computed for
every `(ticker, formation_date)` in the draft's own universe (raw price movement, **no sign(OFI),
no delta, no buy/sell lot — OFI was never loaded**). Decomposed as a one-way random-effects model:

`r_{i,t,k} = f_{t,k} + e_{i,t,k}`, `f_{t,k}` = that day's cross-sectional mean return (the common
factor), `e_{i,t,k}` = the idiosyncratic deviation from it.

| k | n_days | median N_t | σ_e (idiosyncratic SD) | σ_f (day-factor SD) |
|---|---|---|---|---|
| 3 | 58 | 214 | 6.750% | 5.565% |
| **7** | **56** | **202** | **8.785%** | **10.543%** |
| 15 | 47 | 186 | 11.004% | 15.568% |

Note σ_f **exceeds** σ_e at k=7 and k=15 — the common day-level factor is not a small correction
here, it dominates. This is real IDX return structure over the actual 62-day window, not an
assumption.

### 1.3 Why this doesn't violate no-peek, and where the real uncertainty lives

The draft's test statistic is `cont_k = sign(OFI_day) * r_{i,t,k}` — a *sign-conditioned* transform
of the return, not the return itself. Under H0 (no OFI effect), `sign(OFI_day)` is, at minimum, a
±1 label; **whether that label is independent of the common day-factor `f_{t,k}` across tickers is
exactly the unresolved question, and it cannot be answered without inspecting OFI — so it is not
answered here.** Instead, two structural bounds are derived, both computable from `σ_e`/`σ_f` alone:

- **BEST CASE — `sign(OFI)` fully independent of `f_{t,k}` and independent across tickers on the
  same day.** The common factor cancels under random sign-flipping across the cross-section (a
  constant multiplied by independent ±1 draws summed across ~200 tickers averages toward zero), so
  cross-sectional pooling delivers close to its full noise-reduction benefit: `SE_best = σ_e /
  √(N_t · n_days)`.
- **WORST CASE — `sign(OFI)` is itself day-driven (correlated across tickers within a day, and
  correlated with `f_{t,k}`)** — e.g. a day when foreign flow broadly buys or sells the market,
  which `broker_flow`'s own `investor_type` stratification (`Asing`/`Lokal`/`Pemerintah`) records as
  a real, tracked IDX phenomenon, not a hypothetical. Under this case cross-sectional averaging
  provides **no benefit** — the day-level statistic behaves like the already-observed day-to-day
  variability of the raw mean return: `SE_worst = σ_f / √n_days`.
- **MODERATE — geometric mean of the two bounds**, shown only as an illustrative midpoint, not a
  fitted or estimated value.

**No OFI data was used to pick between these cases — that is precisely the point.** The bracket is
wide because the true answer is genuinely unknown without touching the sealed variable, and this
document does not touch it.

## 2. MDE at 80% / 90% power (two-sided α=0.05, t-distribution, df=n_days−1)

| k | Scenario | SE | MDE @ 80% power | MDE @ 90% power |
|---|---|---|---|---|
| 3 | BEST | 0.061% | 0.173% | 0.199% |
| 3 | MODERATE | 0.211% | 0.599% | 0.691% |
| 3 | WORST | 0.731% | 2.078% | 2.400% |
| **7 (primary)** | **BEST** | **0.083%** | **0.235%** | **0.271%** |
| **7 (primary)** | **MODERATE** | **0.341%** | **0.971%** | **1.121%** |
| **7 (primary)** | **WORST** | **1.409%** | **4.009%** | **4.629%** |
| 15 | BEST | 0.118% | 0.336% | 0.388% |
| 15 | MODERATE | 0.517% | 1.476% | 1.703% |
| 15 | WORST | 2.271% | 6.482% | 7.481% |

**The pre-registered economic threshold is 0.60%.** At k=7 (primary): BEST-case MDE (0.235%) clears
it easily; MODERATE-case MDE (0.971%) does **not** — the design can only reliably detect an effect
**62% larger than the threshold itself**; WORST-case MDE (4.01%) is nearly **7× the threshold**.

## 3. Power at economically relevant effect sizes — primary k=7

| Assumed true gross continuation | BEST-case power | MODERATE-case power | WORST-case power |
|---|---|---|---|
| 0.3% (half the friction floor) | ~95% | 13.9% | 5.5% |
| **0.6% (the pre-registered MDE / friction floor itself)** | **~100%** | **40.8%** | **7.0%** |
| 0.9% (1.5× the floor) | ~100% | 73.6% | 9.6% |
| 1.2% (2× the floor) | 100% | 93.3% | 13.3% |
| 1.5% | 100% | 99.1% | 18.2% |

(BEST-case power at 0.9% shows as a numerical `nan` in the raw t-noncentral-CDF computation at very
large noncentrality — a known scipy edge case at extreme ncp, not a real discontinuity; neighboring
values on both sides are ≈100%, so it is reported here as ~100%.)

**At exactly the pre-registered 0.60% threshold, power at the primary k=7 test is ~100% under the
best case and only 41% under the moderate case — below the conventional 80% bar.** Under the worst
case, power never exceeds ~18% even at 2.5× the threshold.

## 4. Assumptions behind the calculation

1. Day-clustered inference (matches the draft's own §9 planned methodology).
2. `σ_e`, `σ_f` estimated from the *unconditional* k-day return distribution over the draft's own
   fixed universe/formation-date set — real data, not a literature guess (this supersedes the
   rough "2–3% literature-typical" bound used in the original draft's §10 sanity check).
3. Normal/t-distribution approximation for the day-level mean (n_days=47–58 is large enough for this
   to be reasonable, not so large that finite-sample t-correction is negligible — a t-distribution
   with the correct df was used throughout, not a normal approximation).
4. The BEST/WORST bracket is a **structural bound**, not a confidence interval — the true SE could
   in principle sit anywhere in [SE_best, SE_worst], or (in a pathological case where `sign(OFI)`
   were *negatively* associated with the day factor) even below SE_best. No probability is assigned
   to where the truth falls within the bracket, because doing so would require inspecting OFI.
5. `ADV≥Rp5bn/day`, `OFI_day` construction, universe methodology, observation unit, and k∈{3,7,15}
   are taken as given from the draft — none were altered to produce this result.

## 5. Sensitivity to cross-sectional / day clustering

This **is** the central finding, not a side note: **the entire adequacy verdict flips depending on
how much cross-sectional dependence order flow carries.** Table §2/§3 already is the sensitivity
analysis the instruction asked for — collapsing it to one number would misrepresent how uncertain
the answer is. Two structural facts push toward taking the MODERATE/WORST end of the bracket more
seriously than the BEST end:

- `σ_f > σ_e` at k=7 and k=15 (§1.2) means the common day factor is **not a minor correction** to
  raw returns on this window — it's the dominant component. There is no reason to assume `sign(OFI)`
  is immune to whatever drives that common factor.
- This repository's own `broker_flow` table stratifies flow by `investor_type`
  (`Asing`/`Lokal`/`Pemerintah`) specifically because broad, same-day, cross-name flow from one
  investor class is a recognized, tracked feature of IDX market structure — not a remote
  possibility invented for this bound. That is an institutional/structural fact about the market,
  independent of anything in this dataset's OFI-return relationship, and it argues against assuming
  the BEST case is the realistic one.

## 6. Verdict

**NOT adequately powered — under any assumption except the least realistic one (full
cross-sectional independence of order-flow sign, which the institution's own data structure gives
reason to doubt).** The primary k=7 test:
- Is comfortably powered **only** under BEST-case assumptions that cannot be verified without
  inspecting the sealed variable.
- Achieves only ~41% power at the pre-registered 0.60% threshold under the MODERATE illustrative
  case, and under 10% under the WORST case — both below the conventional 80% bar, and the WORST
  case never reaches adequate power even at 2.5× the threshold.
- k=3 has a materially better profile (σ_f < σ_e there, MODERATE-case MDE@80% lands almost exactly
  at 0.60%) than k=7 or k=15 — meaning the pre-registered **consistency requirement across k∈{3,7,15}
  is asymmetric**: a true effect could plausibly show at k=3 while failing to reach significance at
  k=15 purely from lower power, not from the mechanism actually decaying. A future non-rejection at
  k=15 specifically would need this power gap disclosed, not read as equal-strength evidence to k=3.

**Per instruction: STOPPING here rather than changing k, the universe rule, the friction floor, the
observation unit, or the multiplicity denominator.** This is a report, not a redesign.

## 7. What would and would not be justified if the experiment fails to reject H0

- **Would be justified:** "no result under the MODERATE/WORST cross-sectional-dependence
  assumption" is close to the *expected* outcome of an underpowered test regardless of whether M2.1
  is true — a null here is only weak evidence against the mechanism, not a competent refutation, per
  this institution's own rule that "corroboration from a test that could not have refuted the
  hypothesis carries zero evidential weight" (R2) applies symmetrically to a null from a test that
  was unlikely to reject even if the effect were real.
- **Would NOT be justified:** treating a null result as F2 (clean prediction failure) with the same
  evidentiary weight `FAIL-PM-0001` carried. HYP-PM-0001's null came from a test with *abundant*
  power (sub-bp MDE over 12.7M bars) — a genuine severe test. This design, under anything but the
  BEST case, is not severe at the 0.60% threshold, so a null here would not license the same
  strength of conclusion.
- **Would NOT be justified:** treating a *positive, significant* result under the MODERATE/WORST
  case as confirmation of the effect size itself — with SE this wide, a significant result would
  likely be detecting an effect several multiples of 0.60%, and the point estimate would carry a
  correspondingly wide confidence interval; the registration should pre-specify reporting the full
  CI, not just the point estimate and p-value.
- **Would be justified regardless of outcome:** a finding on where the truth sits in the BEST/WORST
  bracket itself is new information (e.g. if the experiment's own realized within-day dispersion of
  the *sign(OFI)-weighted* statistic, once unsealed, turns out close to `σ_e/√N_t` rather than `σ_f`,
  that in itself answers a real, previously-unknown structural question about IDX order-flow
  cross-sectional dependence — a legitimate secondary product even from a null primary result).

## 8. What this does and does not do

- ✅ Computes real day-cluster N (post horizon-trim), real σ_e/σ_f from unconditional k-day returns
  over the draft's exact universe, closed-form MDE/power under two structural bounds, and reports
  compute footprint before running anything.
- ❌ Does **not** register, run the confirmatory test, or compute any OFI-conditioned statistic.
- ❌ Does **not** modify `HYP-PM-0002_DRAFT.md` — no k, threshold, universe rule, or denominator was
  changed as a result of this analysis, per instruction.
- **Next:** this is an owner decision, not this document's. Options not implemented here: (a) accept
  the risk and register as-is, treating a future null as inconclusive-not-refuting under the
  MODERATE/WORST case; (b) hold registration and wait for the flow-coverage window to lengthen
  (raises n_days, narrows the bracket); (c) a design change to reduce reliance on cross-sectional
  averaging (e.g. an explicit day-fixed-effects/demeaned test statistic that structurally removes
  `f_{t,k}` rather than hoping `sign(OFI)` cancels it) — noted as a possibility, not proposed as an
  edit to the frozen draft parameters.

---

## 9. Data-maturity checkpoint (added 2026-08-20, same session — owner decision: WAIT)

> **Everything above this line is unchanged from the original power analysis.** This section is a
> pure addendum, appended per owner instruction after the decision to defer registration rather than
> register a knowingly underpowered design or redesign the hypothesis to manufacture power. No k,
> threshold, universe rule, mechanism, or denominator was touched to produce this section — it
> reuses the exact `σ_e`, `σ_f`, `N_t` already computed in §1.2/§1.3 above and asks only "how many
> more of the same kind of day would it take."

### 9.0 Compute check (before running anything, per instruction)

`free -h` immediately before this step: **407MB free RAM, swap 3.8/4GB already in use** — tighter
than the original run. No table load was performed for this section at all: the only database
access was two `SELECT COUNT(DISTINCT date) ...` aggregate queries (never materializing rows into
pandas), used solely to measure two accrual rates (§9.1). Everything else is closed-form algebra on
the constants already sitting in `hyp_pm_0002_decomp.json`. `stockbit_flow_bars`'s 18.3M rows were
not touched.

### 9.1 Method

Both `SE_best(n_days)` and `SE_worst(n_days)` scale as `1/√n_days` with `σ_e`, `σ_f`, `N_t` held
fixed at their §1.2 values (an explicit, stated assumption — see §9.4). Solving
`MDE(n_days) = 0.60%` at 80% power for `n_days` (bisection on the same closed-form t-distribution
formula §2 already used, no simulation) gives the **additional broad-coverage trading days** needed.
Two real accrual rates, measured from the actual OHLCV calendar (COUNT-only queries, no row loads),
convert that into calendar time:

- **Broad-coverage accrual rate:** 62 of the 74 trading days between 2026-04-28 and 2026-08-19 met
  the ≥500-ticker floor → **0.838 broad days per trading day**.
- **Trading-day rate:** 148 of the 232 calendar days between 2026-01-01 and 2026-08-20 were trading
  days → **0.638 trading days per calendar day**.

### 9.2 Result — required additional broad-coverage days, by k (MODERATE scenario, 80% power)

| k | current n_days | required n_days | additional broad days needed | ≈ additional trading days | ≈ additional calendar days | projected checkpoint (from 2026-08-20) |
|---|---|---|---|---|---|---|
| 3 | 58 | 58 | **0** | 0 | 0 | **already met today** |
| **7 (primary)** | **56** | **144** | **88** | **~105** | **~165** | **≈ 2027-02-01** |
| 15 | 47 | 276 | 229 | ~273 | ~428 | ≈ 2027-10-22 |

**WORST-case checkpoints are not reported as target dates** — solving the same equation under the
WORST scenario requires 677 (k=3), 2,426 (k=7), and 5,286 (k=15) broad-coverage days respectively,
i.e. many years to over a decade at the observed accrual rate. That is not a usable planning horizon;
it is itself part of the finding (§9.5).

### 9.3 The checkpoint condition, stated precisely

**Reconsider registration when the primary k=7 leg has accumulated ≥144 broad-coverage trading days
(≥500 reporting tickers in `stockbit_flow_bars`) with a fully realized 7-trading-day-ahead price —
approximately 2027-02-01 if the current ~0.84 broad-day/trading-day accrual rate holds.** This is a
**re-run trigger, not a pre-approval**: when the window reaches this point, **rerun the power
analysis first** (§1–§3 of this document, same script, same closed-form method) using the
then-current `σ_e`/`σ_f`/`N_t` — do not simply count days and assume the checkpoint number above
still holds, because those constants were measured on a 3.9-month window and could shift as the
window lengthens. Only if that rerun shows adequate power (≥80% at the 0.60% MODERATE-case MDE, or
a materially narrowed BEST/WORST bracket that resolves the sensitivity question) should
`HYP-PM-0002` proceed to registration.

### 9.4 Assumptions behind the checkpoint (stated, not hidden)

1. `σ_e`, `σ_f`, and `N_t` are held constant at their current (56-day-window) values. If the
   universe's liquidity composition, the flow feed's reporting breadth, or market volatility regime
   changes materially before 2027-02, the actual required date shifts — this is a **projection under
   continuation of current conditions**, not a guarantee.
2. The 0.838 broad-day and 0.638 trading-day accrual rates are extrapolated forward unchanged. Both
   are recent, short-window measurements (3.9 and 7.6 months respectively) and could themselves
   shift (e.g. if `stockbit_flow_bars`' reporting coverage degrades or improves).
3. The checkpoint targets the **primary k=7 leg only** at MODERATE-case 80% power. k=15's own
   checkpoint (≈2027-10-22) is **materially later** — at the k=7 checkpoint, the k=3/k=7/k=15
   consistency requirement in the draft will likely still have k=15 underpowered even if k=7 and k=3
   are not. A rerun at the k=7 checkpoint should treat a k=15 non-result the same way §7 of this
   document already treats an underpowered null — not as evidence against the mechanism.

### 9.5 What this section does and does not do

- ✅ Computes the minimum additional broad-coverage-day count and a projected calendar checkpoint,
  analytically, from the existing design's own already-computed constants.
- ✅ Reports compute footprint before running (§9.0); used no row-level table loads and no
  simulation.
- ❌ Does not register HYP-PM-0002, redesign it, or change the research question.
- ❌ Does not treat the WORST-case bracket's multi-year-to-decade requirement as a target — it is
  reported (§9.2) as evidence for why the MODERATE case, not the WORST case, is the operative
  planning basis, without asserting the MODERATE case is *known* to be correct (§1.3's bracket logic
  still applies in full at re-run time).

**FINAL STATUS (this session): HYP-PM-0002 = DRAFT / WAITING FOR DATA MATURITY. Registration = NO.
Family slot consumed = NO. Engine defect = NO. Design change = NO. Next action = rerun this power
analysis when the primary k=7 leg reaches ≈144 broad-coverage days (≈2027-02-01 at current accrual),
before any registration decision.**

### 9.6 Cross-reference (added 2026-08-20, same session, after §9 — pure addition)

A follow-up audit asked whether the 62-day window is a genuine source limit or a fixable backfill
gap: `docs/audit/STOCKBIT_FLOW_BARS_HYP_PM_0002_COVERAGE_AUDIT.md`. Short answer: both, at different
boundaries — 2025-01-02 is a genuine vendor floor (confirmed, unrecoverable); 2026-04-28's *broad*
coverage is an ingestion-scope artifact (`stockbit_flow_bars` was never backfilled for the full
universe across 2025-01-02→2026-04-27, unlike its sibling `stockbit_flow`, which already has a
completed, certified backfill). That audit estimates a full-universe bars backfill could raise the
primary k=7 day-cluster N from 56 to roughly 340–365 — comfortably above the 144-day requirement in
§9.2 — but is itself a ≈51–68h vendor-rate-limited job, not something to launch without a separate,
explicit decision. **Neither the WAIT decision above nor any draft parameter changed as a result.**

---

### 9.7 Backfill state record (added 2026-08-20, later same day, after §9.6 — pure addition)

A follow-up **read-only state-recovery verification** confirmed against the live database and host
that the full-universe backfill floated as an option in §9.6 **was never launched** — it is not
running, not partially complete, and did not fail. See
`docs/audit/STOCKBIT_FLOW_BARS_BACKFILL_STATE_2026-08-20.md`. Decisive evidence: per-date ticker
counts across the recoverable 2025-01-02→2026-04-27 window still top out at **124**, unchanged from
the pre-existing narrow collection eras. **The ≈51–68h estimate in §9.6 therefore remains the full
remaining cost, not a stale figure from a job in progress.**

Broad-coverage days stand at **63** (2026-04-28→2026-08-20) against the **144** required by §9.2 —
the +1 versus §1.2's 62 is today's routine daily cron, i.e. exactly the organic accrual §9.1 assumed.
**The WAIT decision, every parameter above, and the ≈2027-02 checkpoint are unchanged;** no OFI
statistic was computed by that verification.

---

**Lineage:** [[HYP-PM-0002_DRAFT]] · [[HYP-PM-0001_POWER]] (sibling document, opposite finding) ·
[[ECONOMIC_MECHANISM_TAXONOMY]] §3 (M2.1) · [[HYPOTHESIS_LIFECYCLE]] §4.1 (R2/R5) ·
[[EVIDENCE_MODEL]] EV-9 (C2 ceiling, before this analysis even runs).
