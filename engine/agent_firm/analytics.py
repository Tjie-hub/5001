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


def agent_agreement(db_path: str) -> list[dict[str, Any]]:
    """Per-agent directional alignment with the final risk decision."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT at.role, at.output, ad.decision
                FROM agent_traces at
                JOIN agent_decisions ad ON at.decision_id = ad.id
                WHERE ad.decision IN ('approve', 'veto')
            """).fetchall()
    except Exception as _e:
        logging.getLogger(__name__).debug("agent_agreement error: %s", _e)
        return []

    from collections import defaultdict
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"decisions": 0, "aligned": 0})

    for row in rows:
        role = row["role"]
        decision = row["decision"]
        counts[role]["decisions"] += 1
        try:
            output = json.loads(row["output"] or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if _is_aligned(role, output, decision):
            counts[role]["aligned"] += 1

    result = []
    for role in ["technical", "flow", "regime", "news", "bull", "bear"]:
        if role in counts:
            d = counts[role]["decisions"]
            a = counts[role]["aligned"]
            result.append({
                "role": role,
                "decisions": d,
                "aligned": a,
                "agreement_pct": round(a / d * 100, 1) if d > 0 else 0.0,
            })
    return result


def _is_aligned(role: str, output: dict, decision: str) -> bool:
    is_approve = decision == "approve"
    if role == "technical":
        return (output.get("verdict") == "BULLISH") == is_approve
    if role == "flow":
        return (output.get("flow_verdict") == "ACCUMULATING") == is_approve
    if role == "regime":
        return (output.get("regime_call") == "BULL") == is_approve
    if role == "news":
        return (output.get("sentiment") == "BULLISH") == is_approve
    if role == "bull":
        return is_approve
    if role == "bear":
        return not is_approve
    return False


def decision_log(db_path: str, limit: int = 100) -> list[dict[str, Any]]:
    """Chronological log of decisions with matched paper trade outcomes."""
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT
                    DATE(ad.scan_time) AS date,
                    ad.ticker,
                    ad.strategy,
                    ad.decision,
                    ad.confidence,
                    ad.size_hint,
                    ad.rationale,
                    pt.status   AS outcome,
                    pt.pnl_pct
                FROM agent_decisions ad
                LEFT JOIN paper_trades pt
                    ON ad.ticker = pt.ticker
                   AND DATE(ad.scan_time) = pt.entry_date
                ORDER BY ad.created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
    except Exception as _e:
        logging.getLogger(__name__).debug("decision_log error: %s", _e)
        return []
