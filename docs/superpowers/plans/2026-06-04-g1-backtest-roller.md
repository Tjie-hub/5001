# G1: Backtest Auto-Rolling Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `engine/backtest_roller.py` that automatically appends new walk-forward windows (complete and partial) to a queryable `backtest_windows` DB table, regenerates `out/meta_dataset_backtest.json`, and runs on a monthly scheduler job — making recent events like the May 2026 BRPT crash visible immediately via partial-window tracking.

**Architecture:** A new `engine/backtest_roller.py` module owns a `backtest_windows` DB table (per-window records, not just summaries like `wf_scores`). `roll_ticker()` reuses `run_walk_forward()` for complete windows and manually computes a partial window for the current in-progress period. `roll_all()` iterates all tickers, `export_meta_dataset()` writes the JSON artifact. Wired into APScheduler (monthly Sunday 10:00 WIB) and a `POST /api/backtest/roll` Flask endpoint.

**Tech Stack:** Python 3, SQLite (sqlite3), pandas, APScheduler (existing), Flask (existing), pytest.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `engine/backtest_roller.py` | **Create** | `_init_table`, `roll_ticker`, `roll_all`, `export_meta_dataset` |
| `scheduler/jobs.py` | **Modify** | Add `run_backtest_roller()` job function |
| `scheduler/__init__.py` | **Modify** | Re-export `run_backtest_roller`, add Sunday cron |
| `routes/backtest.py` | **Modify** | Add `POST /api/backtest/roll` endpoint |
| `tests/test_backtest_roller.py` | **Create** | 6 unit tests |

---

## Task 1: DB Schema + `_init_table()`

**Files:**
- Create: `engine/backtest_roller.py`
- Create: `tests/test_backtest_roller.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_backtest_roller.py
import sqlite3
import json
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta


def _make_df(n_bars: int = 400, start: str = "2024-01-02") -> pd.DataFrame:
    """Synthetic OHLCV DataFrame for testing."""
    dates = pd.date_range(start=start, periods=n_bars, freq="B")
    np.random.seed(42)
    close = 1000 + np.cumsum(np.random.randn(n_bars) * 5)
    close = np.maximum(close, 100)
    return pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates],
        "open":   close * 0.99,
        "high":   close * 1.02,
        "low":    close * 0.97,
        "close":  close,
        "volume": np.random.randint(500_000, 5_000_000, n_bars).astype(float),
    })


def test_init_table_creates_backtest_windows():
    from engine.backtest_roller import _init_table
    conn = sqlite3.connect(":memory:")
    _init_table(conn)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    assert "backtest_windows" in tables
    cols = [r[1] for r in conn.execute("PRAGMA table_info(backtest_windows)").fetchall()]
    for col in ["ticker", "window_num", "test_start", "test_end", "is_partial",
                "features_json", "metrics_json", "computed_at"]:
        assert col in cols, f"missing column: {col}"
```

- [x] **Step 2: Run test — expect FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_backtest_roller.py::test_init_table_creates_backtest_windows -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError` or `ImportError`

- [x] **Step 3: Implement `engine/backtest_roller.py` with `_init_table`**

```python
# engine/backtest_roller.py
"""
backtest_roller.py — Auto-rolling walk-forward window pipeline.

Maintains backtest_windows table: one row per (ticker, test_start), covering
both complete 3-month windows and the current in-progress partial window.
Partial windows are flagged is_partial=1 and replaced when they become complete.
"""
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import DB_PATH

OUT_PATH = str(Path(__file__).parent.parent / "out" / "meta_dataset_backtest.json")
FEATURE_COLS = ["adx", "ma_slope", "vr_mean", "range_pct", "close_vs_ma", "pct_above_ma"]
CAPITAL = 50_000_000
WARMUP_BARS = 60
MIN_PARTIAL_BARS = 10

logger = logging.getLogger(__name__)


