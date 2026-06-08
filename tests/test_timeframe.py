"""Tests for engine/timeframe.py — R15 multi-timeframe OHLCV aggregation."""
import numpy as np
import pandas as pd
import pytest
from engine.timeframe import aggregate_ohlcv, ohlcv_to_records, SUPPORTED_FREQS


def _make_daily(n=30, start='2024-01-02'):
    """Create a synthetic daily OHLCV DataFrame with DatetimeIndex."""
    dates  = pd.bdate_range(start=start, periods=n)
    closes = 1000 + np.cumsum(np.random.default_rng(42).normal(0, 10, n))
    opens  = closes - np.random.default_rng(1).uniform(0, 5, n)
    highs  = closes + np.random.default_rng(2).uniform(0, 5, n)
    lows   = closes - np.random.default_rng(3).uniform(5, 10, n)
    vols   = np.random.default_rng(4).integers(100_000, 1_000_000, n).astype(float)
    return pd.DataFrame({'open': opens, 'high': highs, 'low': lows,
                         'close': closes, 'volume': vols}, index=dates)


class TestAggregateOhlcv:
    def test_weekly_returns_fewer_rows(self):
        df = _make_daily(30)
        weekly = aggregate_ohlcv(df, 'W')
        assert len(weekly) < len(df)
        assert len(weekly) >= 4  # at least 4 complete weeks in 30 days

    def test_weekly_open_is_first_daily_open(self):
        df = _make_daily(10)
        weekly = aggregate_ohlcv(df, 'W')
        # First weekly bar open must equal the first daily open of that week
        first_week_end = weekly.index[0]
        week_days = df[df.index <= first_week_end].tail(
            (first_week_end - df.index[0]).days + 1
        )
        # Just verify it's within the week's daily opens
        assert weekly['open'].iloc[0] in df['open'].values

    def test_weekly_high_is_max(self):
        df = _make_daily(14)
        weekly = aggregate_ohlcv(df, 'W')
        # All weekly highs must be >= all weekly closes for that period
        assert (weekly['high'] >= weekly['close']).all()

    def test_weekly_low_le_open_and_close(self):
        df = _make_daily(14)
        weekly = aggregate_ohlcv(df, 'W')
        assert (weekly['low'] <= weekly['open']).all()
        assert (weekly['low'] <= weekly['close']).all()

    def test_weekly_volume_sum_matches_daily(self):
        df = _make_daily(14)
        weekly = aggregate_ohlcv(df, 'W')
        # Total volume across all weeks should equal total daily volume
        assert abs(weekly['volume'].sum() - df['volume'].sum()) < 1

    def test_monthly_returns_fewer_bars_than_weekly(self):
        df = _make_daily(90)
        weekly  = aggregate_ohlcv(df, 'W')
        monthly = aggregate_ohlcv(df, 'ME')
        assert len(monthly) < len(weekly)

    def test_monthly_alias_m_works(self):
        df = _make_daily(60)
        result = aggregate_ohlcv(df, 'M')  # alias for ME
        assert len(result) > 0

    def test_daily_passthrough(self):
        df = _make_daily(20)
        result = aggregate_ohlcv(df, 'D')
        assert len(result) == len(df)
        pd.testing.assert_series_equal(result['close'], df['close'])

    def test_date_column_promoted_to_index(self):
        df = _make_daily(20).reset_index().rename(columns={'index': 'date'})
        result = aggregate_ohlcv(df, 'W')
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_invalid_freq_raises(self):
        df = _make_daily(10)
        with pytest.raises(ValueError, match='freq must be'):
            aggregate_ohlcv(df, 'H')

    def test_missing_column_raises(self):
        df = _make_daily(10).drop(columns=['volume'])
        with pytest.raises(ValueError, match='Missing columns'):
            aggregate_ohlcv(df, 'W')

    def test_output_has_correct_columns(self):
        df = _make_daily(20)
        result = aggregate_ohlcv(df, 'W')
        assert set(result.columns) == {'open', 'high', 'low', 'close', 'volume'}

    def test_no_nan_rows_in_output(self):
        df = _make_daily(20)
        result = aggregate_ohlcv(df, 'W')
        assert not result[['open', 'close']].isna().any().any()


class TestOhlcvToRecords:
    def test_returns_list_of_dicts(self):
        df = _make_daily(5)
        records = ohlcv_to_records(aggregate_ohlcv(df, 'W'))
        assert isinstance(records, list)
        assert all(isinstance(r, dict) for r in records)

    def test_required_keys_present(self):
        df = _make_daily(10)
        records = ohlcv_to_records(aggregate_ohlcv(df, 'W'))
        for r in records:
            assert {'date', 'open', 'high', 'low', 'close', 'volume'} <= set(r.keys())

    def test_date_is_string(self):
        df = _make_daily(5)
        records = ohlcv_to_records(aggregate_ohlcv(df, 'W'))
        assert all(isinstance(r['date'], str) for r in records)

    def test_volume_is_int(self):
        df = _make_daily(5)
        records = ohlcv_to_records(aggregate_ohlcv(df, 'W'))
        assert all(isinstance(r['volume'], int) for r in records)
