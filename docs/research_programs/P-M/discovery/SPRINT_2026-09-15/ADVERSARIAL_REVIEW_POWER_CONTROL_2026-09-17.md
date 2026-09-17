# ADVERSARIAL REVIEW — HARNESS POWER CONTROL ARTIFACT (2026-09-16)

**Date:** 2026-09-17 · **Reviewer role:** independent adversarial / trading-advisor review, not the
control's author · **Subject:** `HARNESS_POWER_CONTROL_ARTIFACT_2026-09-16.md`
(sha256 `4a747ae941a9038a…`) and its script `HARNESS_POWER_CONTROL_2026-09-16.py`
(sha256 `83b19a8dbf49ae2c…`).

**VERDICT: APPROVED WITH AMENDMENTS.** Provenance is clean and the reporting is honest — the
hashes verify, the log reproduces the artifact's table line-for-line, and every kill-attribution
claim matches the run JSON. The objections below are to the control's **design**, not its
integrity. Conclusions #1 and #3 stand and are strengthened. **Conclusion #2 is refuted by
measurement and must be restricted before this artifact is used as a record.**

---

## 0. Provenance of this review

| Artifact | sha256 |
|---|---|
| `REVIEW_POWER_CONTROL_ARMS_2026-09-17.py` — null / clustered / correlated arms | `bed47fd8b4e429fc…` |
| `REVIEW_BAND_HAC_2026-09-17.py` — overlap-corrected inference on band contact | `d946d13fffd25275…` |
| `REVIEW_SPLIT_COVERAGE_2026-09-17.py` — corporate-actions gap, research impact | `7b2f85b23dd92dca…` |
| `REVIEW_BAND_INDEP_SOURCE_2026-09-16.py` — prior session's independent reimplementation, copied into the corpus so the HAC script's derivation is checkable (its lines 1–124 are embedded verbatim) | `b68eef43dfecf2c1…` |
| Run logs | `cache/review_power_control_arms_run.log`, `cache/review_band_hac_run.log`, `cache/review_split_coverage_run.log` |

The arms script reuses the control's own G1–G5 arithmetic **verbatim**; only the construction of
the treated mask differs. `sprint_lib.py` was not modified (`5b5ea2c28721233c…`, unchanged).

---

## 1. Findings against the artifact

### F-1 — At m ≥ 2,500 only ONE of five gates ever fired. (design)

Across the 120 mid/high-frequency runs, every first-kill is G1. G2, G3, G4 and G5 record zero.
The study is a power analysis of a single arithmetic inequality, presented as a power analysis of
the harness. The MDE needs no simulation to recover: the bar is a mean ≥ 90bp, the pool base is
+21.3bp, and SE at m = 10,000 is 9.96% / √10,000 = 9.96bp, so z = 11.3/9.96 = 1.13 → ~87%
detection. Observed 85%.

### F-2 — "G2 and G5 almost never bind" is a property of the injection, not the harness. (invalid claim)

G5 evaluates `base_era_mean + δ > 0` against era base means of −17.0bp and −5.6bp. For any
δ ≥ 30bp it passes by arithmetic; the gate was never given an opportunity to bind. Under the
clustered arm below, **G2 and G3 become the dominant killers**. The sentence must be deleted, not
softened.

### F-3 — The measured MDE is a lower bound, and conclusion #2 is the claim that depends on it. (REFUTED — see §2)

The injected signal is a uniform random mask: orthogonal to every FM control, constant δ, evenly
spread across dates and liquidity tiers. That is the most detectable signal that can exist. The
artifact's own diagnostics show it — median FM t = 8.34 at m = 10,000/+80bp and 12.56–15.58 at
+150bp. No real 80bp signal produces t = 15.

### F-4 — n = 20 does not resolve the threshold it is read against. (precision)

