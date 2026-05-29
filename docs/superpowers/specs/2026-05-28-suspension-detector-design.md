# G2 — Trading Suspension / Data Gap Detector

**Status**: Approved design, ready for implementation plan
**Date**: 2026-05-28
**Sprint**: 17 (TODO.md G2)
**Estimated effort**: ~3 hours

## Problem

Three of the four tickers in the 2026-05-27 deep-dive reports (BRPT, DEWA, BULL) experienced an identical ~11-calendar-day trading halt in mid-May 2026 followed by a -20% to -28% gap-down on resume. The system was blind to it. Every rolling indicator silently blended the discontinuity:

- `calc_atr` (engine/strategies.py:43) computes True Range as `max(h−l, |h−c.shift()|, |l−c.shift()|)`. On the resume bar, `c.shift()` returns the pre-halt close, so the entire gap-down move is absorbed into one bar's TR. This inflates ATR for the next 14 bars.
- Every other `.rolling()` / `.shift()` indicator (MA, ADX, VR) similarly mixes pre- and post-halt bars as if they were contiguous.

Downstream effects: ATR-based TP/SL targets become wildly wrong, ADX gives false-positive trend readings, walk-forward backtests of any window containing a halt are corrupted, and the user has no visibility into "this stock was suspended, treat its indicators with suspicion."

## Scope (and explicit non-goals)

This spec covers **detection, persistence, and a read API only**. The G2 TODO entry bundles four responsibilities; this first pass implements two and explicitly defers the others:

| Responsibility | In this sprint? |
|---|---|
| Detect trading-day gaps in the OHLCV history | ✅ |
| Persist events and expose a status query | ✅ |
| Adjust indicator math (`calc_atr` etc.) | ❌ — overlaps R9 (indicator library) |
| Telegram `post_suspension` alert | ❌ — that is G8 |
| dive.html shaded-region annotation | ❌ — that is G9 |

The goal is to make the system *aware* of halts and expose that awareness through a small read API. Downstream consumers (G8 alert, G9 chart marker, future indicator-guard work) will read this data; this sprint does not modify any existing scan or strategy code beyond a single fail-soft call site in the scheduler.

## Architecture

One new module, one new SQLite table, one new call site.

### Module: `engine/suspension_detector.py`

Three layers separated by I/O concerns:

```
detect_gaps(df, *, threshold_days=3, price_jump_pct=10.0) -> list[GapEvent]
    # Pure function. No DB, no logging. Takes an OHLCV df, returns events.
    # Easy to unit-test with synthetic frames.

scan_all(ohlcv_map=None, *, threshold_days=3) -> int
    # Loads bulk OHLCV if not provided, runs detect_gaps per ticker,
    # writes events to suspension_events (idempotent via PK).
    # Returns count of rows written/updated.

get_status(ticker, *, as_of=None, post_window=14) -> dict
    # Read API for callers (dive.html, future G8 alert, future indicator-guard).
    # Queries the table for the most recent event and derives flags.
```

**Dependencies**: `pandas`, `sqlite3`, `engine.calendar_filter.is_trading_day`. Nothing else.

### Schema: `suspension_events`

Created inline via `CREATE TABLE IF NOT EXISTS` from a private `_ensure_schema()` helper in the module, called at the top of `scan_all()` and `get_status()`. Matches the project's existing pattern (scheduler.py applies DDL inline rather than via separate migration scripts).

```sql
CREATE TABLE IF NOT EXISTS suspension_events (
    ticker            TEXT NOT NULL,
    last_normal_date  TEXT NOT NULL,   -- ISO date of last bar before the gap
    resume_date       TEXT NOT NULL,   -- ISO date of first bar after the gap
    missing_td        INTEGER NOT NULL, -- trading-day count, calendar-aware
    gap_pct           REAL NOT NULL,    -- (resume_open - last_close) / last_close
    classification    TEXT NOT NULL,    -- 'suspension' | 'data_gap'
    detected_at       TEXT NOT NULL,    -- ISO timestamp
    PRIMARY KEY (ticker, last_normal_date, resume_date)
);
CREATE INDEX IF NOT EXISTS idx_suspension_ticker_resume
    ON suspension_events(ticker, resume_date DESC);
```

Lives in the same `data/walkforward.db` as `ohlcv`. The composite PK makes `scan_all` idempotent — re-running it never duplicates events.

### Call site

In `scheduler.py`, after `fetch_latest()` completes:

```python
try:
    from engine.suspension_detector import scan_all as _scan_suspensions
    _scan_suspensions()
except Exception as e:
    logging.exception("suspension scan failed (non-fatal): %s", e)
```

Fail-soft: a detector exception must never break the daily fetch pipeline.

## Detection logic

For each ticker's OHLCV dataframe (sorted ascending by `date`):

