"""
engine/vpin.py — Merged VPIN Engine
====================================
Combines vpin.py and vpin_multi.py into a single engine module.

Volume-Synchronized Probability of Informed Trading (single-day) and
Multi-Day VPIN Strategy: Pressure → Release.

References:
  - Easley, López de Prado, O'Hara (2012)
    "Flow Toxicity and Liquidity in a High-Frequency World"

Integration:
  - Called by scheduler.py at EOD to populate daily_screen.vpin
  - Called by app.py for /api/vpin and /api/vpin/multi endpoints
  - Sends Telegram alerts on STRONG signals
"""

import math
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_SQRT2 = math.sqrt(2.0)


# ── Thresholds ───────────────────────────────────────────────────────────────

VPIN_THRESHOLDS = {
    'low':      0.20,   # Normal two-sided trading
    'moderate': 0.40,   # Some informed flow
    'high':     0.60,   # Significant informed activity
    # > 0.60 = Toxic
}

# Minimum VPIN std-dev for a meaningful z-score. When VPIN saturates near a
# bound (e.g. pinned ~1.0 for days), variance collapses and a tiny dip would
# otherwise manufacture an extreme z that contradicts the absolute label.
# Below this floor we report z = 0 (no meaningful deviation).
VPIN_Z_MIN_STD = 0.02


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
      3. Fill fixed-volume buckets, recording each bucket's closing price
      4. Bulk Volume Classification (BVC): split each bucket buy/sell via the
         normalized price change V_buy = V·Φ(ΔP/σ); VPIN = mean(|2·Φ(ΔP/σ) - 1|)
         over last n_buckets

    BVC replaces the per-tick up/down "tick rule": on IDX data trades arrive in
    long same-direction runs, so the tick rule made every bucket ~100% one-sided
    and pinned VPIN near 1.0 for every name. BVC keys on the price move per bucket,
    yielding graded imbalances that actually discriminate toxic from normal flow.

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

    # ── Step 3: Fill volume buckets, recording each bucket's closing price ──
    # (tick_type is intentionally ignored — BVC classifies on price change, not
    #  the per-tick up/down rule that saturated VPIN on IDX run-structured data.)
    bucket_closes = []
    start_price = None
    cur_vol = 0
    total_vol = 0

    for row in ticks:
        price = row[0]
        vol = row[1]
        if vol is None or vol <= 0:
            continue
        if start_price is None:
            start_price = price
        total_vol += vol
        cur_vol += vol
        # a single large tick may complete several buckets, all at this price
        while cur_vol >= bucket_size:
            bucket_closes.append(price)
            cur_vol -= bucket_size

    result_base['total_volume'] = total_vol
    result_base['bucket_count'] = len(bucket_closes)

    if len(bucket_closes) < min_buckets:
        result_base['error'] = f'insufficient buckets ({len(bucket_closes)}/{min_buckets})'
        return result_base

    # ── Step 4: Bulk Volume Classification + VPIN ────────────────────────
    # ΔP per bucket = close − previous close (first bucket vs the day's start).
    deltas = []
    prev = start_price
    for p in bucket_closes:
        deltas.append(p - prev)
        prev = p

    mean_dp = sum(deltas) / len(deltas)
    sigma = (sum((d - mean_dp) ** 2 for d in deltas) / len(deltas)) ** 0.5

    buckets = []
    for i, d in enumerate(deltas):
        if sigma > 0:
            buy_frac = 0.5 * (1.0 + math.erf((d / sigma) / _SQRT2))   # Φ(ΔP/σ)
        else:
            buy_frac = 0.5                                            # no price variation
        imbalance = abs(2.0 * buy_frac - 1.0)
        buckets.append({
            'bucket_id': i + 1,
            'v_buy': int(round(buy_frac * bucket_size)),
            'v_sell': int(round((1.0 - buy_frac) * bucket_size)),
            'imbalance': round(imbalance, 4),
            'direction': 'BUY' if buy_frac >= 0.5 else 'SELL',
        })

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


