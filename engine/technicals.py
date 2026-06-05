# engine/technicals.py
import sqlite3

_SUPPORT_LEVELS = [6200, 6000, 5500]


def detect_ihsg_technicals(conn: sqlite3.Connection, date: str) -> dict:
    """Detect death cross, lower high sequence, and support breaks for IHSG.

    Reads ohlcv for ticker='IHSG'. Requires at least 22 bars for MA20.
    Key thresholds: MA5/MA20 cross, 3-peak lower high, support at 6200/6000/5500.
    """
    empty = {
        'date': date, 'close': None, 'ma5': None, 'ma20': None,
        'death_cross': False, 'lower_high': False,
        'support_breaks': [], 'label': 'INSUFFICIENT_DATA',
    }

    rows = conn.execute(
        """SELECT date, high, close FROM ohlcv
           WHERE ticker='IHSG' AND date <= ?
           ORDER BY date DESC LIMIT 30""",
        (date,),
    ).fetchall()

    if len(rows) < 6:
        return empty

    # Rows are newest-first; reverse for chronological order
    rows = list(reversed(rows))
    closes = [r[2] for r in rows]
    highs = [r[1] for r in rows]
    n = len(closes)

    # ── MA5 / MA20 ────────────────────────────────────────────────────────────
    ma5 = sum(closes[-5:]) / 5
    ma20 = sum(closes[-20:]) / 20 if n >= 20 else None

    # Death cross: MA5 < MA20 (cross is "in force" — bearish condition active)
    death_cross = ma20 is not None and ma5 < ma20

    # ── Lower high sequence ───────────────────────────────────────────────────
    # Split history into 3 equal segments; compare their peak highs.
    # Consistent decline across segments = lower high sequence.
    seg = max(n // 3, 3)
    seg1_max = max(highs[:seg])
    seg2_max = max(highs[seg:2 * seg])
    seg3_max = max(highs[2 * seg:]) if highs[2 * seg:] else seg2_max
    lower_high = seg3_max < seg2_max < seg1_max

    # ── Support breaks ────────────────────────────────────────────────────────
    current_close = closes[-1]
    support_breaks = [str(s) for s in _SUPPORT_LEVELS if current_close < s]

    # ── Label ─────────────────────────────────────────────────────────────────
    if death_cross and lower_high:
        label = 'BEARISH_TREND'
    elif death_cross or lower_high or len(support_breaks) >= 2:
        label = 'DOWNTREND'
    elif ma20 is not None and ma5 > ma20 and not lower_high:
        label = 'UPTREND'
    else:
        label = 'NEUTRAL'

    return {
        'date': date,
        'close': current_close,
        'ma5': round(ma5, 2),
        'ma20': round(ma20, 2) if ma20 is not None else None,
        'death_cross': death_cross,
        'lower_high': lower_high,
        'support_breaks': support_breaks,
        'label': label,
    }
