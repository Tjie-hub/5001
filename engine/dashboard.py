"""Market dashboard aggregator — pure data layer for /api/dashboard/risk."""

import sqlite3
from typing import Any


def get_risk_dashboard(db_path: str, date: str) -> dict[str, Any]:
    """Aggregate all market sensors into a single dashboard payload.

    Args:
        db_path: Path to walkforward.db.
        date:    ISO date string (YYYY-MM-DD) for which to compute the snapshot.

    Returns a dict with keys: date, risk_score, tier, components,
    ihsg, breadth, foreign_flow, vpin, accdist.
    """
    from engine.vpin import get_market_vpin_summary
    from engine.breadth import get_market_breadth
    from engine.technicals import detect_ihsg_technicals
    from engine.risk_score import compute_market_risk_score
    from flow_filter import get_market_accdist_summary

    conn = sqlite3.connect(db_path)
    try:
        vpin_s = _safe(get_market_vpin_summary, conn, date) or _empty_vpin()
        accdist_s = _safe_noconn(get_market_accdist_summary, date) or _empty_accdist(date)
        breadth_s = _safe(get_market_breadth, conn, date) or _empty_breadth(date)
        tech_s = _safe(detect_ihsg_technicals, conn, date) or _empty_tech(date)

        foreign_flow = _get_foreign_flow(conn, date)
        risk = compute_market_risk_score(
            vpin_s, accdist_s, breadth_s, tech_s, foreign_flow.get('net_5d')
        )

        ihsg = {
            'close': tech_s.get('close'),
            'ma5': tech_s.get('ma5'),
            'ma20': tech_s.get('ma20'),
            'death_cross': tech_s.get('death_cross', False),
            'lower_high': tech_s.get('lower_high', False),
            'support_breaks': tech_s.get('support_breaks', []),
            'ytd_pct': _calc_ytd(conn, date),
        }

        return {
            'date': date,
            'risk_score': risk['score'],
            'tier': risk['tier'],
            'components': risk.get('components', {}),
            'ihsg': ihsg,
            'breadth': breadth_s,
            'foreign_flow': foreign_flow,
            'vpin': vpin_s,
            'accdist': accdist_s,
        }
    finally:
        conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(fn, conn, date):
    try:
        return fn(conn, date)
    except Exception:
        return None


def _safe_noconn(fn, date):
    try:
        return fn(date)
    except Exception:
        return None


def _get_foreign_flow(conn: sqlite3.Connection, date: str) -> dict:
    """Compute Asing net flow: today, 5d, 20d from broker_flow table."""
    try:
        def _net(days: int) -> float:
            row = conn.execute(
                "SELECT "
                "  COALESCE(SUM(CASE WHEN side='BUY'  THEN lot_value ELSE 0 END), 0) "
                "- COALESCE(SUM(CASE WHEN side='SELL' THEN lot_value ELSE 0 END), 0) "
                "FROM broker_flow "
                "WHERE investor_type='Asing' "
                "  AND trade_date<=? AND trade_date>=date(?,?)",
                (date, date, f'-{days} days'),
            ).fetchone()
            return float(row[0]) if row else 0.0

        today_net = conn.execute(
            "SELECT "
            "  COALESCE(SUM(CASE WHEN side='BUY'  THEN lot_value ELSE 0 END), 0) "
            "- COALESCE(SUM(CASE WHEN side='SELL' THEN lot_value ELSE 0 END), 0) "
            "FROM broker_flow "
            "WHERE investor_type='Asing' AND trade_date=?",
            (date,),
        ).fetchone()
        today_val = float(today_net[0]) if today_net else 0.0
        net_5d = _net(5)
        net_20d = _net(20)
        trend = 'INFLOW' if net_5d > 0 else 'OUTFLOW' if net_5d < 0 else 'NEUTRAL'
        return {'today': today_val, 'net_5d': net_5d, 'net_20d': net_20d, 'trend': trend}
    except Exception:
        return {'today': None, 'net_5d': None, 'net_20d': None, 'trend': 'NEUTRAL'}


def _calc_ytd(conn: sqlite3.Connection, date: str) -> float | None:
    year = date[:4]
    start_row = conn.execute(
        "SELECT close FROM ohlcv WHERE ticker='IHSG' AND date>=? ORDER BY date LIMIT 1",
        (f'{year}-01-01',),
    ).fetchone()
    end_row = conn.execute(
        "SELECT close FROM ohlcv WHERE ticker='IHSG' AND date<=? ORDER BY date DESC LIMIT 1",
        (date,),
    ).fetchone()
    if start_row and end_row and start_row[0]:
        return round((end_row[0] - start_row[0]) / start_row[0] * 100, 2)
    return None


# ── Empty fallbacks ───────────────────────────────────────────────────────────

def _empty_vpin():
    return {'avg_vpin': 0.0, 'pct_above_08': 0.0, 'pct_above_095': 0.0,
            'label': 'INSUFFICIENT_DATA'}


def _empty_accdist(date):
    return {'date': date, 'total': 0, 'dist_count': 0, 'acc_count': 0,
            'neutral_count': 0, 'dist_pct': 0.0, 'acc_pct': 0.0,
            'avg_numeric_score': 0.0, 'label': 'NEUTRAL'}


def _empty_breadth(date):
    return {'date': date, 'advancers': 0, 'decliners': 0, 'unchanged': 0,
            'adv_dec_ratio': 0.0, 'pct_advancing': 0.0, 'pct_above_ma20': 0.0,
            'label': 'INSUFFICIENT_DATA'}


def _empty_tech(date):
    return {'date': date, 'close': None, 'ma5': None, 'ma20': None,
            'death_cross': False, 'lower_high': False, 'support_breaks': [],
            'label': 'INSUFFICIENT_DATA'}
