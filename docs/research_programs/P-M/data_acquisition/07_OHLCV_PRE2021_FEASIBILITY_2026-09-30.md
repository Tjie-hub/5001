# 07 · OHLCV before 2021-07 (incl. delisted) — FEASIBILITY · 2026-09-30

**Item:** extend the price panel back before the corpus start (2021-07-05) toward ≥2012,
including delisted names, to lengthen samples and to measure survivorship. Scoping only; POC run
2026-09-30 (`poc_ohlcv_pre2021_yfinance.py`, output embedded below; no DB writes).

## Verdict

**Surviving names: yes, free and deep. Delisted names: no — yfinance serves none, so a yfinance-
only backfill is survivorship-broken by construction.** Since the effect under study is long-only
cross-sectional, survivorship bias is *optimistic* — a survivors-only long panel would inflate
every long-side screen. That is the disqualifying flaw for a naive backfill, and the reason the
item splits in two.

## POC result (actual, one run)

A. Still-listed long-history names (monthly bars, `period=max`):

| ticker | rows | first bar | last bar |
|---|---|---|---|
| BBRI.JK | 275 | **2003-11** | 2026-09 |
| UNTR.JK | 313 | **2000-09** | 2026-09 |
| HMSP.JK | 301 | **2001-09** | 2026-09 |

B. Delisted/inactive names (from `idx_tickers.status='inactive'`, 14 names):

| ticker | yfinance result |
|---|---|
| ZEUS.JK | EMPTY |
| TURI.JK | EMPTY |
| BSMT.JK | EMPTY |
| FINN.JK | EMPTY |

## Interpretation and gaps

- Daily bars for survivors back to ~2000–2003 are obtainable today (the POC used monthly; daily
  depth is expected to be similar, to be confirmed per-name in a real acquisition brief — Yahoo's
  .JK daily history has known start-date variance by name).
- **Delisted names are entirely absent from yfinance.** Without them, any 2012→2021 extension
  measures only companies that survived to 2026 — the worst IPOs, mergers and failures are
  missing. For long-only screens this biases returns upward; the corpus's own survivorship note
  (54/929 names end early) already flags direction.
- Candidate sources for the delisted tail: IDX historical data services (paid), KSEI archives,
  paid vendors (Bloomberg/Refinitiv), or manual collection from archived IDX daily summaries —
  **no free scripted source identified**; this is an Owner cost/authorization decision, same
  posture as item 06.

## Effort estimate

- Survivors-only daily backfill 2012→2021-07 + gap/finality audit + PIT spec: **1 day** (yfinance
  fetch script reusing the cross-asset POC pattern; ~960 tickers).
- Delisted-name backfill: no free path — **vendor/manual, Owner decision** (do not build before
  that decision).
- Recommended interim use: survivors-only pre-2021 data is fit for *time-series* checks (e.g.
  regime/era robustness of an existing registered test) and unfit for new *cross-sectional*
  discoveries without an explicit survivorship caveat on the card.