def get_market_vpin_summary(conn: sqlite3.Connection, date: str) -> dict:
    """Aggregate per-ticker VPIN from daily_screen into a market-wide toxicity score.

    Thresholds recalibrated for Bulk Volume Classification (BVC) VPIN, which centers
    ~0.30 on a normal day and tops out ~0.6-0.7 (the legacy tick-rule pinned ~1.0, so
    the old 0.70-0.95 thresholds never fire under BVC). Keyed on the average plus the
    share of names above 0.5 (HIGH+). PROVISIONAL — tune once a volatile/crash day is
    observed under BVC:
      CRITICAL : avg_vpin >= 0.50 OR pct_above_05 >= 60%
      RED      : avg_vpin >= 0.45 OR pct_above_05 >= 45%
      ORANGE   : avg_vpin >= 0.40 OR pct_above_05 >= 30%
      YELLOW   : avg_vpin >= 0.35 OR pct_above_05 >= 15%
      GREEN    : below all thresholds
    (pct_above_08/095 are retained for display/back-compat but are ~0 under BVC.)
    """
    rows = conn.execute(
        "SELECT vpin FROM daily_screen WHERE date=? AND vpin IS NOT NULL",
        (date,),
    ).fetchall()

    if not rows:
        return {
            'date': date,
            'tickers_with_vpin': 0,
            'avg_vpin': None,
            'pct_above_08': 0.0,
            'pct_above_095': 0.0,
            'count_above_08': 0,
            'count_above_095': 0,
            'label': 'INSUFFICIENT_DATA',
        }

    vpins = [r[0] for r in rows]
    n = len(vpins)
    avg = sum(vpins) / n
    above_05 = sum(1 for v in vpins if v > 0.5)
    above_06 = sum(1 for v in vpins if v > 0.6)
    above_08 = sum(1 for v in vpins if v > 0.8)
    above_095 = sum(1 for v in vpins if v > 0.95)
    pct_05 = round(above_05 / n * 100, 1)
    pct_06 = round(above_06 / n * 100, 1)
    pct_08 = round(above_08 / n * 100, 1)
    pct_095 = round(above_095 / n * 100, 1)

    if avg >= 0.50 or pct_05 >= 60:
        label = 'CRITICAL'
    elif avg >= 0.45 or pct_05 >= 45:
        label = 'RED'
    elif avg >= 0.40 or pct_05 >= 30:
        label = 'ORANGE'
    elif avg >= 0.35 or pct_05 >= 15:
        label = 'YELLOW'
    else:
        label = 'GREEN'

    return {
        'date': date,
        'tickers_with_vpin': n,
        'avg_vpin': round(avg, 4),
        'pct_above_05': pct_05,
        'pct_above_06': pct_06,
        'pct_above_08': pct_08,
        'pct_above_095': pct_095,
        'count_above_05': above_05,
        'count_above_08': above_08,
        'count_above_095': above_095,
        'label': label,
    }


# ── Signal Definitions ───────────────────────────────────────────────────────

SIGNAL_MAP = {
    # (vpin_regime, delta_dir, price_move) → signal
    ('SPIKE',  'BUY',  'FLAT'):    'STRONG_BUY',
    ('SPIKE',  'BUY',  'UP'):      'WATCH_LONG',
    ('SPIKE',  'BUY',  'DOWN'):    'ACCUMULATION',
    ('SPIKE',  'SELL', 'FLAT'):    'AVOID',
    ('SPIKE',  'SELL', 'UP'):      'DANGER',
    ('SPIKE',  'SELL', 'DOWN'):    'WATCH_SHORT',
    ('RISING', 'BUY',  'FLAT'):    'BUY',
    ('RISING', 'BUY',  'UP'):      'WATCH_LONG',
    ('RISING', 'BUY',  'DOWN'):    'ACCUMULATION',
    ('RISING', 'SELL', 'FLAT'):    'AVOID',
    ('RISING', 'SELL', 'UP'):      'DANGER',
    ('RISING', 'SELL', 'DOWN'):    'WATCH_SHORT',
}