Wilson 95% CIs: 18/20 = 90% → [70%, 97%]; 17/20 = 85% → [64%, 95%]; 2/20 = 10% → [3%, 30%]. Both
+80bp cells straddle the 80% bar the MDE is defined by. With four δ points the supportable
statement is "MDE between 50 and 150bp," not "≈80bp."

**This was demonstrated accidentally.** An independent uniform replication in
`REVIEW_POWER_CONTROL_ARMS` (different RNG stream, same construction) returned 14/20 where the
control returned 18/20 in the same cell — 20 percentage points apart. Pooling both replications:
**32/40 = 80% at m = 2,500; 36/40 = 90% at m = 10,000.**

### F-5 — Type I was never measured. (gap — now closed, §2)

The 10% and 5% at +50bp could not be separated from a baseline false-positive rate. Now measured:
**0/20 in all six null arms.**

### F-6 — The `nw_t` defect is described with the wrong sign. (correction)

`sprint_lib.nw_t` (line 283) computes `x.std(ddof=1) / sqrt(len(x))` — a plain iid SE with no lag
correction, despite the name. Applied in `eval_signal` to `per_day_mean` over **overlapping**
h5/h10/h20 horizons, it makes the SE too small and |t| too large: the gate is too **lenient**, not
too strict. The artifact attributes the m = 600 kills to this defect; the kills are per-date
sparsity — ~1.5 treated cells per date against 7 regressors. Correcting `nw_t` lowers detection
everywhere and raises the MDE, which strengthens conclusions #1 and #3 and further weakens #2.

**Magnitude, measured (§3): 1.3× via NW(20), 1.6× from pooled to day-collapsed+NW — not the √k
worst case.** A reviewer prediction of up to 4.6× was wrong; see §3 for why.

### F-7 — Unstated scope limit. (completeness)

The kill rule is h5-only (`net60_h5 >= 0.003` in `price_family.py:206`). A 60bp round-trip over a
5-day hold is 12.0bp/day of drag; over the 21-day hold where the program's only survivor lives it
is 2.9bp/day. The G1 bar implies a required incremental effect of **68.7bp over base drift**
— ≈34.4%/yr incremental, ≈45%/yr gross at 50 non-overlapping 5-day periods. **No DEAD verdict in
the record speaks to h21 economics at all.**

---

## 2. New measurement — arms the control did not run

Same gate code, same panel (111,511 cells / 376 dates, base h5 = +21.3bp), 20 seeds per cell.
Only the treated-mask construction differs: `uniform` reproduces the control; `clustered` assigns
treatment by whole SESSION (how band contact, vol spikes and most real candidates fire);
`correlated` selects on volume-z, a signal the FM controls partial out.

| arm | m | +0bp | +80bp | +150bp | +300bp |
|---|---|---|---|---|---|
| uniform | 2,500 | 0% | 70% | — | — |
| uniform | 10,000 | 0% | 95% | — | — |
| **clustered** | 2,500 | 0% | **25%** | 40% | 75% |
| **clustered** | 10,000 | 0% | **25%** | 80% | 100% |
| correlated | 2,500 | 0% | 70% | 100% | — |
| correlated | 10,000 | 0% | 85% | 100% | — |

**Clustering destroys detection.** A +80bp effect firing on particular sessions is detected 25% of
the time against 90% for the orthogonal mask. The mechanism is in the diagnostics: median FM
cross-dates collapse from ~370 to 9 (m = 2,500) and 33 (m = 10,000), median FM t falls to ~2.0,
and G3 begins killing. G2 also binds (4–6 first-kills at +80/+150bp) because clustered treatment
lands unevenly across half-years — the two gates F-2 shows were never exercised.

Control-correlation alone is a much smaller penalty (95% → 85% at m = 10,000; median t 8.34 → 6.75).

**Revised MDE for a clustered effect: ≈150bp at m = 10,000, >300bp at m = 2,500** — two to four
times the artifact's headline.

**Type I: 0/20 in every null arm.** Correct, but not reassuring in the way it looks — it is the
same deterministic G1 arithmetic, not calibration.

