"""Tests for engine/backtest_roller.py — rolling walk-forward window pipeline."""
import sqlite3
import json
import pytest
import pandas as pd
import numpy as np


def _make_df(n_bars: int = 400, start: str = "2024-01-02") -> pd.DataFrame:
    """Synthetic OHLCV DataFrame for testing."""
    dates = pd.date_range(start=start, periods=n_bars, freq="B")
    np.random.seed(42)
    close = 1000 + np.cumsum(np.random.randn(n_bars) * 5)
    close = np.maximum(close, 100)
    return pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in dates],
        "open":   close * 0.99,
        "high":   close * 1.02,
        "low":    close * 0.97,
        "close":  close,
        "volume": np.random.randint(500_000, 5_000_000, n_bars).astype(float),
    })


def test_init_table_creates_backtest_windows():
    from research.backtest_roller import _init_table
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


def test_roll_ticker_inserts_complete_windows():
    """roll_ticker inserts complete windows for a 400-bar ticker."""
    from research.backtest_roller import _init_table, roll_ticker
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
    from research.backtest_roller import _init_table, roll_ticker
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
    from research.backtest_roller import _init_table, roll_ticker
    conn = sqlite3.connect(":memory:")
    _init_table(conn)
    df = _make_df(50)
    result = roll_ticker("TINY", df, conn, include_partial=False)
    assert result == {"new_complete": 0, "new_partial": 0}


def test_roll_ticker_partial_window():
    """roll_ticker with include_partial=True includes partial window key in result."""
    from research.backtest_roller import _init_table, roll_ticker
    conn = sqlite3.connect(":memory:")
    _init_table(conn)
    df = _make_df(400)
    result = roll_ticker("BBRI", df, conn, include_partial=True)
    partial_rows = conn.execute(
        "SELECT COUNT(*) FROM backtest_windows WHERE ticker='BBRI' AND is_partial=1"
    ).fetchone()[0]
    assert "new_partial" in result
    assert result["new_partial"] == partial_rows


def test_roll_all_returns_summary(monkeypatch, tmp_path):
    """roll_all returns dict with expected keys."""
    import research.backtest_roller as roller
    import data.loaders as dl
    db = str(tmp_path / "test.db")
    df = _make_df(400)
    monkeypatch.setattr(roller, "DB_PATH", db)
    # roller's lazy import resolves data.loaders at call time (M2) — patch there
    monkeypatch.setattr(dl, "_load_ohlcv_bulk", lambda: {"ACES": df})
    monkeypatch.setattr(dl, "get_all_tickers", lambda: ["ACES"])

    result = roller.roll_all(db_path=db)
    for key in ["new_complete", "new_partial", "tickers_updated", "errors", "total_tickers"]:
        assert key in result, f"missing key: {key}"
    assert result["total_tickers"] == 1
    assert isinstance(result["errors"], list)


def test_export_meta_dataset_format(tmp_path):
    """export_meta_dataset writes valid JSON matching meta_dataset_backtest.json schema."""
    import research.backtest_roller as roller
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
    import research.backtest_roller as roller
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
    with open(out) as f:
        data = json.load(f)
    assert all(e["ticker"] == "ACES" for e in data)