SIGNAL_DESCRIPTIONS = {
    'STRONG_BUY':   'Informed buyers loaded, pressure built, release imminent',
    'BUY':          'Informed buying building, direction confirmed',
    'ACCUMULATION': 'Smart money accumulating on dip — watch for reversal',
    'WATCH_LONG':   'Move already started — late entry risk, trail if in',
    'WATCH_SHORT':  'Informed selling into weakness — could accelerate',
    'AVOID':        'Informed sellers loading — drop coming',
    'DANGER':       'Distribution — smart money selling into rally',
    'NO_SIGNAL':    'No significant informed activity detected',
}

# Trade parameters per signal
TRADE_PARAMS = {
    'STRONG_BUY': {
        'action': 'BUY',
        'tp_pct': 2.5,
        'sl_pct': 1.5,
        'time_stop_days': 5,
        'max_position_pct': 30,
        'confidence': 'HIGH',
    },
    'BUY': {
        'action': 'BUY',
        'tp_pct': 2.0,
        'sl_pct': 1.5,
        'time_stop_days': 5,
        'max_position_pct': 30,
        'confidence': 'MEDIUM',
    },
    'ACCUMULATION': {
        'action': 'BUY',
        'tp_pct': 2.5,
        'sl_pct': 2.0,
        'time_stop_days': 7,
        'max_position_pct': 20,
        'confidence': 'MEDIUM',
    },
}


# ── Multi-Day VPIN Metrics ───────────────────────────────────────────────────