---

## 3. New measurement — overlap-corrected inference on the band-contact result

`REVIEW_BAND_INDEP_SOURCE_2026-09-16.py` reports two t-statistics, both on K = 21 **overlapping**
forward returns sampled every trading day: a pooled-event iid SE (line 129) and a day-clustered
Fama-MacBeth SE (line 158). Neither corrects for the overlap.

| quantity | as reported | corrected | inflation |
|---|---|---|---|
| Pooled ARB-contact excess | −4.18%, t = **−8.11** (n = 2,726 events) | −5.80%, NW(20) t = **−5.08** (n = 589 days) | 1.6× total |
| **C2 magnitude-matched band dummy** | −2.87%, t = **−2.56** | NW(20) t = **−1.98** | 1.29× |
| C2 fall-size coefficient | +25.4%, t = +2.59 | NW(20) t = **+1.86** | 1.39× |

Non-overlapping subsample (every 21st admissible session, three offsets):
−4.47% / −6.12% / −5.36%, t = **−1.64 / −2.49 / −2.89**.

Autocorrelation of the day-collapsed contact series: ρ₁ = 0.24, ρ₂ = 0.08, ≈0 from lag 5 onward.
**This is why the correction is 1.3× and not √21 ≈ 4.6×:** excess is measured against the same-day
universe mean, which strips the common component and leaves a fast-decaying idiosyncratic series.
Most of the pooled inflation is not overlap at all — it is counting 2,726 events as independent
when they occupy 589 days (effective n falls 4.6× before any HAC term applies).

**Reading.** The band-contact *effect* survives correction comfortably: −5.8% over 21 days,
NW t = −5.08, magnitude consistent across three non-overlapping offsets. **The evidence that it is
distinct from fall magnitude does not.** The C2 regression cannot separate the band dummy
(t = −1.98) from fall size (t = +1.86); neither clears |t| ≥ 2, and one of three non-overlapping
offsets sits at −1.64.

The C1 difference-in-means form cited in the handover at t = −3.45/−3.76 was **not** recomputed
here. It carries both defects (same-day cross-section and overlap) with no day-collapse; applying
the 1.6× pooled→day-NW factor measured in row 1 suggests ≈ −2.2, but that is an extrapolation and
should be measured before it is relied on.

---

## 4. Incidental finding — `corporate_actions` split coverage

`sprint_lib.load_corporate_actions` (line 70) reads only `corporate_actions`, which holds **101**
split ex-dates; **292** are reachable via `corporate_action_events`, leaving **198 missing**.

Research impact, measured: of the 198, only 3 land on a session with an actual price bar inside a
research window, and only 2 clear `build_adjusted`'s `|ret| > 0.9` guard — **RAJA 2026-07-16
(−81.0%) and RMKE 2026-07-17 (−82.1%)**, both already known; MLPT at −95% is caught. Pseudo-OOS:
zero.

**Pipeline defect, not a results defect.** Worth fixing (`load_corporate_actions` should union both
tables); does not invalidate any family verdict.

---

## 5. Required amendments to the control artifact

The artifact is **not** amended by this review; these are the conditions for treating it as a record.

1. Restrict conclusion #2 to: *"the harness would have caught a temporally-uniform +80bp effect at
   n ≥ 10,000; it misses a clustered effect of the same size three times in four."*
2. Add the δ = 0 (Type I) and clustered/correlated arms — run, §2.
3. Delete "G2 and G5 almost never bind" (F-2).
4. Correct the `nw_t` direction of bias and state the measured 1.3–1.6× magnitude (F-6).
5. State the h5 / 60bp scope limit and the 68.7bp implied incremental bar (F-7).
6. Widen conclusion #3: the uninformative class is not "n ≤ 1,000" but **any candidate whose
   treatment concentrates on few sessions, at any n**.

---

## 6. Advisory conclusions (owner-facing)

