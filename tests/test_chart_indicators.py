import pandas as pd
import numpy as np
from engine.chart_indicators import (
    volume_profile, fair_value_gaps, support_resistance, detect_patterns)


def _df(rows):
    """rows: list of (date, o, h, l, c, v)"""
    idx = pd.to_datetime([r[0] for r in rows])
    return pd.DataFrame(
        {'open': [r[1] for r in rows], 'high': [r[2] for r in rows],
         'low': [r[3] for r in rows], 'close': [r[4] for r in rows],
         'volume': [r[5] for r in rows]}, index=idx)


def test_volume_profile_poc_at_highest_volume_band():
    # Two bars hug price 100 with big volume, one bar at 110 with tiny volume.
    df = _df([
        ('2026-01-01', 99, 101, 99, 100, 1000),
        ('2026-01-02', 99, 101, 99, 100, 1000),
        ('2026-01-03', 109, 111, 109, 110, 10),
    ])
    vp = volume_profile(df, bins=12)
    assert set(vp.keys()) == {'poc', 'vah', 'val', 'rows'}
    assert abs(vp['poc'] - 100) < 2          # POC near 100
    assert vp['val'] <= vp['poc'] <= vp['vah']
    assert len(vp['rows']) == 12
    assert all('price' in r and 'volume' in r for r in vp['rows'])


def test_fair_value_gaps_detects_bull_and_bear():
    # Bull FVG: bar3.low (106) > bar1.high (102)  -> gap 102..106 at bar2/3
    # Bear FVG: bar3.high (94) < bar1.low (98)    -> gap 94..98
    bull = _df([
        ('2026-01-01', 100, 102, 99, 101, 100),
        ('2026-01-02', 103, 109, 103, 108, 100),
        ('2026-01-03', 107, 110, 106, 109, 100),
    ])
    gaps = fair_value_gaps(bull)
    assert any(g['type'] == 'bull' and g['bottom'] == 102 and g['top'] == 106 for g in gaps)

    bear = _df([
        ('2026-01-01', 100, 101, 98, 99, 100),
        ('2026-01-02', 95, 96, 90, 91, 100),
        ('2026-01-03', 93, 94, 90, 92, 100),
    ])
    gaps2 = fair_value_gaps(bear)
    assert any(g['type'] == 'bear' and g['bottom'] == 94 and g['top'] == 98 for g in gaps2)


def test_support_resistance_finds_pivots():
    # Build a zig-zag: clear swing high at 120, clear swing low at 80.
    rows = []
    prices = [100, 105, 120, 108, 95, 80, 92, 110, 100, 90]
    for i, p in enumerate(prices, 1):
        d = f'2026-01-{i:02d}'
        rows.append((d, p, p + 2, p - 2, p, 100))
    df = _df(rows)
    sr = support_resistance(df, lookback=1, max_levels=6)
    assert set(sr.keys()) == {'support', 'resistance'}
    # swing high 120 -> resistance near 122 (high = p+2); swing low 80 -> support near 78
    assert any(abs(r - 122) < 3 for r in sr['resistance'])
    assert any(abs(s - 78) < 3 for s in sr['support'])


def test_detect_patterns_bullish_engulfing_and_doji():
    df = _df([
        ('2026-01-01', 100, 100.5, 95, 96, 100),    # down candle
        ('2026-01-02', 95, 103, 94.5, 102, 100),    # bullish engulfing of prev body
        ('2026-01-03', 100, 101, 99, 100.05, 100),  # doji (open~close)
    ])
    pats = detect_patterns(df)
    kinds = {(p['date'], p['pattern']) for p in pats}
    assert ('2026-01-02', 'bullish_engulfing') in kinds
    assert ('2026-01-03', 'doji') in kinds
    assert all(p['dir'] in ('bull', 'bear', 'neutral') for p in pats)
