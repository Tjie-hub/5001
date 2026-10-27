# C-001 · KSEI foreign-ownership level and one-month change (monthly rank)

**Status: PROPOSE-ONLY.** No registration, no D-entry, no outcome read.

## 1. Mechanism
Foreign institutional holders on IDX (custodied via KSEI) are better-diversified, longer-horizon, and often
index/mandate-driven. Names with HIGH and RISING foreign share should earn a lower risk premium (crowded,
currency-hedged demand already priced) — or, under the foreign-premium view, the opposite. The panel lets the
sign be risked either way pre-registration; the mechanism (M3.1/M4.4 — liquidity level + mandate flow) is
structural: foreign ownership data is public monthly (KSEI), the constraint (49% cap, reporting) is rule-based.
Persist after costs: monthly turnover ~0.15 (like {OC}), 0.60% RT spread over ~6 rebalances/yr.

## 2. Falsifiable prediction
Formation: month-end F_total/(L_total+F_total) (level A1f) and its 1-month Δ (A2f). Universe: KSEI names with
ADV ≥ Rp 1bn, top-200-by-KSEI-mcap panel (the D-112 universe), monthly 2009-04→. Prediction (to be fixed at
registration, one sign): Q5−Q1 monthly net spread ≥ +0.60%/mo sustained in both halves; kill if t < bar or either
half negative. Benchmark: EW liquid book and IHSG.

## 3. Data
`~/idx_external/ksei/ksei_equity_holdings.csv` (verified today: 211 months 2009-03→, 1,055 names, 141,543
name-months; F_* columns present). Prices: KSEI price column (survivorship-complete) + 5001 ohlcv (2021→) +
pre-2021 backfill. PIT: KSEI file stamped ~1 month after month-end (zip_stamp column) — usable at t+1 month
formation, no look-ahead. Survivorship: KSEI is complete (delisted names present). Risk: F_total includes
foreign-direct + foreign-indirect mix (F_FD vs F_IS etc.) — field choice fixed at registration.

## 4. Counts and prior-only power
209 usable formations (211 − 2 warm-up), same construction as HYP-PM-0020. Calibration from that G0: MDE80 ≈
1.68%/mo → SE ≈ 0.68%/mo. Bar 3.300069 (census 613). Power at effect floor: 0.5%/mo → **~18% (FAILS the 20%
G0 minimum)**; 1.0%/mo → ~43%; 1.5%/mo → ~77%. **Verdict: POWERED ONLY IF the pre-registered floor is set at
≥0.8%/mo; at the 0.5% family convention it is UNDERPOWERED** — the G0 must state its own floor and the owner
must accept it. Not recommended at a 0.5% floor.

## 5. Non-overlap proof
Nearest closed rows: **D10 / HYP-PM-0020** (KSEI *individual* share A1/A2 — the local-retail mechanism; this is
the foreign side, different holder class, different literature); **B6/C2** (foreign vs local *broker* flow — a
flow-instrument contrast, FAILED; this is *holdings stock*, not flow); **B11** (retail-broker imbalance — flow
again). No prior test used F_*. Partial-overlap note (per brief rules): if the owner reads "foreign ownership
premium" as already implied by C2's null, the DIFFERENCE is stock-vs-flow and monthly-vs-daily.

## 6. Cost / capacity
Monthly rebalance, ~80-name legs, turnover ~0.15/mo like {OC}; D-082 cost_realised applies; ADV ≥ Rp 1bn gate
limits capacity concerns; no ARA/ARB dependence (no event execution).

## 7. Distinctness from the live book
Correlation risk with **{FQ} E/P** (same panel, same formation dates): moderate — foreign share correlates with
size and liquidity, less with earnings yield; a Fama-MacBeth incremental test over E/P, size, Parkinson-60
(the D-112 control stack) is mandatory at G0. Vs bank 2-ATR / T1 forward tests: orthogonal (no price-shape
signal).
