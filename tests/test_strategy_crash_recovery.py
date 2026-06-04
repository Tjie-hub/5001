"""Tests for strategy_crash_recovery and check_crash_recovery_signal."""
import sqlite3
import pandas as pd
import numpy as np
import pytest


def _make_crash_df(
    normal_bars: int = 30,
    gap_days: int = 11,
    gap_pct: float = -0.25,
    conf_vr: float = 5.0,
    conf_bullish: bool = True,
    trailing_bars: int = 10,
) -> pd.DataFrame:
    """
    Synthetic OHLCV with one crash event.
    normal_bars: bars before the suspension
    gap_days: calendar days between last normal bar and resume bar
    gap_pct: open-gap on resume bar (negative = gap-down)
    conf_vr: volume multiplier on first confirmation bar (sets VR)
    conf_bullish: whether confirmation bar is close > open
    trailing_bars: bars after confirmation bar
    """
    avg_vol = 1_000_000
    last_close = 2000.0

    # Normal bars
    normal_dates = pd.bdate_range("2025-01-02", periods=normal_bars)
    normal = pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in normal_dates],
        "open":   [last_close * 0.99] * normal_bars,
        "high":   [last_close * 1.01] * normal_bars,
        "low":    [last_close * 0.98] * normal_bars,
        "close":  [last_close] * normal_bars,
        "volume": [float(avg_vol)] * normal_bars,
    })

    # Crash resume bar
    resume_date = normal_dates[-1] + pd.Timedelta(days=gap_days)
    resume_open = last_close * (1 + gap_pct)   # e.g. 1500 for -25%
    crash = pd.DataFrame({
        "date":   [resume_date.strftime("%Y-%m-%d")],
        "open":   [resume_open],
        "high":   [resume_open * 1.01],
        "low":    [resume_open * 0.97],          # resume bar low = SL anchor
        "close":  [resume_open * 0.99],          # slightly bearish resume bar
        "volume": [float(avg_vol)],
    })

    # Confirmation bar
    conf_date = resume_date + pd.Timedelta(days=1)
    conf_open = resume_open
    conf_close = conf_open * 1.04 if conf_bullish else conf_open * 0.96
    conf_vol = float(conf_vr * avg_vol)
    conf = pd.DataFrame({
        "date":   [conf_date.strftime("%Y-%m-%d")],
        "open":   [conf_open],
        "high":   [max(conf_open, conf_close) * 1.01],
        "low":    [min(conf_open, conf_close) * 0.99],
        "close":  [conf_close],
        "volume": [conf_vol],
    })

    # Trailing bars: open near confirmation close (entry price zone),
    # high well above TP so TP gets hit. TP = 1500 + 0.5*(2000-1500) = 1750.
    trail_start = conf_date + pd.Timedelta(days=1)
    trail_dates = pd.bdate_range(trail_start, periods=trailing_bars)
    trail_open_price = conf_close if conf_bullish else conf_open
    trail = pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in trail_dates],
        "open":   [trail_open_price] * trailing_bars,
        "high":   [resume_open * 1.25] * trailing_bars,  # 1875 >> TP 1750
        "low":    [trail_open_price * 0.98] * trailing_bars,
        "close":  [trail_open_price * 1.01] * trailing_bars,
        "volume": [float(avg_vol)] * trailing_bars,
    })

    return pd.concat([normal, crash, conf, trail], ignore_index=True)


def test_no_trades_without_gap():
    """Continuous OHLCV with no calendar gap ≥5d → 0 trades."""
    from engine.strategies import strategy_crash_recovery
    dates = pd.bdate_range("2025-01-02", periods=60)
    df = pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in dates],
        "open":   [2000.0] * 60,
        "high":   [2020.0] * 60,
        "low":    [1980.0] * 60,
        "close":  [2000.0] * 60,
        "volume": [1_000_000.0] * 60,
    })
    result = strategy_crash_recovery(df)
    assert result["strategy"] == "Crash Recovery"
    assert len(result["trades"]) == 0


