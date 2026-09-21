# HYP-PM-0008 · REGISTRATION SPECIFICATION (DRAFT — NOT REGISTERED)

**Mechanism:** I1 · Price-limit (auto-rejection band) pinning — deferred demand under a truncated price path
**Date drafted:** 2026-09-14 · **Owner authorization:** Branch A, 2026-09-14 (authorization to *develop and register*, explicitly **not** to execute)
**Status:** **DRAFT — PENDING OWNER DECISION.** This document is a complete frozen specification awaiting four named preconditions (§20). **It is not a registration. No family slot is consumed. `HYPOTHESIS_REGISTRY.md` is unmodified.**
**Authority:** generated point-in-time record · **Governed by:** [[HYPOTHESIS_LIFECYCLE]] · [[RESEARCH_PROGRAM]] §5.2/§6.1 · [[MARKET_INEFFICIENCY_TAXONOMY]] I1 · [[EVIDENCE_MODEL]]

> **ZERO EMPIRICAL TESTS WERE RUN IN PRODUCING THIS DOCUMENT.** No return, band-contact event, outcome
> statistic, or power figure was computed from data. The only database access was read-only *coverage
> metadata* (table date-span and per-regime session counts, §9) required by the brief's own data-readiness
> criterion. No threshold in this document was chosen by inspecting an outcome.

---

## 0. Why the ID is 0008 and not 0007

`HYP-PM-0007` is **provisionally reserved**: `FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11.md` Part F
proposes mapping `research.db::hypotheses::BROKER-001` (BFI-001) to the alias `HYP-PM-0007` **if and only if
the owner ratifies** that mapping. That ratification is open. Taking 0007 here would collide with a pending
owner act, so this draft takes **0008** and leaves 0007 held.

---

## 1. Mechanism (M-class + constraint + participant class)

**Class:** M6 · market-design artifact. **Domain:** D1 · venue design. **Taxonomy entry:** I1.

IDX enforces an auto-rejection band (ARB on the downside, ARA on the upside) that mechanically forbids
execution beyond a bound computed from the previous session's closing price. When the lower bound binds at
the close of session *t*, the selling intent that would have cleared at a forbidden lower price **is not
extinguished — it is deferred**, and carries into session *t+1* as unexecuted supply.

**Constraint:** the band is a published exchange rule; no participant can transact at a price the venue
rejects. **Participant class:** all — the constraint is not participant-specific, which is why the barrier
is structural rather than behavioural.

**Directional prediction:** conditional on an ARB close-contact at *t*, the next-session return is
**negative** (continuation of the truncated direction), and its magnitude is **increasing in the severity of
truncation**, which is set by band width — an exogenous, decreed quantity.

**Barrier (R17 answer — "why has nobody taken this?"):** M6 structural. Per [[RESEARCH_PROGRAM]] §6.2 this is
the **highest barrier-durability class in the program's own ranking rubric** ("M6 structural (rule-based, no
capital removes it) > M4 > … > M5 behavioral"). No quantity of capital removes a price the venue forbids. Per
[[MARKET_INEFFICIENCY_TAXONOMY]] I1, decay here is a **step function on rule change**, monitored on the
rulebook, not on a return series.

## 2. Null hypothesis

Band width has no causal effect on next-session return conditional on ARB close-contact: the next-session
mean return following ARB close-contact is the same under a tight lower band as under a wide one
(θ_primary = 0). Under the null, any observed post-contact drift is attributable to rival originations that
do not depend on the rule — I10 salience/attention, intrinsic up/down asymmetry from short-selling
infeasibility (H_side), or plain momentum.

## 3. The identification problem, and how this design solves it

[[MARKET_INEFFICIENCY_TAXONOMY]] I1 imposes two binding design requirements, both load-bearing:

> "**Confounded with I10** (band contact is a salience event, so M5 attention is a rival origination for the
> same observation)… **A test that does not separate I1 from I10 tests neither.**"
>
> "**Required evidence: E4 floor (R10).** The discriminating test must separate *deferred demand* from
> *momentum*: both predict continuation."

A within-regime study of "what happens after a limit-down" **cannot** satisfy either requirement: salience,
momentum and deferral all predict the same sign on the same observations. This specification therefore does
**not** estimate a post-contact drift. It estimates the **change in that drift across an exogenous change in
the rule**.

