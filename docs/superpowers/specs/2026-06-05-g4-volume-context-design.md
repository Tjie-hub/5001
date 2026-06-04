# G4: VR Spike Context Classifier — Design Spec
_2026-06-05_

## Problem

Volume ratio spikes carry different meaning depending on market context. BRPT after its May 2026 crash showed VR 2.73x (VOLUME_EXPLOSION), earning 30pts in `score_ticker_reversal()`, but:
- `near_low=0` (stock is 30% above its new post-crash low, not classic reversal setup)
- `above_3ma=0` (still in free-fall after crash)

Score=55 fired an alert, but it's a crash absorption pattern, not a classic reversal. A trader reading this alert needs to know the difference.

## Design

### `classify_volume_context(df: pd.DataFrame) -> str` — `engine/indicators.py`

Pure function, evaluates the **last bar** of the DataFrame. Returns one of 4 string labels (priority order):

| Label | Condition |
|-------|-----------|
| `crash_absorption` | VR ≥ 2.0x AND close ≥ 20% below 20-day high |
| `exhaustion_distribution` | VR ≥ 2.0x AND close < open (bearish) AND close within 5% of 20-day high |
| `breakout_accumulation` | VR ≥ 1.5x AND close within 5% of 20-day high AND close > MA20 |
| `normal` | everything else |

**Implementation detail:**
```python
def classify_volume_context(df: pd.DataFrame) -> str:
    if len(df) < 20:
        return 'normal'
    close  = df['close'].astype(float)
    volume = df['volume'].astype(float)
    
    vr = calc_vol_ratio(df, 20).iloc[-1]
    high_20d = close.rolling(20).max().iloc[-1]
    ma20     = close.rolling(20).mean().iloc[-1]
    last     = df.iloc[-1]
    cl       = float(last['close'])
    op       = float(last['open'])
    
    if pd.isna(vr) or pd.isna(high_20d):
        return 'normal'
    
    pct_from_high = (cl - high_20d) / high_20d  # negative = below high
    
    if vr >= 2.0 and pct_from_high <= -0.20:
        return 'crash_absorption'
    if vr >= 2.0 and cl < op and pct_from_high >= -0.05:
        return 'exhaustion_distribution'
    if vr >= 1.5 and pct_from_high >= -0.05 and not pd.isna(ma20) and cl > ma20:
        return 'breakout_accumulation'
    return 'normal'
```

### Surface in `score_ticker_reversal()` — `engine/premover_detector.py`

Add `vol_context` field to return dict:
```python
from engine.indicators import classify_volume_context
...
return {
    'score':       ...,
    'reasons':     ...,
    'vol_ratio':   ...,
    'near_low':    ...,
    'above_3ma':   ...,
    'green_day':   ...,
    'atr_ratio':   ...,
    'close':       ...,
    'vol_context': classify_volume_context(df),   # NEW
}
```

Same addition in `score_ticker()` (CONTINUATION pattern).

### `watchlist_premover` table

Add `vol_context TEXT` column. Migration at startup (in `_ensure_table()` or inline):
```sql
ALTER TABLE watchlist_premover ADD COLUMN vol_context TEXT;
```
Use `IF NOT EXISTS` guard via try/except (SQLite doesn't support `ADD COLUMN IF NOT EXISTS`).

Update `_upsert_setup()` to include `vol_context` in INSERT and SELECT.

### Telegram alert

In the alert formatting block, when `vol_context != 'normal'`:
```
⚡ Vol: 2.7x [CRASH_ABSORB]
```
Label map: `crash_absorption → CRASH_ABSORB`, `exhaustion_distribution → EXHAUST_DIST`, `breakout_accumulation → BRK_ACCUM`.

## What is NOT changed

- Scoring weights — no threshold changes
- `calc_vol_ratio()` — unchanged
- All strategy backtest functions — unchanged
- `wf_scores` — unaffected

## Tests (`tests/test_volume_context.py`)

1. `test_normal_context` — flat price + normal VR → `'normal'`
2. `test_crash_absorption` — big drop (>20% from high) + VR>2x → `'crash_absorption'`
3. `test_exhaustion_distribution` — near high + bearish close + VR>2x → `'exhaustion_distribution'`
4. `test_breakout_accumulation` — near high + above MA20 + VR>1.5x → `'breakout_accumulation'`
5. `test_score_ticker_reversal_has_vol_context` — `score_ticker_reversal()` return includes `vol_context` key

## Files changed

- `engine/indicators.py` — add `classify_volume_context()`
- `engine/premover_detector.py` — call in `score_ticker_reversal()`, `score_ticker()`, `_upsert_setup()`, alert formatting
- `tests/test_volume_context.py` — new, 5 tests
