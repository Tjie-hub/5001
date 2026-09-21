# FAMILY #5: VOLUME / LIQUIDITY / PARTICIPATION — FAMILY REPORT

**Date:** 2026-09-16 · family-by-family discovery, family 5 of 6 · DISCOVERY ONLY.
**Data:** daily volume / traded value (close×volume) from production OHLCV — PIT-complete, no vendor
semantics, no coverage selection: the cleanest data in the program. Relative participation
`rv = volume / trailing-60-median volume (shift 1)`; `rtv = traded_value / ADV60`;
regime = `ADV20/ADV60`. Suspension-clean base. Declared skip-list honored (raw vol-z alone,
volume-confirmed up-moves P17/P18, compression→new-high P16, liquidity-floor-as-mask).

**Meta-question of this family:** after four families where liquidity killed every candidate as a
confounder — is liquidity (A) merely a control, or (B) itself information-bearing?

## VERDICT: **DEAD** — with the meta-question answered:

> **Liquidity is statistically information-bearing but economically inert for long-only trading.**
> Several participation states carry significant cross-sectional information beyond prior returns
> (rtv≥2: FM β +0.65%, t=5.88; ADV20/60 expansion: +0.57%, t=9.01; heavy-volume churn: +0.82%,
> t=6.32; participation shock: +0.49%, t=3.36) — so B, not A. But every one of those flags belongs
> to names whose *unconditional* forward drift is flat-to-negative (−0.03% to +0.09% net h5) —
> high-participation names underperform, and the conditional edge is exactly cancelled by the
> selection. The tradable direction (quiet names) sits at the base rate. Net: nothing tradable.

## Results (24 declared constructions; full battery in cache/volume_family_run.log)

- **V1 levels:** rtv≥2 −0.03%; own-p95 volume −0.05%; tv-z≥2 +0.21%; subdued 0.5≤rv≤0.8 +0.02% — all
  net-negative. High participation is *bad*; quiet participation is *neutral*.
- **V2 change:** all five change/transition constructions between −0.58% and +0.33% net — dead.
- **V3 persistence:** high-run −0.14%; quiet-run +0.12%; normalization +0.38% — dead.
- **V4 regime:** expansion +0.04%; contraction −0.07%; **V4c sudden deterioration +1.11% gross
  (+0.51% net) — the family's only entry-rule passer, killed below**; sudden expansion +0.14%.
- **V5 2×2:** confirmed up +0.20%; unconfirmed up +0.35%; capitulation −0.21%; drift −0.15% — the
  whole 2×2 is inside ±35bp net. The volume dimension adds ~nothing to the move dimension.
- **V6 no-progress:** churn +0.09% net; narrow+heavy −0.58%; **failed rally on heavy volume −0.55%**
  (the family's strongest negative cell — veto-checked below); exhaustion +0.21%.
- **V7 compression→participation expansion:** +0.23% net — the participation transition itself
  carries nothing (distinct from the killed P16 price-breakout).
- **V8 risk:** liquidity collapse +0.46%; dead tape +0.22%; heavy+deteriorating +0.12% — liquidity
  deterioration is *contrarian-positive* here, not a risk signal.
- **V9 shock:** rv≥3 −0.09%; rv≤0.3 +0.28% — dead.

## The near-passer, and why it died

**V4c "sudden liquidity deterioration"** (ADV20/60 ≤ 0.7 and 5-day change ≤ −20%): h5 +1.11%
gross (+0.51% net), n=2,366, positive in all four halves. Killed by the mandatory checks:
- **FM incrementality:** β = **−0.59% (t = −2.26)** — given prior returns, the flag predicts *worse*
  cross-sectional returns. The portfolio gain is selection (2026H1 crash-recovery sequences).
- **Pseudo-OOS sign flip:** 2021-22 h5 **−0.84%**, 2023-24 h5 **−1.11%** — in normal regimes sudden
  liquidity deterioration is the *risk* signal intuition says it is; the 2025-26 positivity is
  window-specific.
- Tail: top-1% of events = 56% of the gain. Breadth: 4.3 events/day; 26H2 n=209.

**V6c veto check (the strongest negative cell):** failed rallies on heavy volume spread −65bp h5 /
−121bp h10 vs other heavy-volume days, but **26H2 flips +79bp**, ADV-top flips **+0.39%**, FM with
liquidity control t = −1.94 (below bar). Fails the declared filter rule (FM incl. liquidity,
tier robustness). Not promoted.

## Proxy checklist (declared)

- "Proxy for size?" — the negative information in high-participation states survives within ADV
  tiers but the *positive* candidates do not exist outside mid/bottom tiers → yes for anything alive.
- "Proxy for momentum?" — FM controls ret1/ret5z: the V4c reversal story is momentum-in-disguise
  (fails); V4c's OOS flip is a momentum-regime artifact.
- "Proxy for volatility?" — range-based variants (V6b) flat.
- "Tradability filter?" — the liquidity floor is already applied as a mask; levels carry no edge
  beyond it (V1/V4 dead).

## Capacity note

Nothing reached the capacity stage except V4c (dead): 4.3 events/day, median ADV at events
Rp4.34bn — mechanically feasible at Rp50–100M positions (10% participation) but irrelevant given
the kills.

## What cannot be established retrospectively

Canvas survivorship (100% current-roster backfill) applies; the 2021-24 pseudo-OOS mitigates it for
price-family data (and is what killed V4c). No vendor flow involved in this family, so PIT is clean
post-close by construction.

```json
{
  "family": "volume-liquidity-participation",
  "verdict": "DEAD",
  "entry_survivors": [],
  "filter_survivors": [],
  "near_miss": {"V4c-sudden-liquidity-deterioration": "FM -0.59% (t=-2.26); OOS sign-flip; tail 56%"},
  "meta_answer": "liquidity is information-bearing (FM |t| up to 9) but economically inert long-only",
  "constructions_tested": 24,
  "next_family": "#6 cross-family interactions (final)"
}
```
