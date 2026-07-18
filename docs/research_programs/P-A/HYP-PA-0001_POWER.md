# HYP-PA-0001 · Power Analysis (pre-registration)

> **Purpose:** fix the ex-ante `MDE` and confirm the test *can fail* (R2) for [[HYP-PA-0001_DRAFT|HYP-PA-0001]]. **This is pre-registration preparation, not experiment execution** — it uses only the event count N and a volatility nuisance parameter σ. **The reversal effect (mean CAR, its sign, its significance) was NOT computed** and remains sealed until the test runs post-registration under custody (R5, §7.3).

**Date:** 2026-07-17, revised 2026-07-18 · **Inputs:** [[COVERAGE_REPORT|WP-D]] calendar (210 events, 13 clusters) + `ohlcv` daily bars · **Status:** MDE computed; gross/net ambiguity and power-basis ambiguity resolved (readiness-review C-1/C-2); closes the last G1-held item. **CRO ex-ante ratification GRANTED 2026-07-19** (this analysis does not itself register).

## 1. Method (custody-clean)

- **N** = event count, from the WP-D calendar (no effect involved).
- **σ** = median daily log-return volatility of the 86 event tickers over their **full `ohlcv` history**. This is a general volatility nuisance parameter — the reversal effect lives in a conditional mean over a handful of days around each event and is a negligible fraction of ~1,250 trading days, so full-history σ does not encode it.
- **σ_event(k)** = σ_daily · √k (k-day cumulative-abnormal-return dispersion). Reported **raw** (conservative) and with a **×0.85 market-model haircut** (abnormal-return sd < raw).
- **MDE** = (z₁₋α/₂ + z₁₋β) · σ_event / √N = **2.802 · σ_event / √N** (two-sided α=0.05, power=0.80).

Measured: **median daily σ = 2.80%** (mean 3.09%) — high, as expected for the IDX liquid-but-volatile universe.

## 2. Results — MDE (%/event) at 80% power

| N (events) | k=3d | k=5d | k=10d |
|---|---|---|---|
| **210** (pooled, all signed events) | 0.96% / 0.81% | **1.24% / 1.05%** | 1.75% / 1.49% |
| **105** (adds-only) | 1.35% / 1.15% | 1.75% / 1.49% | 2.47% / 2.10% |
| **13** (cluster-limited — see §3) | 3.85% / 3.27% | 4.97% / 4.22% | 7.03% / 5.97% |

*(raw / abnormal-haircut · dataset: 210 events / 13 review-date clusters, median daily σ 2.86%, WP-D 2026-07-17)*

## 3. Interpretation — the binding constraint is N, via clustering

- **Pooled (N=210):** the study can detect a reversal of **~1.1–1.3%/event at k=3–5d**. If the true IDX reconstitution reversal is ≥~1.5% (plausible for a less-liquid market with a forced-flow M6 barrier), the pooled test is **adequately powered**. If it is sub-1%, it is **underpowered**. *(Readiness-review R-2, 2026-07-18: this label previously read "N=188," stale against §2's own N=210 row.)*
- **The fragility (decisive):** reconstitution reversals have a **common component per review date** (the whole cohort rebalances on the same day). If that component dominates, the *effective* N is closer to the **number of review-date clusters (now 13)**, where MDE balloons to **~5%** — badly underpowered. The truth sits between the N=210 and N=13 rows.
- **Consequence:** inference **must be cluster-robust by review date**, and the honest power statement is *"powered for a ~1.2% idiosyncratic reversal; fragile to the review-date-common component."* **Only two review-date gaps remain** (2021-H2, 2022-H1 = **+2 clusters → 15**); closing them is the highest-value power lever, but both are hard to source (2022-H1 has no clean per-index article; 2021-H2 candidates misattribute to 2020).

## 4. Ex-ante criteria — CRO-ratified 2026-07-19 (R5)

> **Ratified 2026-07-19:** the CRO ratified the table below **as recommended**, verbatim; the
> market-model estimation window is fixed at **230 trading days ending ~20 td before
> announcement**; the family-adjusted DSR is **deferred** (single confirmatory in-sample test,
> EXP-PM-0001 precedent). These are now the frozen-ready registered criteria (recorded; the
> irreversible T4 transition is deferred to explicit human authorization).

> **Revised 2026-07-18 — readiness-review resolution (C-1/C-2).** The original single `MDE:
> 1.3%/event` row below conflated two different things: a STATISTICAL detection floor (a
> function of σ, N, and the clustering basis) and an ECONOMIC capturability bar (net of the
> 0.60% round-trip friction). Comparing that single number against a plausible *gross*
> literature effect while `HYP-PA-0001_DRAFT`'s H1 is stated *net* of cost let "adequately
> powered" be asserted about the wrong quantity — the same failure pattern the HYP-PM-0001
> post-mortem names as the root cause of that hypothesis's near-foreordained refutation (its
> §8.1: *"a power statement that is arithmetically correct about the wrong quantity"*). Below,
> the statistical test (Test 1, gross) and the economic reading (Test 2, net) are separated and
> each is given a single, ex-ante-fixed basis. **This resolves the ambiguity. It does not
> resolve the owner's HOLD** — see the revised R2 verdict below.

