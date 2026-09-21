# Dataset Contract — `stockbit_flow`

**Status:** Canonical · **Owner:** data/ingestion (Stockbit fetchers) · **Effective:** 2026-07-27

> This document defines what `stockbit_flow` *is contractually expected to be* — its shape,
> cadence, and known limits — so that a gap or artifact can be checked against a stated
> expectation instead of judged by intuition. It governs interpretation only; it does not change
> ingestion behavior.

## Purpose

Daily net order-flow (buy/sell lot, frequency, and value) per ticker per trading day, sourced from
Stockbit's trade-book/chart endpoint. Feeds smart-money/verdict scoring used by the dashboard,
premarket/EOD scans, and the agent-firm's flow-confirmation signal. It is a **production-facing**
table (read by `scheduler/`, `engine/`, `routes/`) — not a research-owned table, and not subject to
the research/production write fence in `tests/test_research_data_fence.py`.

## Source

- **Upstream:** Stockbit `GET https://exodus.stockbit.com/order-trade/trade-book/chart`
  (`symbol`, `time_interval=1m`, optional `date` for a historical session).
- **Fetchers:** `stockbit_fetcher.py::fetch_flow()` / `run_flow()` (CLI: `python3 stockbit_fetcher.py flow`),
  invoked by:
  - cron `stockbit_flow` (`deploy/crontab`, `30 18 * * 1-5`, `ALL` ticker universe, live session)
  - APScheduler `Broker Flow Fetch 20:15` (`scheduler/jobs.py::run_broker_flow_fetch`, `ALL` + any open paper-trade tickers)
  - manual/backfill invocations with an explicit `--date` (historical session, any ticker subset)
- **Auth:** short-lived Stockbit JWT (`.stockbit_token`, ~24h lifetime, refreshed by `auto_token.py`).
  A request with an expired/invalid token fails at the HTTP layer before reaching this table — see
  Known Artifacts for how that differs from the retention-boundary case below.

## Schema

```sql
CREATE TABLE stockbit_flow (
    ticker TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    buy_lot INTEGER, sell_lot INTEGER, net_lot INTEGER,
    buy_freq INTEGER, sell_freq INTEGER,
    net_value INTEGER,
    last_price INTEGER,
    updated_at TEXT NOT NULL,
    composite_score INTEGER, verdict TEXT, smart_money TEXT, foreign_score REAL,
    PRIMARY KEY (ticker, trade_date)
)
```

One row per `(ticker, trade_date)`. `net_lot = buy_lot − sell_lot`. `composite_score` / `verdict` /
`smart_money` are derived from the same fetch's intraday bars when available (see
`stockbit_fetcher.py::_analyze`) and may be `NULL` on rows written by tooling that only stores the
daily summary (e.g. `backfill_stockbit_flow_gap.py`, which deliberately does not compute these to
stay out of `stockbit_flow_bars` — see Known Artifacts).

## Expected Cadence

One write per ticker per **IDX trading day** (Mon–Fri, ex-holidays), sourced same-day after market
close. There is no intraday update cadence for this table — `stockbit_flow_bars` (a separate table,
out of scope here) carries the minute-level series for the current/recent session.

## Historical Retention

**Historical coverage before `2025-01-02` is not expected and is not an ingestion defect.**

Established by direct, evidence-based testing (`docs/audit/STOCKBIT_FLOW_BACKFILL_FEASIBILITY.md`):
requests for `date < 2025-01-02` return **HTTP 200 with an empty payload** — not an error, not a
rate limit, not an auth failure. The upstream endpoint simply does not retain trade-book history
before that date. This was bisected to single-day precision (`2024-12-30` → empty,
`2025-01-02` → populated) and is treated as a **fixed retention boundary**, not a rolling window —
it did not track "N days before today" when measured.

Consequence: `MIN(trade_date)` for this table can never validly be earlier than `2025-01-02`. A
coverage check must start its expectations at that date, not at the OHLCV corpus start
(`2021-07-05`) or any other production table's history.

## Known Artifacts

- **`trade_date = ''` rows.** The live (non-historical) trade-book endpoint returns an empty `date`
  field pre-/post-session; `fetch_flow()` falls back to the request date or "now" for the *bars*
  path, but a handful of rows in `stockbit_flow` itself were written before that fallback existed
  and carry a blank `trade_date`. **Expected, pre-existing, not corruption.** 98 such rows as of
  2026-07-27. Excluded from all coverage/gap arithmetic (see `DATA_QUALITY_RULES.md`).
- **Sparse ticker coverage on some pre-2026-05 dates.** Several 2025 and early-2026 dates were only
  ever backfilled against a narrower universe (LQ45's 45 tickers, or IDX80's 79) rather than the
  current live `ALL` (~958-ticker) universe. This is expected variation from how each date was
  populated (live cron vs. scoped backfill), not a corruption signal — see
  `docs/audit/STOCKBIT_FLOW_BACKFILL_REPORT.md` for the specific 122-date recovery this contract
  formalizes.
- **`stockbit_flow_bars` is a separate table** (minute-level bars, retention ~2025-07-07 onward,
  narrower than `stockbit_flow`'s retention). It is out of scope for this contract and for
  `tools/check_stockbit_flow_coverage.py`.

## Limitations

- No way to distinguish, from this table alone, "market was closed" from "fetch genuinely failed"
  for a date outside the OHLCV trading calendar — always cross-reference `ohlcv` for the trading-day
  ground truth (as this contract and its validator both do).
- `INSERT OR REPLACE` on the primary key means a re-fetch silently overwrites a prior row for that
  `(ticker, trade_date)` — there is no row-level history/audit trail of revisions.
- Universe membership (`ALL` / `LQ45` / `IDX80`) is not recorded per row, so "was this date meant to
  have 958 tickers or 79?" cannot be answered from the table alone — only inferred heuristically
  (see `check_flow_coverage()` in `scheduler/jobs.py` and the validator's mirrored logic).

## Validation Rules

See `docs/data/DATA_QUALITY_RULES.md` for the full, generalized rule set. Summary as it applies to
this dataset specifically:

| Rule | Applies |
|---|---|
| A trading date `>= 2025-01-02` missing entirely from `stockbit_flow` is a genuine gap | Yes |
| A trading date `< 2025-01-02` missing from `stockbit_flow` is expected, not a gap | Yes |
| `trade_date = ''` rows are excluded from coverage arithmetic, not treated as corrupt | Yes |
| Duplicate `(ticker, trade_date)` rows are invalid | Yes (schema PK should already prevent this) |
| A date whose ticker coverage sits far below its trailing local baseline is a partial day worth flagging | Yes, informational — see rules doc for why this is a warning, not a hard failure |
