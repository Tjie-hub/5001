# REVERSAL_BREAKOUT Pattern — Design Spec

**Date:** 2026-05-13
**Status:** Draft
**Project:** idx-walkforward-5001 / premover_detector.py
**Rationale:** The existing CONTINUATION pattern misses stocks that explode from a low/support base with unusual volume — exactly what ASPR did (+630% in 1 month). These moves lack the classic pre-breakout setup (above MA50, ADX rising, near 52w high) at the time of the initial trigger, making them invisible to the current system until well after the move is established.

---

## 1. Problem Statement

### Current System Blind Spot

The premover detector (`score_ticker()`) uses one pattern: CONTINUATION.

Its scoring rewards stocks that are **already in an uptrend** (above MA50, ADX ≥ 22, near 52w high). This works well for trend-following entries but completely misses **reversal/breakout from a low base** — where the stock hasn't established an uptrend yet, but the first signs of unusual accumulation appear.

**ASPR case study (caught at +71%, should have been caught at +1.5%):**

| Date | Price | Pattern | Premover catches | Should catch |
|---|---|---|---|---|
| Apr 22 | 199 | Near 50d low | Below MA50, ADX low, far from 52w high → **score 0** | — |
| Apr 24 | 202 | Vol 5.8x avg, green day | Still below MA50 → **score 0** | Volume explosion + near low → **70** |
| Apr 27 | 212 | Close > 3d MA, vol surging | Still below MA50 → **score 0** | All reversal signals → **85** |
| May 6 | 452 | ADX=29, above MA50 | **CONTINUATION → 70** (11 days late) | — |

The CONTINUATION pattern is correct to not fire here — ASPR didn't have a continuation setup. But there should be a **second pattern** that catches this type of move.

---

## 2. Pattern Definition: REVERSAL_BREAKOUT

Detects stocks reversing from a low/support base with explosive volume — catching the move BEFORE the uptrend is established.

### 2.1 Indicator Scoring (sum = 100)

| # | Indicator | Pts | Condition | Rationale |
|---|---|---|---|---|
| 1 | **VOLUME_EXPLOSION** | 30 | Latest bar volume > 2.0x trailing 20-day median volume | Primary signal — unusual volume is the earliest sign of accumulation |
| 2 | **PRICE_NEAR_LOW** | 20 | Close within 20% of 50-day lowest close | Confirms stock is reversing from a base/pullback, not buying a breakout |
| 3 | **BREAKING_SHORT_TREND** | 20 | Close > 3-day simple moving average | First measurable sign the short-term downtrend has broken |
| 4 | **POSITIVE_CLOSE** | 15 | Close > previous day's close | Shows buying pressure on the trigger day |
| 5 | **ATR_EXPANSION** | 10 | ATR(14) ≥ rolling 30-period median of ATR(14) | Volatility is at least stable — not contracting (unlike VCP). Punish contracting vol |
| 6 | **FLOW_CONFIRMATION** | 5 | Stockbit composite_score > 0 (latest available) | Smart-money flow adds conviction; small weight since flow data is delayed |

**Total possible: 100**
**Alert threshold: 45**

### 2.2 Threshold Rationale

Threshold 45 means a stock needs to hit at minimum:
- VOLUME_EXPLOSION (30) + PRICE_NEAR_LOW (20) = 50 — hits with only 2 conditions
- Or VOLUME_EXPLOSION (30) + BREAKING_SHORT_TREND (20) = 50

This ensures early detection while filtering out random noise (low-volume days, minor moves not near a base).

### 2.3 ASPR Backtest

| Date | Price | Vol_ratio | Near_50d_low | Close>3dMA | Green | ATR>=med | Flow | Score | Catch? |
|---|---|---|---|---|---|---|---|---|---|
| Apr 22 | 199 | 0.8x | Yes | No | No | — | — | 20 | ❌ |
| Apr 23 | 199 | 2.0x? | Yes | No | No | — | — | ~20-30 | ❌ |
| **Apr 24** | **202** | **5.8x** | **Yes** | **No** | **Yes** | **~5** | **?** | **~70** | **✅** |  |  |  |
| **Apr 27** | **212** | **6.0x?** | **Yes** | **Yes** | **Yes** | **~8** | **?** | **~93** | **✅** |
| Apr 28 | 230 | 4.0x? | Yes | Yes | Yes | — | — | ~100 | Already caught |

