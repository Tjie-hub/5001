# HYP-PA-0001 · Power Analysis (pre-registration)

> **Purpose:** fix the ex-ante `MDE` and confirm the test *can fail* (R2) for [[HYP-PA-0001_DRAFT|HYP-PA-0001]]. **This is pre-registration preparation, not experiment execution** — it uses only the event count N and a volatility nuisance parameter σ. **The reversal effect (mean CAR, its sign, its significance) was NOT computed** and remains sealed until the test runs post-registration under custody (R5, §7.3).

**Date:** 2026-07-17 · **Inputs:** [[COVERAGE_REPORT|WP-D]] calendar (188 events) + `ohlcv` daily bars · **Status:** MDE computed; closes the last G1-held item **pending CRO ex-ante ratification** (does not itself register).

## 1. Method (custody-clean)

- **N** = event count, from the WP-D calendar (no effect involved).
- **σ** = median daily log-return volatility of the 86 event tickers over their **full `ohlcv` history**. This is a general volatility nuisance parameter — the reversal effect lives in a conditional mean over a handful of days around each event and is a negligible fraction of ~1,250 trading days, so full-history σ does not encode it.
- **σ_event(k)** = σ_daily · √k (k-day cumulative-abnormal-return dispersion). Reported **raw** (conservative) and with a **×0.85 market-model haircut** (abnormal-return sd < raw).
- **MDE** = (z₁₋α/₂ + z₁₋β) · σ_event / √N = **2.802 · σ_event / √N** (two-sided α=0.05, power=0.80).

Measured: **median daily σ = 2.80%** (mean 3.09%) — high, as expected for the IDX liquid-but-volatile universe.

## 2. Results — MDE (%/event) at 80% power

| N (events) | k=3d | k=5d | k=10d |
|---|---|---|---|
| **188** (pooled, all signed events) | 0.99% / 0.84% | **1.28% / 1.09%** | 1.81% / 1.54% |
| **94** (adds-only) | 1.40% / 1.19% | 1.81% / 1.54% | 2.56% / 2.18% |
| **11** (cluster-limited — see §3) | 4.10% / 3.49% | 5.29% / 4.50% | 7.49% / 6.36% |

*(raw / abnormal-haircut)*

## 3. Interpretation — the binding constraint is N, via clustering

- **Pooled (N=188):** the study can detect a reversal of **~1.1–1.3%/event at k=3–5d**. If the true IDX reconstitution reversal is ≥~1.5% (plausible for a less-liquid market with a forced-flow M6 barrier), the pooled test is **adequately powered**. If it is sub-1%, it is **underpowered**.
- **The fragility (decisive):** reconstitution reversals have a **common component per review date** (the whole cohort rebalances on the same day). If that component dominates, the *effective* N is closer to the **number of review dates (11)**, where MDE balloons to **~4–5%** — badly underpowered. The truth sits between the N=188 and N=11 rows.
- **Consequence:** inference **must be cluster-robust by review date**, and the honest power statement is *"powered for a ~1.3% idiosyncratic reversal; fragile to the review-date-common component."* **Closing WP-D gaps G-WPD-1/2 raises the number of review-date clusters** (2021-H2, 2022-H1, the two May evals = up to +4 clusters, ~+36%), which is the single most effective way to improve real power here.

## 4. Recommended ex-ante criteria (for CRO ratification — R5)

| Parameter | Recommendation | Rationale |
|---|---|---|
| Reversal window `k` | **5 trading days** | balances reversal-capture against MDE growth in √k |
| `MDE` | **1.3%/event** (pooled, raw-conservative) | the effect the pooled test is powered to detect at 80% |
| Inference | **cluster-robust by review date** | the review-date-common component is real (§3) |
| N posture | register on N=188 **or** first close G-WPD-1/2 for +clusters | CRO trade-off: speed vs robustness |

> **R2 verdict:** the test **can fail** at a plausible effect size (MDE ≈ 1.3% < a plausible ~1.5–2% reversal), so R2 is satisfiable — **conditional on cluster-robust inference and the CRO accepting the clustering fragility.** This closes the last open G1 item for HYP-PA-0001 *as a computation*; **registration still requires the CRO to fix `k`/`MDE` ex ante (R5).**

## 5. What this does and does not do
- ✅ Computes N, σ, and MDE; states registration-readiness.
- ❌ Does **not** register the hypothesis, run the event study, or compute any reversal effect or significance.
- **Next:** CRO ratifies `k`/`MDE` (and decides register-now vs close-gaps-first) → then `DRAFT → REGISTERED` (T4/G1) → then the sealed event study runs under custody.

**Lineage:** [[HYP-PA-0001_DRAFT]] · [[READINESS_ASSESSMENT]] · [[HYPOTHESIS_LIFECYCLE]] §4.1 (R2/R5) · [[EVIDENCE_MODEL]] EV-9 (C2 ceiling).