def calc_vpin_multi(
    conn: sqlite3.Connection,
    ticker: str,
    date: str,
    lookback: int = 10,
) -> Optional[dict]:
    """
    Calculate multi-day VPIN metrics for strategy signals.

    Requires at least 5 days of VPIN data in daily_screen.

    Args:
        conn:       SQLite connection
        ticker:     Stock ticker
        date:       Current date 'YYYY-MM-DD'
        lookback:   Days of VPIN history to analyze (default 10)

    Returns:
        dict or None if insufficient data. Keys:
          vpin_today      float   - today's VPIN
          vpin_yesterday  float   - yesterday's VPIN
          vpin_3d_avg     float   - 3-day average VPIN
          vpin_3d_slope   float   - 3-day linear slope
          vpin_z          float   - z-score vs lookback period
          vpin_regime     str     - SPIKE/RISING/FALLING/NORMAL
          delta_3d        int     - cumulative 3-day delta
          delta_dir       str     - BUY/SELL
          price_chg_3d    float   - 3-day price change %
          price_move      str     - UP/DOWN/FLAT
          pressure        bool    - True if pressure building
          signal          str     - STRONG_BUY/BUY/AVOID/etc
          signal_desc     str     - human-readable description
          trade_params    dict|None - trade parameters if actionable
          days_data       list    - raw daily data for charting
    """
    rows = conn.execute("""
        SELECT date, vpin, delta, cum_delta, close, volume,
               vol_ratio, vwap, signal
        FROM daily_screen
        WHERE ticker = ?
          AND date <= ?
          AND vpin IS NOT NULL
        ORDER BY date DESC
        LIMIT ?
    """, (ticker, date, lookback)).fetchall()

    if len(rows) < 5:
        return None

    # Reverse to chronological order
    rows = list(reversed(rows))

    # Extract arrays
    dates   = [r[0] for r in rows]
    vpins   = [r[1] for r in rows]
    deltas  = [r[2] or 0 for r in rows]
    closes  = [r[4] for r in rows]
    volumes = [r[5] or 0 for r in rows]
    vols_r  = [r[6] for r in rows]

    today_row = rows[-1]
    today_vpin = today_row[1]
    yesterday_vpin = rows[-2][1] if len(rows) >= 2 else None

    # ── VPIN 3-day metrics ───────────────────────────────────────────────
    v3 = vpins[-3:]
    vpin_3d_avg = sum(v3) / len(v3)

    # Simple linear slope over 3 days
    # slope = (y3 - y1) / 2
    vpin_3d_slope = (v3[-1] - v3[0]) / 2 if len(v3) >= 3 else 0

    # ── VPIN z-score ─────────────────────────────────────────────────────
    n = len(vpins)
    mean_vpin = sum(vpins) / n
    variance = sum((v - mean_vpin) ** 2 for v in vpins) / n
    std_vpin = variance ** 0.5

    vpin_z = (today_vpin - mean_vpin) / std_vpin if std_vpin >= VPIN_Z_MIN_STD else 0.0

    # ── VPIN Regime ──────────────────────────────────────────────────────
    if vpin_z >= 2.0:
        vpin_regime = 'SPIKE'
    elif vpin_3d_slope > 0.03:
        vpin_regime = 'RISING'
    elif vpin_3d_slope < -0.03:
        vpin_regime = 'FALLING'
    else:
        vpin_regime = 'NORMAL'

    # ── Delta direction (3-day cumulative) ───────────────────────────────
    delta_3d = sum(deltas[-3:])
    delta_dir = 'BUY' if delta_3d > 0 else 'SELL'

    # ── Price trend (3-day) ──────────────────────────────────────────────
    price_start = closes[-3] if len(closes) >= 3 else closes[0]
    price_end = closes[-1]
    if price_start and price_start > 0:
        price_chg_3d = (price_end - price_start) / price_start
    else:
        price_chg_3d = 0.0

    if abs(price_chg_3d) < 0.015:
        price_move = 'FLAT'
    elif price_chg_3d > 0:
        price_move = 'UP'
    else:
        price_move = 'DOWN'

    # ── Pressure detection ───────────────────────────────────────────────
    pressure = (
        vpin_regime in ('RISING', 'SPIKE')
        and price_move == 'FLAT'
    )

    # ── Signal classification ────────────────────────────────────────────
    signal_key = (vpin_regime, delta_dir, price_move)
    signal = SIGNAL_MAP.get(signal_key, 'NO_SIGNAL')

    # Additional filter: require vol_ratio >= 1.3 today for actionable signals
    today_vol_ratio = vols_r[-1]
    if signal in ('STRONG_BUY', 'BUY', 'ACCUMULATION'):
        if today_vol_ratio is not None and today_vol_ratio < 1.0:
            signal = 'NO_SIGNAL'  # Volume too low to confirm

    # ── VPIN collapse exit signal ────────────────────────────────────────
    # If VPIN was high (z>1.5) 2 days ago but collapsed today (z<0.5)
    vpin_collapse = False
    if len(vpins) >= 3:
        v_2d_ago = vpins[-3]
        if std_vpin >= VPIN_Z_MIN_STD:
            z_2d_ago = (v_2d_ago - mean_vpin) / std_vpin
            if z_2d_ago >= 1.5 and vpin_z < 0.5:
                vpin_collapse = True

    # ── Trade parameters ─────────────────────────────────────────────────
    trade_params = TRADE_PARAMS.get(signal)

    # Reduce position on extreme toxicity
    if trade_params and vpin_z > 2.5:
        trade_params = dict(trade_params)  # copy
        trade_params['max_position_pct'] = 20
        trade_params['note'] = 'Reduced position: extreme VPIN'

    # ── Build daily data for charting ────────────────────────────────────
    days_data = []
    for i, r in enumerate(rows):
        days_data.append({
            'date': r[0],
            'vpin': r[1],
            'delta': r[2],
            'close': r[4],
            'volume': r[5],
            'vol_ratio': r[6],
        })

    return {
        'ticker': ticker,
        'date': date,
        'vpin_today': round(today_vpin, 4),
        'vpin_yesterday': round(yesterday_vpin, 4) if yesterday_vpin else None,
        'vpin_3d_avg': round(vpin_3d_avg, 4),
        'vpin_3d_slope': round(vpin_3d_slope, 4),
        'vpin_z': round(vpin_z, 2),
        'vpin_regime': vpin_regime,
        'vpin_label': classify_vpin(today_vpin),
        'delta_3d': delta_3d,
        'delta_dir': delta_dir,
        'price_chg_3d': round(price_chg_3d, 4),
        'price_move': price_move,
        'pressure': pressure,
        'vpin_collapse': vpin_collapse,
        'signal': signal,
        'signal_desc': SIGNAL_DESCRIPTIONS.get(signal, ''),
        'trade_params': trade_params,
        'lookback_days': len(rows),
        'days_data': days_data,
    }


