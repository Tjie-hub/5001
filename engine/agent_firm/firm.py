"""Agent firm orchestrator. Phase 2: LangGraph DAG, 7 agents.

Public API:
  evaluate(candidates) -> list[AgentDecision]            # sync, full pipeline
  evaluate_staged(candidates) -> list[AgentDecision]     # sync, 2-stage pre-scan (Phase 3)
  evaluate_async(candidates, client) -> ...              # async, for tests
  reset_market_ctx() -> None                             # compat shim, see below

WP3 (Specialist Context Consumption Migration): analyst nodes (technical/flow/regime/news) no
longer receive a raw SQL-query context dict — they read typed Tier 1 context already attached
to the SignalCandidate by engine.agent_firm_context.py (WP2), per ADR-AF-002. This retires
_build_context()'s 7 raw queries entirely, per ADR-AF-002's "Required Implementation Changes"
("_build_context() is deleted, not replaced in place").
"""

import asyncio
import json

from langgraph.graph import END, StateGraph

from . import config
from .agents import bear, bull, flow, news, regime, risk, technical
from .guardrails import apply_guardrails, build_consensus_summary
from .providers.base import FirmLLMProvider
from .providers.factory import build_router
from .schemas import AgentDecision, AgentResult, AgentState, SignalCandidate
from .tools.sqlite_query import query


# ── Legacy market-context cache (Phase 3.2) — retained as a compat shim only ──
# _build_context() (this cache's sole consumer) is retired per ADR-AF-002/WP3; the cache it
# fed has moved to engine.agent_firm_context.py's _batch_ctx/reset_batch_context() (WP2).
# reset_market_ctx() itself is kept, unchanged, purely because scheduler/scanner.py still
# imports and calls it once per scan cycle (scanner.py is out of WP3's scope) — it is now an
# inert no-op flush of a cache nothing populates. Removing it requires a scanner.py edit,
# deferred to a future, scanner-touching work package.

_market_ctx: dict | None = None


def reset_market_ctx() -> None:
    """Compat shim for scheduler/scanner.py's existing call sites — no-op (see above)."""
    global _market_ctx
    _market_ctx = None


# ── Daily spend cap ───────────────────────────────────────────────────────────

def _spend_today() -> float:
    """Sum today's persisted agent cost (local date). Returns 0.0 on any error."""
    import datetime
    import data.db as _db
    try:
        rows = query(
            str(_db.DB_PATH),
            "SELECT COALESCE(SUM(cost_usd), 0.0) AS c FROM agent_decisions "
            "WHERE DATE(created_at) = ?",
            (datetime.date.today().isoformat(),),
        )
        return float(rows[0]["c"]) if rows else 0.0
    except Exception:
        return 0.0


def _over_daily_cap() -> bool:
    """True once today's spend has reached the configured daily cap."""
    cap = config.DAILY_SPEND_CAP_USD
    if cap <= 0:
        return False
    return _spend_today() >= cap


def _capped_decisions(candidates: list[SignalCandidate]) -> list[AgentDecision]:
    return [
        AgentDecision(
            ticker=c.ticker,
            strategy=c.strategy,
            scan_time=c.scan_time,
            quant_score=c.score,
            decision="bypassed",
            rationale=f"Daily spend cap reached (${config.DAILY_SPEND_CAP_USD:.2f})",
        )
        for c in candidates
    ]


# ── Analyst nodes ─────────────────────────────────────────────────────────────
# Each analyst reads its own typed Tier 1 context straight off `candidate` (attached by
# engine.agent_firm_context.py before evaluate/evaluate_staged is ever called, per WP2) —
# no per-scan context dict or db_path is built or threaded through the graph anymore.

async def _run_analysts(state: AgentState) -> dict:
    client = state["client"]
    candidate = state["candidate"]
    t, f, r, n = await asyncio.gather(
        technical.run(candidate, client),
        flow.run(candidate, client),
        regime.run(candidate, client),
        news.run(candidate, client),
    )
    return {
        "technical_result": t,
        "flow_result": f,
        "regime_result": r,
        "news_result": n,
    }


async def _run_bull(state: AgentState) -> dict:
    analysts = [
        state["technical_result"],
        state["flow_result"],
        state["regime_result"],
        state["news_result"],
    ]
    result = await bull.run(state["candidate"], analysts, state["client"])
    return {"bull_result": result}


async def _run_bear(state: AgentState) -> dict:
    analysts = [
        state["technical_result"],
        state["flow_result"],
        state["regime_result"],
        state["news_result"],
    ]
    result = await bear.run(state["candidate"], analysts, state["bull_result"], state["client"])
    return {"bear_result": result}


