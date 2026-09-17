# DISCOVERY HARNESS FALSE-NEGATIVE / POWER CONTROL — CONTROL ARTIFACT

**Date:** 2026-09-16/17 · **Task:** handover open item #3 ("Harness false-negative control —
every DEAD verdict is conditional on a kill rule whose Type II rate is unmeasured").
**Status:** CONTROL COMPLETE. Verdict: **C — MIXED** (details below).

## Provenance

| Artifact | Value |
|---|---|
| Control script | `SPRINT_2026-09-15/HARNESS_POWER_CONTROL_2026-09-16.py` — sha256 `83b19a8dbf49ae2c0ae849dd06a22ef54db0707e6e9c5e1dfb78e7d74a7df4eb` |
| Harness (unmodified) | `SPRINT_2026-09-15/sprint_lib.py` — sha256 `5b5ea2c28721233c77c60e20940f7f9b2fbd0be9e30f909676b9ccc8aedc35dc` |
| Run log (stdout capture) | `cache/harness_power_control_run.log` (includes full JSON: every run's treated-set size, observed effect, per-gate result, day-weighted mean, tier means, OOS means) |
| Seeds | 0–19 (numpy default_rng, master seed 20260916; per-run sub-seeds deterministic) |
| Frequencies | m ∈ {600, 2,500, 10,000} treated events per window (real record frequencies: veto cell ≈898/1.59y; mid-family ≈6.9k; high ≈17k) |
| Effects injected | +30 / +50 / +80 / +150 bp added to treated cells' realized h5 |
| Runs | 3 frequencies × 4 effects × 20 seeds = **240 harness evaluations** |

**Injection method:** treated subsets are uniform random draws of exact size m from the
111,511-cell eligible pool (liquid, suspension-clean, entry-day tradable, full FM controls valid —
i.e. the actual exclusions and missingness of the record). Injected observation:
`y_synth = y_real + δ` on treated cells only; all other cells and all controls untouched. Real fat
tails (pool h5 sd = 9.96%), cross-sectional correlation, calendar clustering, liquidity
distribution and missingness are inherited from the real panel. The pseudo-OOS panel (2021-07..
2024-12, aligned grid — a panel-shape misalignment was found and fixed during this control) receives
the same δ on its own drawn subsets, so a true effect exists in both eras.

**Kill rule evaluated (UNMODIFIED, family-program standard, short-circuited in harness order):**
G1 net h5 ≥ +30bp after 60bp RT floor · G2 pooled per-half mean > 0 in ≥3 of 4 half-years ·
G3 Fama-MacBeth β > 0 with \|t\| ≥ 2 (controls: ret1, ret5z, volume z, ADV tercile, flow z) ·
G4 n ≥ 1,000 events AND ≥ 50 tickers · G5 pseudo-OOS positive in both 2021-22 and 2023-24 eras.

## RESULTS (20 seeds per cell)

| freq | +30bp | +50bp | +80bp | +150bp |
|---|---|---|---|---|
| 600 (veto-cell class) | 0% | 0% | 0% | 0% |
| 2,500 | 0% | 10% | **90%** | 100% |
| 10,000 | 0% | 5% | **85%** | 100% |

**Minimum reliably detectable effect (≥80% detection):**
- m = 600: **>150bp — never reliably detectable** (structural).
- m = 2,500: **≈80bp** (between 50 and 80).
- m = 10,000: **≈80bp** (between 50 and 80).

**First-gate kill attribution (runs killed / why):**
- ≤ +50bp, all frequencies: **G1 (economics) is the sole killer.** Mechanism: pool base mean
  h5 = +21.3bp, so G1 (net ≥ +30bp after 60bp) requires an effect of ≈ **+69bp over base drift**
  before gross clears +90bp. A true +50bp incremental effect yields net ≈ +10bp — a deterministic
  kill, not a sampling accident. Detection at +50bp is 0–10% *everywhere*.
- m = 600, all δ: **G3 (FM incrementality, naive-SE nw_t) and G4 (n ≥ 1,000) jointly bind** —
  at +150bp the FM gate kills 20/20 (|t| median < 2 at this frequency; the handover-known iid-SE
  defect applies) and G4 fails by construction. **Low-frequency candidates are structurally
  undeclarable at any effect size.**
- G2 (halves) and G5 (OOS): almost never bind (G2: ≤2 runs; G5: ≤2 runs, only at 2021-22's
  negative base −0.17%).

**Day-weighted vs event-weighted:** means agree within ~1–9bp for random orthogonal masks
(e.g. m=10,000/+80bp: event +1.01% vs day-weighted +1.09%) — the estimand gap is not the binding
constraint for gate passage; the gates are event-weighted by construction.

**Liquidity tiers:** treated-set means are uniform across ADV terciles for random masks
(±25bp sampling noise) — the detection gap is gate-side, not tier-side. (Real candidates that
concentrate in low-base tiers face a *higher* effective G1 bar; the band-contact/overlay survivor's
mid-cap pocket is exactly such a case.)

## VERDICT: **C — MIXED**

1. **Structurally insensitive to +30bp and +50bp at every frequency** (detection 0–10%): the
   net-of-cost economics gate embeds the base drift, so a true +50bp incremental effect cannot
   clear it. Historical "no edge" conclusions at these magnitudes were **foregone conclusions of
   the gate**, not measured nulls.
2. **+80bp is detectable (85–90%) at mid/high event frequency** — historical DEAD verdicts on
   high-frequency constructions (n ≥ ~2,500/window) are **materially informative for effects
   ≥ ~80bp**: the harness would have caught them.
3. **Low-frequency constructions (n ≤ ~1,000/window) are structurally undeclarable at any δ ≤
   150bp** — killed jointly by the FM gate (naive-SE nw_t, a known defect per handover item #6)
   and the n ≥ 1,000 gate. Historical DEAD verdicts in this class — including the broker-family
   breadth kills (n = 74–940, handover item #4) and anything veto-cell-shaped — are **uninformative**,
   confirming handover item #4 as methodologically necessary.

**Remediation implications (for owner decision — not executed):** low-frequency candidate classes
need either a longer/wider evidence window, a universe extension (handover item #4), or a
re-specified decision standard for sparse events (no corpus precedent exists — see feasibility
review §2); and the FM gate's naive-SE defect (handover item #6) should be fixed before any
further kill decisions rely on it. The five-condition kill rule itself was NOT modified in this
control.

*Reproduce:* `venv/bin/python HARNESS_POWER_CONTROL_2026-09-16.py 2>&1 | tee
cache/harness_power_control_run.log` from this directory (deterministic given the pinned seeds;
~4 min).

---

# ERRATA & AMENDMENTS (2026-09-17 — executor response to ADVERSARIAL_REVIEW_POWER_CONTROL_2026-09-17.md)

The adversarial review (verdict: APPROVED WITH AMENDMENTS) verified all hashes and reproduced the
table, then challenged the control's **design**. Its own measurements (scripts
`REVIEW_POWER_CONTROL_ARMS_2026-09-17.py` `bed47fd8…`, `REVIEW_BAND_HAC_2026-09-17.py` `d946d13f…`,
`REVIEW_SPLIT_COVERAGE_2026-09-17.py` `7b2f85b2…` + logs, all verified by the executor) were
reproduced and **accepted**. The amendments below are applied as instructed; original text above is
preserved unmodified. Item references are the review's.

**A-1 (F-1, accepted).** At m ≥ 2,500 only G1 ever fired: the study is a power analysis of the
economics inequality, presented as a power analysis of the full harness. The reviewer's analytic
recovery of the +80bp cell (z = 11.3/9.96 → ~87%) matches the observed 85%.

**A-2 (F-2, accepted — sentence deleted).** "G2 and G5 almost never bind" was a property of the
uniform-random injection, not the harness. Under session-clustered treatment (the review's arm,
matching how band contact, vol spikes and most real candidates fire), G2 and G3 become dominant
killers (G2: 4–6 first-kills at +80/+150bp; FM cross-dates collapse from ~370 to 9–33).

**A-3 (F-3, accepted — conclusion #2 restricted).** Revised conclusion #2: *"the harness would have
caught a temporally-uniform +80bp effect at n ≥ 10,000 (pooled replications: 32/40 = 80% at m=2,500,
36/40 = 90% at m=10,000); it misses a session-clustered effect of the same size three times in four
(25% detection)."* The uniform random mask is the most-detectable signal that can exist (orthogonal
to every FM control, uniform across dates and tiers — median FM t 8.34 at +80bp/m=10,000).

**A-4 (F-4, accepted).** n = 20 cannot resolve an 80% bar (Wilson 95% CIs straddle it: 90% →
[70, 97]; 85% → [64, 95]). The supportable statement is "MDE between 50 and 150bp per frequency
class," refined by the review's pooled replications.

**A-5 (F-5, accepted).** Type I measured post hoc by the review: 0/20 in all six δ = 0 null arms
(six arms incl. clustered/correlated). Retained as a control result.

**A-6 (F-6, accepted — direction corrected).** `sprint_lib.nw_t` (line 283) is a plain iid SE. On
**overlapping** h5 horizons it makes SE too small and |t| too large: the G3/FM gate is too
**LENIENT**, not too strict — the artifact's low-frequency attribution to this defect had the wrong
sign, and the true m=600 killers are per-date sparsity (~1.5 treated cells/date vs 7 regressors)
plus G4. Measured correction magnitudes (review §3): 1.33× pooled→day-NW on the ARB excess,
1.29×/1.39× on the C2 coefficients — not the √k worst case. Consequence: DEAD verdicts are safer
(leniency only ever added false positives); every positive h5 t-statistic in the corpus should be
read 1.3–1.6× smaller.

**A-7 (F-7, accepted — scope limit stated).** The kill rule is h5-only. The G1 bar implies a
required incremental effect of ≈68.7bp over base drift ≈ **34.4%/yr incremental (≈45%/yr gross at
50 non-overlapping 5-day periods)**. **No DEAD verdict in the record speaks to h21 economics at
all** — the horizon where the program's only survivor lives carries 2.9bp/day of drag, not 12.

**A-8 (conclusion #3 widened, accepted).** The uninformative class is not "n ≤ 1,000": it is **any
candidate whose treatment concentrates on few sessions, at any n** (clustered arm: 25% detection at
+80bp with n = 2,500 AND n = 10,000).

**A-9 (review §4, accepted).** `sprint_lib.load_corporate_actions` sees 101 of 292 split ex-dates
(198 missing from `corporate_action_events`). Research impact measured by the review: only 2 events
land on a research-window bar and clear the |ret|>0.9 guard — **RAJA 2026-07-16 (−81.0%), RMKE
2026-07-17 (−82.1%)** (MLPT −95% caught). Pipeline defect, not a results defect; fix (union both
tables) pending owner go.

**A-10 (review §3 open item — NEW EXECUTOR MEASUREMENT).** The C1 difference-in-means form,
recomputed day-collapsed with NW(20) on the review's own independent admissible-event construction
(`EXECUTOR_C1_DAYCOLLAPSED_2026-09-17.py`, log `cache/executor_c1_daycollapsed_run.log`; split
ex-dates unioned from both tables, 299 after union):
- at-band vs depth-matched near-miss (85–95%): day-mean **−3.47%**, NW(20) t = **−2.56**
  (390 dates, ρ₁ = −0.05) — **survives correct inference** (handover's −3.45/−3.76 deflates 1.35×,
  consistent with the review's measured 1.3–1.6×).
- at-band vs all shallower big falls: day-mean −5.27%, NW(20) t = **−4.77** — survives strongly.
- Depth-monotonicity (near-miss vs shallow): t = −1.01 — NOT established.
- C2 regression form (band dummy vs fall size): remains unseparated (NW t = −1.98 / +1.86, review
  §3).
Consequence for AMENDMENT_001: the review's stated condition for revisiting it ("recompute C1
day-collapsed with HAC") is now satisfied and the C1 contrast survives; the distinct-factor claim
(C2 form) still does not. Adopt/reject remains an owner decision on this split evidence.

*This errata section was written by the control's executor after independent verification of every
review number against `cache/review_*_run.log`. Original artifact text above is unmodified.*

---

# EXECUTOR ROUND-2 UPDATE (2026-09-17 — response to reviewer round 2)

Reviewer round-2 hashes verified (script `11bde462…`, my executor `8b6d364c…` pre-fix, artifact
`602908a2…`, review `18ff81ca…`); R-2/R-3/R-4 tables reproduced exactly from
`cache/review_c1_robustness_run.log`. Both defects accepted and fixed; adverse evidence reproduced
independently and **confirmed with one refinement**.

**E-1 (defect 1, fixed).** The `(ref)` line in `EXECUTOR_C1_DAYCOLLAPSED_2026-09-17.py` passed the
same masks as (a) and reprinted the day-collapsed number; the pooled-event form was never computed.
Fixed (added pooled mode). **Measured:** pooled-event contrast −2.78%, t_iid = **−3.76** (matches
the handover exactly — constructions reconcile); day-collapsed NW(20) t = −2.56; **deflation
1.47× measured** (A-10's inferred 1.35× replaced).

**E-2 (defect 2, fixed).** A-9 direction reversed and corrected: **198 of the 292 reachable split
ex-dates are missing FROM `corporate_actions` and present IN `corporate_action_events`**;
`load_corporate_actions` sees only the 101.

**A-11 (NEW — bandwidth / min_each / cutoff-purification / depth profile; executor independent
reproduction `EXECUTOR_C1_ROBUSTNESS_2026-09-17.py`, log `cache/executor_c1_robustness_run.log`).**

- *Bandwidth (R-A reproduced + extended):* at cut 0.95 the contrast runs −4.66% (0.70–0.95),
  −4.33% (0.80–0.95), −3.47% (0.85–0.95), **−1.82% (0.90–0.95, t=−1.22)**; at cut 0.99 it collapses
  to −0.55%..−2.03% (all |t| < 2). Detection of the contrast is bandwidth-fragile.
- *min_each (R-B reproduced):* −3.47% (me=1) → −2.37% (me=2, t=−1.96) → −2.05% (me=3) → −1.16%
  (me=5). The headline rests on single-observation cohort-days.
- *Cutoff purification (review's cells reproduced; NEW fixed-control cells added):* the review's
  collapsing cells hold the near-miss window pinned to the cut (0.85–cut, 0.90–cut), which moves
  treatment-like depth ≥ 0.95–0.99 observations INTO the control as the cut rises — dilution by
  construction. Holding the control FIXED at 0.85–0.95 and purifying treatment 0.95→0.99: −3.47% →
  **−3.02%, t = −3.02** (n=275) — the contrast survives treatment purification under a fixed
  control.
- *Depth profile vs fixed 0.70–0.85 baseline (NEW — the decisive evidence):* mean excess by depth
  bin: 0.70–0.80 −0.02%, 0.80–0.85 +0.03%, 0.85–0.90 −0.07%, 0.90–0.95 **−2.37%** (t=−2.38),
  0.95–0.97 **−2.86%** (t=−2.18), 0.97–0.99 **−5.07%** (t=−4.83), 0.99–1.01 **−4.04%** (t=−2.45),
  ≥1.01 **−12.52%** (t=−2.31, n=80). **There is no discontinuity at the band** (0.95 or 1.00): the
  break is at depth ≈ 0.90 and severity is monotonically increasing in depth through and beyond the
  band.

**AMENDMENT_001 disposition (revised per reviewer round 2 — accepted).** The reviewer is right that
"split evidence" overstated it. Honest count: C2 regression FAILS; depth-monotonicity FAILS; C1
PASSES at one bandwidth (and survives treatment purification under a fixed control, but the
purified contrast is a fall-depth effect, not a band effect). More decisively, the depth profile
shows a continuous fall-magnitude effect from depth ≈ 0.90 with no discontinuity at the band — so
the mechanism is **fall magnitude / deep-fall avoidance, not band contact**. This makes the
candidate substantially redundant with the already-adopted volatility-decile exclusion overlay.
AMENDMENT_001 is put to the owner as **one-of-three (C1 marginal pass; C2 FAIL; monotonicity FAIL),
with the band framing refuted** — and the operational note that any "deep-fall exclusion" it might
motivate is likely already captured by the overlay.

*Round-2 addendum by the control's executor; all reviewer numbers reproduced before acceptance.*
