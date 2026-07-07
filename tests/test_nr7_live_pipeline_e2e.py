"""Phase 5 fire drill (spec 2026-07-08): drive a synthetic ticker through the
REAL NR7 pipeline — registry → regime → checker → gates → open_trade → monitor
exit — proving the path stays connected (audit C-1 regression guard).

Honesty contract: every gate passes on MERIT (data crafted to satisfy it);
mocks exist only at network seams (flow fetch, agent firm, telegram)."""
import json
import sqlite3

import numpy as np
import pandas as pd
import pytest
import yaml


def _drill_df(n=260, base=1000.0):
    """Uptrend satisfying detect_regime→BULL (ADX>25, MA-slope>+1%) and
    check_trend→UPTREND, ending with an NR7 setup:
    bar[-2] = narrowest range of trailing 7 with volume >= 0.8x avg5;
    bar[-1] = opens above bar[-2] high (breakout) with volume spike."""
    rng = np.random.default_rng(42)
    closes = base * np.cumprod(1 + 0.004 + rng.normal(0, 0.002, n))
    o = closes * 0.998
    h = closes * 1.012
    l = closes * 0.988
    v = np.full(n, 1_000_000.0)
    df = pd.DataFrame({
        'date': pd.date_range('2025-07-01', periods=n, freq='B').astype(str),
        'open': o, 'high': h, 'low': l, 'close': closes, 'volume': v})
    # bar[-2]: NR7 — squeeze the range to clearly narrowest of trailing 7
    i = n - 2
    c = df.loc[i, 'close']
    df.loc[i, 'high'] = c * 1.001
    df.loc[i, 'low'] = c * 0.999
    df.loc[i, 'open'] = c * 0.9995
    df.loc[i, 'volume'] = 1_000_000.0          # >= 0.8x avg5
    # bar[-1]: breakout — opens above NR7 high, closes higher, volume spike
    j = n - 1
    df.loc[j, 'open'] = c * 1.004
    df.loc[j, 'close'] = c * 1.012
    df.loc[j, 'high'] = c * 1.015
    df.loc[j, 'low'] = c * 1.002
    df.loc[j, 'volume'] = 2_500_000.0
    return df


def test_fixture_regime_is_bull_band():
    from engine.regime_filter import detect_regime
    from engine.indicators import calc_adx
    df = _drill_df()
    assert detect_regime(df) == 'BULL'
    assert float(calc_adx(df, 14).iloc[-1]) > 25


def test_fixture_fires_nr7_checker():
    from engine.strategies import check_nr7_signal
    sig = check_nr7_signal(_drill_df())
    assert sig['has_signal'] is True, sig.get('reason')
    assert sig['details'].get('price') or sig['details'].get('entry')