def test_entry_after_crash_resume():
    """Gap-down ≥20% + bullish high-VR bar → at least 1 trade entered."""
    from engine.strategies import strategy_crash_recovery
    df = _make_crash_df(gap_days=11, gap_pct=-0.25, conf_vr=5.0, conf_bullish=True)
    result = strategy_crash_recovery(df)
    assert len(result["trades"]) >= 1, f"expected >=1 trade; got 0"


def test_sl_is_resume_bar_low():
    """SL-triggered exit price reflects resume bar low (apply_costs adjusted)."""
    from engine.strategies import strategy_crash_recovery, apply_costs
    # Force SL hit: trailing bars have low below resume_low
    normal_bars = 30
    avg_vol = 1_000_000
    last_close = 2000.0
    normal_dates = pd.bdate_range("2025-01-02", periods=normal_bars)
    normal = pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in normal_dates],
        "open":   [last_close * 0.99] * normal_bars,
        "high":   [last_close * 1.01] * normal_bars,
        "low":    [last_close * 0.98] * normal_bars,
        "close":  [last_close] * normal_bars,
        "volume": [float(avg_vol)] * normal_bars,
    })
    resume_open = 1500.0
    resume_low_price = resume_open * 0.97   # = 1455.0
    resume_date = normal_dates[-1] + pd.Timedelta(days=11)
    crash = pd.DataFrame({
        "date":   [resume_date.strftime("%Y-%m-%d")],
        "open":   [resume_open],
        "high":   [resume_open * 1.01],
        "low":    [resume_low_price],
        "close":  [resume_open * 0.99],
        "volume": [float(avg_vol)],
    })
    conf_date = resume_date + pd.Timedelta(days=1)
    conf = pd.DataFrame({
        "date":   [conf_date.strftime("%Y-%m-%d")],
        "open":   [resume_open],
        "high":   [resume_open * 1.05],
        "low":    [resume_open * 0.99],
        "close":  [resume_open * 1.04],   # bullish
        "volume": [float(5 * avg_vol)],   # VR > 2
    })
    # Trailing bars with low BELOW resume_low to trigger SL
    trail_dates = pd.bdate_range(conf_date + pd.Timedelta(days=1), periods=5)
    trail = pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in trail_dates],
        "open":   [1480.0] * 5,
        "high":   [1490.0] * 5,
        "low":    [1430.0] * 5,    # below resume_low=1455 → SL hit
        "close":  [1440.0] * 5,
        "volume": [float(avg_vol)] * 5,
    })
    df = pd.concat([normal, crash, conf, trail], ignore_index=True)
    result = strategy_crash_recovery(df)
    assert len(result["trades"]) >= 1
    sl_trade = next((t for t in result["trades"] if t.exit_reason == "SL"), None)
    assert sl_trade is not None, "expected a SL-exit trade"
    expected_sl = apply_costs(resume_low_price, 'SELL')
    # apply_costs is applied twice (stored sl_level → exit), consistent with
    # strategy_inside_bar_breakout pattern. Tolerance accommodates double-application.
    assert abs(sl_trade.exit_price - expected_sl) < 15.0, (
        f"SL exit price {sl_trade.exit_price} not close to expected {expected_sl}"
    )


def test_tp_is_50pct_retracement():
    """TP exit price reflects resume_open + 50% × gap_amount."""
    from engine.strategies import strategy_crash_recovery, apply_costs
    # gap_pct=-0.25: resume_open=1500, gap_amount=500, TP=1750
    df = _make_crash_df(gap_days=11, gap_pct=-0.25, conf_vr=5.0, conf_bullish=True,
                        trailing_bars=15)
    result = strategy_crash_recovery(df)
    assert len(result["trades"]) >= 1
    tp_trade = next((t for t in result["trades"] if t.exit_reason == "TP"), None)
    assert tp_trade is not None, "expected a TP-exit trade"
    # TP = resume_open + 0.5 * gap_amount = 1500 + 0.5*500 = 1750
    # exit_price = apply_costs(1750, 'SELL') = 1750 * (1 - 0.0025 - 0.001) ≈ 1743.9
    expected_tp = apply_costs(1750.0, 'SELL')
    assert abs(tp_trade.exit_price - expected_tp) < 15.0, (
        f"TP exit price {tp_trade.exit_price} not close to expected {expected_tp}"
    )