1. Iterate consecutive bar pairs `(bar_i, bar_{i+1})`.
2. Count trading days strictly between `bar_i.date` and `bar_{i+1}.date` using `is_trading_day()` from `engine/calendar_filter.py`. Weekends and IDX holidays are already excluded by that function.
3. If `missing_td <= threshold_days` (default 3), skip — normal gap.
4. Otherwise compute `gap_pct = (open_{i+1} − close_i) / close_i`.
5. Classify:
   - `|gap_pct| >= price_jump_pct/100` (default ≥10%) → `'suspension'`
   - Otherwise → `'data_gap'` (recorded for visibility but does not trip the post-suspension flag)

The price-discontinuity check distinguishes a real halt (BRPT-style: 11 days missing + −28% gap-down) from a yfinance fetcher miss (a few days missing + continuous price). Without it, the IDX's notoriously unreliable data source would generate constant false positives.

### Worked example — BRPT May 2026

BRPT's history shows a bar at May 14 (close 2080) and the next bar at May 25 (open ≈ 1495).

- Trading days strictly between May 14 and May 25 (exclusive on both ends), filtered by `is_trading_day` (SKB 2026):
  - May 15 (Fri): Cuti Bersama Kenaikan — excluded
  - May 16, 17 (weekend): excluded
  - May 18–22 (Mon-Fri): trading
  - May 23, 24 (weekend): excluded
  → 5 missing trading days. Exceeds threshold of 3.
- `gap_pct = (1495 − 2080) / 2080 = −0.281`, magnitude 28.1% ≥ 10%.
- Result: one event with `missing_td=5`, `gap_pct=-0.281`, `classification='suspension'`.

## `get_status` semantics

Given `as_of` (defaults to today) and `post_window` (default 14 trading days):

```python
{
    "ticker": "BRPT",
    "suspended_now": False,       # True only if as_of is strictly between
                                  # last_normal_date and resume_date of the
                                  # most recent open halt
    "post_suspension": True,      # True if most recent event is a suspension
                                  # AND resume_date <= as_of <= resume_date + post_window
                                  #     (counted in trading days)
    "days_since_resume": 3,       # int, trading days; None if no event
    "last_event": {               # full row dict, or None
        "last_normal_date": "2026-05-14",
        "resume_date": "2026-05-25",
        "missing_td": 5,
        "gap_pct": -0.281,
        "classification": "suspension",
        "detected_at": "2026-05-28T09:00:00+07:00",
    },
}
```

The `post_window=14` default ties the "indicators still contaminated" flag to the default ATR period — when it clears, the rolling-14 windows have rolled past the discontinuity.

## Testing

`tests/test_suspension_detector.py`, all pure unit tests against `detect_gaps()` with hand-built dataframes plus one in-memory-SQLite round-trip:

| Fixture | Expected events |
|---|---|
| Contiguous daily bars, no missing dates | 0 |
| Normal Fri→Mon weekend (no missing trading days) | 0 |
| Long holiday cluster (Mar 19–24 Idul Fitri stretch) | 0 |
| BRPT-shaped 11-cal-day gap with −28% gap-down | 1, classification=`suspension`, `missing_td≥4` |
| 4-trading-day fetch miss with price continuous (<10%) | 1, classification=`data_gap` |
| Round-trip: `scan_all` → `get_status` against in-memory SQLite | status reflects the inserted event |

The integration test uses a real in-memory SQLite (`:memory:`) seeded with two tiny ohlcv dataframes, not a mock — consistent with the project's existing test style.

## Migration / deployment

1. Schema is applied by an inline `_ensure_schema()` helper at the top of `scan_all()` and `get_status()` — same pattern the rest of the project uses. No separate migration script.
2. Backfill is a single call to `scan_all()` against the full `ohlcv_map`. Run it once after deploy to populate historical events (BRPT, DEWA, BULL, and whatever else surfaces from the universe). The daily call from `scheduler.py` will keep it current from then on.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| False positives from yfinance fetch gaps | Price-discontinuity classifier separates `data_gap` from `suspension` |
| Calendar list drifts (2027 holidays not added) | `is_trading_day` falls back to weekday-only, which is still mostly correct; out-of-scope for this sprint |
| Existing OHLCV has weird historical gaps from earlier data backfills | First-run `scan_all` writes them all as visible events; user can audit the table and decide whether to treat any as historical noise |
| Detector exception breaks the daily fetch pipeline | Wrapped in try/except in scheduler with `logging.exception` |
| Storage growth | A halt event per ticker is rare; even decades of data is kilobytes |

## Diff estimate

| File | Δ |
|---|---|
| `engine/suspension_detector.py` (new) | ~180 lines |
| `tests/test_suspension_detector.py` (new) | ~120 lines |
| `scheduler.py` (call site) | +5 lines |

Total: ~3 hours implementation, matching the TODO.md estimate.

## What this unblocks

Once G2 lands, the following become small follow-on changes rather than research projects:

- **G8** Telegram `post_suspension` alert — reads `get_status()`, formats a message.
- **G9** dive.html shaded-region marker — fetches `get_status()` via a new tiny API endpoint, renders a price-line/region on the chart.
- **G1** Backtest auto-roller can skip windows that overlap a halt event for the ticker under test.
- **Indicator-guard variant** (future, paired with R9): a `calc_atr_gap_safe()` that consults the events table to cap TR on resume bars. Not in this sprint.
