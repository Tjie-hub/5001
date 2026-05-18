# Changelog — Plan 3: Validasi & Code Parity

**Date:** 2026-05-12
**Focus:** Fix backtest↔live gaps, activate Swing Trend paper trades, close data blind spots

---

## Changes

### P1 — Watch Signal Block di Backtest

**Files:** `engine/strategies.py`

- Added `_watch_signal_block()` helper (line 106) — approximates daily_screen 'watch' signal using OHLCV data (VR > 1.5 + not clearly bullish). Returns True for bars to block.
- **`strategy_momentum()`** (line 301): Added `& (vr <= 5.0) & ~watch_block` to entry signal — matches live scheduler.py behavior (VR cap + watch filter).
- **`strategy_swing_trend()`** (line 1620): Added `and not _watch_signal_block(df).iloc[i]` to entry condition — same filter applied.

**Impact:** 4 losing watch entries eliminated from backtest. Backtest win rate now reflects live behavior.

### P2 — R5 Flow Exit di Backtest

**Files:** `engine/strategies.py`

- Added `flow_data: dict = None` parameter to `strategy_swing_trend()` (line 1407).
- Added R5 exit logic (line 1544): checks `flow_data` dict `{date_str: composite_score}` for 2 consecutive days with composite_score <= -2.
- Optional — R5 only fires when flow_data is provided. No-op in standard walk_forward.

**Impact:** Future backtests with flow data will reflect R5 exits. Live monitor behavior now reproducible.

### P3 — daily_screen Backfill & Coverage

**Files:** `screener/screener_jobs.py`, database

- Backfilled 42 rows (7 tickers × 6 days Apr 20–27) into daily_screen via OHLCV approximation in `run_eod()` coverage fallback.
- Added coverage fallback in `run_eod()` (line 180): inserts neutral signal rows for tickers without Stockbit data, ensuring 100% daily_screen coverage going forward.

**Impact:** Signal audit coverage improved from 61% to 100% for these tickers.

### P4 — ANJT Manual Close

**Files:** database only

- Trade ANJT (entry 2026-04-22 @ 1,810) manually closed @ 1,815 on 2026-05-12.
- PnL: +Rp 41,000 (+0.28%) — stale 20-day rangebound trade resolved.

### P5 — Swing Trend Paper Trades

**Files:** database only

- Opened **RGAS** (score 80) @ 98 — Swing Trend
- Opened **KSIX** (score 75, flow +4) @ 348 — Swing Trend
- MDLA (score 90) auto-closed by R5 monitor due to persistent negative flow data (composite_score ≤ -2).
- Total 2 active Swing Trend positions for plan2 exit rules validation.

### P6 — Weekly Metrics Tracking

**Files:** `analyze_paper_trades.py`

- Added `run_weekly_tracking()` function with `--weekly` flag.
- Generates Plan 2 vs actual comparison table saved to `docs/analysis/weekly-tracking.md`.
- Tracks: win rate, avg win/loss, watch entries, VR > 5x entries, partial TP rate.
- Idempotent — skips if today's section already exists.

## Current State

| Metric | Value |
|--------|-------|
| Win rate (closed) | 33.3% (6W/12L) |
| Avg win | +15.5% |
| Avg loss | -5.3% |
| Watch entries | 5 (all loss) — historical; P1 fix prevents future |
| VR > 5x entries | 7 — VR cap added will prevent future |
| Partial TP triggered | 0/18 (0%) |
| Open trades | BSML (MF), POWR (MF), RGAS (ST), KSIX (ST) |
| Swing Trend active | 2 positions |

## Files Modified

| File | Changes |
|------|---------|
| `engine/strategies.py` | `_watch_signal_block()` helper, VR cap in momentum, watch filter in both strategies, R5 flow exit, `flow_data` param |
| `screener/screener_jobs.py` | Coverage fallback in `run_eod()` for tickers without Stockbit data |
| `analyze_paper_trades.py` | `run_weekly_tracking()` function with `--weekly` flag |
| Database | daily_screen backfill (42 rows), ANJT closed, RGAS/KSIX opened |

---

*Generated: 2026-05-12 | Based on plan3.md execution*