def test_entry_window_expires():
    """No bullish high-VR bar within 3 bars after crash → 0 trades."""
    from engine.strategies import strategy_crash_recovery
    # conf_bullish=False: confirmation bar is bearish, trailing bars have normal VR(1.0)<2.0
    df = _make_crash_df(gap_days=11, gap_pct=-0.25, conf_vr=5.0, conf_bullish=False,
                        trailing_bars=10)
    result = strategy_crash_recovery(df)
    assert len(result["trades"]) == 0, (
        f"expected 0 trades when confirmation never fires; got {len(result['trades'])}"
    )


def test_check_signal_no_recent_suspension(tmp_path):
    """No suspension in DB within last 5 bars → no signal."""
    from engine.strategies import check_crash_recovery_signal
    db = str(tmp_path / "test.db")
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE suspension_events (
        ticker TEXT, last_normal_date TEXT, resume_date TEXT,
        missing_td INTEGER, gap_pct REAL, classification TEXT, detected_at TEXT
    )""")
    conn.commit()
    conn.close()

    dates = pd.bdate_range("2025-01-02", periods=40)
    df = pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in dates],
        "open":   [2000.0] * 40,
        "high":   [2020.0] * 40,
        "low":    [1980.0] * 40,
        "close":  [2010.0] * 40,
        "volume": [1_000_000.0] * 40,
    })

    result = check_crash_recovery_signal("ACES", df, db_path=db)
    assert result["has_signal"] is False
    assert "no recent" in result["reason"].lower() or "suspension" in result["reason"].lower()


def test_check_signal_with_recent_suspension(tmp_path):
    """Recent suspension in DB + high VR bullish last bar → signal."""
    from engine.strategies import check_crash_recovery_signal
    db = str(tmp_path / "test.db")
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE suspension_events (
        ticker TEXT, last_normal_date TEXT, resume_date TEXT,
        missing_td INTEGER, gap_pct REAL, classification TEXT, detected_at TEXT
    )""")
    dates = pd.bdate_range("2025-01-02", periods=40)
    resume_date_str = dates[-3].strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO suspension_events VALUES (?,?,?,?,?,?,?)",
        ("BRPT", "2025-01-15", resume_date_str, 11, -0.224, "suspension", "2025-03-01")
    )
    conn.commit()
    conn.close()

    avg_vol = 1_000_000.0
    closes = [2000.0] * 40
    opens  = [1990.0] * 40
    volumes = [avg_vol] * 40
    # Resume bar (index -3): gap-down open
    opens[-3]  = 1500.0
    closes[-3] = 1480.0
    # Last bar: high VR + bullish
    opens[-1]  = 1520.0
    closes[-1] = 1580.0           # close > open ✓
    volumes[-1] = 5_000_000.0     # VR ≈ 4.2× > 2.0 ✓

    df = pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in dates],
        "open":   opens,
        "high":   [max(o, c) * 1.01 for o, c in zip(opens, closes)],
        "low":    [min(o, c) * 0.99 for o, c in zip(opens, closes)],
        "close":  closes,
        "volume": volumes,
    })

    result = check_crash_recovery_signal("BRPT", df, db_path=db)
    assert result["has_signal"] is True, f"expected signal, got: {result['reason']}"
    assert "sl" in result["details"]
    assert "tp" in result["details"]
    assert "resume_date" in result["details"]