| Parameter | Recommendation | Rationale |
|---|---|---|
| Reversal window `k` | **5 trading days** | balances reversal-capture against MDE growth in √k |
| **Test 1 — MDE_stat** (PRIMARY, gross) | **~4.97% raw / ~4.22% haircut** (cluster-robust basis, N=210, K=13) | the CONSERVATIVE bound is the single pre-registered statistical criterion — not chosen post hoc from the {1.05%–4.97%} range once results are seen (R7.4, threshold migration) |
| Inference (statistical test) | **cluster-robust (CR1) by review date, fixed as the ONLY method** | the review-date-common component is real (§3); no discretion to switch to pooled-iid SE after seeing results |
| Pooled/iid MDE (1.05–1.24%) | **secondary sensitivity figure only** | reported for transparency; explicitly **not** the registered decision bar |
| **Test 2 — net-of-cost** (SECONDARY, economic) | **DELETE-only subsample (N=105)**, gross point estimate − 0.60% round-trip friction > 0 | scoped to the executable (long-only) side only — ADD-side reversal capture requires shorting, execution-constrained on IDX (readiness-review C-4); applied *after*, not instead of, Test 1 |
| Robustness leg | **SECONDARY_CROSSCHECKED-only subsample (N=98)**, same estimator | declared consistency check, not a selection scan — 53% of events are single-sourced (readiness-review R-4) |
| N posture | **Owner elected (2026-07-19): register on the realized N=210 / K=13 window (2022-08→2026-05)** | HOLD lifted to GO; the 2021-H2/2022-H1 gaps are carried as declared limitations, not closed first (speed-vs-robustness trade-off resolved in favour of registering cluster-robust at 13) |

> **R2 verdict (revised 2026-07-18):** the test is **falsifiable** — MDE_stat is finite and
> fixed ex ante, so it can fail. Whether it is **adequately powered** is a separate, honest
> question: at the conservative (cluster-robust) basis, MDE_stat (~4.97%) sits well above the
> literature-anchored plausible gross effect (~1.5–2%) — meaning a REAL, modest effect would
> likely be *missed* (Type II error), not confirmed. **R2 is satisfied as falsifiability; it is
> NOT satisfied as adequacy**, and this readiness-review pass does not manufacture adequacy the
> data does not support. This closes the last open G1 item for HYP-PA-0001 *as a specification*
> (no ambiguous criterion remains). **On 2026-07-19 the CRO ratified `k`/MDE_stat ex ante (R5)**,
> accepting the marginal-power finding, and the **Owner lifted the HOLD to GO** on the realized
> N=210 / K=13 window (§4a). R2 remains satisfied as falsifiability; the marginal-adequacy risk is
> now an **accepted, declared limitation**, not an open blocker.

