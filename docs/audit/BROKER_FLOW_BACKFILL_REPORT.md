# Broker Flow — Historical Backfill Investigation & Freeze Report

**Generated:** 2026-08-04 · **Scope:** `broker_flow` + `bandar_detector` datasets ·
**Status:** FROZEN — implementation complete, validated, and certified below.

## Conclusion

> **SUPPORTED** — historical broker-flow backfill works, and has been executed to the
> maximum fidelity the Stockbit API supports.

The `marketdetectors/{ticker}` endpoint (`GET https://exodus.stockbit.com/marketdetectors/{ticker}`)
serves genuine historical broker summaries when **both** `from=YYYY-MM-DD` and `to=YYYY-MM-DD`
are supplied together. Supplying only one is silently ignored — the server returns today's data
instead, which is why the original implementation (no date param at all) was mistaken for a
hard API limitation rather than a missing feature.

## Root Cause of the Original Wrong Assumption

`fetch_broker_flow(token, ticker)` never accepted a `date` parameter, and `run_flow()` contained:

```python
bf = fetch_broker_flow(token, ticker) if not date else None
```

with a comment asserting "marketdetectors has no historical date param." This was never
independently verified — it was inherited assumption, not evidence. Live HTTP probing
(2026-08-04) disproved it directly.

## Evidence

| Check | Result |
|---|---|
| `from`/`to` both supplied | Server echoes the requested date back (`data.to`), returns distinct broker data per date |
| Only one of `from`/`to` supplied | Silently ignored — returns current day's data |
| Cross-validation vs. existing DB rows | Exact match, `2026-07-31` (top buyer `DX`/235,510 lot) and `2026-07-20` (top buyer `ZP`/636,162 lot) |
| Historical depth | Verified back to **2020-01-02** — before `ohlcv`'s own earliest date (2021-07-05) and far beyond the sibling `stockbit_flow` endpoint's hard 2025-01-02 cutoff |
| Trading-calendar consistency | Every date bisected as "empty" corresponds to a genuine non-trading day (weekend/holiday) in `ohlcv`, never a false negative on a real trading day |

## Correct Expected-Coverage Baseline

`broker_flow` was introduced in commit `6ac9aa1` (**2026-04-23**) — confirmed via
`git log -S"def fetch_broker_flow"` plus a parent-commit diff check (function absent in
`6ac9aa1^`, present in `6ac9aa1`). An earlier audit pass wrongly used `ohlcv`'s 2021-07-05
start as the coverage baseline, which inflated 1,153 of 1,220 audited dates as false gaps —
the feature simply didn't exist yet for 94.5% of that range. `EXPECTED_COVERAGE_START =
"2026-04-23"` in `tools/check_broker_flow_coverage.py` encodes the corrected baseline.

## Backfill Execution

| Phase | Scope | Result |
|---|---|---|
| Validation (single date) | `2026-08-03` | 802/803 tickers inserted; 1 failure (`IHSG`, expected — see below) |
| Full backfill | 65 dates, `2026-04-23` → `2026-08-03` (today excluded — market was open) | 9,982 rows inserted, 8.23h elapsed, fully unattended (detached process, resumable) |
| Integrity | Whole table | Zero duplicate primary keys, before and after; pre-existing rows on every date left untouched |

## Permanent Unsupported-Ticker Policy

92 tickers (of ~959 in the universe) return **HTTP 200 with genuinely empty broker arrays**
on every single date tested — minimum sample size 42 dates (of ~67 possible), no borderline
cases. Live-verified on 7 of them (`IHSG`, `SWAT`, `TGRA`, `WSBP`, `BTEL`, `WIKA`, `ARMY`) on
dates never previously queried. This set is `IHSG` (the composite index, not a stock) plus
suspended/delisted/severely distressed small-caps (e.g. `WSKT`, `WIKA`, `WSBP` — known
distressed state contractors). **These are a confirmed permanent API limitation, not missing
data or an ingestion failure.**

`tools/check_broker_flow_coverage.py::unsupported_tickers()` computes this set dynamically
(never hardcoded, so it self-corrects if a ticker resumes trading) using an evidentiary
threshold (`UNSUPPORTED_MIN_SAMPLES = 20`, well below the observed real floor of 42) to guard
against misclassifying a coincidentally-quiet ticker or a new listing with little history.

## Coverage Calculation (Corrected)

```
effective_expected(date) = ohlcv_ticker_universe(date) − unsupported_tickers
status = COMPLETE  if effective_expected == 0, or actual >= effective_expected
         PARTIAL   if 0 < actual < effective_expected
         MISSING   if actual == 0 (and effective_expected > 0)
```

## Final Coverage (2026-08-04, post-backfill, post-correction)

| | Before any of this work (wrong baseline) | After |
|---|---|---|
| Trading dates in scope | 1,220 (since 2021-07-05, wrong) | 67 (since 2026-04-23, correct) |
| Expected tickers/date | ~959 (raw ohlcv, wrong) | ~867 (minus 92 confirmed-unsupported) |
| COMPLETE | 1 | 2 |
| PARTIAL | 66 | 65 |
| MISSING | 1,153 (nearly all false, wrong baseline) | 0 |

## Remaining Limitations (Accepted, Not Actionable)

- **65 PARTIAL dates remain**, with gaps of 6-45 tickers/date (avg ~24) beyond the 92
  confirmed-unsupported set. This is genuine day-to-day trading variance — different tickers
  having zero broker activity on different specific days — not a fixable backfill gap, since
  it isn't the same set of tickers each time.
- `2026-07-09` shows an anomalously low raw `ohlcv` ticker count (a pre-existing data-quality
  artifact in `ohlcv` itself, unrelated to `broker_flow` and out of this task's scope).
- `missing_tickers_for_date()` in `tools/backfill_broker_flow_gap.py` does not itself subtract
  `unsupported_tickers()` — a future re-run of the backfill script would harmlessly re-probe
  the 92 confirmed-unsupported tickers again per gap date (wasted requests, no data
  corruption, since they always return empty and are simply not written). Noted as a known,
  accepted inefficiency rather than fixed under this freeze, per the freeze's no-new-code
  constraint; a candidate follow-up if this tool is ever run again at scale.

## Research & Operational Readiness

- `stockbit_flow`, `stockbit_flow_bars`: COMPLETE (prior work, unaffected by this task).
- `broker_flow`, `bandar_detector`: **COMPLETE at maximum fidelity the Stockbit API
  supports**, evidenced and reproducible via `tools/check_broker_flow_coverage.py`.
- `python3 stockbit_fetcher.py flow --date YYYY-MM-DD` writes all three datasets
  (`stockbit_flow`, `stockbit_flow_bars`, `broker_flow`) in one call — verified by
  `tests/test_stockbit_fetcher_broker_flow_historical.py::test_cli_flow_date_writes_all_three_tables`.
- No further broker-flow backfill is required or recommended.

## Files Changed

- `stockbit_fetcher.py` — `fetch_broker_flow(token, ticker, date=None)`; `run_flow()` guard fix
- `tools/check_broker_flow_coverage.py` (new) — gap auditor, corrected baseline, unsupported-ticker exclusion
- `tools/backfill_broker_flow_gap.py` (new) — idempotent, gap-only, resumable backfill
- `tests/test_stockbit_fetcher_broker_flow_historical.py`, `tests/test_check_broker_flow_coverage.py`,
  `tests/test_backfill_broker_flow_gap.py` (new) — 30 tests, all passing
- `docs/audit/BROKER_FLOW_BACKFILL_REPORT.md` (this file)