**First catch: April 24 at price 202 — 11 trading days before the current system caught it at 452.**

---

## 3. Implementation Plan

### 3.1 File Changes

**File: `engine/premover_detector.py`**

#### A. New function: `score_ticker_reversal()`

Signature:
```python
def score_ticker_reversal(df: pd.DataFrame, flow_score: float = None) -> dict:
    """
    Score ticker for REVERSAL_BREAKOUT pattern.
    
    Returns dict with:
      'score'       - int 0-100
      'reasons'     - list of strings (e.g. ['VOLUME_EXPLOSION(5.8x)', ...])
      'vol_ratio'   - float (volume / 20d median volume)
      'near_low'    - int 0/1 (within 20% of 50d low)
      'above_3ma'   - int 0/1
      'green_day'   - int 0/1
      'atr_ratio'   - float (ATR14 / ATR30_median)
      'close'       - float
    """
```

Required data: at least 50 bars (for 3d MA, 20d vol median, 50d low, ATR calculations).

#### B. Table migration in `_init_table()`

Add `pattern_type` column and change uniqueness constraint:

```sql
-- Add column if not exists
ALTER TABLE watchlist_premover ADD COLUMN pattern_type TEXT NOT NULL DEFAULT 'CONTINUATION';

-- Drop old unique index and create new one
-- (SQLite doesn't support ALTER TABLE DROP INDEX, need CREATE UNIQUE INDEX with new name)
CREATE UNIQUE INDEX IF NOT EXISTS idx_premover_unique 
    ON watchlist_premover(ticker, detected_at, pattern_type);
```

New rows inserted with `pattern_type = 'REVERSAL_BREAKOUT'` or `'CONTINUATION'`.

#### C. Modified `run_scan()`

```python
def run_scan(db_path: str, send_alert_fn=None) -> list:
    # ... existing setup code ...
    
    for ticker, df in ohlcv_map.items():
        if ticker == 'IHSG' or len(df) < 60:
            continue
        
        new_setups_for_ticker = []
        
        # Run CONTINUATION pattern
        try:
            result = score_ticker(df, ihsg_df=ihsg_df, flow_score=flow_map.get(ticker))
            if result['score'] >= ALERT_THRESHOLD:
                insert_setup(conn, ticker, detected_at, 'CONTINUATION', result)
                if row_inserted:
                    new_setups_for_ticker.append({'ticker': ticker, 'pattern': 'CONTINUATION', **result})
        except Exception as e:
            print(f"[premover] {ticker} CONTINUATION error: {e}")
        
        # Run REVERSAL_BREAKOUT pattern
        try:
            result = score_ticker_reversal(df, flow_score=flow_map.get(ticker))
            if result['score'] >= REVERSAL_THRESHOLD:
                insert_reversal_setup(conn, ticker, detected_at, result)
                if row_inserted:
                    new_setups_for_ticker.append({'ticker': ticker, 'pattern': 'REVERSAL_BREAKOUT', **result})
        except Exception as e:
            print(f"[premover] {ticker} REVERSAL error: {e}")
    
    # ... alert logic with both patterns ...
```

#### D. Alert message format

When both patterns have new setups, the alert shows them grouped:

```
🔍 Pre-Breakout Setups — 2026-05-13

── REVERSAL_BREAKOUT ──
<b>ASPR</b> — Score 70/100
  VOLUME_EXPLOSION(5.8x) · PRICE_NEAR_LOW · POSITIVE_CLOSE
  Close: 202

── CONTINUATION ──
<b>WINS</b> — Score 100/100
  CONTINUATION(ADX=44) · NEAR_52W_HIGH · ATR_CONTRACTED · VOL_DRYUP
  Close: 565

Total: 2 new setups
```

