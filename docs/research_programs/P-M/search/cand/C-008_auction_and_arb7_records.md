# C-008 · Call-auction tape and the ARB-7% window: prospective records, G0 later

**Status: PROPOSE-ONLY as RECORDS. Not registrable today — the histories are frozen records, not readable data.**

## 1. Mechanism
Two market-design cells are open but data-young:
(a) **Opening call auction** (IEP/IEV formation, match print, first minutes): the jurnal26 auction monitor has
recorded daily reports since 2026-10-16 (first live day 10-26 after the two fixes; today's fires clean).
Auction-price formation is a rule-based dislocation point (M6.2) — the P-A family's I2/I3 cells — but the ONLY
honest instrument is the prospective record: D-098-frozen, readable at 60 sessions / 100 events.
(b) **The ARB 7% window (2026-10-19→12-31, D-107)**: a temporary rule change on the auto-rejection floor. Band-hit
behaviour under 7% vs 15% is a natural experiment in price-limit mechanics (M6.1) — no history exists for the
window itself; the monitors (limit_watch, FWD-PM-HALTARB-001) are recording it.

## 2. Falsifiable prediction (for the eventual G0, stated now so it is cheap later)
(a) names with pre-open IEP gap ≥ +2% that MATCH at the auction continue less than the tape narrative implies
(the P-A null direction), or reverse overnight (consistent with B9/B10's overnight-gap structure);
(b) under the 7% floor, ARB-touch frequency rises and next-day reversal at the re-widened band changes sign vs
the 15% regime. Both are recordable mechanically; neither is read before its gate.

## 3. Data
jurnal26 `data/auction_reports/` (10-16→, frozen per D-098-class rules), `limit_watch`/`bandar_detector` states,
5001 ohlcv for the same names (execution prices). Nothing to acquire. The 7% window ends 2026-12-31 — the
re-widening is itself the comparison event.

## 4. Counts and prior-only power
(a) 60 sessions ≈ 25 names × 60 days ≈ 1,500 name-days; an auction-gap rank design on 60 daily formations →
SE ≈ 1.3%/day → power at 0.5%/day ≈ 8% — **UNDERPOWERED at 60; re-evaluate at 250 sessions (power ~25–30%).**
(b) ~45 trading days of 7% window vs 2+ years of 15%: a before/after frequency comparison, not a return test —
descriptive. Verdict: **records only, G0 deferred to ≥2027-Q2.**

## 5. Non-overlap proof
Nearest rows: **HYP-PA-0001** (reconstitution-day closing auction — a specific event, FAILED; this is the
ORDINARY daily auction); **B15** (band pinning I1 — closed underpowered on OLD data; the 7% window is new
regime data the old test never had); **B16** (halt-arb record — the standing record this extends).

## 6. Cost / capacity
Zero now (monitors already run under ops budgets).

## 7. Distinctness from the live book
Orthogonal. One caution: auction/limit records and the T1/R2 forward tests share the same names — reads must
respect both freeze regimes (no outcome reads on frozen records).

**Recommendation:** no action beyond what is already recording; calendar a G0-feasibility re-check in 2027-Q2
(owner decision).