**A. Do not adopt AMENDMENT_001** — not as primary, not as replacement. The band-contact effect is
real, but the magnitude-matched control that establishes it as a *distinct factor* sits at
t = −1.98 under correct inference and does not clear its own bar. The prior session's disposition
(secondary observational series; REPLACE recommended against) was right, and now rests on
measurement rather than a dispersion argument. Revisit only after the C1 form is recomputed
day-collapsed with HAC.

**B. Leave FWD-PM-VOLEX-001 running unmodified.** Its 21 monthly rebalances are non-overlapping,
so its alpha t = +4.79 is the one headline in this program not exposed to the inference defect in
§3. It is the correctly-specified vehicle; do not alter a live test mid-flight
(Research Master Plan §3.2e).

**C. Read every h5 t-statistic in the corpus 1.3–1.6× smaller.** DEAD verdicts need no revisiting
on this account — leniency only makes them safer. Positive t-claims do: the volume family's
FM t = 5.88 / 9.01 / 6.32 among them.

**D. Handover item #4 (broker re-run on 872 tickers) is confirmed necessary, and its mandate
widens.** The clustered arm shows the failure at m = 2,500 and m = 10,000, not only below
n = 1,000. Any candidate that fires on few sessions is in the uninformative class regardless of
event count.

**E. Fix `nw_t` before any further kill decision relies on it** (handover item #6), and union the
two corporate-action tables in `load_corporate_actions` (§4). Neither is urgent; both are cheap.

---

*Scope of this review: one control artifact, one harness, one market, in-sample. It does not
re-adjudicate any family verdict, and no registry, protocol or production artifact was changed.*

---

## 7. ADDENDUM 2026-09-18 — regime balance (the round-3 pending item, now measured)

`REVIEW_REGIME_BALANCE_2026-09-17.py`, log `cache/review_regime_balance_run.log`.

**The at-band and near-miss cohorts are NOT balanced on regime.** at-band shifts −13.0pp out of
R1 and +9.3pp into R4 relative to near-miss. Price-tier balance within R3 is clean (+1.2/+1.2/
−2.4pp), so the tier confound raised in §1 is dismissed.

| regime | band | events (at-band vs near-miss) | day-mean | NW(20) t |
|---|---|---|---|---|
| R1 | 0.07 | 1,967 vs 1,789 | −2.56% | **−1.69** |
| R4 | 0.15 | 615 vs 278 | −7.57% | **−3.97** |
| R2, R3 | — | 59 vs 17, 85 vs 17 | — | too few dates |

The pooled C1 (−2.56) is therefore **partly composition**: the at-band cohort over-weights R4,
and R4 is where the effect is large. Treat the pooled figure as an upper bound and the
within-regime cells as the estimates.

**Why R1 is weak is predicted by the onset result (§6/REVIEW_ONSET), not evidence against it.**
R1's onset is at depth 0.90 while the near-miss control window is 0.85–0.95 — in R1 the CONTROL
CONTAINS TREATED EVENTS. R4's onset is at 0.95, leaving its control clean, and R4 is the cell
that returns t = −3.97. One control window, two regime-specific thresholds, and the regime whose
threshold falls inside the window is exactly the one that washes out.

The bandwidth table's event counts show the same mechanism from the other side: raising the cut
to 0.99 shrinks at-band 2,726 → 775 while the 0.85–cut control GROWS 2,101 → 4,052, absorbing the
treated 0.95–0.99 events. That quantifies the dilution the executor identified.

**Open (added to the round-3 list): rerun R1's C1 against a 0.70–0.85 control, below R1's own
onset.** If strongly negative, the mechanism holds in both regimes with power and the C1 dilution
is fully explained. If not, the effect is R4-only and far narrower than either session has
claimed. Until then the §6 disposition (NOT YET; blocked on decontamination and redundancy) is
unchanged — this adds a third blocker rather than moving the verdict.
