# EXP-PA-0001 — Evidence Package (terminal product)

**Date:** 2026-08-19 · **Author:** Research Director / CRO · **Hypothesis:** `HYP-PA-0001`
**Evidence tier:** **C2 · competent refutation** (EV-9, N=1, ceiling unchanged) — a first-class
research product (R12 / PG-11)
**Scope:** terminal evidence product for the confirmatory experiment. **No experimental result was
modified; the experiment was not re-run.**

---

## 1. Outcome

| | |
|---|---|
| Experiment status | **COMPLETED** |
| Hypothesis terminal status | **FAILED** — mode **F2 · Prediction failure** |
| Decision basis | Frozen rule ([[HYP-PA-0001_HARNESS_SPEC]] §2): *REFUTED iff Test 1 fails OR Test 2 fails.* **Both failed.** |
| Evidence product | C2 competent refutation + one robust, pre-registered, **non-capturable** directional finding |
| Failure receipt | [[FAILURE_ENTRY]] · `FAIL-PA-0001` |

---

## 2. What was tested

Mechanism `MECH-recon-dislocation` (I8 → I2): index-tracking funds are **mandated** to rebalance at
reconstitution, so the flow is a rule, not a mispricing — an **M6 structural barrier** that no
quantity of arbitrage capital removes (arbitrageurs can shift its timing; the flow must still
clear). Prediction: displacement into the effective-date close, then reversal over t+1..t+k.

Two claims, pre-registered separately (readiness-review C-1):

- **H1_mechanism (PRIMARY)** — gross, both directions: does the mechanism produce
  displacement-and-reversal *at all*?
- **H1_capturable (SECONDARY)** — net-of-cost, **DELETE-only**: is it harvestable long-only?
  ADD-side capture requires shorting the inflated close, execution-constrained on IDX (C-4), so the
  ADD side was pre-registered **gross-only and never claimable as a net edge**.

---

## 3. Execution record

| Item | Value |
|---|---|
| Script | `run_exp_pa_0001.py` — committed **before** execution (see §7 deviation) |
| Corpus | `data/walkforward.db`, opened **read-only** (`file:…?mode=ro`) — structurally enforced |
| Bar filter | `is_final = 1` (research convention; live partial bars excluded) |
| Market index | IHSG |
| Estimation window | 230 td ending 20 td before announcement (CRO-fixed 2026-07-19) |
| Reversal window | t+1 .. t+**5** td (CRO-fixed; non-tunable, X1) |
| Inference | cluster-robust **CR1** (Liang–Zeger), clusters = 13 review dates, df = G−1 = 12 |
| Friction | 0.60% round-trip, **imported** from `engine/exits/costs.py`, asserted equal to the registered value at runtime |
| Outputs | `results.json` (sha256 `27dac1ec…`), `execution.log` |

**Sample accounting — reported at every stage, nothing imputed:**

| Stage | N | Note |
|---|---|---|
| Raw CSV rows | 210 | WP-D `reconstitution_events.csv` |
| Distinct economic events (A-PA6 dedup) | **192** | key = (ticker, effective_date, event_type) |
| Excluded | 12 | insufficient history for a full 230td estimation window; **each itemised individually with its reason** in `results.json` |
| **Analysed** | **180** | 82 ADD / 98 DELETE, 13 clusters |

> **Declared N discrepancy.** The registration quotes N=210 / 105 / 98 — these are raw *row* counts.
> The same registration's A-PA6 mandates dedup **before** analysis. Realised analysis N is therefore
> 180, not 210. Both are reported; the tests used the deduped set. Carried as a declared limitation,
> not concealed.

---

## 4. Results

### Test 1 — PRIMARY (gross, both directions) — **FAIL**

n=180, G=13 · mean **+0.7261%** · SE(CR1) 0.5026% · t = 1.445 · CI95 **[−0.3691%, +1.8212%]**
CR1 asymptotic p = 0.1742 · **exact wild cluster bootstrap p = 0.1794**

CI includes zero → the mechanism claim does not survive.

### Test 2 — CAPTURABLE (DELETE-only, net of cost) — **FAIL**

n=98 · gross **−0.2488%** (SE 0.8535%, t = −0.291) → net of 0.60% friction: **−0.8488%**
net CI95 [−2.7084%, +1.0109%] · CR1 p = 0.7757 · WCB p = 0.7881

Wrong sign gross, negative net → the capturable claim does not survive.

### Robustness leg — SECONDARY_CROSSCHECKED only

n=85 · mean +0.2938% · CI95 [−0.9066%, +1.4943%] · **sign agrees with Test 1.**
Consistency check only. Per R15/X4 it licensed no re-run and no filtered re-test.

### ADD-side — pre-registered, gross-only, **NOT a decision basis**

n=82 · mean **+1.8911%** · SE 0.5615% · t = 3.368 · CI95 **[+0.6677%, +3.1144%]**
CR1 p = 0.0056 · **exact WCB p = 0.0132** · positive in **11 of 13** review dates

---

## 5. Post-hoc inference diagnostic (does not touch the verdict)

Motivation: CR1 is known to under-state standard errors and over-reject when G is small; G=13 is
small. The ADD-side CI's lower bound (+0.67%) sits close enough to zero to warrant checking whether
the inference — or the effect — is an artifact of few clusters.

