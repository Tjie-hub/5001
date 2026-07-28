# Worked Example — End to End

**Layer:** L2 — Research Architecture (proof artifact) · **Status:** Canonical example · **Version:** 1.0 · **Date:** 2026-07-15
**Purpose:** Prove the Research OS architecture *composes* — that every object in the [[RESEARCH_OBJECT_MODEL]] and every Stage (S1–S10) of the pipeline can be instantiated on paper for one mechanism, using **data classified Available Today** in [[DATA_FEASIBILITY_STUDY]]. This is the cheapest possible de-risking of Layers L3–L8. **No code is written here** — this is a paper trace.

**Mechanism chosen:** *Amihud Illiquidity premium* — deliberately anchored on the deepest, most reliable dataset (`ohlcv`, 5 yr) so the example is executable today and not blocked on short-history feeds.

---

## S1 · Literature Discovery → **Literature Card**

```
card_id:              LC-2026-0001
source:               Amihud, Y. (2002), "Illiquidity and stock returns", J. Financial Markets
identified_mechanisms:[ illiquidity_premium ]
empirical_claims:     [ "Expected returns are increasing in the Amihud illiquidity ratio",
                        "Effect is stronger for small/illiquid names",
                        "ILLIQ = avg( |return_d| / value_traded_d )" ]
limitations:          [ "US large-cap sample; monthly horizon; pre-2000 microstructure" ]
```

## S2 · Mechanism Identification → **Economic Mechanism**

```
mechanism_id:      MECH-illiq-premium
classification:    Liquidity / Inventory-Risk compensation
causal_graph:      [investors demand compensation for expected price impact]
                     → [illiquid stocks priced at a discount]
                     → [higher expected forward return]
half_life_estimate: months-to-quarters (not an HFT effect → suits daily data)
persistence_theory: limits-to-arbitrage — illiquidity itself deters the arbitrage
                    that would remove the premium (self-enforcing)
```
*Passes the "must not violate market micro-economics" gate: compensation for impact is first-principles sound.*

## S3 · Hypothesis Registration → **Hypothesis Object** (Gate G1)

```
hypothesis_id:        HYP-2026-0007
mechanism_ref:        MECH-illiq-premium
prediction:           Top-quintile Amihud names earn higher forward 1-month returns
                      than bottom-quintile, cross-sectionally, within the liquid IDX universe
null_hypothesis:      No forward-return difference across Amihud quintiles (H0: Δ = 0)
alternative_hypothesis: Δ_return(Q5 − Q1) > 0
required_data:        [ ohlcv ]              # Available Today (5 yr) ✅
validation_criteria:  { horizon: 21td, min_n_months: 36, alpha: 0.05,
                        family: CROSS_SECTIONAL_LIQUIDITY_2026, DSR_min: 0.90,
                        net_of_cost: true, MDE: 0.30%/month }   # pre-registered ex-ante
preregistration_hash: sha256(<this object, frozen>)            # immutable once REGISTERED
preregistered_at:     2026-07-15T00:00:00Z
status:               REGISTERED
```
**G1 check:** falsifiable ✅, thresholds ex-ante ✅, data in-scope ✅ → **APPROVED to test.**

## S4 · Data Preparation → **Dataset Object** (bound)

```
dataset_id:         DS-ohlcv-2021_2026-liquid
asset_class:        IDX equities, liquid universe (ADV ≥ VALUE_LIQ_MIN_IDR)
resolution:         Daily
regime_classification: mixed (BULL/BEAR/SIDEWAYS present across 5 yr)
provenance_hash:    <research.tracking.dataset_fingerprint>   # reuse v3 mechanism
immutability:       split-adjusted snapshot pinned to fingerprint
```
*G-check: cryptographic immutability satisfied by the existing `dataset_fingerprint`.*

## S5 · Feature Construction → **Feature Definition** (in the FCG)

```
feature_id:            FEAT-amihud-illiq_v1.0
mathematical_formulation:  ILLIQ_i,t = mean_{d in t} ( |r_i,d| / (price_i,d · volume_i,d) )
code_reference:        (to be implemented in L5 — not built here)
dependencies:          [ ohlcv.close, ohlcv.volume ]   # daily return + traded value
version:               Amihud_v1.0_<git-hash>
determinism:           bit-identical (pure function of ohlcv snapshot)
```
*Node type in the [[FEATURE_COMPUTATION_GRAPH]]: Raw(ohlcv) → Return → ILLIQ. Acyclic ✅.*

## S6 · Experiment Execution → **Experiment Object**

