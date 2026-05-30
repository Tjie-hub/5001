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


class TestCalcAdx:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_adx
        assert isinstance(calc_adx(ohlcv, period=14), pd.Series)

    def test_range_0_to_100(self, ohlcv):
        from engine.indicators import calc_adx
        valid = calc_adx(ohlcv, period=14).dropna()
        assert (valid >= 0).all() and (valid <= 100).all()


class TestCalcMaSlope:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_ma_slope
        assert isinstance(calc_ma_slope(ohlcv), pd.Series)

    def test_leading_nan(self, ohlcv):
        from engine.indicators import calc_ma_slope
        # ma_period=20 + shift of slope_window=5 → first 24 rows NaN
        assert calc_ma_slope(ohlcv, ma_period=20, slope_window=5).iloc[:24].isna().all()


class TestCalcVrMean:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_vr_mean
        assert isinstance(calc_vr_mean(ohlcv), pd.Series)


class TestCalcPriceRangePct:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_price_range_pct
        assert isinstance(calc_price_range_pct(ohlcv, window=20), pd.Series)

    def test_non_negative(self, ohlcv):
        from engine.indicators import calc_price_range_pct
        assert (calc_price_range_pct(ohlcv, window=20).dropna() >= 0).all()


class TestCalcCloseVsMa:
    def test_returns_series(self, ohlcv):
        from engine.indicators import calc_close_vs_ma
        assert isinstance(calc_close_vs_ma(ohlcv, period=20), pd.Series)


class TestCalcWeeklyTrend:
    def test_insufficient_data_soft_pass(self, ohlcv):
        from engine.indicators import calc_weekly_trend
        passes, reason = calc_weekly_trend(ohlcv)   # 40 bars < 100
        assert passes is True and 'insufficient' in reason

    def test_uptrend_returns_bool_and_str(self):
        from engine.indicators import calc_weekly_trend
        n = 150
        close = pd.Series(range(1000, 1000 + n), dtype=float)
        df = pd.DataFrame({
            'date':  pd.date_range('2024-01-01', periods=n),
            'close': close,
        })
        passes, reason = calc_weekly_trend(df)
        assert isinstance(passes, bool) and isinstance(reason, str)


class TestWarmupMetadata:
    def test_calc_atr_default(self):
        from engine.indicators import calc_atr
        assert calc_atr.warmup_bars() == 14

    def test_calc_atr_custom(self):
        from engine.indicators import calc_atr
        assert calc_atr.warmup_bars(period=7) == 7

    def test_calc_adx_default(self):
        from engine.indicators import calc_adx
        assert calc_adx.warmup_bars() == 28

    def test_calc_vwap_default(self):
        from engine.indicators import calc_vwap
        assert calc_vwap.warmup_bars() == 60

    def test_get_warmup_returns_max(self):
        from engine.indicators import get_warmup, calc_atr, calc_adx, calc_vwap
        assert get_warmup([calc_atr, calc_adx, calc_vwap]) == 60

    def test_get_warmup_empty(self):
        from engine.indicators import get_warmup
        assert get_warmup([]) == 0
