# COST AUDIT — D-059 AR spread vs realised spread on liquid names · 2026-10-09

**Read-only audit** (no outcomes, no census arms; costs recomputed, never any R).
Branch `research/data-audits-2026-10` @ b26198a. Data: pinned 2026-10-08 walkforward
snapshot (`a2d7e675…`, fingerprint `9c26e0df…`, max_date 2026-10-07), `ticks` table
2026-04-18 → 2026-10-08 (115 sessions, 24,452,705 prints), streamed one session at a
time (D-059's own `validate()` pattern). Estimator: **Roll (1984) on tick data** —
D-059's own validation convention (`cost_by_adv.roll_spread`/`day_autocov`, imported
from the frozen module @ 7e039ee, verified byte-identical). **Lee-Ready is NOT used**:
the corpus has no quotes (prints only), and a signed effective spread needs a quote
midpoint; with a price-change proxy it would just be a noisy transform of the same
information Roll extracts. Runtime: **5.9 min**.

## Corrected cost table — realised spread + fees + impact (round trip, Q = Rp 100m)

Per D-059 bucket × day-type. `s_ar` = D-059's floored AR spread (trailing 21 sessions,
PIT); `s_roll` = realised Roll on ticks (per-name, pooled per cell, floored at the
name's median 1-tick); `cost_*` = 0.50% fees + spread + median impact 2σ_d√(Q/ADV20).

| bucket | day-type | name-days | s_ar | s_roll | σ_d | impact | cost_ar | **cost_realised** | AR/realised |
|--------|----------|----------:|-----:|-------:|----:|-------:|--------:|------------------:|------------:|
| 1–2bn | normal | 7,277 | 1.33% | 0.78% | 3.0% | 1.59% | 3.42% | **2.86%** | 1.71× |
| 1–2bn | wide | 708 | 1.23% | 0.85% | 4.2% | 2.23% | 3.96% | **3.58%** | 1.45× |
| 1–2bn | stress | 104 | 1.22% | 1.13% | 3.2% | 1.67% | 3.39% | **3.30%** | 1.07× |
| 2–5bn | normal | 8,337 | 1.33% | 0.78% | 3.3% | 1.16% | 3.00% | **2.44%** | 1.71× |
| 2–5bn | wide | 685 | 1.19% | 0.74% | 4.4% | 1.61% | 3.30% | **2.86%** | 1.60× |
| 2–5bn | stress | 143 | 1.23% | 0.77% | 3.7% | 1.35% | 3.09% | **2.62%** | 1.61× |
| 5–20bn | normal | 10,797 | 1.15% | 0.75% | 3.5% | 0.70% | 2.35% | **1.96%** | 1.52× |
| 5–20bn | wide | 964 | 0.94% | 0.75% | 4.3% | 0.90% | 2.34% | **2.15%** | 1.25× |
| 5–20bn | stress | 176 | 1.03% | 0.76% | 3.9% | 0.78% | 2.31% | **2.04%** | 1.36× |
| 20–100bn | normal | 7,254 | 0.99% | 0.63% | 3.3% | 0.34% | 1.83% | **1.47%** | 1.57× |
| 20–100bn | wide | 576 | 0.88% | 0.44% | 4.2% | 0.42% | 1.80% | **1.36%** | 2.00× |
| 20–100bn | stress | 109 | 0.99% | 0.42% | 3.7% | 0.39% | 1.88% | **1.31%** | 2.38× |
| >100bn | normal | 3,565 | 0.97% | 0.49% | 3.7% | 0.15% | 1.62% | **1.13%** | 2.00× |
| >100bn | wide | 334 | 0.74% | 0.38% | 6.3% | 0.24% | 1.48% | **1.12%** | 1.96× |
| >100bn | stress | 54 | 0.73% | 0.38% | 4.4% | 0.18% | 1.41% | **1.06%** | 1.93× |

Liquid subset (true-ADV ≥ Rp 10bn): normal s_ar 1.01% vs s_roll 0.64% → **1.85% → 1.49%**;
wide 0.86% vs 0.60% → **1.78% → 1.52%**; stress 0.94% vs 0.59% → **1.84% → 1.49%** (51
names, 246 name-days, 3 days).

## AR overstatement ratios per bucket (normal days)

1–2bn **1.71×** · 2–5bn **1.71×** · 5–20bn **1.52×** · 20–100bn **1.57×** · >100bn
**2.00×**. The overstatement GROWS with liquidity — the D-059 VERDICT's own suspicion
("AR overstates most for liquid names; Spearman vs Roll 0.2") is confirmed and
quantified. On wide/stress days the pattern inverts in an informative way: realised
spreads for liquid names do NOT widen (20–100bn: 0.63% → 0.44%), while AR stays put —
**AR's "mechanical inflation on wide-range days" shows up as the ratio (2.0–2.4×),
because the high/low term prices intraday range that the tape shows is not
compensated by a wider effective spread.**

## The D-079 stress-basket 2.03%, decomposed (costs only, no R recomputed)

D-079's mean cost was 2.0295%/event on bottom-quintile loser baskets (all members
ADV ≥ Rp 10bn). The audit's stress-day liquid cell: fees 0.50pp + AR spread 0.94pp +
impact 0.40pp ≈ 1.84% — the D-079 baskets ran slightly costlier (loser names), 2.03%.
Under realised spreads the same day-type cell is **0.50 + 0.59 + 0.40 ≈ 1.49%**.
So of the 2.03%: **~1.5pp is real** (fees + realised spread + impact) and
**~0.35–0.55pp is AR overstatement**. This does NOT change the D-079 verdict: S1's
beta-adjusted gross excess was ≈ **−0.09%** — the arm fails at zero cost, so a cost
correction cannot resurrect it (it would matter only for near-zero-gross arms).

