"""Pydantic schemas for the agent firm.

Decision lifecycle:
  approve  — Risk Manager approved; signal proceeds to Telegram
  veto     — Risk Manager blocked; signal does not proceed (Phase 3+)
  bypassed — Firm was disabled or kill-switched; signal proceeds unevaluated
  degraded — Risk Manager call failed; signal proceeds (fail-open)

Context objects (TechnicalContext..ConsensusContext, below): the typed input contract for
the computation-boundary migration (docs/agent_firm/ADR-AF-001..004). Agent Firm owns these
type definitions per ADR-AF-002; Production Engine (engine/agent_firm_context.py) is the
sole assembler for the Tier 1 objects, and never re-derives a fact that already has a
canonical producer (ADR-AF-001). All fields are ephemeral — never persisted, JSON-dumped
into LLM prompts only (ADR-AF-002's persistence decision).

WP1 (Foundation) status: these types exist and are unit-tested but are not yet attached to
any live evaluation — SignalCandidate's new fields below all default to None and nothing in
firm.py/the agents reads them yet. Wiring is later work.
"""

from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# ── Context objects (ADR-AF-002 Tier 1, plus ConsensusContext as the documented Tier 2
#    exception) — see docs/agent_firm/AF1_CONTEXT_OBJECT_CATALOG.md for the full field-level
#    rationale and docs/agent_firm/ADR-AF-001-DETERMINISTIC_OWNERSHIP.md for why each
#    passthrough field is a passthrough rather than an independently-computed value. ──


class TechnicalContext(BaseModel):
    """Precomputed technical facts for one ticker. Replaces raw 60-bar OHLCV in the
    Technical Analyst prompt (Audit findings T1, T2). `mechanical_direction` is a
    passthrough of engine.technicals.tech_direction() — never re-derived (ADR-AF-001)."""
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    close_vs_sma50_pct: Optional[float] = None
    ma_slope_20: Optional[float] = None
    adx: Optional[float] = None
    atr: Optional[float] = None
    vol_ratio: Optional[float] = None
    support_levels: list[float] = Field(default_factory=list)
    resistance_levels: list[float] = Field(default_factory=list)
    pattern_flags: list[str] = Field(default_factory=list)
    mechanical_direction: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "NEUTRAL"
    ohlcv_recent_10d: list[dict[str, Any]] = Field(default_factory=list)


class FlowContext(BaseModel):
    """Precomputed flow facts for one ticker. `verdict`/`smart_money`/`composite_score`/
    `foreign_score` are passthroughs of stockbit_flow's own columns (flow_filter.py already
    computes them) — never re-derived (Audit findings F1, F2; ADR-AF-001)."""
    verdict: Optional[str] = None
    smart_money: Optional[str] = None
    composite_score: Optional[int] = None
    foreign_score: Optional[float] = None
    net_foreign_14d: Optional[int] = None
    trend_7d: Literal["accumulating", "distributing", "flat"] = "flat"
    flow_bars_recent: list[dict[str, Any]] = Field(default_factory=list)


class RegimeContext(BaseModel):
    """Precomputed regime facts for one ticker. `regime_call` is a passthrough of
    engine.regime_filter.detect_regime()'s market-wide reading — never a second,
    independently-thresholded classifier (Audit findings R1-R3; ADR-AF-001)."""
    regime_call: Literal["BULL", "BEAR", "SIDEWAYS", "VOLATILE", "UNKNOWN"] = "UNKNOWN"
    sector_tailwind: bool = False
    macro_risk: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    best_strategy: Optional[str] = None
    ticker_consistency_pct: Optional[float] = None
    recent_screen_signals: list[dict[str, Any]] = Field(default_factory=list)


class NewsContext(BaseModel):
    """News/catalyst facts for one ticker. `has_catalyst` is a passthrough of
    engine.catalyst.has_catalyst() — distinct from the News agent's own directional
    `catalyst_sentiment` output, which is genuine NLU, not a duplicate (ADR-AF-001)."""
    mentions_7d: list[dict[str, Any]] = Field(default_factory=list)
    mentions_count_7d: int = 0
    has_catalyst: bool = False
    web_search_results: list[dict[str, Any]] = Field(default_factory=list)


class MarketContext(BaseModel):
    """Market-wide (not ticker-specific) state, cached once per scan cycle."""
    regime: Literal["BULL", "BEAR", "SIDEWAYS", "VOLATILE", "UNKNOWN"] = "UNKNOWN"
    ihsg_trend: Optional[TechnicalContext] = None
    market_risk_score: Optional[float] = None


class PortfolioContext(BaseModel):
    """Currently open paper positions, cached once per scan cycle."""
    open_trades: list[dict[str, Any]] = Field(default_factory=list)
    open_position_count: int = 0

    def has_open_position(self, ticker: str) -> bool:
        return any(t.get("ticker") == ticker for t in self.open_trades)


