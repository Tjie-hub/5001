# FAIL-PA-0001 — Failure Library Entry (immutable)

> **Append-only, immutable** ([[FAILURE_LIBRARY_SCHEMA]], HL-1, R12). This entry is never
> edited or deleted. A competent refutation is a first-class research product (PG-11), not a
> defect. Recorded per O8 / T7.

**Archived:** 2026-08-19 · **Owner:** Chief Research Officer · **Governed by:**
[[FAILURE_LIBRARY_SCHEMA]] · [[HYPOTHESIS_LIFECYCLE]]

---

## Schema record

| Field | Value |
|---|---|
| **failure_id** | `FAIL-PA-0001` |
| **hypothesis_ref** | `HYP-PA-0001` (REGISTERED 2026-07-19T00:19:47Z, sha256 `3692e69a…`) |
| **mechanism_ref** | `MECH-recon-dislocation` — index-reconstitution / closing-auction dislocation (I8→I2) |
| **experiment_ref** | `EXP-PA-0001` (`results.json` sha256 `27dac1ec…`) |
| **failure_reason** | **F2 · Prediction failure** |
| **archived_date** | 2026-08-19 |
| **related_features** | event-study CAR vs IHSG (market model); signed post-effective reversal, k=5 td |

---

## Decision basis (frozen rule, applied verbatim)

The pre-registered rule ([[HYP-PA-0001_HARNESS_SPEC]] §2): **REFUTED iff Test 1 fails OR Test 2
fails.** Both failed.

| Test | Sample | Mean signed reversal | SE (CR1) | t | CR1 p | exact WCB p | CI95 | Verdict |
|---|---|---|---|---|---|---|---|---|
| **1 · PRIMARY** (gross, both directions) | n=180, G=13 | **+0.7261%** | 0.5026% | 1.445 | 0.1742 | 0.1794 | [−0.3691%, +1.8212%] | **FAIL** — CI includes zero |
| **2 · CAPTURABLE** (DELETE-only, net) | n=98, G=13 | gross −0.2488% → **net −0.8488%** | 0.8535% | −0.291 | 0.7757 | 0.7881 | net [−2.7084%, +1.0109%] | **FAIL** — net ≤ 0, and wrong sign gross |

Friction: 0.60% round-trip, **imported** from `engine/exits/costs.py` (COMMISSION_BUY 0.15% +
COMMISSION_SELL 0.25% + SLIPPAGE 0.10% × 2 legs), asserted equal to the registered value at
runtime — not re-derived.

Robustness leg (SECONDARY_CROSSCHECKED only, n=85): mean +0.2938%, CI95 [−0.9066%, +1.4943%].
Sign agrees with Test 1. Reported as a consistency check only; per R15/X4 it licensed no re-run.

**F-mode attribution (R1 — exactly one, defended).** **F2 · Prediction failure.** Defended
against the alternatives:

- **not F4 (cost destruction)** — Test 1 fails on the *gross* measure before friction is applied.
  Cost is not what killed it.
- **not F3 (multiplicity collapse)** — no family-adjusted DSR was applied at this stage (deferred,
  CRO-ratified); the claim fails at its own unadjusted bar.
- **not F5 (regime artifact)** — the effect is absent across the full 2022-08 → 2026-05 window,
  not concentrated in one regime.
- **not F7 (look-ahead contamination)** — the estimation window ends 20 td before announcement;
  the tested quantity is strictly post-effective (t+1..t+k). No forward information enters.
- **not F6 (provenance failure)** — full lineage intact (see the declared deviation below, which
  concerns ceremony, not provenance).

---

## invalid_assumptions

Assumptions that the empirical result places under pressure. Recorded per R1 (Duhem–Quine: a test
refutes the conjunction of hypothesis and auxiliaries, never the hypothesis alone).

- **A-PA3 — falsified as stated.** *"Passive/index-tracking AUM tracking these indices is large
  enough, relative to the name's liquidity, to move the close."* Registered as theory-first
  (Shleifer 1986), explicitly **not IDX-calibrated**. The pooled null is direct evidence that IDX
  passive AUM is insufficient to produce a *detectable, symmetric* dislocation-and-reversal.
- **A-PA2 — untested and now load-bearing.** *"The `ohlcv` close print equals, or closely proxies,
  the closing-auction print used by index funds."* If IDX's closing auction diverges materially
  from the daily close print, the measurement is mis-anchored and the refutation attaches to the
  proxy, not the mechanism. **This assumption was never verified and remains the single most
  credible alternative explanation for the null.** Any successor hypothesis must close it first.
- **The symmetry assumption — falsified, and this is the substantive finding.** The registration
  predicted ADD and DELETE as mirror images. They are not (see below).