**The instrument.** IDX changed the lower band twice inside the OHLCV corpus, on published decree dates
([[LC-PM-0009]]):

| Regime | Period | ARA (upper) | ARB (lower) | Lower band |
|---|---|---|---|---|
| R1 | 2021-07-05 → 2023-06-04 | 35/25/20% | **7%** | tightest |
| R2 | 2023-06-05 → 2023-09-01 | 35/25/20% | 15% | transition (~3 mo — excluded, §7) |
| **R3** | **2023-09-04 → 2025-04-07** | 35/25/20% | **35/25/20%** | **widest (symmetric)** |
| **R4** | **2025-04-08 → present** | 35/25/20% | **15% flat** | **tight** |

Attention, sentiment, manipulation and momentum do not switch on a decree date. **The band width does.**
This is the separation the taxonomy demands, and it is available only because the exchange changed the rule
inside the data window.

**The placebo that completes the separation.** Across R3→R4 the **ARA (upper) band is unchanged** (35/25/20%
throughout). Upper-band contact is equally salient and equally momentum-laden, but its rule did not move.
Therefore:

| | ARB side (rule changed) | ARA side (rule unchanged) |
|---|---|---|
| **I1 · band pinning (this hypothesis)** | effect **changes** R3→R4 | effect **unchanged** |
| **I10 salience / H_side / momentum** | effect **unchanged** | effect **unchanged** |

A rival origination cannot produce a change on the side whose rule moved while leaving unchanged the side
whose rule did not. This is a pre-specified, non-confirmatory placebo (§13).

## 4. Population and PIT universe

- Source: production `ohlcv` (fields `ticker, date, close, volume, is_final`). **No broker-flow table is
  consumed by any part of this specification** (see §17).
- `COALESCE(is_final,1)=1`; `ticker <> 'IHSG'`; `close > 0`.
- **PIT liquidity floor:** trailing 60-session median traded value (`close × volume`), computed with
  `shift(1)` (strictly prior sessions only), **≥ Rp 1,000,000,000**. Declared ex ante; not tuned; chosen as a
  round order-of-magnitude floor, not selected against any outcome.
- **Price floor:** `close(t−1) ≥ Rp 100` (program convention, inherited from BFI-001 §D / G1 §6).
- Sessions come from the `ohlcv` distinct-date calendar; *t−1, t, t+1* must be **strictly consecutive**
  sessions on that calendar.

## 5. Signal construction (formation)

All quantities use `close` only. **`open`, `high` and `low` are not used anywhere in this specification** —
`open` is closed out of the programme (G-1 failed; see `S1-PM-0005`), and `high`/`low` field integrity is
unverified, whereas `close` integrity was verified (`S1-PM-0006` Step 1: 0 null / 0 zero / 0 negative /
0 duplicate `(ticker,date)` over 1,054,382 rows).

```
reference(i,t)      = close(i, t-1)                      # IDX regular-board band reference
tier(i,t)           = 35% if  100 <= reference <=   200
                      25% if  200 <  reference <= 5,000
                      20% if        reference >  5,000
band_lower(i,t)     = tier(i,t)            if regime(t) == R3      # symmetric
                      0.15                 if regime(t) == R4
r(i,t)              = close(i,t) / close(i,t-1) - 1

ARB_contact(i,t)   := r(i,t) <= -( band_lower(i,t) - tol )
ARA_contact(i,t)   := r(i,t) >= +( tier(i,t)      - tol )        # placebo leg
tol                 = 0.005  (50 bp)
```

**`tol` rationale and its limitation (declared, not discovered):** IDX rounds the band to the tick grid, and
the IDX tick-size table **could not be extracted** ([[LC-PM-0006]]; `DISCOVERY_2026-08-21_M2x_short_horizon`
§7). An exact bound is therefore not computable from held data. `tol = 50 bp` is a single declared tolerance
absorbing tick rounding; it is **frozen here and may not be varied at execution**. Sensitivity at
`tol ∈ {25, 100} bp` is a reported robustness output, **never a confirmatory result** (§13).

**Formation timing:** the state is determined at the close of session *t* from `close(t)` and `close(t−1)`,
both known at *t*. No future information enters formation. No T+1-materialized artifact is consumed.

## 6. Entry timing, holding horizon, outcome

