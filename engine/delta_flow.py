"""ATAS-style order-flow delta from Stockbit 1-minute bars.

Reads stockbit_flow_bars (1-min granularity, ~28-day rolling history from
2026-04-20). delta = buy_lot - sell_lot. Granularity is 1-minute, NOT
tick-level — delta_by_price is a 1-min approximation of a footprint.
"""
import sqlite3
import numpy as np
import pandas as pd
from config import DB_PATH

EARLIEST_DATE = '2026-04-20'


def load_bars(ticker: str, date: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """Return the session's 1-min bars for ticker/date, ordered by bar_time.
    Empty DataFrame if none."""
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT bar_time, buy_lot, sell_lot, buy_freq, sell_freq, "
            "net_value, price, delta FROM stockbit_flow_bars "
            "WHERE ticker=? AND trade_date=? ORDER BY bar_time ASC",
            conn, params=(ticker.upper(), date))
    finally:
        conn.close()
    return df


def cvd(ticker: str, date: str, db_path: str = DB_PATH) -> list:
    """Cumulative Volume Delta series: [{time, cvd}]."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        return []
    cum = df['delta'].cumsum()
    return [{'time': t, 'cvd': int(v)} for t, v in zip(df['bar_time'], cum)]


def delta_bars(ticker: str, date: str, db_path: str = DB_PATH) -> list:
    """Per-minute delta histogram: [{time, delta, buy, sell}]."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        return []
    return [{'time': t, 'delta': int(d), 'buy': int(b), 'sell': int(s)}
            for t, d, b, s in zip(df['bar_time'], df['delta'],
                                  df['buy_lot'], df['sell_lot'])]


def delta_by_price(ticker: str, date: str, bins: int = 24, db_path: str = DB_PATH) -> list:
    """Footprint-lite: bucket 1-min bars by price, summing volume (buy+sell)
    and net delta per band. Returns [{price, volume, delta}] low->high.
    1-MINUTE APPROXIMATION of a tick footprint."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        return []
    prices = df['price'].astype(float).values
    vols = (df['buy_lot'] + df['sell_lot']).astype(float).values
    deltas = df['delta'].astype(float).values
    lo, hi = prices.min(), prices.max()
    if hi <= lo:
        return [{'price': round(float(lo), 2),
                 'volume': int(vols.sum()), 'delta': int(deltas.sum())}]
    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    idx = np.clip(np.searchsorted(edges, prices, side='right') - 1, 0, bins - 1)
    out = []
    for b in range(bins):
        m = idx == b
        if not m.any():
            continue
        out.append({'price': round(float(centers[b]), 2),
                    'volume': int(vols[m].sum()),
                    'delta': int(deltas[m].sum())})
    return out


def session_delta_stats(ticker: str, date: str, db_path: str = DB_PATH) -> dict:
    """Aggregate session stats. Out-of-window dates return zeros + a note."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        note = ('no order-flow data before %s' % EARLIEST_DATE
                if date < EARLIEST_DATE else 'no order-flow data for this date')
        return {'total_delta': 0, 'buy_lot': 0, 'sell_lot': 0,
                'net_value': 0, 'note': note}
    return {'total_delta': int(df['delta'].sum()),
            'buy_lot': int(df['buy_lot'].sum()),
            'sell_lot': int(df['sell_lot'].sum()),
            'net_value': int(df['net_value'].sum())}


def stacked_imbalances(ticker: str, date: str, z: float = 2.0, db_path: str = DB_PATH) -> list:
    """Minutes whose |delta| spikes >= z standard deviations above the mean
    absolute delta. Returns [{time, price, delta}]."""
    df = load_bars(ticker, date, db_path)
    if df.empty:
        return []
    ad = df['delta'].abs()
    thresh = ad.mean() + z * ad.std(ddof=0)
    hot = df[ad >= thresh]
    return [{'time': t, 'price': int(p), 'delta': int(d)}
            for t, p, d in zip(hot['bar_time'], hot['price'], hot['delta'])]


def cvd_ema(series: list, length: int = 9) -> list:
    """EMA overlay for a cvd() series. Returns [{time, ema}]."""
    if not series:
        return []
    vals = pd.Series([p['cvd'] for p in series], dtype=float)
    ema = vals.ewm(span=length, adjust=False).mean()
    return [{'time': p['time'], 'ema': round(float(e), 2)}
            for p, e in zip(series, ema)]
