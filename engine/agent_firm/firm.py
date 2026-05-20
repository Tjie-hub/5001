"""Agent firm orchestrator. Phase 1: Technical -> Risk.

Public API:
  evaluate(candidates) -> list[AgentDecision]     # sync, scheduler-facing
  evaluate_async(candidates, client) -> ...       # async, for tests
"""

import asyncio
import json
import time

from . import config
from .agents import risk, technical
from .client import DeepSeekClient
from .schemas import AgentDecision, AgentResult, SignalCandidate


async def _evaluate_one(
    candidate: SignalCandidate,
    client: DeepSeekClient,
) -> AgentDecision:
    import data.db as _db
    db_path = str(_db.DB_PATH)

    start = time.monotonic()
    technical_result = await technical.run(candidate, client, db_path)
    risk_result = await risk.run(candidate, [technical_result], client)

    if risk_result.status == "failed":
        decision_str = "degraded"
        confidence = None
        size_hint = None
        rationale = "Agent firm degraded — quant signal passed through"
    else:
        out = risk_result.output or {}
        decision_str = out.get("decision", "degraded")
        confidence = out.get("confidence")
        size_hint = out.get("size_hint")
        rationale = out.get("rationale")

    traces = [technical_result, risk_result]
    tokens_in = sum(t.tokens_in for t in traces)
    tokens_out = sum(t.tokens_out for t in traces)
    cost_usd = DeepSeekClient._calc_cost(tokens_in, tokens_out)

    return AgentDecision(
        ticker=candidate.ticker,
        strategy=candidate.strategy,
        scan_time=candidate.scan_time,
        quant_score=candidate.score,
        decision=decision_str,
        confidence=confidence,
        size_hint=size_hint,
        rationale=rationale,
        traces=traces,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        duration_s=time.monotonic() - start,
    )


async def evaluate_async(
    candidates: list[SignalCandidate],
    client: DeepSeekClient | None = None,
) -> list[AgentDecision]:
    if client is None:
        client = DeepSeekClient()
    decisions = await asyncio.gather(
        *[_evaluate_one(c, client) for c in candidates]
    )
    for d in decisions:
        _persist(d)
    return list(decisions)


def evaluate(
    candidates: list[SignalCandidate],
    client: DeepSeekClient | None = None,
) -> list[AgentDecision]:
    if not config.is_active():
        return [
            AgentDecision(
                ticker=c.ticker,
                strategy=c.strategy,
                scan_time=c.scan_time,
                quant_score=c.score,
                decision="bypassed",
                rationale="Firm disabled",
            )
            for c in candidates
        ]
    return asyncio.run(evaluate_async(candidates, client))


def _persist(decision: AgentDecision) -> int:
    import data.db as _db
    conn = _db.get_db()
    try:
        cur = conn.execute(
            "INSERT OR REPLACE INTO agent_decisions "
            "(scan_time, ticker, strategy, quant_score, decision, confidence, "
            "size_hint, rationale, tokens_in, tokens_out, cost_usd, duration_s) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                decision.scan_time, decision.ticker, decision.strategy,
                decision.quant_score, decision.decision, decision.confidence,
                decision.size_hint, decision.rationale,
                decision.tokens_in, decision.tokens_out, decision.cost_usd,
                decision.duration_s,
            ),
        )
        decision_id = cur.lastrowid
        for trace in decision.traces:
            conn.execute(
                "INSERT INTO agent_traces "
                "(decision_id, role, prompt_version, output, tools_called, "
                "tokens_in, tokens_out, duration_s) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    decision_id, trace.role, trace.prompt_version,
                    None if trace.output is None else json.dumps(trace.output),
                    json.dumps(trace.tools_called),
                    trace.tokens_in, trace.tokens_out, trace.duration_s,
                ),
            )
        conn.commit()
        return decision_id
    finally:
        conn.close()
