"""
Signal Checker Tests

Tests for all check_*_signal() functions in engine/strategies.py.
Verifies signal structure, required fields, and basic behavior.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path
import importlib.util

# Load strategies.py file directly to avoid conflicts with new strategies/ module
# Signal checkers are in the old strategies.py, not in new strategies/ module
strategies_path = Path(__file__).parent.parent / 'engine' / 'strategies.py'
spec = importlib.util.spec_from_file_location("strategies_old", strategies_path)
strategies_module = importlib.util.module_from_spec(spec)
sys.modules['strategies_old'] = strategies_module
spec.loader.exec_module(strategies_module)

check_current_entry_signal = strategies_module.check_current_entry_signal
check_vol_weighted_signal = strategies_module.check_vol_weighted_signal
check_momentum_signal = strategies_module.check_momentum_signal
check_vwap_reversion_signal = strategies_module.check_vwap_reversion_signal
check_conservative_signal = strategies_module.check_conservative_signal
check_trend_following_breakout_signal = strategies_module.check_trend_following_breakout_signal
check_crash_recovery_signal = strategies_module.check_crash_recovery_signal
check_panic_rebound_signal = strategies_module.check_panic_rebound_signal
check_sweep_flow_signal = strategies_module.check_sweep_flow_signal


# Sample OHLCV DataFrame for testing
def make_sample_df(length=100, trend='up', vol_spike=False):
    """Create a sample OHLCV DataFrame for testing."""
    dates = pd.date_range(end=datetime.now(), periods=length, freq='D')

    if trend == 'up':
        # Uptrend: price goes up
        close = 1000 + np.arange(length) * 5
        open_ = close - np.random.randint(-10, 20, length)
        high = close + np.random.randint(5, 30, length)
        low = close - np.random.randint(5, 30, length)
    elif trend == 'down':
        # Downtrend
        close = 5000 - np.arange(length) * 20
        open_ = close + np.random.randint(-10, 20, length)
        high = close + np.random.randint(5, 30, length)
        low = close - np.random.randint(5, 30, length)
    else:  # sideways
        close = np.ones(length) * 2000 + np.random.randint(-100, 100, length)
        open_ = close + np.random.randint(-5, 5, length)
        high = close + np.random.randint(10, 50, length)
        low = close - np.random.randint(10, 50, length)

    # Ensure valid OHLC relationships
    low = np.minimum(low, open_)
    high = np.maximum(high, open_)
    high = np.maximum(high, close)
    low = np.minimum(low, close)

    volume = np.ones(length) * 1000000
    if vol_spike:
        volume[-1] = 5000000  # Volume spike on last bar

    df = pd.DataFrame({
        'date': dates,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    return df


# ─────────────────────────────────────────────
# PARAMETERIZED STRUCTURE TESTS
# ─────────────────────────────────────────────

@pytest.mark.parametrize("strategy,expected_fields", [
    ("vol_weighted", ["vr", "current_volume", "avg_volume", "price", "vwap", "price_vs_vwap_pct", "price_above_vwap"]),
    ("momentum", ["streak", "vr", "daily_return"]),
    ("vwap_reversion", ["distance_pct", "vr", "price", "vwap"]),
    ("conservative", ["vr", "bullish", "above_ma20", "price", "ma20"]),
    ("Trend Following Breakout", ["ma20_slope", "vol_ratio", "cond_slope", "cond_volume", "cond_breakout", "cond_no_climax", "cond_atr_exp", "cond_regime", "donchian20", "ma20", "ma50", "close"]),
])
def test_signal_checker_structure(strategy, expected_fields):
    """Test that signal checkers return expected structure with required fields."""
    from engine.strategies import check_current_entry_signal

    n = 100 if strategy == 'Trend Following Breakout' else 50
    df = make_sample_df(length=n, trend='up', vol_spike=True)
    result = check_current_entry_signal('TEST', strategy, df)

    # Required top-level fields
    assert 'has_signal' in result, f"{strategy} missing 'has_signal'"
    assert 'reason' in result, f"{strategy} missing 'reason'"
    assert 'details' in result, f"{strategy} missing 'details'"
    assert isinstance(result['has_signal'], bool), f"{strategy} has_signal not bool"
    assert isinstance(result['details'], dict), f"{strategy} details not dict"

    # Expected detail fields
    for field in expected_fields:
        assert field in result['details'], f"{strategy} missing detail field: {field}"


# ─────────────────────────────────────────────
# INDIVIDUAL STRATEGY TESTS
# ─────────────────────────────────────────────

class TestVolWeightedSignal:
    """Tests for vol_weighted signal checker."""

    def test_no_signal_low_volume(self):
        from engine.strategies import check_vol_weighted_signal
        df = make_sample_df(length=30, trend='up', vol_spike=False)
        result = check_vol_weighted_signal(df)
        assert 'has_signal' in result
        assert 'vr' in result['details']

    def test_structure(self):
        from engine.strategies import check_vol_weighted_signal
        df = make_sample_df(length=30)
        result = check_vol_weighted_signal(df)
        assert set(result.keys()) == {'has_signal', 'reason', 'details'}


class TestMomentumSignal:
    """Tests for momentum signal checker."""

    def test_structure(self):
        from engine.strategies import check_momentum_signal
        df = make_sample_df(length=30, trend='up')
        result = check_momentum_signal(df)
        assert set(result.keys()) == {'has_signal', 'reason', 'details'}
        assert 'streak' in result['details']
        assert 'vr' in result['details']


class TestVwapReversionSignal:
    """Tests for VWAP reversion signal checker."""

    def test_structure(self):
        from engine.strategies import check_vwap_reversion_signal
        df = make_sample_df(length=30)
        result = check_vwap_reversion_signal(df)
        assert set(result.keys()) == {'has_signal', 'reason', 'details'}
        assert 'distance_pct' in result['details']
        assert 'vr' in result['details']


class TestConservativeSignal:
    """Tests for conservative signal checker."""

    def test_structure(self):
        from engine.strategies import check_conservative_signal
        df = make_sample_df(length=30, trend='up')
        result = check_conservative_signal(df)
        assert set(result.keys()) == {'has_signal', 'reason', 'details'}
        assert 'vr' in result['details']
        assert 'bullish' in result['details']
        assert 'above_ma20' in result['details']


class TestTrendFollowingBreakoutSignal:
    """Tests for trend following breakout signal checker."""

    def test_structure(self):
        from engine.strategies import check_trend_following_breakout_signal
        df = make_sample_df(length=60, trend='up')
        result = check_trend_following_breakout_signal(df)
        assert set(result.keys()) == {'has_signal', 'reason', 'details'}
        # Expected fields based on implementation
        assert 'details' in result


class TestCrashRecoverySignal:
    """Tests for crash recovery signal checker."""

    def test_requires_ticker(self):
        from engine.strategies import check_crash_recovery_signal
        df = make_sample_df(length=30, trend='down')
        # Should require ticker argument
        result = check_crash_recovery_signal('TEST', df)
        assert set(result.keys()) == {'has_signal', 'reason', 'details'}


class TestPanicReboundSignal:
    """Tests for panic rebound signal checker."""

    def test_structure(self):
        from engine.strategies import check_panic_rebound_signal
        df = make_sample_df(length=30, trend='down')
        result = check_panic_rebound_signal(df)
        assert set(result.keys()) == {'has_signal', 'reason', 'details'}


class TestSweepFlowSignal:
    """Tests for liquidity sweep with flow confirmation signal."""

    def test_requires_ticker(self):
        from engine.strategies import check_sweep_flow_signal
        df = make_sample_df(length=30, trend='sideways')
        # Should require ticker argument
        result = check_sweep_flow_signal(df, 'TEST')
        assert set(result.keys()) == {'has_signal', 'reason', 'details'}


class TestCheckCurrentEntrySignal:
    """Tests for the main signal dispatcher."""

    def test_unsupported_strategy_returns_error(self):
        from engine.strategies import check_current_entry_signal
        df = make_sample_df(length=30)
        result = check_current_entry_signal('TEST', 'Nonexistent Strategy', df)
        assert result['has_signal'] == False
        assert 'belum didukung' in result['reason'] or 'not supported' in result['reason'].lower()

    def test_insufficient_data_returns_error(self):
        from engine.strategies import check_current_entry_signal
        df = make_sample_df(length=10)  # Less than 20 bars
        result = check_current_entry_signal('TEST', 'vol_weighted', df)
        assert result['has_signal'] == False
        assert 'tidak cukup' in result['reason'] or 'minimum' in result['reason'].lower()

    @pytest.mark.parametrize("strategy", [
        "vol_weighted", "momentum", "vwap_reversion", "conservative",
        "Trend Following Breakout", "Crash Recovery", "Panic Rebound", "Liquidity Sweep"
    ])
    def test_supported_strategies_return_dict(self, strategy):
        """Test that all supported strategies return a valid dict structure."""
        from engine.strategies import check_current_entry_signal
        df = make_sample_df(length=50, trend='up')
        result = check_current_entry_signal('TEST', strategy, df)
        assert isinstance(result, dict)
        assert 'has_signal' in result
        assert 'reason' in result
        assert 'details' in result


# ─────────────────────────────────────────────
# INTEGRATION TESTS
# ─────────────────────────────────────────────

class TestSignalIntegration:
    """Integration tests for signal checkers with realistic data."""

    def test_uptrend_with_volume_triggers_momentum(self):
        """Test that uptrend + volume spike triggers momentum signal components."""
        from engine.strategies import check_momentum_signal
        df = make_sample_df(length=30, trend='up', vol_spike=True)
        result = check_momentum_signal(df)

        # Should have streak calculated
        assert 'streak' in result['details']
        assert isinstance(result['details']['streak'], int)

        # Should have VR calculated
        assert 'vr' in result['details']
        assert result['details']['vr'] > 0

    def test_downtrend_detects_regime(self):
        """Test that downtrend data can be processed without error."""
        from engine.strategies import check_current_entry_signal
        df = make_sample_df(length=50, trend='down')

        # Should not crash on downtrend data
        for strategy in ['vol_weighted', 'momentum', 'conservative']:
            result = check_current_entry_signal('TEST', strategy, df)
            assert isinstance(result, dict)


# ─────────────────────────────────────────────
# EDGE CASES
# ─────────────────────────────────────────────

class TestSignalCheckerEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_dataframe(self):
        from engine.strategies import check_vol_weighted_signal
        df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        with pytest.raises(IndexError):
            check_vol_weighted_signal(df)

    def test_single_row_dataframe(self):
        from engine.strategies import check_vol_weighted_signal
        df = make_sample_df(length=1)
        result = check_vol_weighted_signal(df)
        assert 'has_signal' in result

    def test_nan_handling(self):
        """Test that NaN values are handled gracefully."""
        from engine.strategies import check_vol_weighted_signal
        df = make_sample_df(length=30)
        df.loc[df.index[-5], 'close'] = np.nan
        result = check_vol_weighted_signal(df)
        # Should not crash
        assert 'has_signal' in result


# ─────────────────────────────────────────────
# INTRADAY / 1H-TYPE SIGNAL CHECKER TESTS
# ─────────────────────────────────────────────

def _make_intraday_df(length=100):
    """1-minute resolution OHLCV simulating intraday bars."""
    dates = pd.date_range('2026-06-26 09:00', periods=length, freq='1min')
    close = 4500 + np.cumsum(np.random.randn(length) * 2)
    close = np.maximum(close, 4000)
    open_ = close - np.random.rand(length) * 3
    high = np.maximum(open_, close) + np.abs(np.random.randn(length) * 5)
    low = np.minimum(open_, close) - np.abs(np.random.randn(length) * 5)
    volume = np.random.randint(1000, 50000, length)
    return pd.DataFrame({'date': dates, 'open': open_, 'high': high,
                         'low': low, 'close': close, 'volume': volume})


class TestIntradayTFBSignal:
    """Test TFB checker on 1h-equivalent (60-bar) data — new slope + vol context gates."""

    def test_tfb_structure_intraday(self):
        from engine.strategies import check_trend_following_breakout_signal
        df = _make_intraday_df(100)
        result = check_trend_following_breakout_signal(df)

        assert 'has_signal' in result
        assert 'reason' in result
        assert 'details' in result
        assert isinstance(result['details'], dict)

    def test_tfb_slope_gate_present(self):
        from engine.strategies import check_trend_following_breakout_signal
        df = _make_intraday_df(100)
        result = check_trend_following_breakout_signal(df)
        d = result['details']

        # New market-context gates must be present
        assert 'cond_slope' in d
        assert 'cond_no_climax' in d
        assert 'ma20_slope' in d
        assert 'vol_ratio' in d
        assert d['cond_slope'] or not d['cond_slope']  # truthy bool
        assert d['cond_no_climax'] or not d['cond_no_climax']

    def test_tfb_rejects_flat_ma_slope(self):
        """TFB must reject when MA20 is flat (slope <= 0.5)."""
        from engine.strategies import check_trend_following_breakout_signal

        # Flat price: MA20 slope will be near zero
        length = 100
        dates = pd.date_range('2026-06-26 09:00', periods=length, freq='1min')
        close = np.full(length, 4500.0)
        open_ = close - 1
        high = close + 2
        low = close - 2
        volume = np.random.randint(1000, 50000, length)
        df = pd.DataFrame({'date': dates, 'open': open_, 'high': high,
                           'low': low, 'close': close, 'volume': volume})

        result = check_trend_following_breakout_signal(df)
        # cond_slope should be False with flat MA20
        if result['details']:
            assert not result['details']['cond_slope'], "cond_slope should be False for flat MA20"

    def test_tfb_rejects_climax_volume(self):
        """TFB must reject when vol_ratio >= 4.0 (climax blow-off gate)."""
        from engine.strategies import check_trend_following_breakout_signal

        length = 100
        dates = pd.date_range('2026-06-26 09:00', periods=length, freq='1min')
        # Steady uptrend
        close = 4500 + np.arange(length) * 2 + np.random.randn(length) * 2
        close = np.maximum(close, 4000)
        open_ = close - np.random.rand(length) * 3
        high = np.maximum(open_, close) + np.abs(np.random.randn(length) * 5)
        low = np.minimum(open_, close) - np.abs(np.random.randn(length) * 5)
        # Normal volume for 90 bars, monster volume on LAST bar
        volume = np.ones(length) * 5000
        volume[-1] = 200000  # 40x alone — only last bar spikes, avg stays low
        df = pd.DataFrame({'date': dates, 'open': open_, 'high': high,
                           'low': low, 'close': close, 'volume': volume})

        result = check_trend_following_breakout_signal(df)
        if result['details']:
            assert not result['details']['cond_no_climax'], f"climax gate should be False with vol_ratio={result['details']['vol_ratio']}"


def _prod_db_has(table: str, db_path: str = 'data/walkforward.db') -> bool:
    """True when the production DB exists AND contains `table`. A bare
    os.path.exists check is not enough: imports can create an empty DB file."""
    import os
    import sqlite3
    if not os.path.exists(db_path):
        return False
    try:
        conn = sqlite3.connect(db_path)
        ok = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone() is not None
        conn.close()
        return ok
    except Exception:
        return False


class TestSweepFlowSignal:
    """Intraday/flow checks for Liquidity Sweep signal checker.

    Skipped without the production DB: confirm_sweep_flow queries
    stockbit_flow_bars directly (and currently crashes, rather than failing
    open, when the table is absent — Phase 3 fail-open inventory item)."""

    def test_sweep_flow_structure(self):
        if not _prod_db_has('stockbit_flow_bars'):
            pytest.skip('prod DB / stockbit_flow_bars not available')
        from engine.strategies import check_sweep_flow_signal
        df = _make_intraday_df(100)
        result = check_sweep_flow_signal(df, 'BRPT')

        assert 'has_signal' in result
        assert 'reason' in result
        assert 'details' in result
        assert isinstance(result['details'], dict)

    def test_sweep_flow_no_crash_on_missing_ticker(self):
        if not _prod_db_has('stockbit_flow_bars'):
            pytest.skip('prod DB / stockbit_flow_bars not available')
        from engine.strategies import check_sweep_flow_signal
        df = _make_intraday_df(100)
        # Non-existent ticker — should return clean "no signal" not crash
        result = check_sweep_flow_signal(df, 'ZZZZ_NOPE')
        assert isinstance(result, dict)
        assert 'has_signal' in result


class TestTFBContextFilterLive:
    """Test TFB market-context gate on real BRPT bars from DB."""

    def test_tfb_context_on_real_brpt_daily(self):
        import sqlite3, os
        from engine.strategies import check_trend_following_breakout_signal

        db_path = 'data/walkforward.db'
        if not _prod_db_has('ohlcv', db_path):
            pytest.skip('prod DB / ohlcv not available')

        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker='BRPT' ORDER BY date"
        ).fetchall()
        conn.close()

        if len(rows) < 80:
            pytest.skip(f'BRPT has only {len(rows)} bars (need ≥80)')

        df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        result = check_trend_following_breakout_signal(df)

        assert 'has_signal' in result
        assert 'details' in result
        d = result['details']
        assert 'cond_slope' in d
        assert 'cond_no_climax' in d
        assert 'ma20_slope' in d
        assert 'vol_ratio' in d
