"""
vpin.py — Volume-Synchronized Probability of Informed Trading
=============================================================
Calculates VPIN for IDX tickers using tick data from trading.db.

Reference: Easley, López de Prado, O'Hara (2012)
"Flow Toxicity and Liquidity in a High-Frequency World"

Integration:
  - Called by scheduler.py at EOD to populate daily_screen.vpin
  - Called by app.py for /api/vpin endpoint
  - Called by vpin_multi.py for multi-day strategy signals
"""

import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Thresholds ───────────────────────────────────────────────────────────────

VPIN_THRESHOLDS = {
    'low':      0.20,   # Normal two-sided trading
    'moderate': 0.40,   # Some informed flow
    'high':     0.60,   # Significant informed activity
    # > 0.60 = Toxic
}


def classify_vpin(vpin: float) -> str:
    """Return human-readable VPIN label."""
    if vpin is None:
        return 'N/A'
    if vpin < VPIN_THRESHOLDS['low']:
        return 'LOW'
    elif vpin < VPIN_THRESHOLDS['moderate']:
        return 'MODERATE'
    elif vpin < VPIN_THRESHOLDS['high']:
        return 'HIGH'
    else:
        return 'TOXIC'


# ── Core VPIN Calculation ────────────────────────────────────────────────────

def calc_vpin(
    conn: sqlite3.Connection,
    ticker: str,
    date: str,
    n_buckets: int = 50,
    bucket_size: Optional[int] = None,
    avg_vol_lookback: int = 30,
    min_buckets: int = 5,
) -> dict:
    """
    Calculate VPIN for a single ticker on a single date.

    Algorithm:
      1. Get adaptive bucket_size from avg daily volume (last 30 days)
      2. Fetch ticks sorted chronologically
      3. Fill fixed-volume buckets, classify each tick via tick_type
      4. VPIN = mean(|V_buy - V_sell| / V) over last n_buckets

    Args:
        conn:               SQLite connection (row_factory=sqlite3.Row OK)
        ticker:             Stock ticker, e.g. 'BBCA'
        date:               Trade date 'YYYY-MM-DD'
        n_buckets:          Rolling window for VPIN average (default 50)
        bucket_size:        Override auto bucket size (for testing)
        avg_vol_lookback:   Days to look back for avg volume (default 30)
        min_buckets:        Minimum filled buckets required (default 5)

    Returns:
        dict with keys:
          vpin          float|None  - VPIN score 0.0-1.0
          vpin_label    str         - LOW/MODERATE/HIGH/TOXIC/N/A
          bucket_count  int         - total buckets filled
          bucket_size   int|None    - volume per bucket
          buckets       list[dict]  - per-bucket detail
          total_volume  int         - total tick volume processed
          error         str|None    - error message if any
    """
    result_base = {
        'ticker': ticker,
        'date': date,
        'vpin': None,
        'vpin_label': 'N/A',
        'bucket_count': 0,
        'bucket_size': None,
        'buckets': [],
        'total_volume': 0,
        'error': None,
    }

    # ── Step 1: Determine bucket size ────────────────────────────────────
    if bucket_size is None:
        row = conn.execute("""
            SELECT AVG(volume) as avg_vol
            FROM daily_screen
            WHERE ticker = ?
              AND date >= date(?, '-' || ? || ' days')
              AND date < ?
              AND volume > 0
        """, (ticker, date, str(avg_vol_lookback), date)).fetchone()

        avg_vol = row[0] if row and row[0] else None

        if avg_vol is None or avg_vol < 1000:
            result_base['error'] = 'insufficient volume history'
            return result_base

        bucket_size = max(int(avg_vol / n_buckets), 1)

    result_base['bucket_size'] = bucket_size

    # ── Step 2: Fetch ticks ──────────────────────────────────────────────
    ticks = conn.execute("""
        SELECT price, volume, tick_type
        FROM ticks
        WHERE date = ? AND ticker = ?
        ORDER BY time ASC, id ASC
    """, (date, ticker)).fetchall()

    if not ticks or len(ticks) < 10:
        result_base['error'] = f'insufficient ticks ({len(ticks) if ticks else 0})'
        return result_base

    # ── Step 3: Fill volume buckets ──────────────────────────────────────
    buckets = []
    cur_buy = 0
    cur_sell = 0
    cur_vol = 0
    total_vol = 0

    for row in ticks:
        price = row[0]
        vol = row[1]
        ttype = row[2]

        if vol is None or vol <= 0:
            continue

        total_vol += vol

        # Classify volume
        if ttype == 'up':
            cur_buy += vol
        elif ttype == 'down':
            cur_sell += vol
        else:
            # 'unchanged' or None — split 50/50
            half = vol // 2
            cur_buy += half
            cur_sell += vol - half

        cur_vol += vol

        # Fill buckets (handle overflow for multi-bucket fills)
        while cur_vol >= bucket_size:
            # Proportionally allocate to this bucket
            if cur_vol > 0:
                fill_ratio = bucket_size / cur_vol
                b_buy = int(cur_buy * fill_ratio)
                b_sell = bucket_size - b_buy  # ensure exact bucket_size
            else:
                b_buy = b_sell = 0

            imbalance = abs(b_buy - b_sell) / bucket_size

            buckets.append({
                'bucket_id': len(buckets) + 1,
                'v_buy': b_buy,
                'v_sell': b_sell,
                'imbalance': round(imbalance, 4),
                'direction': 'BUY' if b_buy > b_sell else 'SELL',
            })

            # Carry over remainder
            overflow_buy = cur_buy - b_buy
            overflow_sell = cur_sell - b_sell
            overflow_vol = cur_vol - bucket_size

            cur_buy = max(overflow_buy, 0)
            cur_sell = max(overflow_sell, 0)
            cur_vol = max(overflow_vol, 0)

    result_base['total_volume'] = total_vol
    result_base['bucket_count'] = len(buckets)

    # ── Step 4: Calculate VPIN ───────────────────────────────────────────
    if len(buckets) < min_buckets:
        result_base['error'] = f'insufficient buckets ({len(buckets)}/{min_buckets})'
        result_base['buckets'] = buckets
        return result_base

    # Take last n_buckets (or all if fewer)
    window = buckets[-n_buckets:]
    vpin = sum(b['imbalance'] for b in window) / len(window)

    result_base['vpin'] = round(vpin, 4)
    result_base['vpin_label'] = classify_vpin(vpin)
    result_base['buckets'] = buckets

    return result_base


