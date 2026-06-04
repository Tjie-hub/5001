# G1: Backtest Auto-Rolling Pipeline — Design Spec
_2026-06-04_

## Problem

Walk-forward strategy scores are computed across a fixed set of windows that end at the last complete 3-month test period. As of 2026-06-04:

- `wf_scores` (871 tickers): refreshed weekly but stores only per-strategy averages — no per-window breakdown, no way to inspect what any individual window looked like
- `out/meta_dataset_backtest.json`: generated once by `_archive/meta_validate.py`, covers 45 tickers, 4 windows max (latest test_end = 2026-04-29), never auto-refreshed
- **The May 2026 BRPT crash (−35%) is invisible** — BRPT's next WF window would have test_end = 2026-07-16, which exceeds today's OHLCV date, so `walk_forward_split()` drops it

## Goals

1. Store per-window walk-forward data in a queryable DB table (`backtest_windows`)
2. Auto-roll: when new complete 3-month windows become available, insert them
3. Partial-window flag: insert the current in-progress test window (even if < 3 months) so recent crashes are visible — flagged `is_partial=1`
4. Regenerate `out/meta_dataset_backtest.json` from DB automatically (same format, all tickers)
5. Scheduled monthly run (Sunday 10:00 WIB) + on-demand API endpoint

## Architecture

### New file: `engine/backtest_roller.py`

```
backtest_roller.py
├── _init_table(conn)          — CREATE TABLE IF NOT EXISTS backtest_windows
├── roll_ticker(ticker, df, conn, include_partial=True)
│   — runs walk_forward_split(df)
│   — finds windows with test_end not already in DB for this ticker
│   — inserts new complete windows
│   — inserts partial window if data exists beyond last complete test_end
├── roll_all(tickers=None, include_partial=True) → dict summary
│   — loads OHLCV bulk, iterates tickers, calls roll_ticker
│   — returns {new_windows, partial_windows, tickers_updated, errors}
└── export_meta_dataset(path=OUT_PATH, tickers=None) → int
    — reads backtest_windows, writes JSON in existing format
    — returns row count
```

### DB table: `backtest_windows`

```sql
CREATE TABLE IF NOT EXISTS backtest_windows (
    ticker       TEXT NOT NULL,
    window_num   INTEGER,
    train_start  TEXT,
    train_end    TEXT,
    test_start   TEXT NOT NULL,
    test_end     TEXT NOT NULL,
    is_partial   INTEGER DEFAULT 0,   -- 1 = incomplete test period
    features_json TEXT,               -- {"adx": ..., "ma_slope": ..., ...}
    metrics_json  TEXT,               -- {"vol_weighted": {"return": ..., ...}, ...}
    computed_at  TEXT,
    PRIMARY KEY (ticker, test_start)
)
```

### Features per window (same as existing meta_dataset_backtest.json)
`adx`, `ma_slope`, `vr_mean`, `range_pct`, `close_vs_ma`, `pct_above_ma` — computed from the **last bar of the train slice** (forward-looking-safe, represents conditions entering the test window).

### Metrics per window
Per strategy: `return`, `win_rate`, `sharpe`, `max_dd`, `profit_factor` — from `compute_metrics()`.

### Scheduler addition (`scheduler/jobs.py`)
```python
def run_backtest_roller():
    from engine.backtest_roller import roll_all, export_meta_dataset
    summary = roll_all(include_partial=True)
    export_meta_dataset()
    send_telegram(...)
```

Schedule: `CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=WIB)` in `scheduler/__init__.py`.

### Flask endpoint (`routes/backtest.py`)
`POST /api/backtest/roll` — triggers `roll_all()` + `export_meta_dataset()` on demand. Returns summary JSON.

## Partial Window Logic

After completing all full windows, check if there's remaining data beyond the last `test_end`:
```
partial_start = last_complete_test_end
partial_end   = df['date'].max()
partial_bars  = df[df['date'] >= partial_start]
```
If `len(partial_bars) >= 10` (at least 2 weeks of data), insert as `is_partial=1`. This makes the Apr–Jun 2026 period (including BRPT crash) visible immediately.

## `meta_dataset_backtest.json` format (preserved)
```json
[
  {
    "ticker": "BRPT",
    "window": 4,
    "test_start": "2026-04-16",
    "test_end": "2026-06-04",
    "features": {"adx": ..., ...},
    "metrics": {"vol_weighted": {"return": ..., ...}, ...}
  },
  ...
]
```
Partial windows are included in JSON output (consumers can filter by checking if `test_end < today - 90d`).

## What is NOT changed
- `wf_scores` table and `refresh_wf_scores()` — unchanged, still runs Friday
- `walk_forward_split()` — unchanged (no modification to existing engine)
- `backtest_cache` table — unchanged

## Tests (`tests/test_backtest_roller.py`)
1. `test_roll_ticker_inserts_new_windows` — fresh ticker, 4 windows inserted
2. `test_roll_ticker_skips_existing` — idempotent re-run inserts 0
3. `test_roll_ticker_partial_window` — partial window inserted with is_partial=1
4. `test_roll_all_returns_summary` — summary dict has expected keys
5. `test_export_meta_dataset_format` — JSON output matches expected schema
6. `test_export_meta_dataset_tickers_filter` — subset filter respected

## Files changed
- `engine/backtest_roller.py` — new
- `scheduler/jobs.py` — add `run_backtest_roller()`
- `scheduler/__init__.py` — add Sunday 10:00 cron job
- `routes/backtest.py` — add `POST /api/backtest/roll` endpoint
- `tests/test_backtest_roller.py` — new