class RiskContext(BaseModel):
    """The drawdown circuit breaker's live state, cached once per scan cycle. Closes the
    gap named in AF1_FAILURE_CONTRACT.md §6 — previously computed but never delivered to
    any agent."""
    entries_blocked: bool = False
    drawdown_pct: Optional[float] = None
    auth_mode: str = "off"


class ExecutionContext(BaseModel):
    """Capital/exposure state for sizing resolution (ADR-AF-003), cached once per scan
    cycle. Read-only — built from paper_trade.py's existing get_config()/get_open_trades(),
    never by modifying or duplicating open_trade()'s own inline computation."""
    capital: Optional[float] = None
    aggregate_open_exposure_pct: Optional[float] = None
    risk_pct_config: Optional[float] = None
    max_position_pct_config: float = 0.30


class SessionContext(BaseModel):
    scan_time: str
    wib_session: Literal["premarket", "regular", "post-close"] = "regular"


class ConsensusContext(BaseModel):
    """Tier 2 (ADR-AF-002): assembled by Agent Firm itself, after the analyst agents run —
    not a Tier 1 input. Type defined here for WP1 completeness; its builder
    (guardrails.py::build_consensus_summary()) is out of WP1's scope (no analyst wiring
    exists yet to consume it)."""
    negative_count: int = 0
    positive_count: int = 0
    aligned_bullish: int = 0
    already_open_position: bool = False
    entries_blocked: bool = False


class SignalCandidate(BaseModel):
    ticker: str
    strategy: str
    score: float
    scan_time: str
    regime: Optional[str] = None
    flow_verdict: Optional[str] = None
    foreign_score: Optional[float] = None
    indicators: dict[str, Any] = Field(default_factory=dict)

    # New in WP1 (ADR-AF-004): optional Tier 1 context, attached per candidate rather than
    # via a new evaluate() parameter — keeps evaluate()'s signature unchanged (MINOR, not
    # MAJOR, per AGENT_FIRM_GOVERNANCE.md's existing rule for additive optional fields).
    # All default to None; nothing constructs these yet outside this module's own tests.
    technical: Optional[TechnicalContext] = None
    flow: Optional[FlowContext] = None
    regime_context: Optional[RegimeContext] = None
    news: Optional[NewsContext] = None
    market: Optional[MarketContext] = None
    portfolio: Optional[PortfolioContext] = None
    risk_limits: Optional[RiskContext] = None
    execution: Optional[ExecutionContext] = None


class AgentResult(BaseModel):
    role: str
    status: Literal["ok", "failed"]
    output: Optional[dict[str, Any]] = None
    prompt_version: str = "v1"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
    tools_called: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    provider: str = ""
    model: str = ""
    runtime_version: str = ""
    failover: bool = False


class AgentDecision(BaseModel):
    ticker: str
    strategy: str
    scan_time: str
    quant_score: float
    decision: Literal["approve", "veto", "bypassed", "degraded"]
    confidence: Optional[float] = None
    # ADR-AF-003 (implemented): repurposed from "the LLM's raw numeric recommendation" to
    # "the final resolved value engine.position_sizing.resolve_size_hint() produced for this
    # candidate" — but that resolution happens in Production Engine (scheduler/scanner.py),
    # after this AgentDecision is already constructed and persisted, so firm.py itself always
    # leaves this None; closing that audit-trail loop is a deliberately deferred follow-up,
    # not performed by this change (see firm.py::_run_risk()'s own comment at the construction
    # site). Never read directly for executable sizing — engine.position_sizing.resolve_size_hint()
    # is the sole authority for that value (agent_size_hint on the scanner-side row dict).
    size_hint: Optional[float] = None
    # ADR-AF-003 (implemented): the Risk agent's qualitative sizing recommendation — the only
    # sizing signal Agent Firm itself may emit. engine.position_sizing.resolve_size_hint()
    # (Production Engine) combines this with any deterministic edge score to produce the
    # executable agent_size_hint; Agent Firm never writes that number directly.
    size_tier: Optional[Literal["reduce", "normal", "increase"]] = None
    rationale: Optional[str] = None
    traces: list[AgentResult] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
    providers_used: list[str] = Field(default_factory=list)


class AgentState(TypedDict):
    candidate: SignalCandidate
    db_path: str
    context: dict[str, Any]
    client: Any  # FirmLLMProvider (in practice, the ProviderRouter) — in-memory only, not serialized
    technical_result: Optional[AgentResult]
    flow_result: Optional[AgentResult]
    regime_result: Optional[AgentResult]
    news_result: Optional[AgentResult]
    bull_result: Optional[AgentResult]
    bear_result: Optional[AgentResult]
    risk_result: Optional[AgentResult]
    decision: Optional[AgentDecision]