#### E. Updated `get_watchlist()` and `mark_fired()`

- `get_watchlist()`: add optional `pattern_type` filter parameter
- `mark_fired()`: update matched rows regardless of pattern type (or add pattern-specific marking)

### 3.2 Database Schema Change

**Current schema:**
```sql
CREATE TABLE watchlist_premover (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker       TEXT    NOT NULL,
    detected_at  TEXT    NOT NULL,
    score        INTEGER NOT NULL,
    reasons_json TEXT,
    above_ma50   INTEGER,
    adx          REAL,
    near_52w     INTEGER,
    atr_ratio    REAL,
    vol_dryup    REAL,
    rs           REAL,
    close_price  REAL,
    fired        INTEGER DEFAULT 0,
    fired_at     TEXT,
    UNIQUE(ticker, detected_at)
);
```

**New schema:**
```sql
CREATE TABLE watchlist_premover (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker       TEXT    NOT NULL,
    detected_at  TEXT    NOT NULL,
    pattern_type TEXT    NOT NULL DEFAULT 'CONTINUATION',
    score        INTEGER NOT NULL,
    reasons_json TEXT,
    above_ma50   INTEGER,           -- CONTINUATION: above MA50 flag
    adx          REAL,              -- CONTINUATION: ADX value
    near_52w     INTEGER,           -- CONTINUATION: near 52-week high
    near_low     INTEGER,           -- REVERSAL: within 20% of 50d low
    above_3ma    INTEGER,           -- REVERSAL: close > 3d MA
    green_day    INTEGER,           -- REVERSAL: close > prev close
    atr_ratio    REAL,              -- shared: ATR14 / ATR30_median
    vol_ratio    REAL,              -- REVERSAL: volume / 20d median vol
    vol_dryup    REAL,              -- CONTINUATION: volume dry-up ratio
    rs           REAL,              -- shared: relative strength vs IHSG
    close_price  REAL,              -- shared: latest close
    fired        INTEGER DEFAULT 0,
    fired_at     TEXT,
    UNIQUE(ticker, detected_at, pattern_type)
);
```

### 3.3 Validation Criteria

After implementation, run a historical scan and verify:

1. **ASPR triggers REVERSAL_BREAKOUT** on April 24 or 27 at the latest
2. **No false positives** on low-volume, non-reversal days
3. **CONTINUATION unchanged** — existing alerts still fire identically
4. **No duplicate alerts** — same ticker can appear in both patterns on the same day

---

## 4. Edge Cases & Error Handling

| Scenario | Handling |
|---|---|
| Ticker has < 50 bars of OHLCV | Skip REVERSAL_BREAKOUT scoring (returns score 0) |
| Flow data unavailable | FLOW_CONFIRMATION = 0 pts (penalize, don't crash) |
| IHSG data missing | RS-related indicators get 0 pts |
| All-volume days (very quiet stocks) | 20d median volume might be 0 — guard with min volume floor |
| Gap-down reversal day | POSITIVE_CLOSE would fail — stock still scores if other conditions strong enough |
| Multiple patterns same ticker same day | Both stored with different `pattern_type`, separate UNIQUE constraint |
| Existing rows without `pattern_type` | Default to 'CONTINUATION' via ALTER TABLE DEFAULT |

### 4.1 Volume Guard

If 20d median volume < 100,000 shares (penny stock threshold), cap vol_ratio at 1.0 to prevent micro-cap noise:

```python
MEDIAN_VOL_FLOOR = 100_000
if median_vol < MEDIAN_VOL_FLOOR:
    vol_ratio = min(vol_ratio, 1.0)
```

---

## 5. Future Considerations (not in scope)

- **Pattern taxonomy in DB**: Store pattern classification alongside scores for longitudinal analysis
- **Dynamic threshold tuning**: Adjust alert threshold based on market regime (bull/bear/sideways)
- **Multi-timeframe confirmation**: Cross-reference daily with weekly for stronger signals
- **Notification routing**: REVERSAL_BREAKOUT alerts go to a separate Telegram channel (higher noise ratio expected)
