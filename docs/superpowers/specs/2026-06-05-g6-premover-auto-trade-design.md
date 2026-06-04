# G6: Premover → Paper Trade Auto-Execution Toggle — Design Spec
_2026-06-05_

## Problem

BRPT REVERSAL_BREAKOUT fired 2026-05-26 (score=55, vol=1.49B), Telegram alert sent, but `paper_trades` was empty. The system detected the opportunity but had no mechanism to act on it. The gap between detection (premover alert) and execution (paper trade) is manual.

## Design

### Config: `auto_trade_from_premover` in `paper_config`

Three modes stored in `paper_config.auto_trade_from_premover`:
- `"off"` (default): current behavior — scan, alert, stop
- `"shadow"`: scan, alert, evaluate gates, log decision + reason, send Telegram shadow summary — no trade opened
- `"enforce"`: scan, alert, evaluate gates, log decision, open paper trade if gates pass

### New helpers in `paper_trade.py`

**`get_premover_mode() -> str`:**
Reads `auto_trade_from_premover` from `paper_config`. Returns `"off"` if not set.

**`set_premover_mode(mode: str)`:**
Writes to `paper_config`. Validates `mode in ('off', 'shadow', 'enforce')`.

**`evaluate_premover_trade(ticker: str, score: int, pattern_type: str) -> dict`:**
Dry-runs `open_trade()` gates without side effects. Returns:
```python
{'would_trade': bool, 'skip_reason': str | None, 'gates': dict}
```
Gates checked in priority order:
1. `entries_blocked` — DD circuit breaker (`is_entries_blocked()`)
2. `max_open` — positions at limit (`len(get_open_trades()) >= max_open`)
3. `duplicate` — ticker already has open position
4. `regime` — if `filter_regime=1`, queries `backtest_cache` for regime; blocks if `BEAR`

No network calls. Uses only existing DB state.

**`_log_premover_auto(ticker, detected_at, pattern_type, score, mode, eval_result)`:**
Inserts one row into `premover_auto_log` table.

### New DB table: `premover_auto_log`

Added to `init_paper_table()` in `paper_trade.py`:
```sql
CREATE TABLE IF NOT EXISTS premover_auto_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker       TEXT NOT NULL,
    detected_at  TEXT NOT NULL,
    pattern_type TEXT,
    score        INTEGER,
    mode         TEXT,
    would_trade  INTEGER,
    skip_reason  TEXT,
    logged_at    TEXT
)
```

### Updated `run_premover_eod()` — `scheduler/jobs.py`

After `run_scan()` returns `new_setups`:
```python
from paper_trade import get_premover_mode, evaluate_premover_trade, open_trade, _log_premover_auto
mode = get_premover_mode()
if mode in ('shadow', 'enforce') and new_setups:
    today = datetime.now(WIB).strftime('%Y-%m-%d')
    shadow_rows = []
    for s in new_setups:
        ev = evaluate_premover_trade(s['ticker'], s['score'], s['pattern'])
        _log_premover_auto(s['ticker'], today, s['pattern'], s['score'], mode, ev)
        if mode == 'enforce' and ev['would_trade']:
            open_trade(s['ticker'], float(s.get('close', 0)),
                       strategy=None, notify=True)
        shadow_rows.append({'ticker': s['ticker'], 'score': s['score'],
                            'pattern': s['pattern'], **ev})
    _send_premover_auto_summary(shadow_rows, mode, send_telegram)
```

**`_send_premover_auto_summary(rows, mode, send_fn)`** (new helper in `scheduler/jobs.py`):
Sends Telegram message listing each setup with PASS/BLOCK + reason:
```
🤖 Premover SHADOW (3 setups)
✅ BRPT score=55 → PASS
❌ BBCA score=48 → regime_bear
❌ TLKM score=52 → max_open_5
```

### Flask endpoints — `routes/backtest.py`

```python
GET  /api/paper/premover_mode  → {'mode': 'off|shadow|enforce'}
POST /api/paper/premover_mode  body: {'mode': 'off|shadow|enforce'} → {'mode': str}
```

## What is NOT changed

- `run_scan()` in `premover_detector.py` — unchanged
- `open_trade()` in `paper_trade.py` — called as-is in enforce mode
- All existing paper trade filters and circuit breakers — unchanged

## Tests (`tests/test_premover_auto_trade.py`)

1. `test_get_set_premover_mode` — default is `"off"`, set/get round-trip
2. `test_evaluate_premover_trade_passes_all_gates` — clean DB → would_trade=True
3. `test_evaluate_blocks_on_dd_circuit_breaker` — entries_blocked=1 → would_trade=False
4. `test_evaluate_blocks_on_max_open` — 5 open trades, max=5 → would_trade=False
5. `test_evaluate_blocks_on_bear_regime` — backtest_cache has regime=BEAR → would_trade=False
6. `test_api_premover_mode_get_post` — GET returns default, POST sets mode

## Files changed

- `paper_trade.py` — `get_premover_mode`, `set_premover_mode`, `evaluate_premover_trade`, `_log_premover_auto`, `premover_auto_log` table
- `scheduler/jobs.py` — update `run_premover_eod()`, add `_send_premover_auto_summary()`
- `routes/backtest.py` — add 2 endpoints
- `tests/test_premover_auto_trade.py` — new, 6 tests
