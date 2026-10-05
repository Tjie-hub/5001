# 06 · PIT quarterly fundamentals (filing-timestamped, ≥2012, incl. delisted) — FEASIBILITY MEMO · 2026-09-30

**Item (planner task 3A):** quarterly fundamentals WITH filing timestamps, from 2012, including
delisted names — the data a PIT value/profitability/quality/size family ({FQ}) would need.
Scoping + one POC only; no pipeline. POC: `poc_pit_fundamentals_ohlcv.py` (this directory),
run 2026-09-30 (output embedded below).

## Verdict

**No free/scriptable PIT-grade source exists today.** Every candidate either lacks filing
timestamps (yfinance), is Cloudflare-blocked without an Owner ToS ruling (idx.co.id), or is
authenticated history whose scrape is an Owner decision (Stockbit). The {FQ} data gate is
**NOT satisfied**; per the D-065 draft, the family does not open until a PIT source exists.

## POC result (BBCA.JK, yfinance annual income statement, run 2026-09-30)

```json
{"period_end": "2025-12-31",
 "headline": {"TotalRevenue": 114319648000000,
              "NetIncomeContinuousOperations": 57563093000000},
 "filing_timestamp_present": false,
 "note": "Yahoo statements carry period-end columns only; no filing/publication
          timestamp exists anywhere in the payload -- PIT from this source is
          construction, not observation"}
```

Numbers are real and free, but the *filing date is absent by construction* — assuming a lag
("period end + 90 days") fabricates PIT and would fail the program's own evidence standards.

## Sources, ranked by confidence they could work

1. **idx.co.id financial-statement downloads (XBRL/PDF), per-company disclosure pages** —
   coverage: all listed names incl. delisted archives; PIT-ness: **excellent** (every document
   carries an announcement stamp); the single true PIT source. **Access: blocked** — the POC's
   single unauthenticated GET to the site's own announcement endpoint returned **HTTP 403
   (Cloudflare "Just a moment")**; per the ground rules the source was dropped, no bypass
   attempted. **This is an Owner decision point**: authorize a terms-compliant retrieval path
   (or an official IDX data product) before any engineering. Effort post-ruling: 3–5 days build
   + ongoing maintenance.
2. **Stockbit fundamentals (credentials ARE provisioned: `.env` `STOCKBIT_USER/PASS`,
   headless token refresh working — `auto_token.py`)** — authenticated *access* exists, but
   pulling statement history behind auth is a **scrape-behind-auth decision reserved to the
   Owner** (same posture as memo 01); not attempted. PIT-ness unverified (UI shows period
   labels; filing dates unlikely). Coverage from ~2016, delisted names likely absent. Effort
   post-ruling: 1–2 days to inspect + pilot.
3. **IDX Financial Data & Ratio publications / IDX Statistics / Fact Book** — annual
   publications (not quarterly), PIT = publication date, delisted names appear in their final
   year. Usable as an annual cross-check, not a quarterly PIT source. Access: same idx.co.id
   wall as (1). Effort if hand-curated: 1–2 days per decade, manual.
4. **yfinance quarterly/annual statements** — free, scriptable, **no filing timestamps**
   (POC), delisted statements generally purged with the delisted price history (see memo 07).
   Only honest use: period-end-anchored studies explicitly labelled non-PIT, which the program's
   standards treat as in-sample-flavored. Effort: 0.5 day (already working in the POC).
5. **Paid vendor (Refinitiv/FACTIVA/Bloomberg/S&P CIQ)** — would satisfy PIT + delisted +
   2012 depth outright; no subscription provisioned; cost decision for the Owner. Effort once
   licensed: 2–3 days ingest.

## Effort summary if the Owner pursues this for real

- Honest minimum that meets the PIT bar: **Owner-authorized IDX retrieval (3–5 days)** or
  **paid vendor (2–3 days + cost)**. Everything free is either timestamp-less or blocked.
- A no-PIT fallback (yfinance with assumed lags) is buildable in ~1 day but should be
  pre-declared as non-PIT and kept out of any {FQ} registration claim.
