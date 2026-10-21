# Stockbit financials-history probe — result (2026-10-20, run 18:33 WIB)

**Run:** `scripts/probe_stockbit_fin_history.py`. It used the existing token, made no login, never touched the DB,
and made 21 GETs. Raw output is in `out/stockbit_fin_probe_20261020_183349/` (gitignored).
**Verdict: HISTORY_FOUND.** All 5 guessed endpoints answered 200 for all 4 tickers.

| Endpoint | What it returns | BBCA | TLKM | BTEL (delisted per yfinance) | TRAM (delisted per yfinance) |
|---|---|---|---|---|---|
| `findata-view/company/financial` report_type 1/2/3, statement_type 1 | **Quarterly income statement, balance sheet and cash flow** (HTML table, values in IDR) | Q1 2008 → Q2 2026 (74 q) | Q4 2007 → Q2 2026 | Q4 2007 → **Q3 2025** | Q1 2008 → **Q3 2019** |
| same, statement_type 2 | Annual (12M) statements | 2008 → 2025 | 2007 → 2025 | → 2024 | → 2018 |
| `keystats/ratio/v1/{t}?year_limit=10` | 10 years of quarterly values plus TTM and annualised for each key-stats item | 2017 → 2026 | ✓ | ✓ | ✓ |

The income-statement table also carries a **per-quarter share count**, quarterly EPS, PE, P/S, EBITDA, ROA, ROE
and ROCE.

## What it means

- **The {FQ} value/quality lane is unblocked on data.** The 2026-09-18 factor-zoo fundamentals addendum failed on
  data (yfinance: 52.6% coverage, about 4 annual cross-sections). It was never refuted. Here there are about
  18 years of quarterly statements behind credentials we already use.
- **Survivorship is fixable.** Delisted and long-suspended names keep their history (BTEL to Q3 2025, TRAM to
  Q3 2019). That is the bias PATH_REVIEW §3.4 said needed a paid vendor panel. It still needs a list of delisted
  tickers.

## Limits (to state on any card)

1. **No filing or publication dates.** No date-like field exists in the financial endpoints. PIT must use the
   **statutory-lag design** (06_PIT_FUNDAMENTALS_FEASIBILITY): each period is first visible at period end plus
   the regulatory deadline, chosen conservatively. The exact POJK deadlines must be confirmed before freezing.
2. **Values are probably as currently stored (restated), not as first reported.** That is a mild look-ahead in
   the numbers. Label it, or cross-check a sample against the original filings.
3. The data comes as an HTML table: a parser is needed. Rows are Indonesian account names, with a
   bank-specific layout for banks.

## Next steps (owner decisions first)

1. **Owner: ToS call** for a one-off bulk pull with our token. About 1,000 tickers × 3 statements ≈ 3,000 GETs,
   about 75 minutes at 1.5 s each, run on a weekend night.
2. **Build a research-side backfill**, not production:
   - store the raw JSON gzipped, plus a long table (ticker, period, account, value, fetched_at);
   - pin the files by sha256;
   - run it outside trading hours.
3. **Freeze the PIT rule**, then a **{FQ} mechanism D-entry** (a risk premium, admissible under D-070 §1). Then
   the low-turnover value/quality sleeve (PATH_REVIEW §3.5 / SWING_MIDTERM_PLAYBOOK §4A) can finally be tested
   in-house.
4. **Power:** this is the best-powered design available, a monthly cross-section over about 200 months. Event
   studies give only tens to low hundreds of clustered dates.
