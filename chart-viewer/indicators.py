"""Server-side indicator computation (pandas / numpy only).

Every function returns plain Python lists of {"time": epoch_seconds, "value": float}
points (NaN/inf dropped) so the frontend can hand them straight to
lightweight-charts. `compute_all` bundles everything the UI can toggle.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

INTRADAY_TF = {"1m", "5m", "15m", "30m", "1h"}


def _series_points(series: pd.Series, times):
    """Pair a numeric series with epoch times, dropping NaN / inf."""
    out = []
    vals = series.to_numpy(dtype="float64")
    for t, v in zip(times, vals):
        if v is None or not math.isfinite(v):
            continue
        out.append({"time": int(t), "value": float(v)})
    return out


def _sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def _ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 (pure uptrend) RSI is 100.
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _macd(close: pd.Series):
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


def _bollinger(close: pd.Series, window: int = 20, mult: float = 2.0):
    mid = close.rolling(window).mean()
    std = close.rolling(window).std(ddof=0)
    return mid + mult * std, mid, mid - mult * std


def _vwap(h, l, c, v, index, intraday: bool) -> pd.Series:
    typical = (h + l + c) / 3.0
    tpv = typical * v
    if intraday:
        # Reset the VWAP anchor each session day.
        day = index.normalize()
        cum_tpv = tpv.groupby(day).cumsum()
        cum_v = v.groupby(day).cumsum()
    else:
        cum_tpv = tpv.cumsum()
        cum_v = v.cumsum()
    return cum_tpv / cum_v.replace(0.0, np.nan)


def _volume_profile(h, l, c, v, bins: int = 24, value_area: float = 0.70):
    """Histogram of volume by price; returns POC / VAH / VAL price levels."""
    lo = float(l.min())
    hi = float(h.max())
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        return None
    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    # Assign each bar's volume to the bin of its typical price.
    typical = ((h + l + c) / 3.0).to_numpy(dtype="float64")
    vol = v.to_numpy(dtype="float64")
    hist = np.zeros(bins, dtype="float64")
    idx = np.clip(np.digitize(typical, edges) - 1, 0, bins - 1)
    for i, vv in zip(idx, vol):
        if math.isfinite(vv):
            hist[i] += vv
    total = hist.sum()
    if total <= 0:
        return None
    poc_bin = int(hist.argmax())
    # Grow a value area outward from the POC until it holds `value_area` of volume.
    selected = {poc_bin}
    acc = hist[poc_bin]
    lo_i, hi_i = poc_bin, poc_bin
    while acc < total * value_area and (lo_i > 0 or hi_i < bins - 1):
        down = hist[lo_i - 1] if lo_i > 0 else -1.0
        up = hist[hi_i + 1] if hi_i < bins - 1 else -1.0
        if up >= down:
            hi_i += 1
            selected.add(hi_i)
            acc += hist[hi_i]
        else:
            lo_i -= 1
            selected.add(lo_i)
            acc += hist[lo_i]
    sel = sorted(selected)
    return {
        "poc": round(float(centers[poc_bin]), 4),
        "vah": round(float(centers[sel[-1]]), 4),
        "val": round(float(centers[sel[0]]), 4),
    }


def _fvg(o, h, l, c, times, limit: int = 40):
    """3-candle Fair Value Gaps (imbalances).

    Bullish: low[i] > high[i-2]  -> gap zone (high[i-2], low[i])
    Bearish: high[i] < low[i-2]  -> gap zone (high[i], low[i-2])
    Returns the most recent `limit` gaps.
    """
    hi = h.to_numpy(dtype="float64")
    lo = l.to_numpy(dtype="float64")
    out = []
    for i in range(2, len(hi)):
        if not (math.isfinite(hi[i]) and math.isfinite(lo[i]) and
                math.isfinite(hi[i - 2]) and math.isfinite(lo[i - 2])):
            continue
        if lo[i] > hi[i - 2]:
            out.append({"time": int(times[i]), "type": "bullish",
                        "top": round(float(lo[i]), 4), "bottom": round(float(hi[i - 2]), 4)})
        elif hi[i] < lo[i - 2]:
            out.append({"time": int(times[i]), "type": "bearish",
                        "top": round(float(lo[i - 2]), 4), "bottom": round(float(hi[i]), 4)})
    return out[-limit:]


def compute_all(df: pd.DataFrame, times, timeframe: str) -> dict:
    o = df["Open"].astype("float64")
    h = df["High"].astype("float64")
    l = df["Low"].astype("float64")
    c = df["Close"].astype("float64")
    v = df["Volume"].astype("float64")
    intraday = timeframe in INTRADAY_TF

    macd, signal, hist = _macd(c)
    bb_u, bb_m, bb_l = _bollinger(c)

    # MACD histogram carries per-bar color for the frontend.
    hist_pts = []
    hv = hist.to_numpy(dtype="float64")
    for t, val in zip(times, hv):
        if val is None or not math.isfinite(val):
            continue
        hist_pts.append({
            "time": int(t),
            "value": float(val),
            "color": "#26a69a" if val >= 0 else "#ef5350",
        })

    return {
        "sma20": _series_points(_sma(c, 20), times),
        "sma50": _series_points(_sma(c, 50), times),
        "sma200": _series_points(_sma(c, 200), times),
        "ema20": _series_points(_ema(c, 20), times),
        "bb_upper": _series_points(bb_u, times),
        "bb_mid": _series_points(bb_m, times),
        "bb_lower": _series_points(bb_l, times),
        "vwap": _series_points(_vwap(h, l, c, v, df.index, intraday), times),
        "rsi": _series_points(_rsi(c), times),
        "macd": {
            "macd": _series_points(macd, times),
            "signal": _series_points(signal, times),
            "hist": hist_pts,
        },
        "volume_profile": _volume_profile(h, l, c, v),
        "fvg": _fvg(o, h, l, c, times),
    }
