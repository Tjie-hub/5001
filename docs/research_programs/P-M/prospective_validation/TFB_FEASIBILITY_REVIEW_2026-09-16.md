# TFB (PLATFORM-OUTFLOW-INTO-STRENGTH) — ADVERSARIAL FEASIBILITY REVIEW

**Date:** 2026-09-16 · **Stage:** pre-registration feasibility review · DISCOVERY/GOVERNANCE ONLY.
**Name mapping (declared):** "TFB" does not appear in the discovery record or governance corpus by
that name. From the parameters cited (+0.50% bar, σ=4–8%, 24 months, 650+ signals), the referent is
the single parked candidate in protocol V1.1 — **platform-outflow-into-strength** (up-move day
ret1 ≥ +3% & platform-flow z ≤ −1, veto vs flow-neutral up-moves). All numbers below are recomputed
from the actual stored geometry (suspension-clean liquid canvas, 401 admitted sessions,
2025-01-02..2026-09-14 ≈ 1.59y @252; 120,621 eligible ticker-days). If "TFB" means something else,
this review does not apply.

---

## 1. SIGNAL-RATE REALITY (recomputed, not extrapolated)

| Variant | events | /year | /quarter | tickers | per-ticker/yr | top-10 tickers | zero-days |
|---|---|---|---|---|---|---|---|
| **FROZEN SPEC** (≥+3%, z≤−1) | **898** | **564** | **141** | 307 | 1.3 | 14.8% | 238/547* |
| wider move (≥+2%, z≤−1) | 1,156 | 727 | 182 | 343 | 1.6 | 14.8% | 211/547 |
| wider flow (≥+3%, z≤−0.5) | 1,535 | 965 | 241 | 384 | 1.8 | 13.1% | 192/547 |

