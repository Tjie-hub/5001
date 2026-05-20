"""Agent firm analytics — pure SQLite query functions for the audit dashboard."""

import json
import logging
import sqlite3
import statistics
from typing import Any


def cohort_summary(db_path: str) -> dict[str, Any]:
    """Cohort performance: approve vs veto vs baseline (all closed trades)."""
    empty = lambda: {"n": 0, "win_rate": 0.0, "avg_return_pct": 0.0, "sharpe": 0.0}
    result = {"approve": empty(), "veto": empty(), "baseline": empty()}
    try:
        with sqlite3.connect(db_path) as conn:
            approve_pnls = [r[0] for r in conn.execute("""
                SELECT pt.pnl_pct FROM agent_decisions ad
                JOIN paper_trades pt
                  ON ad.ticker = pt.ticker AND DATE(ad.scan_time) = pt.entry_date
                WHERE ad.decision = 'approve' AND pt.status = 'CLOSED'
                  AND pt.pnl_pct IS NOT NULL
            """).fetchall()]
            veto_pnls = [r[0] for r in conn.execute("""
                SELECT pt.pnl_pct FROM agent_decisions ad
                JOIN paper_trades pt
                  ON ad.ticker = pt.ticker AND DATE(ad.scan_time) = pt.entry_date
                WHERE ad.decision = 'veto' AND pt.status = 'CLOSED'
                  AND pt.pnl_pct IS NOT NULL
            """).fetchall()]
            baseline_pnls = [r[0] for r in conn.execute(
                "SELECT pnl_pct FROM paper_trades WHERE status = 'CLOSED' AND pnl_pct IS NOT NULL"
            ).fetchall()]
        result["approve"] = _stats(approve_pnls)
        result["veto"] = _stats(veto_pnls)
        result["baseline"] = _stats(baseline_pnls)
    except Exception as _e:
        logging.getLogger(__name__).debug("cohort_summary error: %s", _e)
    return result


def _stats(pnls: list[float]) -> dict[str, Any]:
    if not pnls:
        return {"n": 0, "win_rate": 0.0, "avg_return_pct": 0.0, "sharpe": 0.0}
    n = len(pnls)
    win_rate = sum(1 for p in pnls if p > 0) / n
    avg = statistics.mean(pnls)
    try:
        std = statistics.stdev(pnls) if n >= 2 else 0.0
        sharpe = avg / std if std > 0 else 0.0
    except statistics.StatisticsError:
        sharpe = 0.0
    return {
        "n": n,
        "win_rate": round(win_rate, 4),
        "avg_return_pct": round(avg, 4),
        "sharpe": round(sharpe, 4),
    }
