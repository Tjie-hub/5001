# FAMILY #2: PRICE / PRICE-STRUCTURE — FAMILY REPORT

**Date:** 2026-09-15 · family-by-family discovery, family 2 of 6 · DISCOVERY ONLY.
**Data:** daily OHLCV (production, is_final=1; open/high/low/close/volume semantics unambiguous;
split/dividend-adjusted returns via the applied-basis convention; 959 tickers, canvas
2025-01-02..2026-09-14, ~123.6K liquid tradable ticker-days). Minute-grain price structure declared
out of scope (adjacent to killed I7/D-family constructions). Suspension-clean base throughout.
Predeclared 18-construction tree, fixed before running; no post-hoc additions.

**Key question:** does price/price-structure structure contain incremental, PIT-usable, tradable
long-only information beyond simple prior-return and volume state?

## VERDICT: **DEAD** (as an entry family; no filter-grade avoidance either)

No construction passed the declared entry kill rule (net-of-60bp h5 ≥ +30bp AND ≥3/4 positive halves
AND FM β>0, |t|≥2 AND n≥1000/50 tickers AND positive 2021–24 pseudo-OOS). The two near-misses died
under the mandatory checks. Results (h5, net of 60bp floor; full surfaces in
`cache/price_family.json`):

| # | Construction | n | h5 gross (net) | halves+ | FM β (t) | Verdict |
|---|---|---|---|---|---|---|
| P1 | gap ≥ +2% | 7,852 | −0.02% (−0.62%) | 3/4 | **+1.18% (6.63)** | portfolio dead; FM/portfolio conflict |
| P2 | gap ≤ −2% [mirror] | 4,821 | +0.24% (−0.36%) | 3/4 | — | below cost |
| P3 | CLV ≥ 0.9, real range | 7,318 | +0.21% (−0.39%) | 3/4 | −0.08% (−0.92) | dead |
| P4 | CLV ≤ 0.1 | 9,006 | −0.27% | 3/4 | — | dead |
| P5 | range ≥1.8×ATR, up | 5,400 | +0.38% (−0.22%) | 3/4 | −0.32% (−2.09) | dead (negative incrementality) |
| P6 | range ≥1.8×ATR, down [mirror] | 5,465 | −0.45% | 3/4 | — | dead |
| P7 | compression ≤0.7×ATR | 38,054 | +0.29% (−0.31%) | 3/4 | +0.13% (2.11) | below cost, FM marginal |
| P8 | up-run ≥4 of 5 | 9,728 | +0.04% (−0.56%) | 3/4 | +0.72% (2.73) | portfolio dead |
| P9 | inside bar | 12,907 | +0.37% (−0.23%) | 3/4 | — | below cost |
| P10 | new 20d-high close | 1,877 | +0.31% (−0.29%) | 3/4 | +1.82% (8.10) | portfolio dead |
| P11 | new 20d-low close [mirror-long] | 3,032 | **+0.97% (+0.37%)** | **4/4** | **−0.17% (−0.62)** | **KILLED: FM fail + OOS fail + tail** |
| P12 | overnight-heavy 5d | 60,872 | −0.37% | 3/4 | +0.17% (2.21) | dead |
| P13 | intraday-heavy 5d | 26,149 | +0.58% (−0.02%) | 3/4 | +0.20% (2.03) | below cost |
| P14 | hammer (bullish rejection candle) | 752 | **−1.03%**, hit 39.9% | 1/4 | — | the classic bullish pattern is *bad* on IDX — but unstable (1/4), not filter-grade |
| P15 | shooting star [mirror] | 1,095 | +0.26% | 3/4 | — | dead |
| P16 | box breakout (compressed → new 20d high) | 370 | +1.49% (+0.89%) | 3/4* | +0.63% (1.93) | **breadth fail** (n<1000; 26H2 cell <30 obs) |
| P17 | up-move ≥3% & low volume | 7,080 | +0.68% (+0.08%) | 3/4 | — | below net margin |
| P18 | up-move ≥3% & high volume | 5,252 | +0.22% | 3/4 | — | volume confirmation *hurts* (P17 > P18) — trivia, not a trade |

\* 26H2 sub-cell below the 30-observation floor.

## The near-misses, and why they died (the important part)

- **P11 (buy closes at new 20-day lows — a 4/4-half bounce, +0.97% h5):** failed every deep check.
  FM incrementality **negative/insignificant** (β −0.17%, t=−0.62) — the bounce is prior-return
  selection, not new information. **Pseudo-OOS 2021-24:** 2021-22 h5 +0.03%, 2023-24 h5 **−0.52%** —
  does not replicate before 2025. Tail: top-1% of observations = 62% of the gain. Liquidity: bottom-ADV
  +1.95% vs top-ADV +0.41%. Same six-foot grave as UP3, dug from the opposite direction.
- **P16 (compression breakout):** best gross economics in the family (+1.49% h5, +0.89% net) but
  **n=370** over 20 months (≈0.6 events/day; the 26H2 cell has <30 observations) — fails the declared
  breadth floor. Not promoted; noted for any future capacity-aware revisit only if a cheaper
  event-definition is predeclared (not done here).
- **P10 / P1 / P8:** FM says "new high closes / gap-ups / up-runs predict positive h5 given controls,"
  but their *portfolios* are at/below cost — statistical cross-sectional contrast without tradable
  magnitude. Per the declared priority (economic magnitude first), these are dead, not conditionally
  alive.

## Incrementality, survivorship, PIT

- FM controls: ret1, ret5z, volume z, platform-flow z. Portfolio economics override FM when they
  conflict (declared rule).
- Price-only signals were given the test UP3 failed: **mandatory 2021-07..2024-12 pseudo-OOS** for
  every entry-rule passer. P11 failed it; nothing else reached it alive.
- PIT: daily OHLC is PIT-complete after the close; entry at close(t+1) carries no look-ahead. The
  canvas survivorship caveat (100% current-roster backfill) applies family-wide and is unfixable
  retrospectively.

## Avoidance reading

The family produced no filter-grade avoidance either: the only negative-info cell (P14 hammer — the
classic bullish reversal candle averaging −1.03% h5 with 39.9% hit rate on IDX) is unstable across
halves (1/4) and small (n=752). Documented as a candle-lore counter-evidence note, not promoted.

## VERDICT: DEAD — stop spending research time on daily price-structure entries.

```json
{
  "family": "price-structure",
  "verdict": "DEAD",
  "entry_survivors": [],
  "avoidance_survivors": [],
  "near_misses": {"P11-20d-low-bounce": "FM + OOS + tail kills", "P16-box-breakout": "breadth fail (n=370)"},
  "constructions_tested": 18,
  "next_family": "flow (new constructions only)"
}
```
