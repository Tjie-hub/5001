# Paper Trade Signal Edge Audit — 2026-05-12

> Cross-referencing paper trade outcomes with screener signals at entry to identify edge conditions.

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Total trades | 18 |
| Closed | 14 |
| Open | 4 |
| Win rate (closed) | 36% (5W / 9L) |
| Avg return (closed) | 3.28% |
| Avg win return | 18.49% |
| Avg loss return | -5.17% |
| Total PnL | Rp 6,154,100 |

## 2. Signal Profile: Wins vs Losses

| Metric | WINS | LOSSES |
|--------|------|--------|
| Avg VPIN | 1.000 | 1.000 |
| Avg vol_ratio | 6.37 | 23.35 |
| Avg delta | 322733137 | 44097261 |
| Avg cum_delta | 322733137 | 44097261 |
| Avg consec_up | 0.8 | 2.8 |
| Avg ADX peak | — | — |
| Most common signal | bullish | watch |
| Most common VPIN label |  |  |

## 3. VPIN Label Distribution

| VPIN Label | Trades | Wins | Win Rate | Avg Return |
|------------|--------|------|----------|------------|
| unknown | 14 | 5 | 36% | 3.28% |

## 4. Volume Ratio Buckets

| Vol Ratio | Trades | Win Rate | Avg Return |
|-----------|--------|----------|------------|
| <1.3x | 1 | 100% | 5.25% |
| 1.3–2.0x | 1 | 100% | 31.51% |
| >2.0x | 6 | 33% | 1.95% |
| unknown | 6 | 17% | -0.43% |

## 5. Per-Strategy Performance

| Strategy | Trades | Win Rate | Avg Return | Avg VPIN | Avg Vol Ratio |
|----------|--------|----------|------------|----------|----------------|
| Momentum Following | 14 | 36% | 3.28% | 1.000 | 14.86 |

## 6. Per-Trade Audit

| # | Ticker | Strategy | Entry Date | Signal | VPIN | VPin Label | Vol Ratio | Delta | PnL% | Exit Reason | Outcome |
|---|--------|----------|------------|--------|------|------------|-----------|-------|------|-------------|---------|
| 1 | LSIP | Momentum | 2026-04-20 | *no data* | *no data* | *no data* | *no data* | *no data* | -4.12% | STOPPED_OUT | **LOSS** |
| 2 | BNGA | Momentum | 2026-04-21 | *no data* | *no data* | *no data* | *no data* | *no data* | -1.33% | STOPPED_OUT | **LOSS** |
| 3 | ANJT | Momentum | 2026-04-22 | *no data* | *no data* | *no data* | *no data* | *no data* | open | — | **OPEN** |
| 4 | BANK | Momentum | 2026-04-22 | *no data* | *no data* | *no data* | *no data* | *no data* | -4.30% | MANUAL | **LOSS** |
| 5 | IPCC | Momentum | 2026-04-27 | *no data* | *no data* | *no data* | *no data* | *no data* | -2.58% | STOPPED_OUT | **LOSS** |
| 6 | KING | Momentum | 2026-04-27 | *no data* | *no data* | *no data* | *no data* | *no data* | -4.85% | STOPPED_OUT | **LOSS** |
| 7 | SMMT | Momentum | 2026-04-27 | *no data* | *no data* | *no data* | *no data* | *no data* | 14.62% | STOPPED_OUT | **WIN** |
| 8 | ADES | Momentum | 2026-05-01 | neutral | 1.000 | — | 0.94 | 332082 | 5.25% | STOPPED_OUT | **WIN** |
| 9 | ASPR | Momentum | 2026-05-01 | bullish | 1.000 | — | 1.58 | 456669298 | 31.51% | STOPPED_OUT | **WIN** |
| 10 | BSML | Momentum | 2026-05-01 | neutral | 1.000 | — | 1.35 | 45009498 | open | — | **OPEN** |
| 11 | ABDA | Momentum | 2026-05-04 | watch | 1.000 | — | 75.31 | 91947 | -7.84% | STOPPED_OUT | **LOSS** |
| 12 | ASPR | Momentum | 2026-05-05 | bullish | 1.000 | — | 2.17 | 401910351 | 32.81% | STOPPED_OUT | **WIN** |
| 13 | ENZO | Momentum | 2026-05-05 | bullish | 1.000 | — | 20.80 | 432020816 | 8.25% | STOPPED_OUT | **WIN** |
| 14 | ABDA | Momentum | 2026-05-06 | watch | 1.000 | — | 7.39 | 75337 | -10.28% | STOPPED_OUT | **LOSS** |
| 15 | ARGO | Momentum | 2026-05-07 | watch | *no data* | *no data* | 4.65 | 550364 | open | — | **OPEN** |
| 16 | TINS | Momentum | 2026-05-07 | watch | *no data* | *no data* | 2.29 | 153354825 | -11.27% | STOPPED_OUT | **LOSS** |
| 17 | BMHS | Momentum | 2026-05-08 | bullish | 1.000 | — | 8.40 | 22866934 | 0.00% | STOPPED_OUT | **LOSS** |
| 18 | POWR | Momentum | 2026-05-12 | watch | *no data* | *no data* | 3.13 | 11321075 | open | — | **OPEN** |

## 7. Key Findings

- **Higher VPIN at entry → better outcomes.** Winning trades had avg VPIN 1.000 vs 1.000 for losses.
- **Volume ratio at entry:** Wins averaged 6.37x vs 23.35x for losses — lower volume at entry correlated with worse outcomes.
- **Delta (buy pressure) at entry:** Wins had avg delta 322733137 vs 44097261 for losses.
- **Best VPIN label:** `unknown` achieved the highest win rate (36%) among labels with ≥2 trades.
- **Best volume ratio bucket:** `>2.0x` had the highest win rate (33%) among buckets with ≥2 trades.
- **Missing screener data:** 10 trade(s) had no matching `daily_screen` row at entry date — these are excluded from signal comparisons.
- **Best strategy by avg return:** `Momentum Following` averaged 3.28% return across 14 closed trades.

---
*Generated: 2026-05-12 13:53 | Source: `data/walkforward.db` tables: `paper_trades`, `daily_screen`*