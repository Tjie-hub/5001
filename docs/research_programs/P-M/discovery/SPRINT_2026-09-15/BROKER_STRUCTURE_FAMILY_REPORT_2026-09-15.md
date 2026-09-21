# FAMILY #4: BROKER-STRUCTURE (investor-class split) — FAMILY REPORT

**Date:** 2026-09-15 · family-by-family discovery, family 4 of 6 · DISCOVERY ONLY.
**Representation tested (genuinely new):** per-broker `investor_type` classes on frozen Dataset B —
**Asing (24 brokers) / Lokal (66) / Pemerintah (4)**, i.e. foreign vs local vs government *broker
domicile classes*. Classic IDX "foreign flow" proxy. **Broker domicile is not end-investor identity**
(program rule). Class constancy verified: 0 of 94 brokers change class. All-broker net ≡ 0, so the
three class nets sum to zero (2 degrees of freedom). Coverage: 30,554 liquid tradable obs (IDX100,
2025-01..2026-08-27, suspension-clean). Declared skip-list honored (aggregate lean, concentration,
persistence, labels — already dead).

## VERDICT: **DEAD — close broker-structure entirely.**

All 12 declared constructions fail the entry kill rule; every FM coefficient is **negative** with
strong t — the same contrarian texture as the bandar family. h5 results (net of 60bp in parens):

| Construction | n | h5 (net) | FM β (t) |
|---|---|---|---|
| F1 foreign inflow (Asing z ≥ +1) | 3,154 | +0.29% (−0.31%) | **−0.90% (−5.26)** |
| F2 foreign outflow [mirror] | 3,433 | +0.25% (−0.35%) | −0.55% (−3.09) |
| F3 foreign intensity (Asing net/ADV ≥ 5%) | 9,890 | +0.13% (−0.47%) | **−0.84% (−7.88)** |
| F4 disagreement: foreign buys / locals sell | 10,407 | +0.15% (−0.45%) | **−0.79% (−7.54)** |
| F4b mirror | 13,353 | +0.24% (−0.36%) | — |
| F5 Pemerintah event (|net| ≥ 1% ADV) | 27,443 | +0.17% (−0.43%) | — |
| F6 foreign persistence ≥3d | 4,488 | 0.00% (−0.60%) | **−0.89% (−7.35)** |
| F7 foreign flip after 3d run | 1,610 | −0.21% | — |
| F8 foreign absorption (down-day + foreign buy) | 650 | +0.21% | −0.60% (−2.24) |
| F9 foreign distribution (up-day + foreign sell) | 873 | +0.81% (+0.21%) | −0.40% (−1.12); w/ liquidity +0.20% (0.55) |
| F10 foreign activity-share surge z≥2 | 802 | 0.00% | +0.12% (0.47) |
| F11 F1 ∩ ADV top tercile | 2,399 | +0.10% | — |
| F12 quartile profile in up-moves | — | flat (0.51–0.56% across quartiles) | — |

Key readings:
1. **Foreign inflow/outflow, disagreement, and persistence are all *contrarian-negative*** after
   price/volume/platform-flow controls — quantitatively the same signature as bandar breadth and
   platform chasing. On IDX in 2025-26, *any* visible "someone is buying" metric — retail platform,
   broker breadth, or foreign-broker class — loads **negatively** on forward returns once the
   price/volume/liquidity state is held fixed.
2. The only nominally positive cell (F9, foreign selling into up-moves, +0.81% gross) fails
   breadth (n=873), decays monotonically across halves (+1.52 → +0.96 → +0.18 → −1.31%), and has
   no FM incrementality with a liquidity control (t=0.55). It is the mirrored, weaker cousin of the
   already-parked platform-outflow observation.
3. No avoidance-grade spread exists here either: the negative cells are broad "these names
   underperform" textures, not crisp veto conditions on otherwise-attractive setups.

## Survivorship / PIT
Frozen Dataset B is the best-provenance store in the program (frozen, fingerprinted), IDX100 roster
only — so breadth is structurally capped and the 2025-26 window caveat applies. No pre-2025 broker
data → no historical OOS. Foreign-broker class ≠ foreign investor (declared limitation on
interpretation, not on computation).

## Family program tally after 4 families
Bandar CLOSED (artifact) · Price-structure DEAD · Flow DEAD · Broker-structure DEAD.
The only live item in the entire program remains the **parked observation** (not a registered
candidate): *mid-cap up-moves with heavy platform outflow underperformed in 2025-26* — confirmable,
if at all, only on prospective capture data.

```json
{
  "family": "broker-structure",
  "verdict": "DEAD",
  "entry_survivors": [],
  "filter_survivors": [],
  "constructions_tested": 12,
  "program_state": "families 1-4 closed DEAD/CLOSED; remaining: #5 volume/liquidity/participation, #6 cross-family interactions"
}
```
