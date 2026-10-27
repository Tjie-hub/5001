# C-002 · Foreign-ownership cap proximity as an exclusion overlay (anti-edge)

**Status: PROPOSE-ONLY.**

## 1. Mechanism
IDX foreign-ownership limits cap foreign holders near 49% (lower in some sectors). As a name approaches the cap,
the marginal buyer of last resort becomes the local retail/retail-broker base — the price-supporting, informed
demand is exhausted. Prediction direction: TOP-proximity names (F share ≥ 45–48%) underperform the liquid book
over 1–3m — an **avoidance/exclusion** design (like VOLEX), long-only by construction (you simply do not hold
them). Structural barrier: the cap is a standing regulation; proximity is public monthly (KSEI). M4.3
(mandate-driven exclusion) + M5.3 (local disposition).

## 2. Falsifiable prediction
Formation: F_total/(L+F) at month-end t; leg = bottom book EXCLUDING the top decile of proximity. Pass: excluded
names' forward 1m/3m excess vs the EW liquid book is significantly NEGATIVE (they drag), and the clean book's
net return improves by ≥ 0.15%/mo (the {LC} book-economics benchmark). Kill: excluded names' excess ≥ 0, or book
improvement < 0.05%/mo.

## 3. Data
Same KSEI CSV (verified: 43,285 name-months at ≥45% foreign share, 9,048 at 35–45% — the cell is dense, not a
rare-event study). Prices/mcap/universe: as C-001. PIT: zip_stamp +1 month. Sector caps (banking/other) can be
honoured with the sector map where it exists; "cap" proxied by the 49% generic line (conservative).

## 4. Counts and prior-only power
209 formations. Two powered sub-designs: (a) difference-of-means excluded-vs-rest ≈ rank-spread SE 0.68%/mo →
MDE80 ≈ 1.7%/mo — underpowered at plausible drag sizes (~0.3–0.6%/mo) → **do NOT register as a spread test**;
(b) **paired book-vs-book overlay comparison** (with/without exclusion on the same months, paired t) — the VOLEX
and {LC} precedent: paired design cuts SE roughly by the correlation (∼0.9), MDE80 ≈ 0.5–0.6%/mo against a
0.15–0.3%/mo plausible gain — still below 80% but **clears the 20% G0 minimum at a 0.30%/mo floor (power ≈
25–35%)**. Verdict: **marginal; viable only as a paired overlay arm with its own floor ≥ 0.30%/mo.**

## 5. Non-overlap proof
Nearest rows: **D10** (individual share — holder class differs), **C-001** (foreign LEVEL as a rank signal — this
is proximity to a REGULATORY CEILING as an exclusion, a threshold mechanism not a monotone rank), **D7/VOLEX**
(the overlay precedent — mechanism differs: volatility vs constrained demand). {LC} C7 is the *young-listing*
exclusion; different population entirely.

## 6. Cost / capacity
Overlay on an existing book → near-zero added turnover (excluded names are simply replaced); no event execution;
ADV gate unchanged. This is the cheapest possible design class in the repo's history.

## 7. Distinctness from the live book
Overlays compose (BOOK_OVERLAY_POLICY): stacking with VOLEX is additive, not correlated (foreign-proximity vs
volatility decile — check rank overlap at G0; both must not collapse to the same 20 names). Vs {FQ}: independent
fields; FM incremental test mandatory.
