"""Flow-confirmation gate for SMC liquidity-sweep entries.

Joins engine/smc.py sweep detection to the existing flow data:
  - daily tier:    stockbit_flow.composite_score (int [-8,+8])
  - intraday tier: stockbit_flow_bars via delta_flow.session_delta_stats
Gate is fail-open on missing data (so full-history backtests run price-only)
and fail-closed on negative flow (so live trades require real flow).
"""
import sqlite3
from config import DB_PATH
from engine.delta_flow import session_delta_stats


def _daily_flow_score(ticker: str, date: str, db_path: str):
    """composite_score for ticker/date as float, or None if absent/unparseable."""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT composite_score FROM stockbit_flow WHERE ticker=? AND trade_date=?",
            (ticker.upper(), date)).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    if row is None or row[0] is None:
        return None
    try:
        return float(row[0])
    except (TypeError, ValueError):
        return None


def confirm_sweep_flow(ticker: str, date: str, db_path: str = DB_PATH) -> dict:
    """Return {confirmed: bool, source: 'daily'|'intraday'|'none', reason, score}."""
    cs = _daily_flow_score(ticker, date, db_path)
    if cs is not None:
        if cs > 0:
            return {'confirmed': True, 'source': 'daily',
                    'reason': f'composite_score {cs:+.0f} > 0', 'score': cs}
        return {'confirmed': False, 'source': 'daily',
                'reason': f'composite_score {cs:+.0f} <= 0', 'score': cs}
    stats = session_delta_stats(ticker, date, db_path)
    if not stats.get('note'):  # rows present for this ticker/date
        total = stats['total_delta']
        if total >= 0:
            return {'confirmed': True, 'source': 'intraday',
                    'reason': f'session delta {total:+d} >= 0', 'score': float(total)}
        return {'confirmed': False, 'source': 'intraday',
                'reason': f'session delta {total:+d} < 0', 'score': float(total)}

    return {'confirmed': True, 'source': 'none',
            'reason': 'no flow data (passthrough)', 'score': None}
