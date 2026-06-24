import pandas as pd
import numpy as np
from engine.smc import detect_liquidity_sweep, calc_sweep_signal


def _df(rows):
    """rows: list of (date, open, high, low, close, volume)."""
    return pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])


def test_detect_bullish_pdl_sweep():
    # Bar 3's PDL is bar 2's low (105). Low 95 < 105, wick=(105-95)/(108-95)=0.77 >= 0.3,
    # close 106 > 105 -> bullish sweep signal=1.
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),
        ('2026-05-02', 106, 109, 105, 107, 1_000_000),
        ('2026-05-03', 106, 108,  95, 106, 1_500_000),
    ])
    sweeps = detect_liquidity_sweep(df, use_weekly=False)
    assert not sweeps.empty
    bull = sweeps[sweeps['signal'] == 1]
    assert len(bull) == 1
    assert bull.iloc[0]['sweep_type'] == 'pdl'
    assert bull.iloc[0]['direction'] == 'bullish'
    assert bull.iloc[0]['wick_pct'] >= 0.3


def test_no_sweep_when_wick_too_small():
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),
        ('2026-05-02', 106, 109, 104, 107, 1_000_000),  # PDL for bar3 = 104
        ('2026-05-03', 106, 120, 103, 119, 1_500_000),  # low 103 < 104 but wick tiny
    ])
    sweeps = detect_liquidity_sweep(df, use_weekly=False)
    assert sweeps[sweeps['signal'] == 1].empty


def test_calc_sweep_signal_marks_bullish_bar():
    df = _df([
        ('2026-05-01', 105, 110, 100, 108, 1_000_000),
        ('2026-05-02', 106, 109, 105, 107, 1_000_000),
        ('2026-05-03', 106, 108,  95, 106, 1_500_000),
    ])
    sig = calc_sweep_signal(df)
    assert sig.iloc[2] == True
    assert sig.iloc[0] == False
