"""Agent firm orchestrator. Phase 2: LangGraph DAG, 7 agents.

Public API:
  evaluate(candidates) -> list[AgentDecision]            # sync, full pipeline
  evaluate_staged(candidates) -> list[AgentDecision]     # sync, 2-stage pre-scan (Phase 3)
  evaluate_async(candidates, client) -> ...              # async, for tests
  reset_market_ctx() -> None                             # call at scan start to flush cache
"""

import asyncio
import json
import time

from langgraph.graph import END, StateGraph

from . import config
from .agents import bear, bull, flow, news, regime, risk, technical
from .client import DeepSeekClient
from .guardrails import apply_guardrails
from .schemas import AgentDecision, AgentResult, AgentState, SignalCandidate
from .tools import news_lookup
from .tools.sqlite_query import query


# ── Shared market context cache (Phase 3.2) ───────────────────────────────────
# Reset once per scan batch via reset_market_ctx(); avoids N redundant queries
# for open_trades and IHSG data when evaluating N candidates.

_market_ctx: dict | None = None


def reset_market_ctx() -> None:
    """Call at the start of each scan batch to flush the per-scan market cache."""
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


# ── Context pre-fetch ────────────────────────────────────────────────────────

def _build_context(state: AgentState) -> dict:
    global _market_ctx
    import data.db as _db
    db_path = str(_db.DB_PATH)
    ticker = state["candidate"].ticker

    if _market_ctx is None:
        _market_ctx = {
            "open_trades": query(
                db_path,
                "SELECT ticker, entry_price, lots, tp_price, sl_price "
                "FROM paper_trades WHERE status='OPEN'",
            ),
            "ihsg": query(
                db_path,
                "SELECT date, close FROM ohlcv WHERE ticker='IHSG' ORDER BY date DESC LIMIT 20",
            ),
        }

    context = {
        "ohlcv": query(
            db_path,
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker=? ORDER BY date DESC LIMIT 60",
            (ticker,),
        ),
        "broker_flow": query(
            db_path,
            "SELECT trade_date, broker_code, side, lot_value, investor_type FROM broker_flow "
            "WHERE ticker=? AND trade_date >= date('now', '-14 days') ORDER BY trade_date DESC",
            (ticker,),
        ),
        "stockbit_flow": query(
            db_path,
            "SELECT trade_date, buy_lot, sell_lot, net_lot, net_value, verdict, "
            "smart_money, foreign_score, composite_score FROM stockbit_flow "
            "WHERE ticker=? AND trade_date >= date('now', '-14 days') ORDER BY trade_date DESC",
            (ticker,),
        ),
        "stockbit_flow_bars": query(
            db_path,
            "SELECT trade_date, bar_time, buy_lot, sell_lot, delta, net_value "
            "FROM stockbit_flow_bars "
            "WHERE ticker=? AND trade_date >= date('now', '-7 days') "
            "ORDER BY trade_date DESC, bar_time",
            (ticker,),
        ),
        "wf_scores": query(
            db_path,
            "SELECT strategy, consistency_pct, avg_return_pct, avg_sharpe, weighted_score "
            "FROM wf_scores WHERE ticker=? ORDER BY weighted_score DESC",
            (ticker,),
        ),
        "sector_data": query(
            db_path,
            "SELECT date, signal, vpin_label, vol_ratio FROM daily_screen "
            "WHERE ticker=? ORDER BY date DESC LIMIT 10",
            (ticker,),
        ),
        "news_mentions": news_lookup.lookup(db_path, ticker, days=7),
        "open_trades": _market_ctx["open_trades"],
        "ihsg": _market_ctx["ihsg"],
    }
    return {"db_path": db_path, "context": context}


# ── Analyst nodes ─────────────────────────────────────────────────────────────

