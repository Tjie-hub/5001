# Cost by liquidity — result (2026-09-25, `RESULT_20260925T022702Z.json`)

Run once under `PREDECLARATION.md` (sha256 `ac3a1a19…596b`). Script sha256 `d405921a…3ee0`. An earlier attempt was
killed by the OS (out of memory) while loading 65.5M `ticks` rows, after printing the cost table and before
validation. The rerun streams `ticks` per session. The model and parameters are unchanged, and the cost table
reproduced identically.

## Pre-declared verdict: **FRICTION**

Primary cell: ex-2025, adv20 < Rp 5bn, Rp 100m per position. T1 net of modeled cost is **+0.11%/trade**
(N 2,027; t_month 0.15, DK60 0.13), against a modeled all-in cost of 3.48% per round trip. That is below the
REGIME-002 FAIL floor of +0.30%.

## A · Modeled cost by liquidity (T1 universe name-days, 2021-07 → 2026-09-16)

| adv20 | median spread | 1-tick floor | name-days at floor | impact Rp 25m / 100m / 500m (round trip) |
|---|---:|---:|---:|---|
| Rp 1–2bn | 1.05% | 0.74% | 50% | 0.71 / 1.42 / 3.18% |
| Rp 2–5bn | 0.99% | 0.71% | 51% | 0.52 / 1.05 / 2.34% |
| Rp 5–20bn | 0.91% | 0.62% | 51% | 0.31 / 0.63 / 1.40% |
| Rp 20–100bn | 0.86% | 0.47% | 48% | 0.15 / 0.29 / 0.66% |
| > Rp 100bn | 0.68% | 0.37% | 52% | 0.06 / 0.13 / 0.29% |

Validation against Roll on 1-minute prints (863 names, 2026-04-18 → 09-25):
- Roll comes in lower in every bucket (1–5bn: 0.84/0.74% vs AR 1.32/1.18%; ratio 0.64, so no uncertainty flag).
- Spearman ρ is 0.6–0.7 for sub-Rp 20bn names and only 0.2 for liquid names.
- **Abdi-Ranaldo overstates the spread, most of all in liquid names.**

## B · T1 net of modeled cost, ex-2025 (mean %/trade, DK60 t)

| cell | Rp 25m | Rp 100m | Rp 500m |
|---|---|---|---|
| all trades | −0.33 (−0.65) | −0.80 (−1.55) | −1.96 (−3.71) |
| adv20 ≥ Rp 5bn | −1.03 (−2.03) | −1.30 (−2.55) | −1.98 (−3.78) |
| **adv20 < Rp 5bn** | +0.94 (1.09) | **+0.11 (0.13)** | −1.92 (−2.27) |

## Reading (≤5 lines)

1. **The 0.60% round trip in REGIME-002 is far too low.** A tick alone is 0.4–0.7% of price for the median
   T1 name, before fees and impact. Even the Roll-based spread (≈0.4 pp below AR in the Rp 1–5bn bucket)
   leaves the primary cell at about +0.5%, t < 1. It is below the PASS bar under either spread estimate.
2. **At Rp 25m per position a small edge may remain:** +0.9% on Roll-adjusted costs, but t ≈ 1. That is a
   hobby-size capacity, not a tradeable test.
3. **In liquid names T1 has nothing after any realistic cost.** Gross is +0.89% ex-2025, all-in is about 1%.
4. **Model limits:** Y = 1 impact is at the conservative end, the tick table is assumed constant, and there
   are no real fills. The protocol's own remedy (realised fills) still governs.
