# G5 — Fundamental Data Auto-Refresh on Price Shock

_Date: 2026-05-29_
_Task: TODO Sprint 17 G5_

---

## Problem

`check_fundamental()` in `scheduler.py` uses the most recent `stockbit_keystats` row for a ticker regardless of age. BRPT evidence: fundamentals were 6 weeks stale (fetched Apr 14) when REVERSAL_BREAKOUT fired May 26. NPM -4.47%, DER 3.47 were live red flags invisible to the filter.

Staleness is dangerous specifically when combined with a price shock — a crash may reflect deteriorating fundamentals not yet visible in 30+ day old data.

---

## Decision: Block only on stale + price shock (Option C)

- **Stale + no shock** → allow through (log `stale:Nd` for visibility)
- **Stale + price shock** → attempt re-fetch; if re-fetch fails → block
- **Fresh** → unchanged behaviour

Rationale: stale data on a quiet stock is low risk. Stale data after a -20% crash is high risk.

---

## New Functions (all in `scheduler.py`, near existing `check_fundamental()`)

### `_detect_price_shock(df, pct=0.20, window=5) -> bool`

Compares `close.iloc[-1]` vs `close.iloc[-window-1]`. Returns `True` if the drop exceeds `pct`. Returns `False` if `df` is `None` or has fewer than `window + 1` rows.

```python
def _detect_price_shock(df, pct: float = 0.20, window: int = 5) -> bool:
    if df is None or len(df) < window + 1:
        return False
    closes = df['close'].iloc[-(window + 1):]
    base = closes.iloc[0]
    if base <= 0:
        return False
    return (closes.iloc[-1] - base) / base < -pct
```

### `_load_stockbit_token() -> str | None`

Reads `.stockbit_token` from project root. Returns `None` if the file is missing, unreadable, or the content does not start with `'eyJ'` (not a JWT).

```python
def _load_stockbit_token() -> str | None:
    token_file = os.path.join(os.path.dirname(__file__), ".stockbit_token")
    try:
        with open(token_file, 'r') as f:
            t = f.read().strip()
        return t if t.startswith('eyJ') else None
    except Exception:
        return None
```

### `check_keystats_freshness(ticker, df, stale_threshold=30) -> tuple[bool, str]`

| Condition | Returns |
|-----------|---------|
| No keystats row | `(True, 'no_data')` |
| `fetch_date` ≤ 30 days ago | `(True, 'OK')` |
| Stale + no price shock | `(True, 'stale:{N}d')` |
| Stale + shock + re-fetch success | `(True, 'refreshed:{N}d')` |
| Stale + shock + no token | `(False, 'stale_shock:{N}d,no_token')` |
| Stale + shock + API returned empty | `(False, 'stale_shock:{N}d,fetch_empty')` |
| Stale + shock + exception | `(False, 'stale_shock:{N}d,fetch_error')` |

Re-fetch uses `fetch_keystats(token, ticker)` and `save_keystats(conn, stats)` imported from `stockbit_fetcher`. No new API needed. Uses `sqlite3.connect(DB_PATH)` directly — does not call `init_db()` (table already exists).

---

## Signal Pipeline Change

In `scan_momentum_signals()`, `df = ohlcv_map.get(ticker)` is currently assigned inside a `try:` block **after** the fundamental check. Move it above the fundamental block, then update the fundamental section:

```python
for ticker in tickers:
    wf = wf_map.get(ticker)
    if wf and wf["consistency_pct"] < BLACKLIST:
        continue

    # Fetch OHLCV early — needed by freshness check below
    df = ohlcv_map.get(ticker)

    # Fundamental filter
    if _f_fundamental:
        freshness_ok, fresh_reason = check_keystats_freshness(ticker, df)
        if not freshness_ok:
            logging.info(f"[scan] {ticker} blocked: {fresh_reason}")
            continue
        fund_ok, fund_reason = check_fundamental(ticker)
        if not fund_ok:
            continue
    else:
        flow_reason = "fundamental filter OFF"
    # ... rest of loop unchanged, remove the duplicate `df = ohlcv_map.get(ticker)` line
    #     from the try: block below
```

---

## Out of Scope

- Refreshing keystats for tickers that already failed `check_fundamental()` — no value (they're already blocked)
- Changing the PE/ROE/PBV thresholds in `check_fundamental()` — unchanged
- Scheduling periodic batch re-fetches — separate concern, not part of G5
- `scheduled_multi_strategy_scan()` — only `scan_momentum_signals()` is updated in this task; multi-strategy scan can follow the same pattern in a future task

---

## Imports

Add to the top of `scheduler.py` (lazy import inside function body to avoid circular import risk):

```python
# inside check_keystats_freshness():
from stockbit_fetcher import fetch_keystats, save_keystats
```

---

## Tests (`tests/test_fundamental_refresh.py`)

Five unit tests using `pytest` + `unittest.mock`. All tests use an in-memory SQLite DB and mock `fetch_keystats` where needed.

| Test | Setup | Expected |
|------|-------|----------|
| `test_fresh_data_passes` | fetch_date = today | `(True, 'OK')` |
| `test_stale_no_shock_passes` | fetch_date = 45d ago, flat closes | `(True, 'stale:45d')` |
| `test_stale_shock_no_token_blocks` | 45d ago, -25% closes, no token file | `(False, 'stale_shock:45d,no_token')` |
| `test_stale_shock_refresh_success` | 45d ago, -25% closes, token file present, mock fetch returns stats | `(True, 'refreshed:45d')` |
| `test_no_keystats_row_passes` | empty stockbit_keystats table | `(True, 'no_data')` |

---

## What Changes at Runtime

- Tickers with keystats >30 days stale and a recent -20% shock will be re-fetched inline during `scan_momentum_signals()`. A successful re-fetch logs `refreshed:Nd` to INFO. A failed re-fetch blocks the ticker and logs `stale_shock:Nd,...` to INFO.
- Tickers with stale data but no shock are allowed through and log `stale:Nd` at DEBUG level (silent in production logs).
- No change to tickers with fresh data or no keystats row.