async def _run_analysts(state: AgentState) -> dict:
    client = state["client"]
    candidate = state["candidate"]
    ctx = state["context"]
    db_path = state["db_path"]
    t, f, r, n = await asyncio.gather(
        technical.run(candidate, client, db_path),
        flow.run(candidate, client, ctx),
        regime.run(candidate, client, ctx),
        news.run(candidate, client, ctx),
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

    if result.status == "failed":
        decision_str = "degraded"
        confidence = None
        size_hint = None
        rationale = "Agent firm degraded — quant signal passed through"
    else:
        out = result.output or {}
        decision_str = out.get("decision", "degraded")
        confidence = out.get("confidence")
        size_hint = out.get("size_hint")
        rationale = out.get("rationale")
        # Deterministic guardrails (post-LLM): override approve→veto on a hard
        # flow contradiction or sub-floor confidence in a weak regime. Keyed on
        # analyst verdicts, not the scale-inconsistent quant_score.
        analysts = [state["technical_result"], state["flow_result"],
                    state["regime_result"], state["news_result"]]
        new_decision, override = apply_guardrails(decision_str, confidence, analysts)
        if override:
            decision_str = new_decision
            size_hint = 0.0
            rationale = f"[{override}] {rationale or ''}".strip()

    traces = [
        state["technical_result"], state["flow_result"],
        state["regime_result"], state["news_result"],
        state["bull_result"], state["bear_result"], result,
    ]
    tokens_in = sum(t.tokens_in for t in traces)
    tokens_out = sum(t.tokens_out for t in traces)
    cost_usd = DeepSeekClient._calc_cost(tokens_in, tokens_out)
    candidate = state["candidate"]

    decision = AgentDecision(
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
        duration_s=0.0,
    )
    return {"risk_result": result, "decision": decision}


# ── Persist node ──────────────────────────────────────────────────────────────

def _persist_node(state: AgentState) -> dict:
    _persist(state["decision"])
    return {}


# ── Graph compilation ─────────────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(AgentState)
    g.add_node("build_context", _build_context)
    g.add_node("run_analysts", _run_analysts)
    g.add_node("run_bull", _run_bull)
    g.add_node("run_bear", _run_bear)
    g.add_node("run_risk", _run_risk)
    g.add_node("persist", _persist_node)
    g.set_entry_point("build_context")
    g.add_edge("build_context", "run_analysts")
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
    client: DeepSeekClient | None = None,
) -> list[AgentDecision]:
    if client is None:
        client = DeepSeekClient()
    initial_states = [
        AgentState(
            candidate=c,
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
    if _over_daily_cap():
        return _capped_decisions(candidates)
    return asyncio.run(evaluate_async(candidates, client))


# ── Phase 3: Two-stage pre-scan ───────────────────────────────────────────────

async def _run_stage1(
    candidate: SignalCandidate,
    client: DeepSeekClient,
) -> tuple[AgentResult, AgentResult]:
    """Stage 1: technical + regime in parallel (~$0.004 per candidate)."""
    import data.db as _db
    db_path = str(_db.DB_PATH)
    ctx = {
        "wf_scores": query(
            db_path,
            "SELECT strategy, consistency_pct, avg_return_pct, avg_sharpe, weighted_score "
            "FROM wf_scores WHERE ticker=? ORDER BY weighted_score DESC",
            (candidate.ticker,),
        ),
        "sector_data": query(
            db_path,
            "SELECT date, signal, vpin_label, vol_ratio FROM daily_screen "
            "WHERE ticker=? ORDER BY date DESC LIMIT 10",
            (candidate.ticker,),
        ),
    }
    return await asyncio.gather(
        technical.run(candidate, client, db_path),
        regime.run(candidate, client, ctx),
    )


def _is_both_bearish(tech: AgentResult, reg: AgentResult) -> bool:
    tech_bearish = tech.status == "ok" and (tech.output or {}).get("verdict") == "BEARISH"
    reg_bearish = reg.status == "ok" and (reg.output or {}).get("regime_call") == "BEAR"
    return tech_bearish and reg_bearish


async def evaluate_staged_async(
    candidates: list[SignalCandidate],
    client: DeepSeekClient | None = None,
) -> list[AgentDecision]:
    """
    Two-stage evaluation:
      Stage 1 (cheap): technical + regime per candidate in parallel.
      Both bearish → auto-VETO (saves ~$0.011 per candidate).
      At least one bullish → Stage 2: full 7-agent pipeline.
    In bear markets, 60-80% of candidates fail Stage 1.
    """
    if client is None:
        client = DeepSeekClient()

    stage1_pairs = await asyncio.gather(*[_run_stage1(c, client) for c in candidates])

    vetoed: list[AgentDecision] = []
    stage2_candidates: list[SignalCandidate] = []

    for candidate, (tech_r, reg_r) in zip(candidates, stage1_pairs):
        if _is_both_bearish(tech_r, reg_r):
            tokens_in = tech_r.tokens_in + reg_r.tokens_in
            tokens_out = tech_r.tokens_out + reg_r.tokens_out
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
                cost_usd=DeepSeekClient._calc_cost(tokens_in, tokens_out),
                duration_s=0.0,
            )
            vetoed.append(decision)
            _persist(decision)
        else:
            stage2_candidates.append(candidate)

    stage2_decisions = await evaluate_async(stage2_candidates, client) if stage2_candidates else []
    return vetoed + stage2_decisions


def evaluate_staged(
    candidates: list[SignalCandidate],
    client: DeepSeekClient | None = None,
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
