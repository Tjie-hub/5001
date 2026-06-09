# G5 — Fundamental Data Auto-Refresh on Price Shock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block entry signals when keystats are stale (>30 days) AND a ≥20% price shock occurred; attempt inline re-fetch first, fall through to block only if re-fetch fails.

**Architecture:** Three helper functions added to `scheduler.py` immediately after `check_fundamental()` (line 181). `scan_momentum_signals()` moves `df = ohlcv_map.get(ticker)` above the fundamental block and inserts a `check_keystats_freshness()` call before the existing `check_fundamental()` call. Tests live in a new `tests/test_fundamental_refresh.py`.

**Tech Stack:** Python 3.12, SQLite, pandas, pytest, unittest.mock. No new dependencies.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `scheduler.py` | Modify | Add 3 helper functions after line 181; update `scan_momentum_signals` loop |
| `tests/test_fundamental_refresh.py` | Create | Unit tests for all 3 helpers |

---

## Task 1: Tests for `_detect_price_shock` and `_load_stockbit_token`

**Files:**
- Create: `tests/test_fundamental_refresh.py`
- Modify: `scheduler.py` (implementation only after tests are written)

- [x] **Step 1: Create the test file with failing tests**

```python
# tests/test_fundamental_refresh.py
import os
import sqlite3
from datetime import date, timedelta
from unittest.mock import patch
import pandas as pd
import pytest

from scheduler import _detect_price_shock, _load_stockbit_token


def _flat_df(n=20, close=1000.0):
    return pd.DataFrame({"close": [close] * n, "date": ["2026-01-01"] * n})


def _shock_df(window=5, base=1000.0, drop_pct=0.25):
    closes = [base] + [base * (1 - drop_pct)] * window
    return pd.DataFrame({"close": closes, "date": ["2026-01-01"] * (window + 1)})


class TestDetectPriceShock:
    def test_flat_price_no_shock(self):
        assert _detect_price_shock(_flat_df()) is False

    def test_25pct_drop_is_shock(self):
        assert _detect_price_shock(_shock_df()) is True

    def test_none_df_returns_false(self):
        assert _detect_price_shock(None) is False

    def test_too_short_returns_false(self):
        df = pd.DataFrame({"close": [1000, 700], "date": ["2026-01-01", "2026-01-02"]})
        assert _detect_price_shock(df, window=5) is False

    def test_exactly_20pct_drop_is_shock(self):
        closes = [1000.0] + [800.0] * 5
        df = pd.DataFrame({"close": closes, "date": ["2026-01-01"] * 6})
        assert _detect_price_shock(df, pct=0.20) is True

    def test_19pct_drop_not_shock(self):
        closes = [1000.0] + [810.0] * 5
        df = pd.DataFrame({"close": closes, "date": ["2026-01-01"] * 6})
        assert _detect_price_shock(df, pct=0.20) is False


class TestLoadStockbitToken:
    def test_valid_jwt_returned(self, tmp_path):
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig")
        assert _load_stockbit_token(str(tf)).startswith("eyJ")

    def test_missing_file_returns_none(self, tmp_path):
        assert _load_stockbit_token(str(tmp_path / "nofile")) is None

    def test_non_jwt_content_returns_none(self, tmp_path):
        tf = tmp_path / ".stockbit_token"
        tf.write_text("not-a-jwt-token")
        assert _load_stockbit_token(str(tf)) is None

    def test_empty_file_returns_none(self, tmp_path):
        tf = tmp_path / ".stockbit_token"
        tf.write_text("")
        assert _load_stockbit_token(str(tf)) is None
```

