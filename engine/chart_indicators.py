"""Custom chart overlays computed from an OHLCV DataFrame.

Pure functions, no I/O. Columns expected (lowercase): open, high, low,
close, volume, with a DatetimeIndex or 'date' column. VWAP/VWMA are NOT
here — reuse engine.indicators.calc_vwap / calc_vwma (DRY).
"""
import numpy as np
import pandas as pd


def volume_profile(df: pd.DataFrame, bins: int = 24) -> dict:
    """Volume-by-price histogram. Spreads each bar's volume across the
    [low, high] range it traded, then buckets into `bins` price bands.

    Returns: {poc, vah, val, rows:[{price, volume}]} where rows are
    ordered low->high price. POC = band with max volume. VAH/VAL bound the
    70% value area around POC.
    """
    if df is None or df.empty:
        return {'poc': None, 'vah': None, 'val': None, 'rows': []}

    lo = float(df['low'].min())
    hi = float(df['high'].max())
    if hi <= lo:
        hi = lo + 1.0
    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vol = np.zeros(bins)

    for _, r in df.iterrows():
        b_lo, b_hi, v = float(r['low']), float(r['high']), float(r['volume'])
        if b_hi <= b_lo:
            # flat bar — dump all volume in its band
            i = min(int(np.searchsorted(edges, b_lo, side='right')) - 1, bins - 1)
            vol[max(i, 0)] += v
            continue
        # overlap fraction of this bar's range with each band
        ov_lo = np.maximum(edges[:-1], b_lo)
        ov_hi = np.minimum(edges[1:], b_hi)
        ov = np.clip(ov_hi - ov_lo, 0, None)
        frac = ov / (b_hi - b_lo)
        vol += frac * v

    poc_i = int(np.argmax(vol))
    poc = float(centers[poc_i])

    # 70% value area expanding from POC
    target = vol.sum() * 0.70
    lo_i = hi_i = poc_i
    acc = vol[poc_i]
    while acc < target and (lo_i > 0 or hi_i < bins - 1):
        down = vol[lo_i - 1] if lo_i > 0 else -1
        up = vol[hi_i + 1] if hi_i < bins - 1 else -1
        if up >= down:
            hi_i += 1
            acc += vol[hi_i]
        else:
            lo_i -= 1
            acc += vol[lo_i]

    rows = [{'price': round(float(centers[i]), 2), 'volume': round(float(vol[i]), 2)}
            for i in range(bins)]
    return {'poc': round(poc, 2),
            'vah': round(float(centers[hi_i]), 2),
            'val': round(float(centers[lo_i]), 2),
            'rows': rows}


def fair_value_gaps(df: pd.DataFrame) -> list:
    """3-candle imbalance. Bullish gap when low[i] > high[i-2]; bearish
    when high[i] < low[i-2]. Zone = the gap between those two extremes,
    stamped at candle i's date.

    Returns: [{type:'bull'|'bear', top, bottom, date}] (most recent last).
    """
    if df is None or len(df) < 3:
        return []
    out = []
    highs = df['high'].values
    lows = df['low'].values
    if isinstance(df.index, pd.DatetimeIndex):
        dates = [d.strftime('%Y-%m-%d') for d in df.index]
    else:
        dates = [str(d) for d in df.get('date', range(len(df)))]
    for i in range(2, len(df)):
        if lows[i] > highs[i - 2]:
            out.append({'type': 'bull',
                        'bottom': round(float(highs[i - 2]), 2),
                        'top': round(float(lows[i]), 2),
                        'date': dates[i]})
        elif highs[i] < lows[i - 2]:
            out.append({'type': 'bear',
                        'bottom': round(float(highs[i]), 2),
                        'top': round(float(lows[i - 2]), 2),
                        'date': dates[i]})
    return out


def support_resistance(df: pd.DataFrame, lookback: int = 5, max_levels: int = 6) -> dict:
    """Swing-pivot S/R. A pivot-high is a bar whose high is the max within
    +/- lookback bars; pivot-low symmetrically on lows. Returns the most
    recent `max_levels` of each, sorted by price.

    Returns: {support:[...], resistance:[...]}.
    """
    if df is None or len(df) < (2 * lookback + 1):
        return {'support': [], 'resistance': []}
    highs = df['high'].values
    lows = df['low'].values
    res, sup = [], []
    n = len(df)
    for i in range(lookback, n - lookback):
        win_h = highs[i - lookback:i + lookback + 1]
        win_l = lows[i - lookback:i + lookback + 1]
        if highs[i] == win_h.max():
            res.append((i, round(float(highs[i]), 2)))
        if lows[i] == win_l.min():
            sup.append((i, round(float(lows[i]), 2)))
    # most recent first, take max_levels, then sort by price
    res_levels = sorted({p for _, p in sorted(res, reverse=True)[:max_levels]})
    sup_levels = sorted({p for _, p in sorted(sup, reverse=True)[:max_levels]})
    return {'support': sup_levels, 'resistance': res_levels}


def detect_patterns(df: pd.DataFrame) -> list:
    """Classic single/two-candle patterns: doji, hammer, shooting_star,
    bullish_engulfing, bearish_engulfing.

    Returns: [{date, pattern, dir}] where dir in bull|bear|neutral.
    """
    if df is None or df.empty:
        return []
    o = df['open'].values; h = df['high'].values
    l = df['low'].values; c = df['close'].values
    if isinstance(df.index, pd.DatetimeIndex):
        dates = [d.strftime('%Y-%m-%d') for d in df.index]
    else:
        dates = [str(d) for d in df.get('date', range(len(df)))]
    out = []
    for i in range(len(df)):
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        body = abs(c[i] - o[i])
        upper = h[i] - max(o[i], c[i])
        lower = min(o[i], c[i]) - l[i]
        if body <= rng * 0.1:
            out.append({'date': dates[i], 'pattern': 'doji', 'dir': 'neutral'})
        elif lower >= body * 2 and upper <= body:
            out.append({'date': dates[i], 'pattern': 'hammer', 'dir': 'bull'})
        elif upper >= body * 2 and lower <= body:
            out.append({'date': dates[i], 'pattern': 'shooting_star', 'dir': 'bear'})
        if i > 0:
            # engulfing vs previous body
            prev_bull = c[i - 1] >= o[i - 1]
            cur_bull = c[i] >= o[i]
            if cur_bull and not prev_bull and c[i] >= o[i - 1] and o[i] <= c[i - 1]:
                out.append({'date': dates[i], 'pattern': 'bullish_engulfing', 'dir': 'bull'})
            elif not cur_bull and prev_bull and o[i] >= c[i - 1] and c[i] <= o[i - 1]:
                out.append({'date': dates[i], 'pattern': 'bearish_engulfing', 'dir': 'bear'})
    return out