**(a) Exact null-imposed wild cluster bootstrap, Rademacher weights.** With G=13 the bootstrap
distribution is *exactly enumerable* (all 2¹³ = 8192 sign vectors), so this carries **zero Monte
Carlo error**. All three samples reach the same conclusion under WCB as under the asymptotic test.
ADD: p = 0.0132 (108/8192), ~2.4× the asymptotic p — the expected direction of small-G correction —
and still clear of α=0.05.

**(b) Leave-one-cluster-out jackknife (ADD).** All 13 refits hold t between **2.79 and 5.05**, CI
excluding zero in every case, lower bounds spanning +0.34% to +1.26%. **No single review date is
load-bearing.**

**Reading:** the ADD-side effect is robust to both small-G inference correction and to any single
cluster's removal, and is broad-based across review dates. It is not an artifact of few clusters.

**Contrast, recorded for completeness:** Test 1 and the DELETE side are each *fragile* to a single
cluster — dropping 2024-02-01 flips Test 1's CI to exclude zero, and the DELETE sign flips on
dropping either 2024-02-01 or 2026-05-04. **This was not used, and must never be used, to revisit
the verdict** (R15/X4). It is recorded as a characterisation of cluster heterogeneity; 2024-02-01
carries 17 deletions against a typical 6–8, immediately before IDX's semiannual→quarterly
methodology transition.

---

## 6. What this experiment establishes beyond its own verdict

**6.1 The refutation is informative, not underpowered.** Realised CR1 SE = 0.50% against a
pre-registered MDE_stat of ~4.97% (implying an expected SE near 2.3%) — roughly **4× better
resolution than the design targeted**. `HYP-PA-0001_POWER.md` appears to have assumed effective
N = the 13 clusters; realised intra-cluster correlation is low, placing effective N far closer to
180. The wild bootstrap confirms the CR1 SE is honest rather than flattering (0.1794 vs 0.1742).
An effect several times smaller than the study was powered for would have been detected. **The
pooled null is a real null.**

**6.2 The apparatus is calibrated — this experiment is a positive control.** Prior to this run the
programme had produced two nulls and nothing else, leaving open a question no null can answer:
*can this pipeline detect anything at all?* The ADD-side result — same data, same estimator, same
clustering, same script, robust under exact WCB and a full leave-one-out — demonstrates that it
can. **This retroactively raises the evidential value of both FAIL-PM-0001 and FAIL-PA-0001 from
uninformative silence to informative nulls.** It is arguably this experiment's most valuable
output, and it is a byproduct.

**6.3 The mechanism is directional.** Full reasoning in [[FAILURE_ENTRY]] §lessons_learned. In
short: additions revert as predicted; deletions are confounded by the deterioration that caused
their deletion, and the two effects cancel under pooling.

---

## 7. Declared process deviation

**No frozen `MANIFEST.md` was created pre-execution (T5 skipped).** Recorded, not remediated —
authoring a "pre-execution" record after the result is known would falsify lineage.

Provenance is nonetheless intact: the script was **committed to git before execution** (immutable
pre-execution anchor), the corpus was opened **read-only by construction**, and `results.json`
carries the corpus fingerprint, the friction constants, the four resolved spec ambiguities, and
every excluded event with its individual reason. The guarantee T5 exists to provide is present;
the artifact is not.

*Observation for the programme:* the git commit supplied every substantive guarantee the MANIFEST
was designed to supply, at materially lower cost. Worth weighing when the per-experiment ceremony
is next reviewed.

---

## 8. Terminal disposition and what is NOT claimed

**FAILED is terminal (HL-3).** No re-run, no k/filter/parameter change (X2–X5, R15). HYP-PA-0001
stays counted in the P-A family {I2, I3, I8} (X8).

**Explicitly not claimed:**

- The ADD-side result is **not** a validated edge and **not** a trade signal. It was pre-registered
  gross-only precisely because it is shorting-constrained on IDX (C-4). It carries no decision rule
  and no promotion path.
- It does **not** rescue HYP-PA-0001 and cannot be used to. Any continuation is **T12 supersession**
  — a new registration, new G1, counted afresh in the family.
- No family-adjusted DSR was computed at this stage (deferred, CRO-ratified). A successor
  hypothesis inherits a family whose I8/I2 evidence is already entangled (LIM3).

**Free, non-registrable consequences** (knowledge, not strategy — no family slot required):
do not open a position in a newly-added name during the t+1..t+5 window; an existing holder of a
name being added may sell into the inclusion. Both sidestep the shorting constraint entirely.

---

## 9. Lineage

[[HYP-PA-0001_REGISTERED]] (sha256 `3692e69a…`) · [[HYP-PA-0001_HARNESS_SPEC]] §1–§2 (field mapping
and decision rule, implemented verbatim) · [[HYP-PA-0001_POWER]] §4 (MDE, see §6.1) · WP-D
[[COVERAGE_REPORT]] / [[DATA_DICTIONARY]] / [[SOURCE_REGISTRY]] (the event calendar) ·
`EXP-PA-0001/results.json` + `execution.log` + `diagnostic_cluster_inference.json` ·
[[FAILURE_ENTRY]] `FAIL-PA-0001` · [[FAILURE_REGISTRY]] · [[HYPOTHESIS_REGISTRY]]
