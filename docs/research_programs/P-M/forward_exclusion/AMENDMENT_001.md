# FWD-PM-VOLEX-001 — AMENDMENT 001

**Date:** 2026-09-16 · **Status:** DRAFT, awaiting owner decision
**Effect if adopted:** adds pre-declared SECONDARY series. **The primary is unchanged.**

---

## 1. What prompted this

A same-day discovery pass established that IDX auto-rejection band contact
**subsumes** the Parkinson volatility measure the primary uses. In a bivariate
cross-sectional regression on forward 21-day returns:

| | coefficient | t |
|---|---|---|
| band contact (trailing 60) | **−5.77%** | **−3.61** |
| Parkinson-60 range volatility | +0.10% | +0.06 |

The underlying effect is large and survives the controls that would kill it:

- limit-down (ARB) contact → **−4.2% to −5.1%** over the next 21 sessions,
  t = −8 to −10, ~2,700–3,200 events. Negative in **all three** band regimes in
  **both** implementations: R1 −4.39%/−8.78%, R3 −8.62%/−12.72%, R4 −2.56%/−5.03%
  (independent / original), every cell significant
- it is not merely "the stock fell a lot": a fall to 85–95% of the band gives
  −1.4% to −2.6%, a fall **to** the band gives −4.2% to −5.1%; the difference is
  **−2.5 to −2.8 points, t = −3.45 to −3.76**
- controlling for fall size in a day-clustered regression, the band dummy
  survives at **−2.9% to −3.4%, t = −2.56 to −3.13**
- replicated by an **independent reimplementation** (long-format numpy, positional
  forward returns, raw prices with explicit split exclusion, no shared library)

Ranges are given because the two implementations differ by ±20% on levels; the
*difference* — the actual claim — is stable and slightly stronger in the cleaner one.

## 2. Why the primary is NOT being changed

The obvious move is to swap the primary onto the better signal. The power
arithmetic forbids it. Per-period dispersion, measured on the 45-period
in-sample series:

| rule | mean/mo | SD/mo | months to power its own mean |
|---|---|---|---|
| **A · Parkinson top-decile (current primary)** | +0.403% | **0.669%** | **17** |
| E · band contact OR Parkinson (union) | +0.633% | 1.829% | 52 |
| D · either band contact | +0.481% | 1.740% | 81 |
| B · ARB contact alone | +0.406% | 1.519% | 87 |
| C · ARA contact alone | +0.168% | 0.745% | 122 |

*(80% power, one-sided α=0.05, against each rule's own in-sample mean.)*

The union's larger mean is more than cancelled by 2.7× the dispersion. Adopting
it would move the decision point from **2028-09 to beyond 2030**, or — if the
n=24 gate were left in place — would guarantee a non-rejection that cannot
distinguish "no effect" from "underpowered". **RESEARCH_PROTOCOL rule R2:**
*"corroboration from a test that could not have refuted the hypothesis carries
zero evidential weight."*

Parkinson is the weaker signal and the better **instrument**. Those are
different things, and the forward test needs the second.

## 3. What this amendment does

Adds two **pre-declared secondary series**, recorded from the next formation,
carrying **no decision weight**:

- **S1 · band-contact membership.** For each formation, the subset of the
  universe with ≥1 auto-rejection band contact in the trailing 60 sessions,
  and its realised forward-21d return.
- **S2 · union cohort.** The union of S1 and the primary's Parkinson decile.

Pre-declaring them now means that if the primary passes and the secondaries are
later examined, they are not post-hoc. It also starts their clock: at ~52 months
S2 becomes independently testable, which is only possible if collection begins now.

**Multiplicity is unaffected.** The primary remains k=1. Secondaries are
descriptive; no secondary result may be reported inferentially, promoted to
primary, or used to reinterpret the primary outcome. This is the same treatment
§12 already gives the existing secondaries.

## 4. What this amendment does NOT do

- does not change the universe, estimator, exclusion fraction, entry convention,
  horizon, benchmark, cadence, session guard, decision rule, or α
- does not change the n=12 read / n=24 decision structure
- does not add a candidate to the decision set
- does not alter any recorded formation

## 5. Band-contact definition (frozen here, for S1)

Contact on session *t* if the **raw** close-to-close move breaches the band in
force, within 5%:

```
ARA (upper), constant across the corpus:
    prior close <= Rp 200   -> 35%      > Rp 5000 -> 20%      else 25%
ARB (lower), by published IDX decree:
    R1  2021-07-05 .. 2023-06-04   7%
    R2  2023-06-05 .. 2023-09-01   15%
    R3  2023-09-04 .. 2025-04-07   tiered, same as ARA
    R4  2025-04-08 .. present      15%
```

- computed on **raw, as-traded** prices — the band applies to raw prices, not
  adjusted ones

**The table above is verified against the data, not merely cited.** The daily
return distribution shows a sharp floor at exactly the claimed level in every
regime, with 14-27x more mass sitting AT the band than beyond it:

| regime | claimed ARB | 0.1st pctile of daily returns | at band | beyond band | ratio |
|---|---|---|---|---|---|
| R1 | 7% | −9.0% | 1.942% | 0.142% | **13.7x** |
| R2 | 15% | **−14.9%** | 0.307% | 0.019% | **15.9x** |
| R3 | tiered 35/25/20 | −24.6% | — | — | — |
| R4 | 15% | **−14.9%** | 0.446% | 0.016% | **27.2x** |

The residual mass beyond the floor is corporate actions (the −98.1% and −95.0%
minima are unadjusted splits) and special-board names, which is why §5's split
exclusion is load-bearing.
- **split / bonus / reverse ex-dates are excluded**, sourced from
  `corporate_action_events` **∪** `corporate_actions`. This is load-bearing:
  `corporate_actions` holds 101 split ex-dates, `corporate_action_events` 292.
  A 5:1 split is a −80% raw move, which passes the research harness's
  `|ret|>0.9` guard and would register as a false limit-down contact — RAJA
  (2026-07-16, −81.0%) and RMKE (2026-07-17, −82.1%) do exactly that
- **future rule changes:** the band in force is whatever IDX has decreed for that
  session. A decree during the test is recorded in the deviation log and does
  **not** invalidate it — the rule is exogenous and publicly observable. It is
  logged, never retro-applied.

## 6. Known limitation carried

The mechanism is unresolved. The drafted `HYP-PM-0008` identification design
separates I1 (band pinning) from I10 (salience/attention) by treating ARB as
treatment and ARA as placebo — but run on this corpus **the placebo moves**:
ARA R3 +2.01% (t=+0.40) → ARA R4 −5.19% (t=−2.37), across dates when the ARA
rule did not change. The design therefore separates neither. S1 is registered as
an **economic** series, not a mechanism claim: it is not necessary to know why
limit-down names keep falling in order to stop holding them.

Separately and materially: producing the evidence above **spent the in-sample
blindness of HYP-PM-0008**, whose spec states that zero empirical tests were run
in producing it. Any confirmatory test of that hypothesis must now be prospective.

## 7. Owner decision

- [ ] **ADOPT** — record S1/S2 as pre-declared secondaries from the next formation
- [ ] **DECLINE** — primary continues unchanged, band contact stays an unregistered
      discovery result
- [ ] **REPLACE the primary with the union** — *recommended against*: pushes the
      decision beyond 2030 or guarantees an uninformative null (§2)

Adopting changes no number in the primary test and cannot affect its verdict.
