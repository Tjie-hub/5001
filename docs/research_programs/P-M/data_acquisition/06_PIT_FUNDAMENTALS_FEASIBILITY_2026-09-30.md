# 06 · PIT quarterly fundamentals (with filing timestamps, ≥2012, incl. delisted) — FEASIBILITY · 2026-09-30

**Item:** point-in-time quarterly fundamentals for the {FQ} family (value, profitability, quality,
size) — the data gap FINDINGS_2026-09-18 §6 called "the single highest-value data acquisition" and
whose Yahoo fetch was closed as a data null (52.6% coverage, ~4 annual cross-sections, no
timestamps). Scoping only; no backfill, no pipeline.

## Verdict

**No free/scriptable source with per-statement filing timestamps was found in this pass.** Two
probes were made (idnfinancials, and the already-provisioned Stockbit access assessed from repo
tooling). The realistic design is (a) numbers from a public/vendor source, plus (b) a
**conservative statutory filing date** (period end + regulatory publication deadline) when actual
announcement timestamps are unavailable — later-than-true first-available ⇒ no look-ahead by
construction, at the cost of burning the first ~2 months of each quarter's signal. This is a
usable PIT approximation for screens, and it must be labelled as such on any card.

## Sources, probed and ranked

1. **idx.co.id financial-statement announcements + PDF/XBRL downloads** — the authoritative
   source: every periodic statement is announced with a date, and the statements themselves are
   downloadable. **Probe result:** the announcements area is a JS app backed by POST APIs;
   plain-HTTP probes of the search UI were not attempted beyond confirming the pattern (the
   earlier D-c POC session hit bot-guarding on IDX fetch paths). Scripted bulk access = Owner
   ToS/technical decision; per-name manual downloads are feasible but do not scale.
   **Effort if authorized:** 3–5 days build + maintenance; coverage incl. delisted names is the
   best of any option (delisted names' statements remain published).
2. **Stockbit (provisioned: `.env` creds + `auto_token.py` → `exodus.stockbit.com/keystats/<TICKER>`)** —
   keystats carries PE/PBV/ROE/EPS; the corpus only began recording 2026-04, but whether the
   endpoint serves **history** (and with what timestamps) is decidable with **one authenticated
   probe (~1h)** — not run in this scoping pass. Coverage for delisted names: unknown.
3. **idnfinancials.com (probed live, BBCA)** — quarterly Net Interest Income / Net Profit by
   fiscal quarter (e.g. BBCA Q4/2024 net profit IDR 13,762,442 jt) **with period labels only —
   no publication/filing dates on the page**; plain fetch returns **403** (bot-guarded; a
   reader-view fetch works, automation-friendly access is therefore fragile). Historic depth and
   delisted coverage unverified. Usable as a numbers source paired with statutory PIT dates.
4. **IDX periodic publications (Financial Data & Ratio, IDX Statistics/Fact Book)** — annual
   aggregates; no per-statement timestamps; no delisted history. Reference/QA use only.
5. **yfinance fundamentals** — already tested by the program: null (52.6% coverage, no
   timestamps). Closed; do not revisit.

## POC (item-mandated shape: one ticker, one fiscal year)

- Ticker/fiscal year attempted: BBCA, FY2024 → period end **2024-12-31**; quarterly numbers
  retrievable (Q4/2024 net profit IDR 13,762,442 jt, net interest income IDR 21,331,393 jt from
  idnfinancials live probe 2026-09-30).
- **Filing date: NOT obtainable from any probed public page.** Under the conservative design the
  PIT date for FY2024 would be **2025-04-30** (statutory annual publication deadline) — i.e. the
  numbers are treated as first-visible 4 months after period end. Quarterly statements: +2 months
  after quarter end by the same rule. Exact POJK citation to be confirmed before a card relies on
  the rule.
- Sample output captured in this memo (no DB writes, no backfill).

## Effort estimate

- Stockbit history probe: **1h** (decides whether a numbers source with real timestamps already
  exists behind our own credentials).
- Conservative-PIT build (numbers from idnfinancials/IDX PDFs + statutory dates, 2012→present,
  incl. delisted where obtainable): **3–5 days**, mostly per-statement date sourcing for delisted
  names; coverage realistically ≥90% of currently-listed, materially lower for delisted.
- Authoritative IDX announcement scrape: 3–5 days **+ Owner authorization** (bot-guarded).