# ── Intraday VPIN Series (for charting) ──────────────────────────────────────

def calc_vpin_series(
    conn: sqlite3.Connection,
    ticker: str,
    date: str,
    n_buckets: int = 50,
    bucket_size: Optional[int] = None,
    rolling_window: int = 20,
) -> dict:
    """
    Calculate rolling VPIN over the trading day for charting.

    Returns a time-series of VPIN values as buckets accumulate,
    using a rolling window of `rolling_window` buckets.

    Returns:
        dict with:
          series    list of [bucket_id, vpin_value]
          vpin      float  - final VPIN (same as calc_vpin)
          label     str    - VPIN classification
    """
    full = calc_vpin(conn, ticker, date, n_buckets, bucket_size)

    if full['vpin'] is None:
        return {
            'series': [],
            'vpin': None,
            'label': 'N/A',
            'error': full.get('error'),
        }

    buckets = full['buckets']
    series = []

    for i in range(rolling_window - 1, len(buckets)):
        window = buckets[max(0, i - rolling_window + 1):i + 1]
        rolling_vpin = sum(b['imbalance'] for b in window) / len(window)
        series.append([i + 1, round(rolling_vpin, 4)])

    return {
        'series': series,
        'vpin': full['vpin'],
        'label': full['vpin_label'],
        'bucket_count': full['bucket_count'],
        'bucket_size': full['bucket_size'],
    }


# ── Batch VPIN for all tickers (EOD) ─────────────────────────────────────────

def calc_vpin_batch(
    conn: sqlite3.Connection,
    tickers: list,
    date: str,
    n_buckets: int = 50,
) -> dict:
    """
    Calculate VPIN for all tickers. Used by scheduler at EOD.

    Returns:
        dict: {ticker: {vpin, vpin_label, bucket_count, ...}, ...}
    """
    results = {}
    for ticker in tickers:
        try:
            r = calc_vpin(conn, ticker, date, n_buckets)
            results[ticker] = r
        except Exception as e:
            logger.error(f"[vpin] Error calculating {ticker}: {e}")
            results[ticker] = {
                'vpin': None,
                'vpin_label': 'N/A',
                'error': str(e),
            }
    return results


def get_latest_vpin_date(conn, ticker, date):
    """Find the most recent date with VPIN data, on or before given date."""
    row = conn.execute("""
        SELECT date FROM daily_screen
        WHERE ticker = ? AND date <= ? AND vpin IS NOT NULL
        ORDER BY date DESC LIMIT 1
    """, (ticker, date)).fetchone()
    return row[0] if row else None
