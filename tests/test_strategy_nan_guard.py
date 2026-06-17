"""NaN-safety guards for strategy numeric helpers.

Root cause: numeric guards using `<=` silently pass NaN (every comparison
with NaN is False), so NaN reaches int() and raises ValueError. These
tests reproduce both crash sites seen in the live scan log (2026-06-17):
  - lot_size()           int(risk_rp / risk_per_lot)
  - _get_poc_hvn()       int((row['low'] - price_min) / bucket_size)
"""
import numpy as np
import pandas as pd
from engine.strategies import lot_size, _get_poc_hvn


def test_lot_size_nan_price_does_not_crash():
    # NaN price defeats `risk_per_lot <= 0` guard -> int(NaN) crash.
    out = lot_size(50_000_000, float('nan'), 0.02, 0.05)
    assert isinstance(out, int) and out >= 1


def test_lot_size_nan_sl_pct_does_not_crash():
    out = lot_size(50_000_000, 1000.0, 0.02, float('nan'))
    assert isinstance(out, int) and out >= 1


def test_lot_size_valid_still_computes():
    # capital 50M, price 1000, risk 2% -> risk_rp 1,000,000;
    # risk_per_lot = 1000*100*0.05 = 5000 -> 200 lots, capped at 30%.
    out = lot_size(50_000_000, 1000.0, 0.02, 0.05)
    assert out >= 1


def _window(rows):
    """rows: list of (open, high, low, close, volume)."""
    return pd.DataFrame(rows, columns=['open', 'high', 'low', 'close', 'volume'])


def test_get_poc_hvn_all_nan_window_returns_none():
    nan = float('nan')
    df = _window([(nan, nan, nan, nan, nan) for _ in range(5)])
    poc, hvn = _get_poc_hvn(df)
    assert poc is None and hvn == []


def test_get_poc_hvn_single_nan_row_does_not_crash():
    # Valid rows give finite price_min/max, but one NaN bar hits int(NaN).
    nan = float('nan')
    rows = [(100, 102, 99, 101, 1000),
            (101, 103, 100, 102, 1200),
            (nan, nan, nan, nan, nan),     # degenerate bar
            (102, 104, 101, 103, 900)]
    df = _window(rows)
    poc, hvn = _get_poc_hvn(df)
    assert poc is not None and np.isfinite(poc)
