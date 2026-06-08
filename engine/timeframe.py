"""Multi-timeframe OHLCV aggregation (R15).

Converts a daily OHLCV DataFrame into weekly or monthly bars using
pandas DatetimeIndex resample — same approach used by calc_weekly_trend
but for full OHLCV (open=first, high=max, low=min, close=last, volume=sum).

Supported freq codes:
  'D'  — daily   (pass-through, no resampling)
  'W'  — weekly  (week ending Friday; pandas default)
  'ME' — monthly end (pandas >= 2.2 alias for 'M')

Column requirements: open, high, low, close, volume (plus a date index
or a 'date' column that will be promoted to index).
"""

import pandas as pd
from typing import Literal

SUPPORTED_FREQS = frozenset({'D', 'W', 'ME', 'M'})


def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with a DatetimeIndex; promotes 'date' column if needed."""
    if isinstance(df.index, pd.DatetimeIndex):
        return df
    if 'date' in df.columns:
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        return df.set_index('date')
    raise ValueError("DataFrame must have a DatetimeIndex or a 'date' column")


def aggregate_ohlcv(
    df: pd.DataFrame,
    freq: str = 'W',
) -> pd.DataFrame:
    """Resample a daily OHLCV DataFrame to the given frequency.

    Args:
        df:   Daily OHLCV DataFrame.
        freq: Pandas offset alias — 'D', 'W', 'ME' (monthly), or 'M' (alias for 'ME').

    Returns:
        Resampled DataFrame with columns: open, high, low, close, volume.
        Index is DatetimeIndex at period-end dates.
        Rows with all-NaN OHLCV are dropped.
    """
    freq = freq.upper()
    if freq == 'M':
        freq = 'ME'  # pandas 2.2+ requires explicit period-end alias
    if freq not in SUPPORTED_FREQS:
        raise ValueError(f"freq must be one of {sorted(SUPPORTED_FREQS)}, got {freq!r}")

    df = _ensure_datetime_index(df)

    required = {'open', 'high', 'low', 'close', 'volume'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if freq == 'D':
        return df[['open', 'high', 'low', 'close', 'volume']].copy()

    resampled = df.resample(freq).agg(
        open=('open',   'first'),
        high=('high',   'max'),
        low=('low',     'min'),
        close=('close', 'last'),
        volume=('volume', 'sum'),
    )
    # Drop weeks/months where the market was closed (no data)
    return resampled.dropna(subset=['open', 'close'])


def ohlcv_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert an OHLCV DataFrame (with DatetimeIndex) to JSON-safe records."""
    records = []
    for ts, row in df.iterrows():
        records.append({
            'date':   ts.strftime('%Y-%m-%d'),
            'open':   round(float(row['open']),   2) if pd.notna(row['open'])   else None,
            'high':   round(float(row['high']),   2) if pd.notna(row['high'])   else None,
            'low':    round(float(row['low']),    2) if pd.notna(row['low'])    else None,
            'close':  round(float(row['close']),  2) if pd.notna(row['close'])  else None,
            'volume': int(row['volume'])              if pd.notna(row['volume']) else None,
        })
    return records
