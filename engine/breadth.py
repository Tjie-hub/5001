# engine/breadth.py
import sqlite3


def get_market_breadth(conn: sqlite3.Connection, date: str) -> dict:
    """Market breadth for a given date from the ohlcv table.

    Computes:
      - advancers/decliners (close vs previous trading day close)
      - % stocks above their 20-day MA
      - label: BULL_MARKET / NEUTRAL / WEAK / BEAR_MARKET / INSUFFICIENT_DATA
    """
    # ── Advancers / Decliners ────────────────────────────────────────────────
    # Find the previous trading date (latest date in ohlcv that is < current date)
    prev_date_row = conn.execute(
        "SELECT MAX(date) FROM ohlcv WHERE date < ?", (date,)
    ).fetchone()
    prev_date = prev_date_row[0] if prev_date_row else None

    adv = dec = unch = 0
    total = 0

    if prev_date:
        rows = conn.execute(
            """SELECT t.close, p.close
               FROM ohlcv t
               JOIN ohlcv p ON t.ticker = p.ticker AND p.date = ?
               WHERE t.date = ?""",
            (prev_date, date),
        ).fetchall()
        total = len(rows)
        for t_close, p_close in rows:
            if t_close > p_close:
                adv += 1
            elif t_close < p_close:
                dec += 1
            else:
                unch += 1

    if total == 0:
        return {
            'date': date, 'total': 0,
            'advancers': 0, 'decliners': 0, 'unchanged': 0,
            'adv_dec_ratio': 0.0, 'pct_advancing': 0.0,
            'pct_above_ma20': 0.0, 'label': 'INSUFFICIENT_DATA',
        }

    pct_adv = round(adv / total * 100, 1)
    adv_dec_ratio = round(adv / max(dec, 1), 2)

    # ── % above MA20 ────────────────────────────────────────────────────────
    # For each ticker on `date`, compare close to its 20-bar average
    # (using up to 20 trading days ending on `date`).
    ma20_rows = conn.execute(
        """SELECT o.ticker, o.close,
                  (SELECT AVG(h.close)
                   FROM (SELECT close FROM ohlcv
                         WHERE ticker = o.ticker AND date <= o.date
                         ORDER BY date DESC LIMIT 20) h
                  ) AS ma20
           FROM ohlcv o
           WHERE o.date = ?""",
        (date,),
    ).fetchall()

    above_ma20 = sum(1 for _, cl, ma in ma20_rows if ma is not None and cl > ma)
    total_ma = sum(1 for _, cl, ma in ma20_rows if ma is not None)
    pct_above_ma20 = round(above_ma20 / total_ma * 100, 1) if total_ma else 0.0

    # ── Label ────────────────────────────────────────────────────────────────
    if pct_adv >= 60:
        label = 'BULL_MARKET'
    elif pct_adv >= 45:
        label = 'NEUTRAL'
    elif pct_adv >= 30:
        label = 'WEAK'
    else:
        label = 'BEAR_MARKET'

    return {
        'date': date,
        'total': total,
        'advancers': adv,
        'decliners': dec,
        'unchanged': unch,
        'adv_dec_ratio': adv_dec_ratio,
        'pct_advancing': pct_adv,
        'pct_above_ma20': pct_above_ma20,
        'label': label,
    }
