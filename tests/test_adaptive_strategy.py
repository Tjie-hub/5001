"""Tests for adaptive_strategy_selector() in scheduler/scanner.py.

Phase 2C: live selection gates on positive pooled wf_edge expectancy (not
per-ticker wf_scores consistency). The fixture pins _get_disabled_strategies
to an empty set so these tests isolate the SELECTOR mechanism (regime map ∩
positive-edge wf_edge); the default disabled roster is covered in
tests/test_edge_selector.py.
"""
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
    """Temp DB with a wf_edge table patched into scanner.DB_PATH. Event guard,
    macro panic and the disabled set are pinned so tests are deterministic and
    isolated from live config."""
    import scheduler.scanner as sc
    db = str(tmp_path / "sc.db")
    monkeypatch.setattr(sc, "DB_PATH", db)
    monkeypatch.setattr(sc, "_event_guard_active", lambda: (False, 0.5))
    monkeypatch.setattr(sc, "_macro_panic_state", lambda: False)
    monkeypatch.setattr(sc, "_get_disabled_strategies", lambda: set())
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE wf_edge (
            ticker TEXT, strategy TEXT, expectancy_pct REAL, expectancy_rp REAL,
            win_rate REAL, consistency_pct REAL, sharpe REAL, n_trades INTEGER,
            windows_tested INTEGER, last_computed TEXT,
            PRIMARY KEY (ticker, strategy)
        )
    """)
    conn.commit()
    conn.close()
    return db


def _insert_edge(db, ticker, strategy, expectancy_pct):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO wf_edge VALUES (?,?,?,?,?,?,?,?,?,?)",
        (ticker, strategy, expectancy_pct, 0.0, 55.0, 40.0, 0.4, 60, 15, "2026-07-04"),
    )
    conn.commit()
    conn.close()


def test_bull_prefers_tfb(wf_db):
    """BULL regime → TFB selected when it has positive wf_edge expectancy;
    counter-trend / sweep strategies never leak into a BULL scan."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_edge(wf_db, "BBCA", "Trend Following Breakout", 1.2)

    df = _make_regime_df(adx_val=30, ma_slope_val=2.0)
    result = adaptive_strategy_selector("BBCA", df)
    assert "Trend Following Breakout" in result
    assert "Crash Recovery" not in result
    assert "Liquidity Sweep" not in result


def test_bull_excludes_negative_edge_candidate(wf_db):
    """A BULL-map candidate with NEGATIVE wf_edge expectancy is not selected."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_edge(wf_db, "BBCA", "momentum", -0.7)      # in BULL_MODERATE map, but loses

    df = _make_regime_df(adx_val=30, ma_slope_val=2.0)
    result = adaptive_strategy_selector("BBCA", df)
    assert "momentum" not in result


def test_bear_returns_counter_trend_book(wf_db):
    """BEAR regime → counter-trend book (Crash Recovery, Panic Rebound) always
    present; momentum-family never appears. Liquidity Sweep is in the BEAR map
    but NOT the counter-trend book, so it is edge-gated: absent without a
    positive wf_edge row, present with one."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_edge(wf_db, "BEAR_T", "Trend Following Breakout", 1.5)   # off-map for BEAR
    _insert_edge(wf_db, "BEAR_T", "momentum", 1.0)                   # off-map for BEAR

    df = _make_regime_df(adx_val=30, ma_slope_val=-2.5)
    result = adaptive_strategy_selector("BEAR_T", df)
    assert set(result) == {"Crash Recovery", "Panic Rebound"}, result

    # Once it earns a positive edge, it joins the BEAR candidates.
    _insert_edge(wf_db, "BEAR_T", "Liquidity Sweep", 0.8)
    result2 = adaptive_strategy_selector("BEAR_T", df)
    assert "Liquidity Sweep" in result2, result2


def test_sideways_routes_panic_rebound(wf_db):
    """SIDEWAYS regime → Panic Rebound (counter-trend) present; trend-following
    strategies must not appear even with a positive edge (off the sideways map)."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_edge(wf_db, "FLAT_T", "Trend Following Breakout", 1.2)   # off-map for SIDEWAYS

    df = _make_regime_df(adx_val=15, ma_slope_val=0.2)
    result = adaptive_strategy_selector("FLAT_T", df)
    assert "Panic Rebound" in result
    assert "Trend Following Breakout" not in result


def test_no_positive_edge_returns_no_wf_strategies(wf_db):
    """BULL regime, only an off-map negative-edge strategy → no wf-gated pick
    (and no counter-trend book in BULL)."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_edge(wf_db, "BULL_NOWF", "Liquidity Sweep", -1.0)   # off-map + negative

    df = _make_regime_df(adx_val=30, ma_slope_val=2.0)
    result = adaptive_strategy_selector("BULL_NOWF", df)
    assert result == [], result