- [x] **Step 2: Run tests to confirm they fail (functions don't exist yet)**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/test_fundamental_refresh.py -v 2>&1 | head -30
```

Expected: `ImportError: cannot import name '_detect_price_shock' from 'scheduler'`

- [x] **Step 3: Implement `_detect_price_shock` and `_load_stockbit_token` in `scheduler.py`**

Insert immediately after `check_fundamental()` ends (after line 181, before the `# Module-level regime classifier cache` comment):

```python
def _detect_price_shock(df, pct: float = 0.20, window: int = 5) -> bool:
    """True if close dropped more than pct over the last window bars."""
    if df is None or len(df) < window + 1:
        return False
    closes = df['close'].iloc[-(window + 1):]
    base = closes.iloc[0]
    if base <= 0:
        return False
    return (closes.iloc[-1] - base) / base < -pct


def _load_stockbit_token(_token_file: str = None) -> str:
    """Read Stockbit JWT from .stockbit_token. Returns None if missing or invalid."""
    if _token_file is None:
        _token_file = os.path.join(os.path.dirname(__file__), ".stockbit_token")
    try:
        with open(_token_file, 'r') as f:
            t = f.read().strip()
        return t if t.startswith('eyJ') else None
    except Exception:
        return None
```

Use the Edit tool with this `old_string` / `new_string`:

**old_string:**
```
# Module-level regime classifier cache: {ticker: (date_str, RegimeClassifier)}
_regime_clf_cache: dict = {}
```

**new_string:**
```
def _detect_price_shock(df, pct: float = 0.20, window: int = 5) -> bool:
    """True if close dropped more than pct over the last window bars."""
    if df is None or len(df) < window + 1:
        return False
    closes = df['close'].iloc[-(window + 1):]
    base = closes.iloc[0]
    if base <= 0:
        return False
    return (closes.iloc[-1] - base) / base < -pct


def _load_stockbit_token(_token_file: str = None) -> str:
    """Read Stockbit JWT from .stockbit_token. Returns None if missing or invalid."""
    if _token_file is None:
        _token_file = os.path.join(os.path.dirname(__file__), ".stockbit_token")
    try:
        with open(_token_file, 'r') as f:
            t = f.read().strip()
        return t if t.startswith('eyJ') else None
    except Exception:
        return None


# Module-level regime classifier cache: {ticker: (date_str, RegimeClassifier)}
_regime_clf_cache: dict = {}
```

- [x] **Step 4: Run Task 1 tests to confirm they pass**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/test_fundamental_refresh.py::TestDetectPriceShock tests/test_fundamental_refresh.py::TestLoadStockbitToken -v
```

Expected: 10 tests PASSED

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add tests/test_fundamental_refresh.py scheduler.py
git commit -m "$(cat <<'EOF'
feat(g5): add _detect_price_shock and _load_stockbit_token helpers

Foundation for G5 fundamental auto-refresh: price shock detector
(>20% drop in 5 bars) and Stockbit token file reader.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Implement and test `check_keystats_freshness`

**Files:**
- Modify: `tests/test_fundamental_refresh.py` (add new test class)
- Modify: `scheduler.py` (add `check_keystats_freshness` after `_load_stockbit_token`)

- [x] **Step 1: Add failing tests for `check_keystats_freshness`**

Append to `tests/test_fundamental_refresh.py`:

```python
from scheduler import check_keystats_freshness


def _make_keystats_db(tmp_path, fetch_date_str=None):
    """Minimal stockbit_keystats table; optionally insert one BRPT row."""
    db = str(tmp_path / "test.db")
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE stockbit_keystats (
            ticker TEXT NOT NULL,
            fetch_date TEXT NOT NULL,
            pe_ttm REAL, pbv REAL, roe REAL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (ticker, fetch_date)
        )
    """)
    if fetch_date_str:
        conn.execute(
            "INSERT INTO stockbit_keystats (ticker, fetch_date, pe_ttm, pbv, roe, updated_at) "
            "VALUES (?,?,?,?,?,?)",
            ("BRPT", fetch_date_str, 10.0, 2.0, 15.0, "2026-01-01T00:00:00")
        )
    conn.commit()
    conn.close()
    return db


class TestCheckKeystatsFreshness:
    def test_no_row_passes(self, tmp_path):
        db = _make_keystats_db(tmp_path)
        ok, reason = check_keystats_freshness("BRPT", None, _db_path=db)
        assert ok is True
        assert reason == "no_data"

    def test_fresh_data_passes(self, tmp_path):
        db = _make_keystats_db(tmp_path, date.today().isoformat())
        ok, reason = check_keystats_freshness("BRPT", _flat_df(), _db_path=db)
        assert ok is True
        assert reason == "OK"

    def test_stale_no_shock_passes(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        ok, reason = check_keystats_freshness("BRPT", _flat_df(), _db_path=db)
        assert ok is True
        assert reason == "stale:45d"

    def test_stale_shock_no_token_blocks(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        missing = str(tmp_path / "notoken")
        ok, reason = check_keystats_freshness(
            "BRPT", _shock_df(), _db_path=db, _token_file=missing
        )
        assert ok is False
        assert "stale_shock" in reason
        assert "no_token" in reason

    def test_stale_shock_refresh_success(self, tmp_path):
        old = (date.today() - timedelta(days=45)).isoformat()
        db = _make_keystats_db(tmp_path, old)
        tf = tmp_path / ".stockbit_token"
        tf.write_text("eyJmYWtlLnRva2Vu.payload.sig")
        mock_stats = {"ticker": "BRPT", "pe_ttm": 8.0, "roe": 12.0, "pbv": 2.0}
        with patch("stockbit_fetcher.fetch_keystats", return_value=mock_stats), \
             patch("stockbit_fetcher.save_keystats", return_value=None):
            ok, reason = check_keystats_freshness(
                "BRPT", _shock_df(), _db_path=db, _token_file=str(tf)
            )
        assert ok is True
        assert "refreshed" in reason
```

- [x] **Step 2: Run new tests to confirm they fail**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/test_fundamental_refresh.py::TestCheckKeystatsFreshness -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'check_keystats_freshness' from 'scheduler'`

- [x] **Step 3: Implement `check_keystats_freshness` in `scheduler.py`**

Use the Edit tool. Insert after `_load_stockbit_token` (which ends with `return None`) and before `# Module-level regime classifier cache`.

**old_string:**
```
    except Exception:
        return None


# Module-level regime classifier cache: {ticker: (date_str, RegimeClassifier)}
```

**new_string:**
```
    except Exception:
        return None


def check_keystats_freshness(ticker: str, df, stale_threshold: int = 30,
                             _db_path: str = None, _token_file: str = None):
    """
    Returns (ok: bool, reason: str).
    Stale + price shock: attempts re-fetch via Stockbit API.
      - Re-fetch success: (True,  'refreshed:{N}d')
      - No token:         (False, 'stale_shock:{N}d,no_token')
      - API fail:         (False, 'stale_shock:{N}d,fetch_error')
    Stale + no shock:     (True,  'stale:{N}d')   — allow through
    Fresh:                (True,  'OK')
    No data:              (True,  'no_data')
    """
    db = _db_path or DB_PATH
    try:
        conn = sqlite3.connect(db)
        row = conn.execute(
            'SELECT fetch_date FROM stockbit_keystats WHERE ticker=? ORDER BY fetch_date DESC LIMIT 1',
            (ticker,)
        ).fetchone()
        conn.close()
    except Exception:
        return True, 'db_error'

    if not row:
        return True, 'no_data'

    from datetime import date as _date
    try:
        fetch_date = _date.fromisoformat(row[0])
    except Exception:
        return True, 'bad_date'

    stale_days = (_date.today() - fetch_date).days

    if stale_days <= stale_threshold:
        return True, 'OK'

    if not _detect_price_shock(df):
        logging.debug(f"[keystats] {ticker} stale:{stale_days}d, no shock — allow")
        return True, f'stale:{stale_days}d'

    # Stale + price shock — attempt re-fetch
    token = _load_stockbit_token(_token_file)
    if not token:
        logging.info(f"[keystats] {ticker} stale_shock:{stale_days}d — no token, blocking")
        return False, f'stale_shock:{stale_days}d,no_token'

    try:
        from stockbit_fetcher import fetch_keystats, save_keystats
        stats = fetch_keystats(token, ticker)
        if not stats:
            logging.info(f"[keystats] {ticker} stale_shock:{stale_days}d — fetch empty, blocking")
            return False, f'stale_shock:{stale_days}d,fetch_empty'
        conn2 = sqlite3.connect(db)
        save_keystats(conn2, stats)
        conn2.commit()
        conn2.close()
        logging.info(
            f"[keystats] {ticker} refreshed after {stale_days}d stale — "
            f"PE={stats.get('pe_ttm')} ROE={stats.get('roe')}"
        )
        return True, f'refreshed:{stale_days}d'
    except Exception as _e:
        logging.warning(f"[keystats] {ticker} re-fetch error: {_e}")
        return False, f'stale_shock:{stale_days}d,fetch_error'


# Module-level regime classifier cache: {ticker: (date_str, RegimeClassifier)}
```

- [x] **Step 4: Run all Task 2 tests**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/test_fundamental_refresh.py -v
```

Expected: All 15 tests PASSED (10 from Task 1 + 5 new)

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add tests/test_fundamental_refresh.py scheduler.py
git commit -m "$(cat <<'EOF'
feat(g5): add check_keystats_freshness with stale+shock re-fetch logic

Detects stale keystats (>30d) + price shock (>20% in 5 bars); attempts
inline Stockbit re-fetch. Blocks only on stale+shock+failed refresh.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Wire `check_keystats_freshness` into `scan_momentum_signals`

**Files:**
- Modify: `scheduler.py` lines 301–351 (the ticker loop in `scan_momentum_signals`)

- [x] **Step 1: Move `df` assignment above the fundamental block**

In `scan_momentum_signals`, find and replace this block using the Edit tool:

**old_string** (exact text from lines 301–311):
```
    for ticker in tickers:
        wf = wf_map.get(ticker)
        if wf and wf["consistency_pct"] < BLACKLIST:
            continue
        # Fundamental filter
        if _f_fundamental:
            fund_ok, fund_reason = check_fundamental(ticker)
            if not fund_ok:
                continue
        else:
            flow_reason = "fundamental filter OFF"
```

**new_string:**
```
    for ticker in tickers:
        wf = wf_map.get(ticker)
        if wf and wf["consistency_pct"] < BLACKLIST:
            continue
        df = ohlcv_map.get(ticker)
        # Fundamental filter
        if _f_fundamental:
            freshness_ok, fresh_reason = check_keystats_freshness(ticker, df)
            if not freshness_ok:
                logging.info(f"[scan_momentum] {ticker} blocked: {fresh_reason}")
                continue
            fund_ok, fund_reason = check_fundamental(ticker)
            if not fund_ok:
                continue
        else:
            flow_reason = "fundamental filter OFF"
```

- [x] **Step 2: Remove the now-duplicate `df` assignment from the try block**

Find and replace in the same function:

**old_string** (include the next line for uniqueness):
```
        try:
            df = ohlcv_map.get(ticker)
            if df is None or len(df) < 25:
                continue
            vr     = calc_vol_ratio(df)
```

**new_string:**
```
        try:
            if df is None or len(df) < 25:
                continue
            vr     = calc_vol_ratio(df)
```

- [x] **Step 3: Run the full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: All 15 new tests pass + all pre-existing tests pass. Zero failures.

- [x] **Step 4: Smoke-check scheduler imports and function is reachable**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
venv/bin/python -c "
from scheduler import check_keystats_freshness, _detect_price_shock, _load_stockbit_token
print('imports OK')
import pandas as pd
df = pd.DataFrame({'close': [1000.0]*20, 'date': ['2026-01-01']*20})
print('shock test:', _detect_price_shock(df))
print('token test:', _load_stockbit_token('/tmp/notoken'))
"
```

Expected output:
```
imports OK
shock test: False
token test: None
```

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add scheduler.py
git commit -m "$(cat <<'EOF'
feat(g5): wire check_keystats_freshness into scan_momentum_signals

Signals for tickers with stale fundamentals (>30d) + >=20% price shock
are now blocked unless a live re-fetch from Stockbit succeeds.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Mark TODO complete and final verification

**Files:**
- Modify: `TODO.md`

- [x] **Step 1: Mark G5 complete in TODO.md**

In `TODO.md`, find:

```
- [x] **G5. Fundamental data auto-refresh on price shock**
```

Replace `- [ ]` with `- [x]` and append a completion note:

```
- [x] **G5. Fundamental data auto-refresh on price shock** — SHIPPED 2026-05-29. `check_keystats_freshness()` in `scheduler.py`: blocks stale+shock signals; allows stale-but-quiet through; attempts inline re-fetch via `.stockbit_token` before blocking.
```

- [x] **Step 2: Verify no stray `os.getenv` or hardcoded paths were introduced**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
grep -n "check_keystats_freshness\|_detect_price_shock\|_load_stockbit_token" scheduler.py
```

Expected: 4 definition lines + 2 call sites (one in `check_keystats_freshness` calling the helpers, one in `scan_momentum_signals`).

- [x] **Step 3: Commit TODO update**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
git add TODO.md
git commit -m "$(cat <<'EOF'
docs(todo): mark G5 fundamental auto-refresh shipped

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```
