import pytest

from engine.agent_firm.schemas import SignalCandidate, AgentResult, AgentDecision, AgentState


def test_agent_state_has_required_keys():
    c = SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.0, scan_time="2026-05-20T10:00:00+07:00",
    )
    # TypedDict — verify it can be instantiated as a plain dict with expected keys
    state: AgentState = {
        "candidate": c,
        "db_path": "/tmp/t.db",
        "context": {},
        "client": None,
        "technical_result": None,
        "flow_result": None,
        "regime_result": None,
        "news_result": None,
        "bull_result": None,
        "bear_result": None,
        "risk_result": None,
        "decision": None,
    }
    assert state["db_path"] == "/tmp/t.db"


def test_signal_candidate_minimal():
    c = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    assert c.ticker == "BBRI"
    assert c.regime is None
    assert c.indicators == {}


def test_signal_candidate_full():
    c = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
        regime="BULL", flow_verdict="STRONG_BUY",
        foreign_score=3.42, indicators={"vwma_above": True},
    )
    assert c.regime == "BULL"
    assert c.indicators["vwma_above"] is True


def test_agent_result_defaults():
    r = AgentResult(role="technical", status="ok")
    assert r.tokens_in == 0
    assert r.tokens_out == 0
    assert r.duration_s == 0.0
    assert r.tools_called == []
    assert r.error is None


def test_agent_decision_required_fields():
    d = AgentDecision(
        ticker="BBRI", strategy="momentum_following",
        scan_time="2026-05-19T16:00:00+07:00",
        quant_score=4.2, decision="approve",
    )
    assert d.decision == "approve"
    assert d.confidence is None
    assert d.traces == []


def test_agent_decision_rejects_invalid_decision():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AgentDecision(
            ticker="BBRI", strategy="momentum_following",
            scan_time="2026-05-19T16:00:00+07:00",
            quant_score=4.2, decision="maybe",
        )


def test_agent_result_provider_fields_default_empty():
    from engine.agent_firm.schemas import AgentResult
    r = AgentResult(role="technical", status="ok")
    assert r.provider == ""
    assert r.model == ""
    assert r.runtime_version == ""
    assert r.failover is False
    assert r.cost_usd == 0.0


def test_agent_decision_providers_used_defaults_empty_list():
    from engine.agent_firm.schemas import AgentDecision
    d = AgentDecision(
        ticker="BBRI", strategy="x", scan_time="t", quant_score=1.0, decision="approve",
    )
    assert d.providers_used == []


# ── WP1 (Foundation): new Tier 1/Tier 2 context objects — see
#    docs/agent_firm/ADR-AF-001..004 and docs/agent_firm/AF2_ARCHITECTURE_CERTIFICATION.md.
#    None of these are consumed anywhere yet — these tests verify construction,
#    validation, and serialization only. ──

def test_signal_candidate_new_context_fields_default_none_backward_compatible():
    """Existing call sites that construct SignalCandidate with only the original fields
    must keep working unchanged (AGENT_FIRM_GOVERNANCE.md: additive optional fields are
    MINOR, not MAJOR) — this is the direct backward-compatibility check for ADR-AF-004."""
    c = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    assert c.technical is None
    assert c.flow is None
    assert c.regime_context is None
    assert c.news is None
    assert c.market is None
    assert c.portfolio is None
    assert c.risk_limits is None
    assert c.execution is None


def test_signal_candidate_accepts_context_objects():
    from engine.agent_firm.schemas import TechnicalContext, FlowContext

    c = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
        technical=TechnicalContext(sma20=100.0, mechanical_direction="BULLISH"),
        flow=FlowContext(verdict="BULLISH", net_foreign_14d=5000),
    )
    assert c.technical.sma20 == 100.0
    assert c.technical.mechanical_direction == "BULLISH"
    assert c.flow.net_foreign_14d == 5000


def test_signal_candidate_serializes_nested_context_to_json():
    """These objects are JSON-dumped straight into LLM prompts (ADR-AF-002's serialization
    decision) — round-trip must preserve nested structure exactly."""
    import json
    from engine.agent_firm.schemas import TechnicalContext

    c = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
        technical=TechnicalContext(
            sma20=100.0, support_levels=[95.0, 90.0], mechanical_direction="BULLISH",
        ),
    )
    dumped = json.loads(c.model_dump_json())
    assert dumped["technical"]["sma20"] == 100.0
    assert dumped["technical"]["support_levels"] == [95.0, 90.0]
    assert dumped["technical"]["mechanical_direction"] == "BULLISH"


def test_agent_decision_size_tier_defaults_none_backward_compatible():
    d = AgentDecision(
        ticker="BBRI", strategy="x", scan_time="t", quant_score=1.0, decision="approve",
    )
    assert d.size_tier is None
    # size_hint's pre-existing behavior is unchanged by the new field's addition.
    assert d.size_hint is None


def test_agent_decision_rejects_invalid_size_tier():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AgentDecision(
            ticker="BBRI", strategy="x", scan_time="t", quant_score=1.0,
            decision="approve", size_tier="double_it",
        )


def test_agent_decision_accepts_valid_size_tier():
    d = AgentDecision(
        ticker="BBRI", strategy="x", scan_time="t", quant_score=1.0,
        decision="approve", size_tier="increase",
    )
    assert d.size_tier == "increase"


def test_portfolio_context_has_open_position_method():
    from engine.agent_firm.schemas import PortfolioContext

    p = PortfolioContext(open_trades=[{"ticker": "BBRI"}, {"ticker": "TLKM"}])
    assert p.has_open_position("BBRI") is True
    assert p.has_open_position("UNKNOWN") is False


@pytest.mark.parametrize("cls_name", [
    "TechnicalContext", "FlowContext", "RegimeContext", "NewsContext", "MarketContext",
    "PortfolioContext", "RiskContext", "ExecutionContext", "ConsensusContext",
])
def test_context_object_constructs_with_all_defaults(cls_name):
    """Every new context type must be constructible with zero arguments — required for
    the 'may exist unused, nothing consumes it yet' WP1 constraint."""
    from engine.agent_firm import schemas as _schemas

    cls = getattr(_schemas, cls_name)
    instance = cls()
    assert instance is not None
    # Must be JSON-serializable even in its default state.
    assert instance.model_dump_json() is not None


def test_session_context_requires_scan_time():
    from pydantic import ValidationError
    from engine.agent_firm.schemas import SessionContext

    with pytest.raises(ValidationError):
        SessionContext()
    s = SessionContext(scan_time="2026-07-29 08:35")
    assert s.wib_session == "regular"  # default before any derivation logic is applied
