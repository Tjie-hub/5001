"""Tests for classify_volume_context() in engine/indicators.py."""
import pandas as pd
import numpy as np
import pytest


def _make_df(n: int = 25, close: float = 1000.0, volume: float = 1_000_000.0,
             last_close: float = None, last_open: float = None,
             last_volume: float = None, high_20d: float = None) -> pd.DataFrame:
    """
    Synthetic OHLCV. All bars identical except optionally the last bar.
    high_20d: if set, first 20 bars' high = high_20d so rolling 20d-high = high_20d.
    """
    closes  = [close] * n
    opens_  = [close * 0.99] * n
    highs   = [close * 1.01] * n
    lows    = [close * 0.98] * n
    volumes = [volume] * n

    if high_20d is not None:
        for i in range(min(20, n)):
            highs[i] = high_20d

    if last_close  is not None: closes[-1]  = last_close
    if last_open   is not None: opens_[-1]  = last_open
    if last_volume is not None: volumes[-1] = last_volume

    dates = pd.bdate_range("2025-01-02", periods=n)
    return pd.DataFrame({
        "date":   [d.strftime("%Y-%m-%d") for d in dates],
        "open":   opens_,
        "high":   highs,
        "low":    lows,
        "close":  closes,
        "volume": volumes,
    })


def test_normal_context():
    """Flat price and normal volume → 'normal'."""
    from engine.indicators import classify_volume_context
    df = _make_df(25)
    assert classify_volume_context(df) == "normal"


def test_crash_absorption():
    """VR≥2x and close ≥20% below 20d high → 'crash_absorption'."""
    from engine.indicators import classify_volume_context
    # 20d high = 2000, last close = 1500 → pct_from_high = -25%
    # last volume = 5x avg → VR ≈ 4.2x
    df = _make_df(25, close=2000.0, volume=1_000_000.0,
                  last_close=1500.0, last_open=1520.0,
                  last_volume=5_000_000.0, high_20d=2000.0)
    assert classify_volume_context(df) == "crash_absorption"


def test_exhaustion_distribution():
    """VR≥2x + bearish close + near 20d high → 'exhaustion_distribution'."""
    from engine.indicators import classify_volume_context
    # last close=1960 (within 2% of high 2000), bearish (close < open), high volume
    df = _make_df(25, close=2000.0, volume=1_000_000.0,
                  last_close=1960.0, last_open=1990.0,
                  last_volume=5_000_000.0, high_20d=2000.0)
    assert classify_volume_context(df) == "exhaustion_distribution"


def test_breakout_accumulation():
    """VR≥1.5x + close near 20d high + above MA20 + bullish → 'breakout_accumulation'."""
    from engine.indicators import classify_volume_context
    # last close=2010 (0.5% above high 2000), bullish (close > open), moderate volume
    df = _make_df(25, close=2000.0, volume=1_000_000.0,
                  last_close=2010.0, last_open=1990.0,
                  last_volume=2_500_000.0, high_20d=2000.0)
    assert classify_volume_context(df) == "breakout_accumulation"


def test_short_df_returns_normal():
    """DataFrame with fewer than 20 bars → 'normal' (insufficient data)."""
    from engine.indicators import classify_volume_context
    df = _make_df(5)
    assert classify_volume_context(df) == "normal"


def test_score_ticker_reversal_includes_vol_context():
    """score_ticker_reversal() return dict must have 'vol_context' key."""
    from engine.premover_detector import score_ticker_reversal
    df = _make_df(60, close=2000.0, volume=1_000_000.0)
    result = score_ticker_reversal(df)
    assert "vol_context" in result, (
        f"score_ticker_reversal missing 'vol_context'. Keys: {list(result.keys())}"
    )
    assert result["vol_context"] in (
        "crash_absorption", "exhaustion_distribution",
        "breakout_accumulation", "normal"
    )
