"""
vpin_multi.py — Multi-Day VPIN Strategy: Pressure → Release
=============================================================
Tracks VPIN trends over multiple days to detect informed flow
building up before a significant price move.

Strategy logic:
  - Rising/Spiking VPIN = informed traders positioning
  - Flat price + rising VPIN = pressure building (pre-breakout)
  - VPIN collapse after spike = pressure released (move happened)
  - Combined with delta direction for trade bias

Integration:
  - Called by scheduler.py at EOD after vpin.calc_vpin
  - Called by app.py for /api/vpin/multi endpoint
  - Sends Telegram alerts on STRONG signals
"""

import sqlite3
import logging
from typing import Optional
from screener.vpin import classify_vpin

logger = logging.getLogger(__name__)


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

    vpin_z = (today_vpin - mean_vpin) / std_vpin if std_vpin > 0.001 else 0.0

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
        if std_vpin > 0.001:
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