async def _run_risk(state: AgentState) -> dict:
    all_results = [
        state["technical_result"],
        state["flow_result"],
        state["regime_result"],
        state["news_result"],
        state["bull_result"],
        state["bear_result"],
    ]
    result = await risk.run(state["candidate"], all_results, state["client"])
    candidate = state["candidate"]

    if result.status == "failed":
        decision_str = "degraded"
        confidence = None
        size_tier = None
        rationale = "Agent firm degraded — quant signal passed through"
    else:
        out = result.output or {}
        decision_str = out.get("decision", "degraded")
        confidence = out.get("confidence")
        # AF-2 ADR-AF-003: the Risk agent recommends a qualitative size_tier, not a numeric
        # size_hint — engine.position_sizing.resolve_size_hint() (Production Engine) is now
        # the sole authority that turns this into the executable agent_size_hint number.
        size_tier = out.get("size_tier")
        rationale = out.get("rationale")
        # Deterministic guardrails (post-LLM): override approve→veto on a hard flow
        # contradiction, sub-floor confidence in a weak regime, ≥3 negative analyst
        # verdicts (K1, WP4), or an already-open position (K2, WP4). Keyed on analyst
        # verdicts and Tier 1 context (candidate.portfolio/.risk_limits, ADR-AF-002),
        # never the scale-inconsistent quant_score.
        analysts = [state["technical_result"], state["flow_result"],
                    state["regime_result"], state["news_result"]]
        consensus = build_consensus_summary(
            analysts, candidate.ticker,
            portfolio_ctx=candidate.portfolio, risk_ctx=candidate.risk_limits,
        )
        new_decision, override = apply_guardrails(
            decision_str, confidence, analysts, consensus=consensus,
        )
        if override:
            decision_str = new_decision
            size_tier = None
            rationale = f"[{override}] {rationale or ''}".strip()

    traces = [
        state["technical_result"], state["flow_result"],
        state["regime_result"], state["news_result"],
        state["bull_result"], state["bear_result"], result,
    ]
    tokens_in = sum(t.tokens_in for t in traces)
    tokens_out = sum(t.tokens_out for t in traces)
    cost_usd = sum(t.cost_usd for t in traces)
    providers_used = sorted({t.provider for t in traces if t.provider})

    decision = AgentDecision(
        ticker=candidate.ticker,
        strategy=candidate.strategy,
        scan_time=candidate.scan_time,
        quant_score=candidate.score,
        decision=decision_str,
        confidence=confidence,
        # AF-2 ADR-AF-003: size_hint is no longer set here — it is repurposed by the ADR to
        # eventually carry resolve_size_hint()'s final resolved value (Production Engine,
        # engine/position_sizing.py), which is not computed until after this decision has
        # already been persisted (see _persist(), below). Closing that audit-trail loop is
        # explicitly out of this change's scope (not listed in ADR-AF-003's "Required
        # Implementation Changes") — left None here, deliberately, rather than silently
        # inventing new cross-module persistence-update logic. size_tier is the Risk agent's
        # own qualitative recommendation, unchanged by this deferral.
        size_hint=None,
        size_tier=size_tier,
        rationale=rationale,
        traces=traces,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        duration_s=0.0,
        providers_used=providers_used,
    )
    return {"risk_result": result, "decision": decision}


# ── Persist node ──────────────────────────────────────────────────────────────

def _persist_node(state: AgentState) -> dict:
    _persist(state["decision"])
    return {}


# ── Graph compilation ─────────────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("run_analysts", _run_analysts)
    g.add_node("run_bull", _run_bull)
    g.add_node("run_bear", _run_bear)
    g.add_node("run_risk", _run_risk)
    g.add_node("persist", _persist_node)
    g.set_entry_point("run_analysts")
    g.add_edge("run_analysts", "run_bull")
    g.add_edge("run_bull", "run_bear")
    g.add_edge("run_bear", "run_risk")
    g.add_edge("run_risk", "persist")
    g.add_edge("persist", END)
    return g.compile()


_GRAPH = _build_graph()


# ── Public API ────────────────────────────────────────────────────────────────

async def evaluate_async(
    candidates: list[SignalCandidate],
    client: FirmLLMProvider | None = None,
) -> list[AgentDecision]:
    if client is None:
        client = build_router()
    initial_states = [
        AgentState(
            candidate=c,
            # db_path/context are vestigial AgentState keys nothing reads anymore
            # (see _run_analysts) — populated empty only because AgentState's
            # TypedDict shape still declares them (schemas.py is out of WP3's scope).
            db_path="",
            context={},
            client=client,
            technical_result=None,
            flow_result=None,
            regime_result=None,
            news_result=None,
            bull_result=None,
            bear_result=None,
            risk_result=None,
            decision=None,
        )
        for c in candidates
    ]
    results = await asyncio.gather(*[_GRAPH.ainvoke(s) for s in initial_states])
    return [r["decision"] for r in results]