- **Entry:** close of session *t* (the session at which the band bound).
- **Outcome:** `y(i,t) = log( close(i,t+1) / close(i,t) )` — close-to-close, next consecutive session.
- **Primary horizon: k = 1.** Fixed before execution. The mechanism's own timescale is one session: deferred
  intent that survives the overnight is, by *t+2*, no longer distinguishable from fresh demand.
- **Secondary horizons k ∈ {2, 3}** are reported as robustness only and can never become the primary (§18).

## 7. Regime scope and exclusions

**Regimes used:** R3 (control, wide/symmetric) and R4 (treatment, tight) **only**.

- **R2 excluded** — ~3 months; [[LC-PM-0009]] transportability condition 6 designates it a transition, not a
  regime.
- **R1 excluded from the primary** — it is contaminated by a concurrent, non-band rule change (trading hours
  reverted to pre-pandemic on 2023-04-03, inside R1) and by the pandemic substrate. R1 enters only as a
  pre-specified, clearly-labelled dose-response *secondary* (§13), never as primary evidence.

**Observation-level exclusions (all pre-specified, all counted and reported):**

| # | Exclusion | Reason |
|---|---|---|
| E1 | Any of *t−1, t, t+1* missing from the session calendar, or non-consecutive | suspension / halt proxy; no held suspension table (§19) |
| E2 | `close` null / zero / negative at *t−1, t, t+1*; `volume = 0` at *t* or *t+1* | non-trading |
| E3 | A `corporate_actions` row exists for the ticker with `date ∈ [t−1, t+1]` | the band is computed off a reference price a split/dividend redefines ([[LC-PM-0009]] condition 4) |
| E4 | Ticker `RAJA` | mixed OHLCV adjustment basis (`DATASET_B_SEMANTIC_REGISTER_v1`: `ohlcv.close/volume` VERIFIED WITH DEFECT) |
| E5 | The ticker's first 20 sessions of appearance in `ohlcv` | IPO first-day bands are 2× normal ([[LC-PM-0009]] condition 3); no listing-date table is held (§19). Left-censoring at 2021-07-05 is declared and does not bind on R3/R4 |
| E6 | Sessions where IHSG `r(t) ≤ −8%` | 2025-04-08 changed halt thresholds **simultaneously** with the band ([[LC-PM-0009]] condition 5 — compound treatment); this removes the sessions on which the compound arm can bite |
| E7 | `close(t−1) < Rp 100`; PIT liquidity floor unmet | §4 |

## 8. Primary estimand — ONE test

Cross-sectional means are aggregated **to a daily series first**, then tested — the program's registered
convention (BFI-001 §G/§I; C3 and C7 both executed this way), which prevents cross-sectional correlation
within a date from inflating the test statistic.

```
Step 1   For each session date d in R3 ∪ R4 with >= 1 qualifying ARB-contact event:
             m(d) = mean over qualifying events i of  y(i,d)
         Dates with zero qualifying events are skipped and counted (not zero-filled).

Step 2   OLS on the daily series:      m(d) = alpha + theta * 1{ d in R4 } + e(d)
         Newey-West standard errors, lag = 5.

PRIMARY  theta_primary = the fitted coefficient on 1{d in R4};  two-sided p.
```

**`theta_primary` is the single primary result.** Nothing else in this document can become the primary.

**Directional prediction:** `theta_primary < 0` — the tight-ARB regime defers *more* selling, so
next-session continuation is *more* negative under R4 than under R3.

**Direction is read after execution, never prejudged in the output** (BFI-001 §G convention): the harness
reports the signed coefficient and its two-sided p; the sign is compared to this document's pre-registered
prediction only at interpretation.

## 9. Data readiness (coverage metadata only — no outcome computed)

Read-only coverage check on production `ohlcv`, 2026-09-14:

| Fact | Value |
|---|---|
| Corpus span / rows / tickers | 2021-07-05 → 2026-09-14 · 1,085,437 rows · 959 tickers |
| **R3 sessions (control)** | **377** |
| **R4 sessions (treatment)** | **343** |
| `corporate_actions` rows | 2,171 (`ticker, date, action, value, source`) |

Both arms exist with comparable session counts, on ~10× the calendar span of frozen Dataset B (386
sessions). **No event count, no return, and no outcome statistic was computed** — event counts are the
subject of the §11 preflight gate and are deliberately unknown at registration.

## 10. Controls