## Recommended replacement

`cost_realised.py` (this directory, sha256 sidecar alongside) — frozen API matching
the D-059 call-shape so future G0s cite it directly:

```python
from cost_realised import realised_spread, d059_cost_realised
s = realised_spread(adv20_idr, daytype="normal"|"wide"|"stress")
cost = d059_cost_realised(adv20_idr, sigma_d, daytype, q_idr=100e6)  # fees + s + impact
```

Impact and fees are D-059's, unchanged; only the spread is replaced. Validity: ADV ≥
Rp 1bn (no sub-1bn cell was measured — keep D-059 AR below Rp 1bn, where the AR/Roll
gap is smallest anyway). "stress" is a 3-day refinement of "wide", not an independent
estimate. **Re-computing past verdicts is NOT in scope and NOT recommended here** —
that is an owner-gated re-run per study.

## Past results that used the AR spread on liquid names

1. **D-059 / T1 (HYP-PM-0010)** — the friction verdict itself; its own validation
   flagged the gap (this audit closes it).
2. **forward_robust vol-exclusion overlay** (`P-M/forward_robust/robust_report.py`)
   — used `cost_by_adv` on the liquid universe.
3. **HYP-PM-0019 market-stress reversal G0/G1** (D-079) — cost leg, mean 2.03%
   (decomposed above; verdict unaffected).
4. **HYP-PM-0018 tender-offer floor G0** (D-080) — the D-059 cost sits INSIDE the S8
   spread floor; of its 9 near-misses, **PTRO-2022 missed by 0.02pp** — an
   AR-corrected floor would likely admit it (12 → 13 eligible; the stop rule is
   unchanged at n < 20, so the D-080 outcome stands either way). Disclosed for the
   owner; nothing recomputed here.

NOT affected (never import cost_by_adv in their outcome paths — verified by git grep
across their branches): exit-study, ml-rank, sniper-filter, dividend-clientele.

## Files

`cost_audit.py` (the audit), `COST_AUDIT.json` (all cells), `STRESS_DATES.json`
(63 D-079 dates — date fields only, count and per-year cross-checked against the
stress census; 3 fall inside the ticks window), `cost_realised.py` +
`cost_realised.sha256` (the frozen replacement).

*— ZCode, 2026-10-09*