\* session count includes 146 pre-window rows; annualization uses the 401-session real window
(corrected rates shown above supersede the script's 2.17y division). Events/day (frozen spec):
mean 1.64, median(active) 2, p90 6, max 13; **38% of sessions have zero events**.

**Regime concentration (frozen spec):** bear 25.1% of events (h5 **−1.32%**), side 28.2% (−0.77%),
bull 37.2% (+0.54%). **Tier rates:** ADV-top 181 events (**83/yr**), mid 338 (156/yr), bottom
379 (175/yr). Pooled event spread: **−1.16%** (veto −0.44%, n=859; control +0.72%, n=6,293).

**Maximum plausible rate under universe tiers:** the full-roster frozen-spec rate is 564/yr; the
executable (top-ADV) tier yields only **~83/yr** — 21 months per 150 events even there.

## 2. ALTERNATIVE EVIDENCE METHODOLOGY IN THE CORPUS

Searched: RESEARCH_PROGRAM.md (§5.2 six elements, §6.1 admissibility R1–R17, weighted ranking
rule), g1_harness registrations, LC cards, decision records. Findings:
- **G1 registered-family precedent (authoritative):** a retained family {C2, C3} with Holm α=0.05
  across the family at primary k=5 (k∈{3,5,10}) exists. This solves **multiplicity**, not power:
  Holm across a family makes per-member bars *stricter* and requires multiple credible live
  members. It does not raise the information rate.
- **LC-PM-0010 (literature-grade only):** event-study methodology citing Shapiro–Wilk + Wilcoxon
  signed-rank for non-normal paired data. A literature card — not a governance-validated estimator;
  and a signed-rank test on the same paired series has comparable power characteristics (it does
  not manufacture observations).
- **No authoritative sparse-event / exact-binomial / sequential / alpha-spending methodology
  exists anywhere in the corpus.** Stated plainly per the review instruction.

## 3. THREE QUESTIONS, SEPARATE

- **A. Positive expectancy at all?** Unknown and unprovable prospectively at realistic n. The
  pooled in-sample point estimate is −1.16% (suggestive), but the preregistered day-weighted
  estimand is **+0.17% in-sample** (estimand dependence disclosed in V1.1 §11) and the pooled
  statistic failed FM-liquidity incrementality (t=0.49) with a mid-cap pocket profile. There is no
  estimand on which the candidate currently shows both an effect and incrementality.
- **B. Clears the institutional +0.50%/trade economic bar?** As a *filter*, the historical pooled
  avoided-loss spread (−1.16%) exceeds 0.50% — but that statistic is (i) event-weighted, (ii)
  regime-clustered (25% of events in the drawdown state), (iii) absent in the top-ADV tier, and
  (iv) not incremental after liquidity controls. The day-weighted version clears nothing. So: no
  demonstrated bar-clearing under the honest estimand.
- **C. Enough observations to establish B in a reasonable timebox?** **No.** Power arithmetic:
  pooled per-event estimand at σ≈8%, Δ=0.50%, one-sided α=0.05, power 80% ⇒ ~3,100 events per
  group ⇒ **5.6 years** of veto accrual at 564/yr (3.3 years even at the widest declared variant,
  965/yr — and the widest variant is a post-hoc widening). Preregistered day-weighted estimand at
  σ=11.1% ⇒ ~3,060 sessions ⇒ **12.1 years**. 24-month MDE (pooled, most generous variant):
  ≈0.53–0.67% — still above the 0.50% bar.

## 4. HISTORICAL PRIOR EVIDENCE (strongest already on record)

- **Sample:** 898 veto events / 6,293 control events (frozen spec, suspension-clean).
- **Walk-forward results:** NONE. No walk-forward execution was ever registered for this candidate.
- **OOS results:** NONE. Flow data begins 2025-01; no historical holdout exists.
- **Cost treatment:** spread reported gross; filter economics only as 40/50/60bp non-gating
  sensitivity.
- **Stability:** pooled spread negative in 4/4 half-years at all six declared threshold cells —
  the strongest stability fact on record — but the day-weighted estimand is +0.17% (estimand
  dependence).
- **Drawdown / concentration:** never computed as a strategy (no implementation existed);
  concentration: mid-ADV pocket (ADV-top +0.07%), top-10 tickers 15% of events, 25% of events in
  the drawdown regime.
- **Signal frequency:** 564/yr (frozen spec); 1.3 per-ticker/yr; 38% zero-event sessions.
- **Prior governance verdicts:** never registered. Family #3 = AVOIDANCE → parked; adversarial
  pass = downgraded after FM-liquidity failure; protocol V1.1 = estimand-dependence disclosure.
- **Authoritative vs exploratory:** **EVERYTHING is exploratory/discovery-grade.** No component of
  this candidate's evidence base is authoritative in the governance sense. The strongest
  discovery-grade evidence is the pooled −1.16% spread with 4/4-half stability — concurrently
  documented with its own incrementality failure.

## 5. PROSPECTIVE DESIGN OPTIONS (comparison, no selection bias)

| | A. TFB standalone pooled | B. TFB in a strategy-family framework (G1/Holm precedent) | C. No TFB experiment | D. Higher-frequency validated mechanism |
|---|---|---|---|---|
| Information gained | pooled-spread replication | replication + multiplicity-controlled family inference | none on TFB | potentially real edge info |
| Sample in 12 / 24 mo | ~564 / ~1,128 veto | same per member (Holm worsens) | — | n/a — no mechanism exists |
| MDE at 24 mo (80%/5% 1-sided) | ≈0.53–0.67% (> 0.50% bar) | worse (Holm) | — | — |
| Governance complexity | high (estimand war: pooled vs day-weighted) | highest (family selection = new dof) | none | highest (would need new validation) |
| Researcher-dof risk | high (pooled estimand re-introduces the misleading statistic; family selection post-hoc = mining) | high | low | high |
| Establishes +0.50%/trade bar in 24 mo? | **No** (MDE > bar) | **No** | — | **No corpus candidate** |

## 6. NO SAMPLE-SIZE FICTION

The honest statement, exactly: **TFB cannot establish the +0.50%/trade institutional claim within
24 months under its current signal rate — under any declared estimand, any declared threshold
variant, or any estimator that exists in the governance corpus.** The pooled estimand reaches a
~0.53–0.67% MDE at 24 months (above the bar) and is disqualified by concentration, regime
clustering, and its own incrementality failure; the preregistered day-weighted estimand needs
~12 years and showed a positive in-sample mean. None of the six forbidden escapes (lower MDE,
indefinite timebox, relaxed standard, unrelated pooling, universe change, invented precedent) is
applied here.

## 7. DECISION: **C — INFEASIBLE**

Do not spend prospective validation capacity on TFB. The candidate closes as
**UNRESOLVED — DEPRIORITIZED (cannot be powered)** — an honest, permanent status distinct from
FAIL: it was never testable at the institutional bar, and its in-sample day-weighted evidence is
already unfavorable.

**What replaces TFB as the next prospective research target: nothing in the validated corpus
qualifies** (Option D fails: every higher-frequency construction in the record failed its family
kill rules; the only high-frequency fact — the program-wide contrarian pattern in visible buying —
is not a packaged strategy). The prospective slot should stay **empty of inferential protocols**
until a candidate exists with prior × frequency × feasibility jointly satisfied. Separately, and
independent of any experiment: the owner may still choose to run the capture service as **pure
data-asset preservation** (vendor history decays; only near-session captures are durable) with NO
inferential protocol attached. That is an infrastructure decision, not a validation experiment,
and must not be conflated with one.

No registration. No execution. No code changes. No scheduler activation.