- **Regime is the treatment**, not a nuisance control — no additional regime control is admitted.
- **The ARA-side placebo (§13) is the control for salience/momentum**, not a covariate.
- **No return-based or flow-based covariate is admitted.** Adding covariates post hoc is R7.4/R15 territory.
- Liquidity and price enter only as *universe filters* fixed in §4, never as estimated controls.

## 11. Power / MDE — and the pre-execution feasibility gate

The event count is **unknown by design**: computing it is a data-touching act the Branch A authorization
forbids, and the discovery record that surfaced this candidate identified exactly this count as its one
open barrier ("that count is an S2 feasibility task… computing it is exactly where discovery would start
contaminating confirmation" — `DISCOVERY_2026-08-21_M6_I1_price_limits` §6).

The MDE is therefore declared **ex ante from assumed parameters, frozen here**, and the sample is checked
against it **before** any outcome is computed:

| Parameter | Declared value | Source of the value |
|---|---|---|
| Δ (minimum detectable difference) | **0.60%** | the estate round-trip friction floor — the §6.1 F4 bar; an effect below it is a free kill |
| σ (assumed sd of the **daily series** `m(d)`) | **2.0%** | declared ex ante, **not measured**; a conservative round figure |
| α / power | 0.05 two-sided / 0.80 | program convention |
| ⇒ **required event-days per arm** | **n ≥ 175** | n = 2σ²(z_{α/2}+z_β)²/Δ² = 2(0.02)²(2.802)²/(0.006)² ≈ 174.4 |
| ⇒ **required events per arm** | **N ≥ 1,090** | same expression at the event level with σ_event = 5.0% (declared, not measured) |

**FEASIBILITY GATE (binding, pre-outcome).** At preflight the harness counts qualifying ARB-contact
**events** and **event-days** per arm — counts only, with the outcome column not read. Then:

- If **both** arms satisfy `event-days ≥ 175` **and** `events ≥ 1,090` → the gate opens; execute §8 once.
- Otherwise → **the test is not run.** The hypothesis terminates as **RETIRED — UNPOWERED**, which is a
  terminal state that is **explicitly not a failure** ([[HYPOTHESIS_LIFECYCLE]] §3.1; [[RESEARCH_PROGRAM]]
  §4) and must never be filed as `FAILED` or entered in the Failure Registry as one.

This gate is the R2 answer ("the test CAN fail") and simultaneously the honest treatment of the one barrier
the discovery record left open. **The R3 arm is where it is most likely to bite**: under R3 the lower band
is 20–35% wide, so close-contact should be far rarer than under R4's flat 15%. A shortfall there is a
legitimate, pre-registered, non-failure outcome — not a reason to widen `tol`, lower the floor, or pool R1.

## 12. Inference method

- Newey-West HAC, lag = 5, on the daily series regression of §8. Two-sided p.
- **Multiplicity:** the primary is a **single cell** — Holm at the primary is the identity
  (`holm_p = raw two-sided p`). Every other quantity in this document is non-confirmatory (§13) and enters
  no Holm family.
- **No bootstrap, no clustering beyond the daily aggregation, no alternative estimator** may be substituted
  at execution.

## 13. Secondary and non-confirmatory outputs (exhaustive; none can become primary)

| # | Output | Status |
|---|---|---|
| S1 | **ARA-side placebo** — §8 re-run on `ARA_contact`. I1 requires this to be **null**; a placebo as large as the primary falsifies the *band* reading even if the primary is significant | **pre-specified placebo**, interpretive, not confirmatory |
| S2 | Horizons k ∈ {2,3} | robustness |
| S3 | `tol ∈ {25,100} bp` sensitivity | robustness |
| S4 | R1 dose-response (7% / 15% / 20–35%) | secondary, **labelled contaminated** (concurrent 2023-04-03 trading-hours change) |
| S5 | Per-tier split (35/25/20) | descriptive only — tier is endogenous to price level |
| S6 | `theta_net = theta_primary − 0.006` | **reported cost sensitivity, never a statistical verdict** (program convention) |
| S7 | Event counts, exclusion counts per rule, skipped-date counts | provenance |

## 14. Cost model

Estate round-trip floor **0.60%**, applied as the §13 S6 sensitivity only. Per [[RESEARCH_PROGRAM]] §1.1 /
PG-12, profit is not evidence; the cost figure never converts a statistical result into a verdict.

## 15. Missing-data, corporate-action, and suspension rules

- **Missing data:** no imputation, no forward-fill, no interpolation, ever. A missing input at *t−1, t* or
  *t+1* removes the observation (E1/E2) and increments a counted exclusion.
- **Corporate actions:** E3 removes the observation outright. No reference-price reconstruction is attempted —
  attempting one would require an adjustment basis the corpus does not uniformly hold (E4).
- **Suspensions:** no suspension table is held (§19). Suspension is proxied by session-calendar
  non-consecutiveness plus zero volume (E1/E2). This is a **declared proxy, not a measurement**.

## 16. Kill rule / refutation condition (R14 — one sentence)

> **If `theta_primary` is not negative with two-sided p < 0.05 under the §8 specification, the hypothesis
> that IDX auto-rejection band width causally defers selling demand into the following session is refuted,
> and HYP-PM-0008 terminates as FAILED (mode F2 · prediction failure).**

## 17. Semantic-register gate compliance (D-049 `all-broker-net-identity`)

The gate adopted by **D-049** governs "all future broker-flow research". Compliance is **trivial and
total**: this specification consumes **no broker-flow field of any kind** — no `value`, no `lot`, no
`value_total`, no `investor_type`, no `freq`, no `bandar_detector` field, and no Dataset B table. Its entire
input surface is `ohlcv.{ticker,date,close,volume,is_final}` plus `corporate_actions`. The five required
validations resolve as:

1. **Accounting identity check** — N/A; no net is constructed from two sides of one transaction population.
2. **Semantic source verification** — `close` is a traded price, not a signed side aggregate; integrity
   independently verified (`S1-PM-0006` Step 1).
3. **Aggregation-level verification** — N/A; no broker aggregation exists.
4. **Truncation behavior** — N/A; the top-25 disclosure truncation that voids `broker_flow` nets does not
   touch `ohlcv`.
5. **PIT availability** — §5: formation uses `close(t)` and `close(t−1)` only, both known at *t*.

**This is the substantive reason the candidate survives.** The identity defect that invalidated HYP-PM-0003
and BFI-001's primary, and the `freq` UNKNOWN semantic that withdrew C1a/C1b, are both *instrument*
defects in `broker_flow`. A hypothesis that does not touch that instrument inherits none of them.

## 18. No-rescue rule

Frozen at registration, binding on every future session:

1. **A null under §16 is terminal.** Continuation is possible only via T12 supersession — a new, dated
   registration consuming its own family slot.
2. **No re-cut may be promoted to primary** after seeing an outcome: not by tier, liquidity band, side
   (ARB↔ARA), horizon, `tol`, sub-period, regime re-pooling, or universe floor.
3. **`tol`, the liquidity floor, the price floor, the horizon, the regime boundaries, and the exclusion set
   are frozen by this document** and may not be varied at execution. A variation is R7.4 threshold migration
   / R15 rescue and retroactively deletes the evidence.
4. **The feasibility gate outcome is not negotiable**: a shortfall yields RETIRED — UNPOWERED, never a
   relaxed re-run.
5. **The descriptive figures in [[LC-PM-0007]] (+2.44% ARA close-to-open, China) and `S1-PM-0006`
   (−0.587% after ≥10% falls) are CONTEXT ONLY.** They did not set, and may not set, any threshold,
   horizon, direction, or decision rule here.

## 19. Interpretation rule — and the capturability declaration made *before* any result

**Declared now so it cannot be spun later.** This is a **gross, directional, knowledge-producing test. It is
not a capital claim**, and a confirmation must never be reported as one:

- A confirmed ARB-side continuation is **downward**. Capturing it requires **short-selling**, which IDX does
  not practically permit. The capturable leg **does not exist**.
- The ARA side is the long-capturable direction, but [[LC-PM-0007]] establishes that at a limit-up the queue
  is composed of buyers, so a late arrival is not filled: *the mechanism that creates the effect excludes
  you from it.*
- This is structurally **the HYP-PA-0001 situation** — whose ADD-side effect was real (+1.89%, WCB
  p = 0.0132) and still did not rescue the hypothesis, because it was pre-registered gross-only and not
  capturable.

Accordingly: the maximum product of this registration is a **mapped efficiency boundary** — which
[[RESEARCH_PROGRAM]] §8 counts as a first-class asset "of equal standing to a validated mechanism" — and
**never a promotion to shadow or capital**. Terminal reachable evidence tier is **C2** (EV-9/LIM6/LIM8: the
N=1 adversarial-review ceiling), as for every hypothesis in this institution.

**The owner must decide whether a permanent family slot is worth a knowingly non-capturable test (§20 D-3).**

## 20. BLOCKERS — the four preconditions, none of which this document may resolve

| # | Blocker | Why it is not mine to resolve | Resolver |
|---|---|---|---|
| **B1** | **Family / multiplicity determination.** I1 belongs to **no open family** (`DISCOVERY_2026-08-21_M6_I1_price_limits` §6). Worse, the taxonomy records I1 as **confounded with I2 and I3** — both already inside **P-A's declared family {I2, I3, I8}** — and **modified by I12**, inside **P-M's {I5,I6,I7,I12}**. PG-7 makes confound-driven merges *mandatory*, but §2.1/D-028 **closed the merge window**: "a family may never later be narrowed or split… the only future remedy is termination and a new family from zero, forfeiting every survivor." | This is a multiplicity-family act reserved to the Owner/CRO. The brief instructs: STOP before changing the registry. | **Owner** |
| **B2** | **Primary verification of the two decrees.** [[LC-PM-0009]] grades its own regime timeline "corroborated but **NOT primary-verified**" (AEI primary source robots-disallowed) and states that primary verification of the **2023-09-04** and **2025-04-08** decrees is "a **hard S2 prerequisite, not a nicety**", because for an M6 claim B8 market-structure obsolescence is **fatal**. **Discrepancy to resolve:** `DATASET_B_SEMANTIC_REGISTER_v1` records the same bands with status **`VERIFIED`** — which the card it cites does not support. The whole identification rests on these two dates. | Requires retrieving SK Kep-00003/BEI/04-2025 and the 2023 "Auto Rejection Simetris Tahap II" decree — an external document-retrieval act, not an inference. | **Owner / researcher** |
| **B3** | **Feasibility gate outcome unknown** (§11). Admissibility gate §6.1 auto-rejects a candidate where "the test could not fail (no power/MDE) — R2". The MDE is declared (§11); whether the sample meets it is unknown and **must not be computed under a Branch A authorization**. | Branch A forbids data-touching execution; the count is the §11 preflight's first act. | **preflight, post-authorization** |
| **B4** | **Two exclusion instruments are not held.** Verified absent this session: **no board-membership table** (Papan Pemantauan Khusus — a full-call-auction, ±10% *different market mechanism* that [[LC-PM-0009]] condition 2 requires excluding) and **no listing-date or suspension table**. `idx_tickers.in_idx80` is `REJECTED FOR RESEARCH USE` (stale 2026-04-27 snapshot). E5/E1 are declared **proxies**, not measurements. | Either accept the proxies on the record, or admit new data. | **Owner** |

### The three owner decisions, stated exactly

- **D-1 (B1) — Family determination.** Choose one, on the D-048 Option-B precedent:
  **(a)** open a new separately-denominated family (e.g. "P-M · L-family", members {I1}), explicitly making
  **no** I-taxonomy merge and recording the I1↔I2/I3/I12 confounds as a preserved, non-blocking caveat;
  **(b)** register HYP-PM-0008 **into P-A's {I2, I3, I8}** family on the I1↔I2/I3 confound, accepting a 2nd
  P-A slot; **(c)** refuse registration on the ground that the mandatory PG-7 merge is unavailable post-D-028.
  *No option may be taken silently; each changes a permanent denominator.*
- **D-2 (B2) — Decree verification.** Authorize primary retrieval of the two decrees, **or** accept the
  Q3 secondary corroboration on the record as sufficient for an M6 registration (and accept B8 exposure),
  **or** hold the registration until retrieval.
- **D-3 (§19) — Knowingly non-capturable test.** Confirm that a permanent family slot may be spent on a
  gross-only test whose capturable leg is structurally absent, on the HYP-PA-0001 precedent.

---

## 21. What this document does NOT do

Does not register HYP-PM-0008 · does not consume a family slot · does not modify `HYPOTHESIS_REGISTRY.md`,
`FAILURE_REGISTRY.md`, `DECISION_LOG.md`, or `EXPERIMENT_LEDGER.jsonl` · does not execute anything · does not
compute any return, event count, or power figure from data · does not touch Dataset B, the semantic register,
`g1_config`, C3, C7, C8, or any production database (the §9 check was read-only coverage metadata) · does not
open, narrow, widen, or pool any multiplicity family · does not create a terminal verdict.
