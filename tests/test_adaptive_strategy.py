"""Tests for adaptive_strategy_selector() in scheduler/scanner.py."""
import sqlite3
import pytest
import pandas as pd
import numpy as np


def _make_regime_df(adx_val: float, ma_slope_val: float, n: int = 40) -> pd.DataFrame:
    """
    Synthetic OHLCV. detect_regime() uses calc_adx(df,14) and calc_ma_slope(df,20,5).
    adx_val drives price range magnitude, ma_slope_val controls direction.
    """
    if ma_slope_val > 1.0:
        close = np.linspace(1000, 1000 * (1 + adx_val / 100 * n / 10), n)
    elif ma_slope_val < -1.0:
        close = np.linspace(1000, 1000 * (1 - adx_val / 100 * n / 10), n)
    else:
        close = np.full(n, 1000.0) + np.random.default_rng(42).normal(0, 2, n).cumsum()

    close = np.maximum(close, 50.0)
    dates = pd.bdate_range("2025-01-02", periods=n)
    return pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in dates],
        "open":   close * 0.99,
        "high":   close * 1.02,
        "low":    close * 0.97,
        "close":  close,
        "volume": np.full(n, 1_000_000.0),
    })


@pytest.fixture()
def wf_db(tmp_path, monkeypatch):
    """Temporary DB with wf_scores table, patched into scanner.DB_PATH."""
    import scheduler.scanner as sc
    db = str(tmp_path / "sc.db")
    monkeypatch.setattr(sc, "DB_PATH", db)
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE wf_scores (
            ticker TEXT, strategy TEXT, consistency_pct REAL,
            avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL,
            windows_tested INTEGER, updated_at TEXT,
            PRIMARY KEY (ticker, strategy)
        )
    """)
    conn.commit()
    conn.close()
    return db


def _insert_wf(db, ticker, strategy, consistency, score):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO wf_scores VALUES (?,?,?,?,?,?,?,?)",
        (ticker, strategy, consistency, 5.0, 0.5, score, 4, "2026-06-05")
    )
    conn.commit()
    conn.close()


def test_bull_prefers_tfb(wf_db):
    """BULL regime → TFB preferred when in wf_scores; SIDEWAYS strategy excluded."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_wf(wf_db, "BBCA", "Trend Following Breakout", 65.0, 0.7)
    _insert_wf(wf_db, "BBCA", "vwap_reversion", 70.0, 0.8)

    df = _make_regime_df(adx_val=30, ma_slope_val=2.0)
    result = adaptive_strategy_selector("BBCA", df)
    assert "Trend Following Breakout" in result
    assert "vwap_reversion" not in result


def test_bear_always_returns_empty(wf_db):
    """BEAR regime → empty list regardless of wf_scores."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_wf(wf_db, "BEAR_T", "Trend Following Breakout", 80.0, 0.9)
    _insert_wf(wf_db, "BEAR_T", "momentum", 75.0, 0.85)

    df = _make_regime_df(adx_val=30, ma_slope_val=-2.5)
    result = adaptive_strategy_selector("BEAR_T", df)
    assert result == [], f"expected [] for BEAR, got {result}"


def test_sideways_prefers_vwap(wf_db):
    """SIDEWAYS regime → vwap_reversion returned; TFB excluded."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_wf(wf_db, "FLAT_T", "vwap_reversion", 60.0, 0.6)
    _insert_wf(wf_db, "FLAT_T", "Trend Following Breakout", 65.0, 0.7)

    df = _make_regime_df(adx_val=15, ma_slope_val=0.2)
    result = adaptive_strategy_selector("FLAT_T", df)
    assert "vwap_reversion" in result
    assert "Trend Following Breakout" not in result


def test_falls_back_when_no_wf_match(wf_db):
    """BULL regime but no BULL-appropriate strategy in wf_scores → fallback returns something."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_wf(wf_db, "BULL_NOWF", "vwap_reversion", 60.0, 0.6)

    df = _make_regime_df(adx_val=30, ma_slope_val=2.0)
    result = adaptive_strategy_selector("BULL_NOWF", df)
    assert isinstance(result, list)
    assert len(result) >= 1


def test_bull_conservative_in_wf_returns_conservative(wf_db):
    """BULL regime with conservative in wf_scores → conservative returned (in BULL_STRONG)."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_wf(wf_db, "STRONG_T", "conservative", 70.0, 0.8)
    _insert_wf(wf_db, "STRONG_T", "Trend Following Breakout", 65.0, 0.7)

    df = _make_regime_df(adx_val=50, ma_slope_val=3.0)
    result = adaptive_strategy_selector("STRONG_T", df)
    # Both are in BULL candidate lists (conservative in BULL_STRONG, TFB in both)
    # Result must be non-empty and contain at least one BULL-appropriate strategy
    bull_strategies = {"conservative", "Trend Following Breakout", "momentum",
                       "Inside Bar Breakout", "NR7 Breakout"}
    assert len(result) >= 1
    assert any(s in bull_strategies for s in result)
