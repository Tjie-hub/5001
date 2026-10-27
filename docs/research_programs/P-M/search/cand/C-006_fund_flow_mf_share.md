# C-006 · Mutual-fund ownership share and its change (KSEI MF/PF fields)

**Status: PROPOSE-ONLY.**

## 1. Mechanism
Indonesian mutual funds (Reksa Dana) and pension funds are mandate-driven monthly rebalancers with disclosed
custody (KSEI F_*/L_* fields by type: MF, PF). Their aggregate share of a name measures **structural demand
supply**: rising MF/PF share = persistent mandated accumulation; falling share = redemption-driven selling that
must find a retail bid. Two riskable directions (fixed at registration): (a) high/Δ+ MF share → drift
continuation (mandate flow persistence, M4.4); (b) Δ− after a market drawdown = forced redemption overhang →
underperformance. Rule-based, public monthly, durable while the fund industry's custody reporting stands.

## 2. Falsifiable prediction
Formation: (L_MF+L_PF+F_MF+F_PF)/total at t (A1m) and 1-m Δ (A2m), top-200 KSEI-mcap universe, ADV ≥ Rp 1bn.
Q5−Q1 monthly net spread (direction pre-registered), 209 formations, both halves > 0, FM incremental over
E/P/size/Parkinson/VOLEX. Kill at the family's standard gates.

## 3. Data
Same KSEI CSV — the MF/PF columns exist and are populated (verified schema; per-bucket density to be counted at
build, expected high: every name-month carries all 9+9 buckets). All C-001 PIT/survivorship properties apply
unchanged.

## 4. Counts and prior-only power
209 formations, SE ≈ 0.68%/mo (C-001 calibration). Power at floor: 0.5%/mo → ~18% (fails 20%); 0.8%/mo → ~35%;
1.2%/mo → ~65%. **Verdict: marginal — viable only with a pre-registered floor ≥ 0.8%/mo.** Prior magnitude
unknown on IDX (foreign literature on fund-ownership premium ~0.3–0.8%/mo — borderline).

## 5. Non-overlap proof
Nearest rows: **D10 {OC}** (individual retail share — the complement holder class; MF/PF is institutional,
opposite mechanism); **C-001** (foreign side — different holder class again); **B11 {RF}** (retail BROKER flow
imbalance — daily flow, withdrawn; this is monthly holdings stock). The {OC} registration tested exactly ONE
holder class; the taxonomy (KSEI field table) leaves MF/PF/CP/IB/SC untested — this file names the two most
mandate-bound.

## 6. Cost / capacity
Identical to C-001: monthly, ~80-name legs, low turnover, ADV-gated, no event execution.

## 7. Distinctness from the live book
Same formation calendar as {FQ}; MF share correlates with size — the FM incremental stack is the separator (and
the reason to run it AFTER {FQ} G0 lands, reusing that control stack verbatim).

**Pairing note:** C-001 and C-006 share a panel and a build; if the owner takes either, building both costs ~one
G0 (family governance decides whether they are one {OC}-widening or a new KSEI-family — a new widening, since
{OC} families never narrow, D-083).
