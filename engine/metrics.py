"""Engine-level operational metrics (Production Engine Phase 2, Workstream
2B Task 2B-2). Extracts the same query set app.py's Prometheus /metrics
route (`prometheus_metrics()`) already computes, as a reusable service
function -- app.py's route is left untouched (it's a live scrape target and
out of this task's scope), so this necessarily duplicates that query set
rather than sharing it; both now read the same tables independently.

Unlike the Prometheus route's market-risk query (`risk_score`/`computed_at`
-- columns that don't exist in market_risk_log; see engine/risk_alert.py
for the real schema, `score`/`created_at`, also used correctly by
engine/trade_plan.py), this uses the real column names. That pre-existing
defect in app.py is not fixed here -- flagged in
docs/superpowers/specs/2026-08-06-2b2-metrics-api-design.md.
"""
from datetime import date as _date

from data.db import connect as db_connect


def _today() -> str:
    return str(_date.today())


def _q(conn, sql, *params):
    try:
        row = conn.execute(sql, params).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def get_engine_metrics(db_path: str) -> dict:
    """Same operational counters app.py's Prometheus endpoint exposes, as a
    plain dict. No fail-soft here beyond the per-query try/except in _q()
    (matching the Prometheus route's own pattern) -- a totally unreachable
    DB raises, and the caller lets that hit the standard 500 envelope."""
    conn = db_connect(db_path)
    try:
        today = _today()
        open_trades     = _q(conn, "SELECT COUNT(*) FROM paper_trades WHERE status='OPEN'") or 0
        signals_today   = _q(conn, "SELECT COUNT(*) FROM scheduled_signals WHERE date(scan_time)=?", today) or 0
        buy_signals     = _q(conn, "SELECT COUNT(*) FROM scheduled_signals WHERE date(scan_time)=? AND signal_direction='BUY'", today) or 0
        sell_signals    = _q(conn, "SELECT COUNT(*) FROM scheduled_signals WHERE date(scan_time)=? AND signal_direction='SELL'", today) or 0
        agent_decisions = _q(conn, "SELECT COUNT(*) FROM agent_decisions WHERE date(scan_time)=?", today) or 0
        ohlcv_tickers   = _q(conn, "SELECT COUNT(DISTINCT ticker) FROM ohlcv WHERE date=?", today) or 0
        risk_score      = _q(conn, "SELECT score FROM market_risk_log ORDER BY created_at DESC LIMIT 1")
        avg_vpin        = _q(conn, "SELECT AVG(vpin) FROM daily_screen WHERE date=? AND vpin IS NOT NULL", today)
        last_scan_str   = _q(conn, "SELECT MAX(scan_time) FROM scheduled_signals")
    finally:
        conn.close()

    return {
        "open_trades": open_trades,
        "signals_today_total": signals_today,
        "signals_today_buy": buy_signals,
        "signals_today_sell": sell_signals,
        "agent_decisions_today": agent_decisions,
        "ohlcv_tickers_today": ohlcv_tickers,
        "market_risk_score": risk_score,
        "avg_vpin_today": avg_vpin,
        "last_scan_at": last_scan_str,
    }