- **A-PA5 — untouched.** The cost authority's applicability to *auction* prints specifically
  remains unverified. Not load-bearing here (Test 1 failed pre-cost), but still open.

---

## lessons_learned

**1. The mechanism is directional, not symmetric — and the asymmetry has a clean economic reading.**

| Side | n | Mean signed reversal | CI95 | Reading |
|---|---|---|---|---|
| ADD | 82 | **+1.8911%** | [+0.6677%, +3.1144%] | predicted direction, robust |
| DELETE | 98 | **−0.2488%** | — | wrong sign, indistinguishable from zero |

Additions receive forced buying, become temporarily overpriced, and revert — the mechanism as
written. Deletions receive forced selling, but names are deleted *because* they are already
deteriorating (falling liquidity, falling market cap, negative momentum). The mandated-flow
reversal and genuine continued decline push in opposite directions and cancel. **Pooling a real
one-sided effect with a confounded null produced the null that refuted the claim.**

**2. The tradeable side and the effect are on opposite sides — structurally, not by bad luck.**
ADD-side capture requires shorting, execution-constrained on IDX (readiness-review C-4), so it was
pre-registered gross-only and is **not** claimed as an edge. DELETE-side is long-only executable
but carries both no signal and ~1.5× the noise (SE 0.85% vs 0.56%) — deleted names are thinner and
more idiosyncratic. More data would worsen this ratio, not improve it. Any successor mechanism in
this family inherits the problem.

**3. The study was substantially better powered than pre-registration assumed — so this is an
informative null, not an underpowered miss.** Realised CR1 SE = 0.50% against a pre-registered
MDE_stat of ~4.97% (implying an expected SE near 2.3%). Back-solving, `HYP-PA-0001_POWER.md`
appears to have assumed effective N = the 13 clusters; the realised intra-cluster correlation is
low, placing effective N far closer to 180. **The exact wild cluster bootstrap confirms the CR1 SE
is honest** (WCB p 0.1794 vs asymptotic 0.1742). The pooled effect is not merely undetected — an
effect ~4× smaller than the design targeted would have been detected.

**4. Second consecutive F2, and the shared cause is not captured by the F-taxonomy.** FAIL-PM-0001
(−0.0008% gross) and FAIL-PA-0001 (+0.7261% gross) both died at short horizons against the same
0.60% round-trip friction wall. Both are individually F2, but the *program-level* pattern —
horizon/friction mismatch — has no F-code, so §5.3's failure-mode diagnostic cannot surface it.
**Recommendation: a friction-feasibility screen at G1** — a mechanism whose plausible effect cannot
clear ~2× round-trip at its natural horizon should be killed at F1 (cheap) rather than F2
(expensive). Both experiments would have been.

**5. Larger-N clusters are not equivalent economic events.** Review date 2024-02-01 carries 17
deletions (typical: 6–8) averaging −3.225%, immediately preceding IDX's semiannual→quarterly
methodology transition. It looks like a one-off methodology-driven purge rather than a routine
reconstitution. **This is recorded as a characterisation only. It was not used to alter the
verdict, and the leave-one-out finding that dropping it flips Test 1 is explicitly NOT a rescue
(R15/X4).** Any successor must argue cluster heterogeneity *ex ante*.

---

## Declared process deviation

**No frozen `MANIFEST.md` was created pre-execution (T5 skipped).** PM-0001 established the
pattern; this experiment did not follow it. Recorded rather than remediated — writing a
"pre-execution" record after seeing the result would falsify lineage, which is precisely what the
custody model exists to prevent.

**Provenance is nonetheless intact:** `run_exp_pa_0001.py` was committed to git *before* execution,
supplying an immutable pre-execution anchor; the script opens the corpus read-only (`mode=ro`,
structurally enforced, not by convention); and `results.json` records the resolved spec
ambiguities, the friction constants, the corpus fingerprint, and every excluded event with its
individual reason. The guarantee the MANIFEST was meant to provide exists; the artifact does not.

---

## Terminal status

**FAILED is terminal (HL-3).** No re-run, no parameter/k/filter change (X2–X5, R15). HYP-PA-0001
remains counted in the **P-A family {I2, I3, I8}** permanently (X8) — a failure never reduces the
denominator. Continuation, if any, is **T12 supersession**: a *new* registration under a new G1,
counted afresh in the family.

**Note on family exhaustion:** the taxonomy records I8 as causally upstream of I2 (LIM3 — shared
observations, not independent evidence), and I3 as competing with I2 for the same session-boundary
observations. This single experiment therefore consumes materially more of the P-A family's
evidential space than a one-of-three member count implies.
