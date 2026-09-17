# HYP-PM-0010 — REGISTERED

**Registered:** 2026-09-17T06:35:57+00:00 · **Program:** P-M · **Family:** Price-Trend {T1} (member 1)
**Spec id:** FWD-PM-REGIME-001 · **Status:** REGISTERED → IN_TESTING
**Frozen protocol:** `P-M/forward_regime/PROTOCOL.md` · sha256 `4d3d27dabbb93c2bc89519d3b9f2d2bd894a0e503660258a7765f2f7568b6255`
**Ledger:** `P-M/forward_regime/ledger.json` (opened empty; no back-fill permitted)

## Mechanism

Time-series momentum in liquid IDX equities. A per-stock trend state — EMA20 slope over 10
sessions > +2%, Kaufman efficiency ratio(20) >= 0.30, and >= 70% of the last 20 closes above EMA20,
all evaluated on data through t-1 — identifies names in a directional trend. Entry on regime onset
at that session's close; exit when the close falls more than 3 x ATR14 below the highest high since
entry, capped at 60 sessions.

## Frozen endpoint and decision rule

Primary endpoint: per-trade excess = (net trade return) − (IHSG return over the identical holding
window), aggregated as a mean with one-way standard errors clustered on entry date.

- Interim read at 12 months: **report only**, no decision.
- Decision at 24 months (~514 trading days):
  - **PASS** — mean excess >= +0.55%/trade and one-sided clustered t > 1.65
  - **FAIL** — mean excess <= 0, or mean < +0.30%/trade
  - **INCONCLUSIVE** — otherwise
- One-directional early stop: abandon if mean < −0.50%/trade after 12 months.

## Backtest reference (in-sample discovery, no confirmatory weight)

7,422 trades / 1,162 entry-date clusters, 2021-07-05 → 2026-09-16:
full sample +2.260%/trade (SE 0.350%, t 6.45); **ex-2025 planning basis +1.106%/trade
(SE 0.330%, t 3.35)**. Portfolio ex-2025: +10.46%/yr excess at the operator's stated 0.50% round
trip, Sharpe 0.75; breakeven round trip 1.47%.

## Family declaration (binding, append-only)

**P-M · Price-Trend {T1}** — directional trend features derived from OHLCV (moving-average slope,
Kaufman efficiency ratio, participation above a moving average, ATR-based exits); liquid IDX
universe; data epoch 2021-07-05 → 2026-09-16. Opened at this registration per D-028/PG-3.
No price-feature family existed beforehand: FWD-PM-VOLEX-001 is an unregistered prospective record
holding no family slot, so no family was split. Widening {T1} later is permitted; narrowing or
splitting it is not.

## Disclosed prior search

A 48-cell threshold grid (slope x ER x participation) was run **before** registration and is
recorded in PROTOCOL.md limitation 8. A tighter cell (.10/.40/.90) roughly doubles the ex-2025
per-signal excess but inverts in 2026 (−3.09%) and cuts breadth 69%; it is deliberately **not**
adopted. Adopting any cell from that grid requires a new spec id and inherits its multiplicity count.

## Carried limitations

Survivorship (corpus holds only names still listed as of 2026-09; bias optimistic, unmeasured);
2025 dominance; optimistic close-to-close fill assumptions; effective breadth ~10 from ~131 nominal
positions; sector neutrality untested and unenforceable (no ticker→sector map for 77% of the
universe); long-only, beta ~0.95; lottery-shaped distribution (median trade negative, 33% win rate).
