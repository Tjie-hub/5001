from engine.agent_firm.schemas import SignalCandidate, AgentResult, AgentDecision


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
        regime="TRENDING", flow_verdict="STRONG_BUY",
        foreign_score=3.42, indicators={"vwma_above": True},
    )
    assert c.regime == "TRENDING"
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
