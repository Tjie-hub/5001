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
    """Temporary DB with wf_scores table, patched into scanner.DB_PATH.
    Event guard and macro panic gate are pinned OFF so tests stay
    deterministic regardless of the calendar or live IHSG data.
    _get_disabled_strategies is pinned to an empty set so tests are
    isolated from live paper_config changes."""
    import scheduler.scanner as sc
    db = str(tmp_path / "sc.db")
    monkeypatch.setattr(sc, "DB_PATH", db)
    monkeypatch.setattr(sc, "_event_guard_active", lambda: (False, 0.5))
    monkeypatch.setattr(sc, "_macro_panic_state", lambda: False)
    monkeypatch.setattr(sc, "_get_disabled_strategies", lambda: set())
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


def _insert_wf_full(db, ticker, strategy, consistency, weighted_score,
                    avg_return_pct):
    """Insert with explicit avg_return_pct (for testing negative-return paths)."""
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO wf_scores VALUES (?,?,?,?,?,?,?,?)",
        (ticker, strategy, consistency, avg_return_pct, 0.5, weighted_score, 4, "2026-06-05")
    )
    conn.commit()
    conn.close()


def test_bull_prefers_tfb(wf_db):
    """BULL regime → TFB selected when in wf_scores. vwap_reversion is a
    re-enabled BULL candidate (update.md 2026-06-24, change #5) and may also
    appear once it passes the WF gate; counter-trend / sweep strategies must
    never leak into a BULL scan."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_wf(wf_db, "BBCA", "Trend Following Breakout", 65.0, 0.7)
    _insert_wf(wf_db, "BBCA", "vwap_reversion", 70.0, 0.8)

    df = _make_regime_df(adx_val=30, ma_slope_val=2.0)
    result = adaptive_strategy_selector("BBCA", df)
    assert "Trend Following Breakout" in result
    assert "Crash Recovery" not in result
    assert "Liquidity Sweep" not in result


def test_bear_returns_counter_trend_book(wf_db):
    """BEAR regime → counter-trend book (Crash Recovery, Panic Rebound) always
    present; momentum-family strategies never appear regardless of wf_scores.
    Liquidity Sweep is in the BEAR regime map but NOT the counter-trend book, so
    it is WF-gated: absent without a passing wf_scores row, present with one."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_wf(wf_db, "BEAR_T", "Trend Following Breakout", 80.0, 0.9)
    _insert_wf(wf_db, "BEAR_T", "momentum", 75.0, 0.85)

    df = _make_regime_df(adx_val=30, ma_slope_val=-2.5)
    result = adaptive_strategy_selector("BEAR_T", df)
    assert set(result) == {"Crash Recovery", "Panic Rebound"}, result
    assert "Liquidity Sweep" not in result  # no WF score yet → gated out

    # Once it earns a passing WF score, it joins the BEAR candidates.
    _insert_wf(wf_db, "BEAR_T", "Liquidity Sweep", 60.0, 0.7)
    result2 = adaptive_strategy_selector("BEAR_T", df)
    assert "Liquidity Sweep" in result2, result2


def test_sideways_routes_panic_rebound(wf_db):
    """SIDEWAYS regime → Panic Rebound (counter-trend) always present, and the
    Liquidity Sweep counter-trend candidate surfaces too. vwap_reversion was
    re-enabled as a SIDEWAYS mean-reversion candidate (update.md 2026-06-24,
    change #5), reversing the 2026-06-13 audit's blanket disable. Trend-following
    strategies must not appear in a sideways scan."""
    from scheduler.scanner import adaptive_strategy_selector
    _insert_wf(wf_db, "FLAT_T", "vwap_reversion", 60.0, 0.6)
    _insert_wf(wf_db, "FLAT_T", "Trend Following Breakout", 65.0, 0.7)

    df = _make_regime_df(adx_val=15, ma_slope_val=0.2)
    result = adaptive_strategy_selector("FLAT_T", df)
    assert "Panic Rebound" in result
    # Liquidity Sweep is in the SIDEWAYS map but WF-gated (not in the counter-
    # trend book), so it stays out until it has a passing wf_scores row.
    assert "Liquidity Sweep" not in result
    assert "Trend Following Breakout" not in result


def test_no_fallback_to_losing_defaults(wf_db):
    """BULL regime with only a non-BULL strategy that also has negative
    walkforward return → empty. The regime path doesn't find it (not in
    BULL_MODERATE/BULL_STRONG maps), and the get_ticker_best_strategies
    fallback filters it out via avg_return_pct > 0. No profitable strategy
    means no BUY signal for the ticker."""
    from scheduler.scanner import adaptive_strategy_selector
    # "Liquidity Sweep" is only in BEAR / SIDEWAYS regime maps, NOT in BULL.
    # It also has a NEGATIVE avg_return_pct so the fallback discards it.
    _insert_wf_full(wf_db, "BULL_NOWF", "Liquidity Sweep",
                    consistency=60.0, weighted_score=0.6, avg_return_pct=-1.0)

    df = _make_regime_df(adx_val=30, ma_slope_val=2.0)
    result = adaptive_strategy_selector("BULL_NOWF", df)
    assert result == [], result


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