```
experiment_id:      EXP-2026-0031
hypothesis_ref:     HYP-2026-0007
feature_set_ref:    FEAT-amihud-illiq_v1.0
in_sample_period:   2021-07 → 2024-06     # calibration (quintile breakpoints)
out_of_sample_period: 2024-07 → 2026-06   # validation — custody-enforced (S-note)
methodology:        monthly cross-sectional quintile sort; long Q5 / short Q1;
                    forward 21-td return; Newey-West t-stat; seed logged
```
*Custody note: quintile breakpoints fit on in-sample only; OOS window sealed until S7 (enforcement is an L7 deliverable — see [[RESEARCH_VALIDATION_FRAMEWORK]]).*

## S7 · Statistical Validation → **Validation Report** (draft) (Gate G3)

Reuses the v3 `research/gatekeeper` machinery ([[RESEARCH_OS_RECONCILIATION]] §4):

```
report_id:          VR-2026-0031
statistical_metrics: { point_Δ: +0.42%/mo, CI95: [+0.08, +0.76],
                       t_NW: 2.31, DSR: 0.88 (WATCH), PBO(CSCV): 0.19,
                       multiplicity_family: CROSS_SECTIONAL_LIQUIDITY_2026 (size 5) }
```
*G3: exceeds pre-registered CI bar; DSR in WATCH band; PBO below 0.5. Draft = WATCHLIST-equivalent.*

## S8 · Robustness Testing → **Validation Report** (finalized)

```
net_of_cost:        premium survives round-trip cost model? Δ_net = +0.24%/mo  (marginal)
liquidity_capacity: capacity binds — Q5 names are BY CONSTRUCTION illiquid;
                    market impact consumes much of the gross edge
regime_stability:   premium concentrated in high-vol regime; weak in low-vol
decay:              stable over the 5-yr sample (no monotone decay)
```

## S9 · Peer Review → **Reviewer Sign-off** + Gate G4

```
reviewer_signoff_id: SGN-2026-0031
reviewer:            Validation Reviewer (adversarial, independent)
economic_defense:    mechanism causality accepted (impact compensation)
methodology_audit:   reproducible from Hypothesis + methodology only ✅
verdict:             CONFIRM effect exists but CAPACITY-CONSTRAINED
```

## S10 · Knowledge Promotion → **Accepted Knowledge** OR **Failure Library**

Two illustrative outcomes — both paths exercised to prove the fork composes:

**If accepted:**
```
knowledge_id:       KNW-illiq-premium-2026
mechanism_ref:      MECH-illiq-premium
validation_ref:     VR-2026-0031
decay_monitor_id:   DEC-illiq-2026   # live tracker of ongoing validity (L8 object)
scope_caveat:       capacity-constrained; research knowledge, NOT a trade signal
```

**If rejected (e.g. net-of-cost Δ had crossed to ≤0):**
```
failure_id:         FAIL-2026-0031
hypothesis_ref:     HYP-2026-0007
mechanism_ref:      MECH-illiq-premium
experiment_ref:     EXP-2026-0031
failure_reason:     Destroyed by Transaction Costs / Capacity
invalid_assumptions:[ "premium exploitable at size" ]
lessons_learned:    "illiquidity premium is real but non-harvestable — archive to
                    prevent re-testing; informs capacity gate for future liquidity work"
related_features:   [ FEAT-amihud-illiq_v1.0 ]
```

---

## Object coverage checklist (proof the model composes)

| Object (from Research Object Model) | Instantiated | Extension? |
|---|---|---|
| Literature Card | ✅ S1 | core |
| Economic Mechanism | ✅ S2 | core |
| Hypothesis | ✅ S3 | core |
| Dataset | ✅ S4 | core |
| Feature Definition | ✅ S5 | core |
| Experiment | ✅ S6 | core |
| Validation Report | ✅ S7–S8 | core |
| Knowledge Object | ✅ S10 | core |
| Failure Library Entry | ✅ S10 (reject path) | core |
| **Regime** | ✅ S8 (regime_stability) | extension |
| **Cost Model** | ✅ S8 (net_of_cost) | extension |
| **Reviewer Sign-off** | ✅ S9 | extension |
| **Decay Monitor** | ✅ S10 (accept path) | extension |
| **Lineage Edge** | ✅ every `_ref` link | extension |

**Result:** every core object and every extension object appears at least once; all 10 Stages and Gates G1/G3/G4 are exercised; both the accept and reject terminal paths compose. The architecture is proven consistent on paper for an Available-Today mechanism. ✅
