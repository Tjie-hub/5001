"""Query-based provider health/ops metrics, computed from agent_traces +
provider_events (design doc §12). No live metrics infra (Prometheus/StatsD)
— same report-time-query pattern as engine/health_report.py."""

import datetime
import statistics
from typing import Literal, Optional

from pydantic import BaseModel

from ..tools.sqlite_query import query


class ProviderStats(BaseModel):
    calls: int
    failures: int
    timeouts: int
    daily_calls: int
    success_rate: float
    failure_rate: float
    timeout_rate: float
    failover_rate: float
    avg_latency_s: float
    p50_latency_s: float
    p95_latency_s: float
    circuit_state: Literal["CLOSED", "OPEN", "HALF_OPEN"]
    cost_usd: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * pct))
    return sorted_vals[idx]


def provider_stats(db_path: str, provider: str, since: str) -> ProviderStats:
    rows = query(
        db_path,
        "SELECT duration_s, error, cost_usd, tokens_in, tokens_out FROM agent_traces "
        "WHERE provider = ? AND created_at >= ?",
        (provider, since),
    )
    calls = len(rows)
    failures = sum(1 for r in rows if r["error"] is not None)
    timeouts = sum(1 for r in rows if r["error"] and "timed out" in r["error"].lower())
    durations = sorted(float(r["duration_s"] or 0.0) for r in rows)

    today = datetime.date.today().isoformat()
    daily_rows = query(
        db_path,
        "SELECT COUNT(*) AS c FROM agent_traces WHERE provider = ? AND DATE(created_at) = ?",
        (provider, today),
    )
    daily_calls = int(daily_rows[0]["c"]) if daily_rows else 0

    failover_rows = query(
        db_path,
        "SELECT COUNT(*) AS c FROM provider_events "
        "WHERE provider = ? AND event_type = 'provider_failover' AND created_at >= ?",
        (provider, since),
    )
    failovers = int(failover_rows[0]["c"]) if failover_rows else 0

    circuit_rows = query(
        db_path,
        "SELECT event_type FROM provider_events WHERE provider = ? "
        "AND event_type IN ('provider_circuit_open', 'provider_circuit_closed') "
        "ORDER BY created_at DESC LIMIT 1",
        (provider,),
    )
    circuit_state = "CLOSED"
    if circuit_rows and circuit_rows[0]["event_type"] == "provider_circuit_open":
        circuit_state = "OPEN"

    is_zai = provider == "zai"
    cost_usd = sum(float(r["cost_usd"] or 0.0) for r in rows) if is_zai else None
    tokens_in = sum(int(r["tokens_in"] or 0) for r in rows) if is_zai else None
    tokens_out = sum(int(r["tokens_out"] or 0) for r in rows) if is_zai else None

    return ProviderStats(
        calls=calls,
        failures=failures,
        timeouts=timeouts,
        daily_calls=daily_calls,
        success_rate=(calls - failures) / calls if calls else 1.0,
        failure_rate=failures / calls if calls else 0.0,
        timeout_rate=timeouts / calls if calls else 0.0,
        failover_rate=failovers / calls if calls else 0.0,
        avg_latency_s=statistics.fmean(durations) if durations else 0.0,
        p50_latency_s=_percentile(durations, 0.50),
        p95_latency_s=_percentile(durations, 0.95),
        circuit_state=circuit_state,
        cost_usd=cost_usd, tokens_in=tokens_in, tokens_out=tokens_out,
    )