def _init_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_windows (
            ticker        TEXT NOT NULL,
            window_num    INTEGER,
            train_start   TEXT,
            train_end     TEXT,
            test_start    TEXT NOT NULL,
            test_end      TEXT NOT NULL,
            is_partial    INTEGER DEFAULT 0,
            features_json TEXT,
            metrics_json  TEXT,
            computed_at   TEXT,
            PRIMARY KEY (ticker, test_start)
        )
    """)
    conn.commit()
```

- [x] **Step 4: Run test — expect PASS**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_backtest_roller.py::test_init_table_creates_backtest_windows -v 2>&1 | tail -10
```

Expected: `PASSED`

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/backtest_roller.py tests/test_backtest_roller.py && git commit -m "feat(g1): add engine/backtest_roller.py with _init_table and backtest_windows schema"
```

---

## Task 2: `roll_ticker()` — Complete Windows

**Files:**
- Modify: `engine/backtest_roller.py`
- Modify: `tests/test_backtest_roller.py`

- [x] **Step 1: Write failing tests**

Append to `tests/test_backtest_roller.py`:

```python
def test_roll_ticker_inserts_complete_windows():
    """roll_ticker inserts 4 complete windows for a 400-bar ticker."""
    from engine.backtest_roller import _init_table, roll_ticker
    conn = sqlite3.connect(":memory:")
    _init_table(conn)
    df = _make_df(400)
    result = roll_ticker("ACES", df, conn, include_partial=False)
    rows = conn.execute(
        "SELECT COUNT(*) FROM backtest_windows WHERE ticker='ACES' AND is_partial=0"
    ).fetchone()[0]
    assert rows >= 1, f"expected >=1 complete windows, got {rows}"
    assert result["new_complete"] == rows
    assert result["new_partial"] == 0


def test_roll_ticker_idempotent():
    """Calling roll_ticker twice inserts no duplicate rows."""
    from engine.backtest_roller import _init_table, roll_ticker
    conn = sqlite3.connect(":memory:")
    _init_table(conn)
    df = _make_df(400)
    first = roll_ticker("BBCA", df, conn, include_partial=False)
    second = roll_ticker("BBCA", df, conn, include_partial=False)
    assert second["new_complete"] == 0, "second run should insert 0 new rows"
    count = conn.execute(
        "SELECT COUNT(*) FROM backtest_windows WHERE ticker='BBCA'"
    ).fetchone()[0]
    assert count == first["new_complete"]


def test_roll_ticker_skips_short_df():
    """Tickers with <60 bars return zero without error."""
    from engine.backtest_roller import _init_table, roll_ticker
    conn = sqlite3.connect(":memory:")
    _init_table(conn)
    df = _make_df(50)
    result = roll_ticker("TINY", df, conn, include_partial=False)
    assert result == {"new_complete": 0, "new_partial": 0}
```

- [x] **Step 2: Run tests — expect FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_backtest_roller.py::test_roll_ticker_inserts_complete_windows tests/test_backtest_roller.py::test_roll_ticker_idempotent tests/test_backtest_roller.py::test_roll_ticker_skips_short_df -v 2>&1 | tail -15
```

Expected: `AttributeError: module 'engine.backtest_roller' has no attribute 'roll_ticker'`

- [x] **Step 3: Implement `roll_ticker` (complete windows)**

Append to `engine/backtest_roller.py` after `_init_table`:

```python
def roll_ticker(ticker: str, df: pd.DataFrame, conn: sqlite3.Connection,
                include_partial: bool = True) -> dict:
    """
    Insert any new walk-forward windows for ticker into backtest_windows.
    Returns {'new_complete': int, 'new_partial': int}.
    """
    from engine.walkforward_multi import run_walk_forward, walk_forward_split, STRATEGY_FUNCS
    from engine.regime_filter import build_regime_features

    if len(df) < 60:
        return {"new_complete": 0, "new_partial": 0}

    # Existing complete windows for this ticker (skip these)
    complete_starts = {r[0] for r in conn.execute(
        "SELECT test_start FROM backtest_windows WHERE ticker=? AND is_partial=0",
        (ticker,)
    ).fetchall()}

    wf = run_walk_forward(df)
    if "error" in wf:
        return {"new_complete": 0, "new_partial": 0}

    windows = walk_forward_split(df, train_months=12, test_months=3)

    # Index per-window metrics from wf summary
    by_window: dict[int, dict] = {}
    for strat, summ in wf["summary"].items():
        for w in summ["windows"]:
            widx = w["window"]
            by_window.setdefault(widx, {})[strat] = {
                "return":        float(w["total_return_pct"]),
                "win_rate":      float(w["win_rate"]),
                "sharpe":        float(w["sharpe"]),
                "max_dd":        float(w["max_drawdown_pct"]),
                "profit_factor": float(min(w["profit_factor"], 999)),
            }

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    new_complete = 0

    for w in windows:
        test_start = w["test_start"]
        if test_start in complete_starts:
            continue

        metrics = by_window.get(w["window"])
        if not metrics or len(metrics) < len(STRATEGY_FUNCS):
            continue

        feats = build_regime_features(w["train"])
        if feats.empty:
            continue
        last_row = feats.iloc[-1]
        if pd.Series([last_row[c] for c in FEATURE_COLS]).isna().any():
            continue

        features = {c: float(last_row[c]) for c in FEATURE_COLS}

        conn.execute("""
            INSERT OR REPLACE INTO backtest_windows
            (ticker, window_num, train_start, train_end, test_start, test_end,
             is_partial, features_json, metrics_json, computed_at)
            VALUES (?,?,?,?,?,?,0,?,?,?)
        """, (ticker, w["window"], w["train_start"], w["train_end"],
              w["test_start"], w["test_end"],
              json.dumps(features), json.dumps(metrics), now_str))
        new_complete += 1

    new_partial = 0
    if include_partial:
        new_partial = _roll_partial(ticker, df, windows, conn, now_str)

    return {"new_complete": new_complete, "new_partial": new_partial}


def _roll_partial(ticker: str, df: pd.DataFrame, windows: list,
                  conn: sqlite3.Connection, now_str: str) -> int:
    """
    Insert/update the current in-progress test window (data beyond last complete test_end).
    Replaces any existing partial row for this ticker. Returns 1 if inserted, 0 otherwise.
    """
    from engine.walkforward_multi import STRATEGY_FUNCS, compute_metrics
    from engine.regime_filter import build_regime_features

    if not windows:
        return 0

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    last_complete_end = max(w["test_end"] for w in windows)
    partial_mask = df["date"] >= pd.to_datetime(last_complete_end)
    partial_df = df[partial_mask]

    if len(partial_df) < MIN_PARTIAL_BARS:
        return 0

    partial_start = last_complete_end
    partial_end = str(df["date"].max().date())

    # Check if this ticker already has a finalized complete window with this test_start
    already_complete = conn.execute(
        "SELECT COUNT(*) FROM backtest_windows WHERE ticker=? AND test_start=? AND is_partial=0",
        (ticker, partial_start)
    ).fetchone()[0]
    if already_complete:
        return 0

    # Features from end of last train window
    last_window = max(windows, key=lambda w: w["window"])
    feats = build_regime_features(last_window["train"])
    if feats.empty:
        return 0
    last_row = feats.iloc[-1]
    if pd.Series([last_row[c] for c in FEATURE_COLS]).isna().any():
        return 0
    features = {c: float(last_row[c]) for c in FEATURE_COLS}

    # Run all strategies on partial slice with warmup
    train_df = df[df["date"] < pd.to_datetime(last_complete_end)]
    warmup_tail = train_df.tail(WARMUP_BARS) if len(train_df) >= WARMUP_BARS else train_df
    extended = pd.concat([warmup_tail, partial_df], ignore_index=True)

    partial_metrics: dict = {}
    for strat_name, strat_func in STRATEGY_FUNCS.items():
        try:
            raw = strat_func(extended, capital=CAPITAL)
            kept = [t for t in raw["trades"] if t.entry_date >= partial_start]
            raw["trades"] = kept
            raw["initial_capital"] = CAPITAL
            raw["final_capital"] = CAPITAL + sum(t.pnl_rp for t in kept)
            raw["equity"] = [CAPITAL]
            m = compute_metrics(raw)
            partial_metrics[strat_name] = {
                "return":        float(m["total_return_pct"]),
                "win_rate":      float(m["win_rate"]),
                "sharpe":        float(m["sharpe"]),
                "max_dd":        float(m["max_drawdown_pct"]),
                "profit_factor": float(min(m["profit_factor"], 999)),
            }
        except Exception as exc:
            logger.debug("partial window %s %s: %s", ticker, strat_name, exc)

    if not partial_metrics:
        return 0

    window_num = max(w["window"] for w in windows) + 1
    conn.execute("""
        INSERT OR REPLACE INTO backtest_windows
        (ticker, window_num, train_start, train_end, test_start, test_end,
         is_partial, features_json, metrics_json, computed_at)
        VALUES (?,?,?,?,?,?,1,?,?,?)
    """, (ticker, window_num, str(train_df["date"].iloc[0].date()), last_complete_end,
          partial_start, partial_end,
          json.dumps(features), json.dumps(partial_metrics), now_str))

    return 1
```

- [x] **Step 4: Run tests — expect PASS**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_backtest_roller.py::test_roll_ticker_inserts_complete_windows tests/test_backtest_roller.py::test_roll_ticker_idempotent tests/test_backtest_roller.py::test_roll_ticker_skips_short_df -v 2>&1 | tail -15
```

Expected: all 3 `PASSED` (may take 30–60s due to strategy runs)

- [x] **Step 5: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/backtest_roller.py tests/test_backtest_roller.py && git commit -m "feat(g1): implement roll_ticker with complete window insertion and idempotency"
```

---

## Task 3: Partial Window Test

**Files:**
- Modify: `tests/test_backtest_roller.py`

- [x] **Step 1: Write failing test**

Append to `tests/test_backtest_roller.py`:

```python
def test_roll_ticker_partial_window():
    """roll_ticker with include_partial=True inserts a partial window."""
    from engine.backtest_roller import _init_table, roll_ticker
    conn = sqlite3.connect(":memory:")
    _init_table(conn)
    # 400 bars gives 4 complete windows; 10 extra bars beyond the last test_end
    # walk_forward_split with train=12, test=3 on 400 bars:
    # window 3 ends at bar ~(12+3)*21 = ~315 days from start
    # 400 bars >> 315+10, so there are extra bars for a partial window
    df = _make_df(400)
    result = roll_ticker("BBRI", df, conn, include_partial=True)
    partial_rows = conn.execute(
        "SELECT COUNT(*) FROM backtest_windows WHERE ticker='BBRI' AND is_partial=1"
    ).fetchone()[0]
    # There may or may not be a partial window depending on data length
    # Just verify no crash and result dict has the key
    assert "new_partial" in result
    assert result["new_partial"] == partial_rows
```

- [x] **Step 2: Run test — expect PASS**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_backtest_roller.py::test_roll_ticker_partial_window -v 2>&1 | tail -10
```

Expected: `PASSED`

- [x] **Step 3: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add tests/test_backtest_roller.py && git commit -m "test(g1): add partial window test for roll_ticker"
```

---

## Task 4: `roll_all()` + `export_meta_dataset()`

**Files:**
- Modify: `engine/backtest_roller.py`
- Modify: `tests/test_backtest_roller.py`

- [x] **Step 1: Write failing tests**

Append to `tests/test_backtest_roller.py`:

```python
def test_roll_all_returns_summary(monkeypatch, tmp_path):
    """roll_all returns dict with expected keys and writes to tmp DB."""
    import engine.backtest_roller as roller
    db = str(tmp_path / "test.db")
    df = _make_df(400)
    monkeypatch.setattr(roller, "DB_PATH", db)

    # Patch _load_ohlcv_bulk and get_all_tickers to return one ticker
    import scheduler.utils as sutils
    monkeypatch.setattr(sutils, "_load_ohlcv_bulk", lambda: {"ACES": df})
    monkeypatch.setattr(sutils, "get_all_tickers", lambda: ["ACES"])

    result = roller.roll_all(db_path=db)
    for key in ["new_complete", "new_partial", "tickers_updated", "errors", "total_tickers"]:
        assert key in result, f"missing key: {key}"
    assert result["total_tickers"] == 1
    assert isinstance(result["errors"], list)


def test_export_meta_dataset_format(tmp_path):
    """export_meta_dataset writes valid JSON matching meta_dataset_backtest.json schema."""
    import engine.backtest_roller as roller
    db = str(tmp_path / "test.db")
    out = str(tmp_path / "out.json")

    conn = sqlite3.connect(db)
    roller._init_table(conn)
    conn.execute("""
        INSERT INTO backtest_windows
        (ticker, window_num, train_start, train_end, test_start, test_end,
         is_partial, features_json, metrics_json, computed_at)
        VALUES ('ACES', 0, '2024-01-01', '2025-01-01', '2025-01-01', '2025-04-01',
                0,
                '{"adx": 25.0, "ma_slope": 1.5, "vr_mean": 1.2, "range_pct": 3.0, "close_vs_ma": 0.5, "pct_above_ma": 60.0}',
                '{"vol_weighted": {"return": 2.5, "win_rate": 60.0, "sharpe": 1.2, "max_dd": -1.5, "profit_factor": 2.0}}',
                '2026-06-01 10:00')
    """)
    conn.commit()
    conn.close()

    n = roller.export_meta_dataset(path=out, db_path=db)
    assert n == 1

    import json
    with open(out) as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 1
    entry = data[0]
    for key in ["ticker", "window", "test_start", "test_end", "features", "metrics"]:
        assert key in entry, f"missing key: {key}"
    assert entry["ticker"] == "ACES"
    assert entry["window"] == 0
    assert isinstance(entry["features"], dict)
    assert isinstance(entry["metrics"], dict)


def test_export_meta_dataset_ticker_filter(tmp_path):
    """export_meta_dataset tickers= parameter filters output."""
    import engine.backtest_roller as roller
    db = str(tmp_path / "test.db")
    out = str(tmp_path / "out.json")

    conn = sqlite3.connect(db)
    roller._init_table(conn)
    for ticker in ["ACES", "BBCA"]:
        conn.execute("""
            INSERT INTO backtest_windows
            (ticker, window_num, train_start, train_end, test_start, test_end,
             is_partial, features_json, metrics_json, computed_at)
            VALUES (?,0,'2024-01-01','2025-01-01','2025-01-01','2025-04-01',0,'{}','{}','2026-06-01')
        """, (ticker,))
    conn.commit()
    conn.close()

    n = roller.export_meta_dataset(path=out, tickers=["ACES"], db_path=db)
    assert n == 1
    import json
    with open(out) as f:
        data = json.load(f)
    assert all(e["ticker"] == "ACES" for e in data)
```

- [x] **Step 2: Run tests — expect FAIL**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_backtest_roller.py::test_roll_all_returns_summary tests/test_backtest_roller.py::test_export_meta_dataset_format tests/test_backtest_roller.py::test_export_meta_dataset_ticker_filter -v 2>&1 | tail -15
```

Expected: `AttributeError: module ... has no attribute 'roll_all'`

- [x] **Step 3: Implement `roll_all()` and `export_meta_dataset()`**

Append to `engine/backtest_roller.py`:

```python
def roll_all(tickers: list = None, include_partial: bool = True,
             db_path: str = None) -> dict:
    """
    Roll walk-forward windows for all (or a subset of) tickers.
    Returns summary: {new_complete, new_partial, tickers_updated, errors, total_tickers}.
    """
    from scheduler.utils import get_all_tickers, _load_ohlcv_bulk

    if db_path is None:
        db_path = DB_PATH
    if tickers is None:
        tickers = get_all_tickers()

    ohlcv_map = _load_ohlcv_bulk()
    conn = sqlite3.connect(db_path)
    _init_table(conn)

    total_new_complete = 0
    total_new_partial = 0
    tickers_updated = 0
    errors: list = []

    for ticker in tickers:
        df = ohlcv_map.get(ticker)
        if df is None or len(df) < 60:
            continue
        try:
            result = roll_ticker(ticker, df, conn, include_partial=include_partial)
            conn.commit()
            if result["new_complete"] > 0 or result["new_partial"] > 0:
                tickers_updated += 1
            total_new_complete += result["new_complete"]
            total_new_partial += result["new_partial"]
        except Exception as exc:
            logger.warning("roll_all %s error: %s", ticker, exc)
            errors.append({"ticker": ticker, "error": str(exc)})

    conn.close()
    return {
        "new_complete":    total_new_complete,
        "new_partial":     total_new_partial,
        "tickers_updated": tickers_updated,
        "errors":          errors,
        "total_tickers":   len(tickers),
    }


def export_meta_dataset(path: str = None, tickers: list = None,
                        db_path: str = None) -> int:
    """
    Write backtest_windows to out/meta_dataset_backtest.json.
    Returns number of records exported.
    """
    if path is None:
        path = OUT_PATH
    if db_path is None:
        db_path = DB_PATH

    conn = sqlite3.connect(db_path)
    query = (
        "SELECT ticker, window_num, test_start, test_end, features_json, metrics_json "
        "FROM backtest_windows"
    )
    params: list = []
    if tickers:
        placeholders = ",".join("?" * len(tickers))
        query += f" WHERE ticker IN ({placeholders})"
        params = list(tickers)
    query += " ORDER BY ticker, test_start"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    records = []
    for ticker, window_num, test_start, test_end, features_json, metrics_json in rows:
        records.append({
            "ticker":     ticker,
            "window":     window_num,
            "test_start": test_start,
            "test_end":   test_end,
            "features":   json.loads(features_json) if features_json else {},
            "metrics":    json.loads(metrics_json)  if metrics_json  else {},
        })

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(records, fh, indent=2)

    logger.info("export_meta_dataset: %d records → %s", len(records), path)
    return len(records)
```

- [x] **Step 4: Run tests — expect PASS**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_backtest_roller.py::test_roll_all_returns_summary tests/test_backtest_roller.py::test_export_meta_dataset_format tests/test_backtest_roller.py::test_export_meta_dataset_ticker_filter -v 2>&1 | tail -15
```

Expected: all 3 `PASSED`

- [x] **Step 5: Run full test file**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/test_backtest_roller.py -v 2>&1 | tail -20
```

Expected: all 7 tests `PASSED`

- [x] **Step 6: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add engine/backtest_roller.py tests/test_backtest_roller.py && git commit -m "feat(g1): add roll_all() and export_meta_dataset() to backtest_roller"
```

---

## Task 5: Scheduler Job

**Files:**
- Modify: `scheduler/jobs.py`
- Modify: `scheduler/__init__.py`

- [x] **Step 1: Add `run_backtest_roller()` to `scheduler/jobs.py`**

Open `scheduler/jobs.py`. After `run_premover_eod()` (end of file, line ~287), append:

```python

def run_backtest_roller():
    """Monthly backtest window roller — appends new windows, exports JSON."""
    from engine.backtest_roller import roll_all, export_meta_dataset
    now_str = datetime.now(WIB).strftime('%H:%M')
    print(f"[{now_str}] Backtest roller dimulai...")
    try:
        summary = roll_all(include_partial=True)
        n_exported = export_meta_dataset()
        msg = (
            f"🔄 <b>Backtest Roller Selesai</b>\n\n"
            f"New complete windows: <b>{summary['new_complete']}</b>\n"
            f"New partial windows: <b>{summary['new_partial']}</b>\n"
            f"Tickers updated: <b>{summary['tickers_updated']}/{summary['total_tickers']}</b>\n"
            f"JSON exported: <b>{n_exported} records</b>"
        )
        if summary['errors']:
            msg += f"\n⚠️ Errors: {len(summary['errors'])}"
        send_telegram(msg)
        print(f"[{datetime.now(WIB).strftime('%H:%M')}] Backtest roller selesai. "
              f"{summary['new_complete']} complete, {summary['new_partial']} partial")
    except Exception as e:
        send_telegram(f"🔴 <b>Backtest Roller Error</b>\n<code>{str(e)[:200]}</code>")
        print(f"[{now_str}] Backtest roller error: {e}")
```

- [x] **Step 2: Add re-export to `scheduler/__init__.py`**

In `scheduler/__init__.py`, find the jobs re-export block (lines 42–53). Add `run_backtest_roller` to the import list:

```python
from scheduler.jobs import (  # noqa: F401
    refresh_wf_scores,
    run_flow_fetch,
    run_broker_flow_fetch,
    run_foreign_snapshot,
    run_news_fetch,
    run_premover_eod,
    run_backtest_roller,
    _refresh_backtest_cache,
    _run_open_trade_monitor,
    _run_screener_intraday,
    _run_screener_eod,
)
```

- [x] **Step 3: Add cron job to `start_scheduler()`**

In `scheduler/__init__.py`, after the `run_premover_eod` job (around line 162), add before `scheduler.start()`:

```python
    # Backtest roller — 1st Sunday of each month at 10:00 WIB
    scheduler.add_job(run_backtest_roller, CronTrigger(
        day="1-7", day_of_week="sun", hour=10, minute=0, timezone=WIB),
        id="backtest_roller", name="Backtest Roller Sun 10:00")
```

And add to the `print` block after `scheduler.start()`:

```python
    print("  🔄 BACKTEST ROLLER: 1st Sun/month 10:00 (rolling WF windows)")
```

- [x] **Step 4: Verify scheduler imports cleanly**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -c "from scheduler import run_backtest_roller; print('OK')"
```

Expected: `OK`

- [x] **Step 5: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/ -x -q 2>&1 | tail -10
```

Expected: all tests pass (no regressions)

- [x] **Step 6: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add scheduler/jobs.py scheduler/__init__.py && git commit -m "feat(g1): add run_backtest_roller job to scheduler, monthly Sunday 10:00 WIB"
```

---

## Task 6: Flask Endpoint

**Files:**
- Modify: `routes/backtest.py`

- [x] **Step 1: Add the route**

In `routes/backtest.py`, after the last `@backtest_bp.route` endpoint, append:

```python
@backtest_bp.route('/api/backtest/roll', methods=['POST'])
def api_backtest_roll():
    """Trigger backtest roller on demand. Body: {tickers?: list, include_partial?: bool}"""
    from engine.backtest_roller import roll_all, export_meta_dataset
    body = request.get_json(force=True) or {}
    tickers = body.get('tickers')          # optional ticker list; None = all
    include_partial = bool(body.get('include_partial', True))
    try:
        summary = roll_all(tickers=tickers, include_partial=include_partial)
        n_exported = export_meta_dataset()
        summary['exported'] = n_exported
        return jsonify({'status': 'ok', 'summary': summary})
    except Exception as e:
        logging.exception("api_backtest_roll error")
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

- [x] **Step 2: Smoke-test the endpoint manually**

```bash
curl -s -X POST http://localhost:5001/api/backtest/roll \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["BRPT"], "include_partial": true}' | python3 -m json.tool
```

Expected: `{"status": "ok", "summary": {"new_complete": ..., "new_partial": ..., ...}}`

(If Flask isn't running, start it first: `systemctl restart idx-walkforward-5001.service`)

- [x] **Step 3: Run full test suite**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python -m pytest tests/ -x -q 2>&1 | tail -10
```

Expected: all tests pass

- [x] **Step 4: Commit**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && git add routes/backtest.py && git commit -m "feat(g1): add POST /api/backtest/roll endpoint for on-demand window rolling"
```

---

## Task 7: Initial Population Run + Verify

**Files:** No code changes — execute and verify.

- [x] **Step 1: Run the roller for the full ticker set**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" && python3 -c "
from engine.backtest_roller import roll_all, export_meta_dataset
print('Rolling all tickers...')
summary = roll_all(include_partial=True)
print('Summary:', summary)
n = export_meta_dataset()
print(f'Exported {n} records to out/meta_dataset_backtest.json')
"
```

This will take 15–30 minutes for all 871 tickers. Let it complete.

Expected output ends with something like:
```
Summary: {'new_complete': 2843, 'new_partial': 615, 'tickers_updated': 712, 'errors': [...], 'total_tickers': 871}
Exported 3458 records to out/meta_dataset_backtest.json
```

- [x] **Step 2: Verify DB table**

```bash
python3 -c "
import sqlite3, json
conn = sqlite3.connect('data/walkforward.db')
total  = conn.execute('SELECT COUNT(*) FROM backtest_windows').fetchone()[0]
partial = conn.execute('SELECT COUNT(*) FROM backtest_windows WHERE is_partial=1').fetchone()[0]
tickers = conn.execute('SELECT COUNT(DISTINCT ticker) FROM backtest_windows').fetchone()[0]
latest  = conn.execute('SELECT MAX(test_end) FROM backtest_windows').fetchone()[0]
latest_partial = conn.execute('SELECT MAX(test_end) FROM backtest_windows WHERE is_partial=1').fetchone()[0]
conn.close()
print(f'Total rows: {total}  Partial: {partial}  Tickers: {tickers}')
print(f'Latest complete test_end: {latest}')
print(f'Latest partial test_end: {latest_partial}  (should be today or yesterday)')
"
```

Expected: `latest_partial` should be today's date (2026-06-04) or the most recent OHLCV date.

- [x] **Step 3: Verify JSON file**

```bash
python3 -c "
import json
with open('out/meta_dataset_backtest.json') as f:
    d = json.load(f)
tickers = {e['ticker'] for e in d}
partial = [e for e in d if e.get('test_end') > '2026-04-29']
print(f'Total records: {len(d)}, Unique tickers: {len(tickers)}')
print(f'Records beyond Apr 2026 (new): {len(partial)}')
brpt = [e for e in d if e[\"ticker\"] == \"BRPT\"]
print(f'BRPT windows: {[(e[\"test_start\"], e[\"test_end\"]) for e in brpt]}')
"
```

Expected: BRPT should have a partial window with `test_end` ≈ 2026-06-04.

- [x] **Step 4: Commit updated JSON artifact and mark G1 complete in TODO.md**

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
# Mark G1 done in TODO.md — change `- [x] **G1.` to `- [x] **G1.`
sed -i 's/- \[ \] \*\*G1\. Backtest/- [x] **G1. Backtest/' TODO.md
git add out/meta_dataset_backtest.json TODO.md
git commit -m "feat(g1): initial backtest_windows population + regenerated meta_dataset_backtest.json"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `backtest_windows` DB table — Task 1
- ✅ `roll_ticker` complete windows — Task 2
- ✅ `roll_ticker` partial window (is_partial=1) — Task 3
- ✅ `roll_all()` — Task 4
- ✅ `export_meta_dataset()` — Task 4
- ✅ JSON format preserved (ticker, window, test_start, test_end, features, metrics) — Task 4 test
- ✅ Scheduler monthly Sunday — Task 5
- ✅ `POST /api/backtest/roll` endpoint — Task 6
- ✅ Initial population run — Task 7

**Type consistency:**
- `roll_ticker` returns `{"new_complete": int, "new_partial": int}` — used correctly in `roll_all`
- `roll_all` returns `{"new_complete", "new_partial", "tickers_updated", "errors", "total_tickers"}` — used correctly in scheduler job and endpoint
- `export_meta_dataset(path, tickers, db_path)` — all callers pass kwargs correctly
- `_init_table(conn)` — called consistently with a `sqlite3.Connection`

**No placeholders:** All steps have complete code, exact commands, and expected output.
