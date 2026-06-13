"""Tests for R16 — session-level indicator cache in engine/indicators.py."""
import numpy as np
import pandas as pd
import pytest

from engine.indicators import (
    _INDICATOR_CACHE,
    _df_key,
    clear_indicator_cache,
    calc_atr,
    calc_vwap,
    calc_vol_ratio,
    calc_weekly_trend,
)


def _make_df(n=60, seed=0):
    rng = np.random.default_rng(seed)
    closes = 1000 + np.cumsum(rng.normal(0, 10, n))
    opens  = closes - rng.uniform(0, 5, n)
    highs  = closes + rng.uniform(0, 5, n)
    lows   = closes - rng.uniform(5, 10, n)
    vols   = rng.integers(100_000, 1_000_000, n).astype(float)
    dates  = pd.bdate_range('2024-01-02', periods=n)
    return pd.DataFrame({'open': opens, 'high': highs, 'low': lows,
                         'close': closes, 'volume': vols}, index=dates)


class TestClearIndicatorCache:
    def setup_method(self):
        clear_indicator_cache()

    def test_clear_returns_count(self):
        df = _make_df()
        calc_atr(df)
        n = clear_indicator_cache()
        assert n >= 1

    def test_cache_empty_after_clear(self):
        df = _make_df()
        calc_atr(df)
        clear_indicator_cache()
        assert len(_INDICATOR_CACHE) == 0

    def test_clear_on_empty_returns_zero(self):
        clear_indicator_cache()
        assert clear_indicator_cache() == 0


class TestCalcAtrCache:
    def setup_method(self):
        clear_indicator_cache()

    def test_result_cached_after_first_call(self):
        df = _make_df()
        calc_atr(df, 14)
        assert ('atr', _df_key(df), 14) in _INDICATOR_CACHE

    def test_second_call_returns_same_object(self):
        df = _make_df()
        r1 = calc_atr(df, 14)
        r2 = calc_atr(df, 14)
        assert r1 is r2  # identical object — cache hit

    def test_different_periods_cached_separately(self):
        df = _make_df()
        calc_atr(df, 14)
        calc_atr(df, 7)
        assert ('atr', _df_key(df), 14) in _INDICATOR_CACHE
        assert ('atr', _df_key(df), 7)  in _INDICATOR_CACHE

    def test_different_dfs_cached_separately(self):
        df1, df2 = _make_df(seed=0), _make_df(seed=1)
        calc_atr(df1, 14)
        calc_atr(df2, 14)
        assert ('atr', _df_key(df1), 14) in _INDICATOR_CACHE
        assert ('atr', _df_key(df2), 14) in _INDICATOR_CACHE

    def test_cached_value_matches_fresh(self):
        df = _make_df()
        cached = calc_atr(df, 14)
        clear_indicator_cache()
        fresh = calc_atr(df, 14)
        pd.testing.assert_series_equal(cached, fresh)


class TestCalcVolRatioCache:
    def setup_method(self):
        clear_indicator_cache()

    def test_result_cached(self):
        df = _make_df()
        calc_vol_ratio(df, 20)
        assert ('vol_ratio', _df_key(df), 20) in _INDICATOR_CACHE

    def test_second_call_is_cache_hit(self):
        df = _make_df()
        r1 = calc_vol_ratio(df, 20)
        r2 = calc_vol_ratio(df, 20)
        assert r1 is r2

    def test_cached_matches_fresh(self):
        df = _make_df()
        cached = calc_vol_ratio(df, 20)
        clear_indicator_cache()
        fresh = calc_vol_ratio(df, 20)
        pd.testing.assert_series_equal(cached, fresh)


class TestCalcVwapCache:
    def setup_method(self):
        clear_indicator_cache()

    def test_result_cached(self):
        df = _make_df()
        calc_vwap(df, 60)
        assert ('vwap', _df_key(df), 60) in _INDICATOR_CACHE

    def test_second_call_is_cache_hit(self):
        df = _make_df()
        r1 = calc_vwap(df, 60)
        r2 = calc_vwap(df, 60)
        assert r1 is r2


class TestCalcWeeklyTrendCache:
    def setup_method(self):
        clear_indicator_cache()

    def test_result_cached(self):
        df = _make_df(n=150)
        calc_weekly_trend(df)
        assert ('weekly_trend', _df_key(df)) in _INDICATOR_CACHE

    def test_second_call_is_cache_hit(self):
        df = _make_df(n=150)
        r1 = calc_weekly_trend(df)
        r2 = calc_weekly_trend(df)
        assert r1 is r2

    def test_short_df_result_cached(self):
        df = _make_df(n=50)  # < 100 bars → soft-pass
        result = calc_weekly_trend(df)
        assert result == (True, 'W:insufficient_data')
        assert ('weekly_trend', _df_key(df)) in _INDICATOR_CACHE

    def test_cached_tuple_matches_fresh(self):
        df = _make_df(n=150)
        cached = calc_weekly_trend(df)
        clear_indicator_cache()
        fresh = calc_weekly_trend(df)
        assert cached == fresh
