import pytest
import pandas as pd
import numpy as np


@pytest.fixture
def ohlcv():
    n = 40
    np.random.seed(42)
    close = 1000 + np.cumsum(np.random.randn(n) * 10)
    high = close + np.abs(np.random.randn(n) * 5)
    low  = close - np.abs(np.random.randn(n) * 5)
    return pd.DataFrame({
        'date':   pd.date_range('2025-01-01', periods=n),
        'open':   close - np.random.randn(n) * 3,
        'high':   high,
        'low':    low,
        'close':  close,
        'volume': np.random.randint(1_000_000, 5_000_000, n).astype(float),
    })


class TestCalcAtr:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_atr
        assert isinstance(calc_atr(ohlcv, period=14), pd.Series)

    def test_length_matches(self, ohlcv):
        from engine.indicators import calc_atr
        assert len(calc_atr(ohlcv, period=14)) == len(ohlcv)

    def test_leading_nan(self, ohlcv):
        from engine.indicators import calc_atr
        result = calc_atr(ohlcv, period=14)
        assert result.iloc[:13].isna().all()

    def test_no_nan_after_warmup(self, ohlcv):
        from engine.indicators import calc_atr
        result = calc_atr(ohlcv, period=14)
        assert not result.iloc[13:].isna().any()   # was iloc[14:]

    def test_positive_values(self, ohlcv):
        from engine.indicators import calc_atr
        assert (calc_atr(ohlcv, period=14).dropna() > 0).all()


class TestCalcVwap:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_vwap
        assert isinstance(calc_vwap(ohlcv, window=20), pd.Series)

    def test_leading_nan(self, ohlcv):
        from engine.indicators import calc_vwap
        result = calc_vwap(ohlcv, window=20)
        assert result.iloc[:19].isna().all()

    def test_no_nan_after_warmup(self, ohlcv):
        from engine.indicators import calc_vwap
        assert not calc_vwap(ohlcv, window=20).iloc[20:].isna().any()


class TestCalcVolRatio:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_vol_ratio
        assert isinstance(calc_vol_ratio(ohlcv, period=20), pd.Series)

    def test_no_nan(self, ohlcv):
        from engine.indicators import calc_vol_ratio
        assert not calc_vol_ratio(ohlcv, period=20).isna().any()

    def test_mean_near_one(self, ohlcv):
        from engine.indicators import calc_vol_ratio
        assert abs(calc_vol_ratio(ohlcv, period=20).mean() - 1.0) < 0.5


class TestCalcDelta:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_delta
        assert isinstance(calc_delta(ohlcv), pd.Series)

    def test_no_nan(self, ohlcv):
        from engine.indicators import calc_delta
        assert not calc_delta(ohlcv).isna().any()


class TestCalcVwma:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_vwma
        assert isinstance(calc_vwma(ohlcv, period=20), pd.Series)

    def test_leading_nan(self, ohlcv):
        from engine.indicators import calc_vwma
        assert calc_vwma(ohlcv, period=20).iloc[:19].isna().all()


class TestCalcSma:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_sma
        assert isinstance(calc_sma(ohlcv, period=20), pd.Series)

    def test_no_nan(self, ohlcv):
        from engine.indicators import calc_sma
        assert not calc_sma(ohlcv, period=20).isna().any()

    def test_converges_to_rolling_mean(self, ohlcv):
        from engine.indicators import calc_sma
        result   = calc_sma(ohlcv, period=20)
        expected = ohlcv['close'].rolling(20).mean().iloc[20]
        assert abs(result.iloc[20] - expected) < 0.01


class TestCalcRelativeStrength:
    def test_returns_float(self, ohlcv):
        from engine.indicators import calc_relative_strength
        assert isinstance(calc_relative_strength(ohlcv, ohlcv, period=20), float)

    def test_same_ticker_is_one(self, ohlcv):
        from engine.indicators import calc_relative_strength
        assert abs(calc_relative_strength(ohlcv, ohlcv, period=20) - 1.0) < 0.001

    def test_none_fallback(self):
        from engine.indicators import calc_relative_strength
        assert calc_relative_strength(None, None) == 1.0