# ── Scan all tickers for signals ─────────────────────────────────────────────

def scan_vpin_signals(
    conn: sqlite3.Connection,
    tickers: list,
    date: str,
    min_signal_level: str = 'BUY',
) -> list:
    """
    Scan all tickers for multi-day VPIN signals.
    Returns list of tickers with actionable signals, sorted by strength.

    Args:
        conn:              SQLite connection
        tickers:           List of tickers to scan
        date:              Trade date
        min_signal_level:  Minimum signal to include

    Returns:
        list of dicts, each from calc_vpin_multi, filtered and sorted
    """
    actionable = ('STRONG_BUY', 'BUY', 'ACCUMULATION', 'DANGER', 'AVOID')
    if min_signal_level == 'ALL':
        actionable = tuple(SIGNAL_MAP.values())

    results = []
    for ticker in tickers:
        try:
            multi = calc_vpin_multi(conn, ticker, date)
            if multi is None:
                continue
            if multi['signal'] in actionable:
                results.append(multi)
        except Exception as e:
            logger.error(f"[vpin_multi] Error scanning {ticker}: {e}")

    # Sort: STRONG_BUY first, then by vpin_z descending
    signal_priority = {
        'STRONG_BUY': 0, 'BUY': 1, 'ACCUMULATION': 2,
        'DANGER': 3, 'AVOID': 4,
        'WATCH_LONG': 5, 'WATCH_SHORT': 6, 'NO_SIGNAL': 9,
    }
    results.sort(key=lambda x: (
        signal_priority.get(x['signal'], 9),
        -abs(x['vpin_z'])
    ))

    return results


# ── Telegram Alert Formatter ─────────────────────────────────────────────────

def format_vpin_alert(multi: dict) -> str:
    """
    Format a multi-day VPIN result into a Telegram message.
    """
    emoji = {
        'STRONG_BUY':   '🔥🔥',
        'BUY':          '🔥',
        'ACCUMULATION': '🟡',
        'DANGER':       '🔴',
        'AVOID':        '⛔',
        'WATCH_LONG':   '👀',
        'WATCH_SHORT':  '👀',
    }

    regime_emoji = {
        'SPIKE':   '⚡',
        'RISING':  '📈',
        'FALLING': '📉',
        'NORMAL':  '➖',
    }

    sig = multi['signal']
    e = emoji.get(sig, '📊')
    re = regime_emoji.get(multi['vpin_regime'], '')

    lines = [
        f"{e} VPIN ALERT: {multi['ticker']}",
        f"",
        f"Signal: {sig}",
        f"  → {multi['signal_desc']}",
        f"",
        f"VPIN: {multi['vpin_today']:.4f} ({multi['vpin_label']})",
        f"Regime: {re} {multi['vpin_regime']}",
        f"Z-score: {multi['vpin_z']:.1f}σ",
        f"3D slope: {multi['vpin_3d_slope']:+.4f}",
        f"",
        f"Delta 3D: {multi['delta_dir']} ({multi['delta_3d']:+,})",
        f"Price 3D: {multi['price_move']} ({multi['price_chg_3d']:+.2%})",
        f"Pressure: {'YES 🔴' if multi['pressure'] else 'NO'}",
    ]

    if multi.get('trade_params'):
        tp = multi['trade_params']
        lines.extend([
            f"",
            f"── Trade Plan ──",
            f"TP: {tp['tp_pct']}% | SL: {tp['sl_pct']}%",
            f"Time stop: {tp['time_stop_days']}d",
            f"Max pos: {tp['max_position_pct']}%",
        ])
        if tp.get('note'):
            lines.append(f"⚠️ {tp['note']}")

    if multi.get('vpin_collapse'):
        lines.extend([
            f"",
            f"⚠️ VPIN COLLAPSE detected — trail SL to breakeven",
        ])

    return '\n'.join(lines)
