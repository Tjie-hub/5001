# Cost by liquidity — pre-declaration (frozen before the first run)

**Written:** 2026-09-25, before `cost_by_adv.py` was run on real data · **Authority:** Owner instruction
2026-09-25 ("start path 1") · **Context:** `universe_screen/SCREEN_HYPOTHESIS_2026-09-25.md`. The T1 ex-2025
edge sits in names with adv20 < Rp 5bn (+3.01%/trade out-of-filter vs +0.29% in). This measures whether
realistic trading cost in those names eats it.

**Descriptive only.** FWD-PM-REGIME-002 keeps its frozen 0.60% endpoint and decision rule. Nothing here is
a fill. The protocol's own remedy (realised fills) remains the authority once fills exist.

## 1. Cost model (per round trip, fixed now)

`cost = fees + spread + impact`

- **fees = 0.50%**. The protocol's stated commissions + 0.1% sell tax (PROTOCOL §2, "open ambiguity").
- **spread = ½ s(entry) + ½ s(exit)**. s is the relative effective spread on that session:
  - Abdi & Ranaldo (2017) close-high-low estimator: `s² = mean over the trailing 21 traded sessions of
    4·(c_t − η_t)·(c_t − η_{t+1})`, with c = log close and η = (log high + log low)/2. Uses sessions t−21..t−1
    only, so it is known at the decision.
  - Set to 0 if the mean is negative, then **floored at one tick / close**.
  - Tick table (IDX, assumed constant over 2021–26): Rp 1 below 200, 2 to <500, 5 to <2,000, 10 to <5,000,
    25 at ≥5,000.
  - Zero-volume sessions are excluded from the window.
- **impact = 2 · σ_d · √(Q / adv20)**, one leg each way with Y = 1 (square-root law). σ_d = std of daily
  close-to-close log returns over the same trailing 21 sessions. adv20 is as in the frozen universe filter.
  Evaluated at entry and applied to both legs.
- **Q ∈ {Rp 25m, Rp 100m, Rp 500m}** per position. **Rp 100m is the primary size.**

## 2. Validation (reported, not a gate)

On the `ticks` table (1-minute last prices, 2026-04-18 → 2026-09-25):
- a per-name Roll (1984) spread from the autocovariance of 1-minute log price changes;
- compared with the Abdi-Ranaldo spread for the same names over the same dates, by ADV bucket (medians and
  Spearman ρ).

If the two differ by more than 2× in the median of the Rp 1–5bn bucket, the result carries a
**model-uncertainty** flag.

## 3. Outputs

- **A.** Cost table by adv20 bucket (Rp 1–2bn, 2–5bn, 5–20bn, 20–100bn, >100bn): median spread, tick floor,
  and impact at each Q. Computed over all universe name-days (the frozen T1 universe), 2021-07 → 2026-09-16.
- **B.** T1 spec-002 reference trades (`overlap_audit.t1_trades`, data ≤ 2026-09-16). Net excess after
  modeled cost is `gross excess − cost`, where gross excess = the frozen net + 0.60%. Reported by the A5
  split (in / out) and by the same ADV buckets, FULL and ex-2025, at each Q. The t-statistics are
  month-cluster and DK(L=60).

## 4. Interpretation — fixed now

Primary cell: **ex-2025, adv20 < Rp 5bn, Q = Rp 100m.**

| outcome | condition |
|---|---|
| **survives cost** | mean ≥ +0.55%/trade (the REGIME-002 PASS bar) **and** DK t ≥ 2.0 |
| **friction** | mean ≤ +0.30%/trade (the REGIME-002 FAIL floor) |
| **unclear** | otherwise |

No other cost parameters, sizes or buckets will be run.