def evaluate(
    candidates: list[SignalCandidate],
    client: FirmLLMProvider | None = None,
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
    if _over_daily_cap():
        return _capped_decisions(candidates)
    return asyncio.run(evaluate_async(candidates, client))


# ── Phase 3: Two-stage pre-scan ───────────────────────────────────────────────

async def _run_stage1(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
) -> tuple[AgentResult, AgentResult]:
    """Stage 1: technical + regime in parallel (~$0.004 per candidate). Both read their
    typed Tier 1 context straight off `candidate`, same as the full pipeline's analyst node."""
    return await asyncio.gather(
        technical.run(candidate, client),
        regime.run(candidate, client),
    )


def _is_both_bearish(tech: AgentResult, reg: AgentResult) -> bool:
    tech_bearish = tech.status == "ok" and (tech.output or {}).get("verdict") == "BEARISH"
    reg_bearish = reg.status == "ok" and (reg.output or {}).get("regime_call") == "BEAR"
    return tech_bearish and reg_bearish


async def evaluate_staged_async(
    candidates: list[SignalCandidate],
    client: FirmLLMProvider | None = None,
) -> list[AgentDecision]:
    """
    Two-stage evaluation:
      Stage 1 (cheap): technical + regime per candidate in parallel.
      Both bearish → auto-VETO (saves ~$0.011 per candidate).
      At least one bullish → Stage 2: full 7-agent pipeline.
    In bear markets, 60-80% of candidates fail Stage 1.
    """
    if client is None:
        client = build_router()

    stage1_pairs = await asyncio.gather(*[_run_stage1(c, client) for c in candidates])

    vetoed: list[AgentDecision] = []
    stage2_candidates: list[SignalCandidate] = []

    for candidate, (tech_r, reg_r) in zip(candidates, stage1_pairs):
        if _is_both_bearish(tech_r, reg_r):
            tokens_in = tech_r.tokens_in + reg_r.tokens_in
            tokens_out = tech_r.tokens_out + reg_r.tokens_out
            cost_usd = tech_r.cost_usd + reg_r.cost_usd
            providers_used = sorted({p for p in (tech_r.provider, reg_r.provider) if p})
            decision = AgentDecision(
                ticker=candidate.ticker,
                strategy=candidate.strategy,
                scan_time=candidate.scan_time,
                quant_score=candidate.score,
                decision="veto",
                rationale="Stage 1 pre-screen: technical BEARISH + regime BEAR",
                traces=[tech_r, reg_r],
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                duration_s=0.0,
                providers_used=providers_used,
            )
            vetoed.append(decision)
            _persist(decision)
        else:
            stage2_candidates.append(candidate)

    stage2_decisions = await evaluate_async(stage2_candidates, client) if stage2_candidates else []
    return vetoed + stage2_decisions


def evaluate_staged(
    candidates: list[SignalCandidate],
    client: FirmLLMProvider | None = None,
) -> list[AgentDecision]:
    """Sync wrapper for evaluate_staged_async. Use instead of evaluate() in bear markets."""
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
    if _over_daily_cap():
        return _capped_decisions(candidates)
    return asyncio.run(evaluate_staged_async(candidates, client))


# ── Persistence ───────────────────────────────────────────────────────────────

def _persist(decision: AgentDecision) -> int:
    import data.db as _db
    conn = _db.get_db()
    try:
        cur = conn.execute(
            "INSERT OR REPLACE INTO agent_decisions "
            "(scan_time, ticker, strategy, quant_score, decision, confidence, "
            "size_hint, size_tier, rationale, tokens_in, tokens_out, cost_usd, duration_s, "
            "providers_used) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                decision.scan_time, decision.ticker, decision.strategy,
                decision.quant_score, decision.decision, decision.confidence,
                decision.size_hint, decision.size_tier, decision.rationale,
                decision.tokens_in, decision.tokens_out, decision.cost_usd,
                decision.duration_s, json.dumps(decision.providers_used),
            ),
        )
        decision_id = cur.lastrowid
        for trace in decision.traces:
            conn.execute(
                "INSERT INTO agent_traces "
                "(decision_id, role, prompt_version, output, tools_called, "
                "tokens_in, tokens_out, cost_usd, duration_s, provider, model, "
                "runtime_version, failover, error) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    decision_id, trace.role, trace.prompt_version,
                    None if trace.output is None else json.dumps(trace.output),
                    json.dumps(trace.tools_called),
                    trace.tokens_in, trace.tokens_out, trace.cost_usd, trace.duration_s,
                    trace.provider, trace.model, trace.runtime_version,
                    int(trace.failover), trace.error,
                ),
            )
        conn.commit()
        return decision_id
    finally:
        conn.close()
