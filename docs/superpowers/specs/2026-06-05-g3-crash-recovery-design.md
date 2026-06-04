# G3: Crash Recovery Strategy — Design Spec
_2026-06-05_

## Problem

No existing strategy handles post-suspension gap-down or crash recovery entries. BRPT crashed −35% in May 2026 (11-day suspension, resume open −22.4% gap), the REVERSAL_BREAKOUT premover pattern fired (score=55), but:
- All 10 `STRATEGY_FUNCS` strategies use ATR-based or %-based TP/SL — none are calibrated for post-crash bounce dynamics
- ATR is contaminated by the gap bar (inflated 3–5×), making ATR-based SL too wide
- REVERSAL_BREAKOUT is a detection pattern, not a tradeable strategy with TP/SL management

BRPT post-resume data confirms the opportunity:
- Resume bar 2026-05-25: open 1615, low 1480, close 1495 (gap-down from 2080 = −22.4%)
- Bar +1 (2026-05-26): open 1500, close 1565, vol 1.49B (avg ~300M → VR ≈4.9×) → bullish close
- By 2026-06-02: high 2210 — eventual 45% recovery above the resume open

## Design

### `strategy_crash_recovery()` — `engine/strategies.py`

**Signature:** `strategy_crash_recovery(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> dict`

**Crash resume detection (OHLCV-based, no DB):**
```
date_diff = diff of consecutive dates in calendar days
open_gap_pct = (open[i] - close[i-1]) / close[i-1]
is_crash_resume = (date_diff >= 5) AND (open_gap_pct <= -0.20)
```
- `date_diff >= 5`: identifies suspension gaps (≥5 calendar days covers weekends+2 missing trading days minimum; normal weekend = 2-3 days)
- `open_gap_pct <= -0.20`: ≥20% gap-down on resume

**Entry window (state machine):**
- When crash resume detected at bar `i`:
  - Record `resume_low = df['low'][i]`, `resume_open = df['open'][i]`, `gap_amount = close[i-1] - resume_open`
  - Open entry_window for next 3 bars (`i+1` to `i+3`)
- In entry_window: enter if VR > 2.0x AND close > open AND NOT already in trade
  - Enter at `open` of the NEXT bar (i.e., signal on bar j, entry at bar j+1 open)
  - Skip if `resume_low >= entry_price` (pathological — use 2% fallback SL)
  - Skip if `TP <= entry_price × 1.02` (insufficient upside)

**TP/SL:**
```
SL = resume_low  (the absolute low of the crash resume bar, NOT ATR-based)
TP = resume_open + 0.5 × gap_amount  (50% gap retracement from resume open)
sl_pct = (entry_price - SL) / entry_price
```
SL fallback: if `sl_pct < 0.005` (< 0.5%), use `sl_pct = 0.02` (2% floor).

**Lot sizing:** `lot_size(capital, entry_price, 0.02, sl_pct)` — same 2% risk convention as all other strategies.

**Exit:** SL hit (lo ≤ SL) → sell at SL; TP hit (hi ≥ TP) → sell at TP; last bar → EOD close.

**Constants:**
```python
CRASH_MIN_GAP_DAYS = 5      # calendar day threshold for suspension proxy
CRASH_GAP_DOWN_PCT = -0.20  # -20% gap-down threshold
CRASH_VR_MIN = 2.0          # volume ratio confirmation
CRASH_ENTRY_WINDOW = 3      # max bars after resume to enter
CRASH_TP_RETRACEMENT = 0.50 # 50% gap retracement
```

### `check_crash_recovery_signal()` — `engine/strategies.py`

For live signal checking (uses `suspension_events` DB, avoids date arithmetic):
```python
def check_crash_recovery_signal(ticker: str, df: pd.DataFrame) -> dict:
    # 1. Query suspension_events for this ticker with resume_date within last 5 trading bars
    # 2. If recent suspension found: check VR > 2.0x and close > open on last bar
    # 3. Compute SL (resume bar low from OHLCV) and TP (50% gap retracement)
    # 4. Return standard {has_signal, reason, details} dict
```

### Wiring

**`engine/walkforward_multi.py`:**
```python
from engine.strategies import strategy_crash_recovery

STRATEGY_FUNCS['Crash Recovery'] = strategy_crash_recovery
```

**`engine/strategies.py` — `check_current_entry_signal()`:**
```python
elif strategy == 'Crash Recovery':
    result = check_crash_recovery_signal(ticker, df)
```
(No weekly-trend gate for this strategy — crash recovery is a counter-trend play, weekly trend is irrelevant.)

## What is NOT changed

- `run_strategy()` helper — not used by crash recovery (custom loop required for fixed-price SL)
- `wf_scores` refresh logic — unchanged; crash recovery will have sparse data on most tickers
- All existing strategies — no modifications

## Expectations

For most tickers: 0 trades (no suspension events in history) → wf_scores metrics all 0.
For BRPT, DEWA, BULL (tickers with confirmed 2026 suspension events): 1–2 trades per window if data covers the event.

## Tests (`tests/test_strategy_crash_recovery.py`)

1. `test_no_signal_without_gap` — continuous data, no gap ≥5d → 0 trades
2. `test_entry_after_crash_resume` — synthetic gap-down + bullish bar → 1 trade
3. `test_sl_is_resume_bar_low` — verify SL equals resume bar low, not ATR
4. `test_tp_is_50pct_retracement` — verify TP = resume_open + 0.5 × gap_amount
5. `test_entry_window_expires` — no confirmation in 3 bars → 0 trades
6. `test_check_crash_recovery_signal_no_recent_suspension` — no suspension in DB → no signal
7. `test_check_crash_recovery_signal_with_recent_suspension` — suspension in DB + VR/close → signal

## Files changed

- `engine/strategies.py` — add `strategy_crash_recovery()`, `check_crash_recovery_signal()`, wire into `check_current_entry_signal()`
- `engine/walkforward_multi.py` — add `'Crash Recovery': strategy_crash_recovery` to `STRATEGY_FUNCS`
- `tests/test_strategy_crash_recovery.py` — new, 7 tests