## 4a. Readiness tracking (owner status: **GO** — HOLD lifted 2026-07-19)

Updated after each WP-D improvement (WP-3). HYP-PA-0001 was **owner-held** through 2026-07-18; the Owner **lifted the HOLD to GO on 2026-07-19** (register on the realized N=210 / K=13 window). Registration still requires explicit human authorization of the irreversible T4 action; this document does not register.

| Date | Clusters | Pooled N | Cluster-limited MDE (k=5) | Remaining blockers | Recommendation |
|---|---|---|---|---|---|
| 2026-07-17 (a) | 9 | 154 | ~5.3% | 2021-H2, 2022, May-evals, IDX80 gaps | compute power |
| 2026-07-17 (b) | 11 | 188 | ~5.3% | 2021-H2, 2022-H1, May-2024/25, IDX80 | close gaps for clusters |
| 2026-07-17 (c) | 12 | 194 | ~5.1% | 2021-H2, 2022-H1, May-2024; IDX80 gaps; primary-verify | HOLD |
| **2026-07-17 (d)** | **13** | **210** | **~5.0%** | **2021-H2, 2022-H1** (quarterly era now complete); IDX80(2022-H2/2023-H1); primary-verify (Cloudflare) | **HOLD — keep expanding WP-D** |
| **2026-07-18 (e)** | 13 (unchanged) | 210 (unchanged) | ~5.0% (unchanged) | Same two clusters; **no new data collected this pass** | **HOLD — unchanged.** Readiness-review specification gaps (C-1–C-4, R-1–R-5: gross/net ambiguity, power basis, harness spec, ADD-side execution) all closed by documentation; power adequacy is a data question this pass does not touch |
| **2026-07-19 (f)** | 13 (unchanged) | 210 (unchanged) | ~5.0% (unchanged) | **None — Owner accepted residual gaps (2021-H2, 2022-H1) as declared limitations** | **GO — HOLD lifted.** CRO ratified criteria as recommended; estimation window fixed at 230 td; DSR deferred. Register on realized N=210 / K=13; irreversible T4 transition deferred to explicit human authorization |

**Effective power read:** pooled MDE ≈1.2% is stable; the binding cluster-limited MDE improved only marginally (5.3%→5.0%) because each pass adds ~1 cluster. **All quarterly-era reviews are now covered**; the two remaining clusters (2021-H2, 2022-H1) are the hardest to source. Through 2026-07-18 registration was not recommended at 13 clusters (owner HOLD). **On 2026-07-19 the Owner resolved this trade-off in favour of registering cluster-robust at 13**, accepting the two hard early-history gaps (2021-H2, 2022-H1) as declared limitations rather than investing in manual/primary retrieval first.

## 5. What this does and does not do
- ✅ Computes N, σ, and MDE; states registration-readiness.
- ✅ (2026-07-18) Separates the statistical (gross) and economic (net) criteria and fixes the
  inference basis ex ante, closing readiness-review C-1/C-2. See §4.
- ❌ Does **not** register the hypothesis, run the event study, or compute any reversal effect or significance.
- ✅ (2026-07-19) The HOLD→GO conversion and CRO ratification are now recorded (see §4 / §4a). This analysis still does **not** close the cluster-count gap (the two gaps are accepted as declared limitations) and does **not** itself register the hypothesis.
- **Next:** with CRO ratification and Owner GO recorded (2026-07-19), the only remaining step is the irreversible `DRAFT → REGISTERED` (T4/G1) under **explicit human authorization** → then the sealed event study runs under custody, per the harness spec [[HYP-PA-0001_HARNESS_SPEC]].

**Lineage:** [[HYP-PA-0001_DRAFT]] · [[READINESS_ASSESSMENT]] · [[HYP-PA-0001_HARNESS_SPEC]] · [[HYPOTHESIS_LIFECYCLE]] §4.1 (R2/R5) · [[EVIDENCE_MODEL]] EV-9 (C2 ceiling).
