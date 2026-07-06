"""Tests for run_agent_firm_gate() in scheduler/scanner.py.

Phase 1 behavior: agent evaluates intersection_results (all strategy signals),
not flow_confirmed (the flow-gated subset). This unblocks the agent in bear
markets where flow_confirmed is always empty.
"""
import sys
from unittest.mock import MagicMock

from engine.agent_firm.schemas import SignalCandidate
from scheduler.scanner import run_agent_firm_gate


def _make_result(ticker, flow_score, confirmed=False):
    return {
        "ticker": ticker,
        "strategies": ["vol_weighted"],
        "flow": {"score": flow_score, "verdict": "SELL" if flow_score < 0 else "BUY",
                 "smart_money": "NO", "confirmed": confirmed},
        "signal_reasons": ["vol_weighted: signal"],
        "signal_details": {"vol_weighted": {"price": 1000}},
    }


def _mock_firm_module(evaluate_fn):
    m = MagicMock()
    m.evaluate_staged = MagicMock(side_effect=evaluate_fn)
    return m


def _mock_config_module(is_active=True, get_enforce=False):
    m = MagicMock()
    m.is_active = MagicMock(return_value=is_active)
    m.get_enforce = MagicMock(return_value=get_enforce)
    return m


def _call_gate(intersection_results, flow_confirmed, mock_firm, mock_cfg,
               date_str="2026-06-05", time_str="08:00"):
    """Call run_agent_firm_gate() with mocked engine.agent_firm dependencies.

    The gate does ``from engine.agent_firm import firm`` / ``import config`` lazily,
    which resolves to attributes on the already-imported package. Patch both the
    package attributes and sys.modules so mocking is robust regardless of whether
    the real submodules were imported by an earlier test in the same session.
    """
    import engine.agent_firm as _pkg
    from unittest.mock import patch
    with patch.object(_pkg, "firm", mock_firm), \
         patch.object(_pkg, "config", mock_cfg), \
         patch.dict(sys.modules, {
             "engine.agent_firm.firm": mock_firm,
             "engine.agent_firm.config": mock_cfg,
         }):
        return run_agent_firm_gate(
            intersection_results, flow_confirmed, date_str, time_str
        )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_gate_skipped_when_firm_disabled():
    """Agent gate is a no-op when firm is disabled — flow_confirmed passes through unchanged."""
    flow_confirmed = [_make_result("BBRI", flow_score=3, confirmed=True)]
    intersection_results = list(flow_confirmed)

    result = _call_gate(intersection_results, flow_confirmed,
                        _mock_firm_module(lambda c: []),
                        _mock_config_module(is_active=False))

    assert result == flow_confirmed


def test_gate_evaluates_from_intersection_when_flow_confirmed_empty():
    """Bear market: flow_confirmed is empty but agent still evaluates intersection_results."""
    evaluate_calls = []
    intersection_results = [_make_result("BBCA", flow_score=-2, confirmed=False)]
    flow_confirmed = []

    _call_gate(intersection_results, flow_confirmed,
               _mock_firm_module(lambda c: evaluate_calls.append(c) or []),
               _mock_config_module(is_active=True))

    assert len(evaluate_calls) == 1, "agent should run even when flow_confirmed is empty"
    assert evaluate_calls[0][0].ticker == "BBCA"
    assert evaluate_calls[0][0].score == -2.0  # flow score as evidence, not a gate


def test_gate_candidates_capped_at_20():
    """Cost guard: agent evaluates at most 20 tickers regardless of intersection_results size."""
    evaluate_calls = []
    intersection_results = [_make_result(f"TK{i:02d}", 1) for i in range(30)]

    _call_gate(intersection_results, [],
               _mock_firm_module(lambda c: evaluate_calls.append(c) or []),
               _mock_config_module(is_active=True))

    assert len(evaluate_calls) == 1
    assert len(evaluate_calls[0]) == 20, "must cap at 20 candidates for cost control"


def test_gate_idle_log_when_intersection_empty(capsys):
    """When intersection_results is empty, agent logs idle instead of silently skipping."""
    _call_gate([], [],
               _mock_firm_module(lambda c: []),
               _mock_config_module(is_active=True))

    assert "Agent firm: idle" in capsys.readouterr().out


def test_gate_shadow_mode_does_not_filter_flow_confirmed():
    """Shadow mode: agent evaluates but flow_confirmed for paper trades is unchanged."""
    approved = MagicMock(ticker="AMMN", decision="approve")
    vetoed = MagicMock(ticker="MDKA", decision="veto")

    flow_confirmed = [
        _make_result("AMMN", flow_score=1, confirmed=True),
        _make_result("MDKA", flow_score=2, confirmed=True),
    ]

    result = _call_gate(flow_confirmed, flow_confirmed,
                        _mock_firm_module(lambda c: [approved, vetoed]),
                        _mock_config_module(is_active=True, get_enforce=False))

    assert len(result) == 2  # shadow mode: both pass through


def test_gate_enforce_mode_filters_from_intersection_results():
    """Enforce mode: approved set comes from intersection_results, not flow_confirmed."""
    approved = MagicMock(ticker="AMMN", decision="approve")
    vetoed = MagicMock(ticker="MDKA", decision="veto")

    intersection_results = [
        _make_result("AMMN", flow_score=1, confirmed=False),
        _make_result("MDKA", flow_score=-1, confirmed=False),
    ]

    result = _call_gate(intersection_results, [],
                        _mock_firm_module(lambda c: [approved, vetoed]),
                        _mock_config_module(is_active=True, get_enforce=True))

    assert len(result) == 1
    assert result[0]["ticker"] == "AMMN"


def test_enforce_degraded_non_flow_confirmed_is_dropped(monkeypatch):
    """C-9 fix: degraded (LLM failed) on a NON-flow-confirmed ticker falls back
    to the flow gate → dropped. Explicit approve still promotes."""
    import engine.fail_open_alarm as fa
    monkeypatch.setattr(fa, "fail_open_alarm", lambda *a, **k: "")
    approved = MagicMock(ticker="AMMN", decision="approve")
    degraded = MagicMock(ticker="MDKA", decision="degraded")

    intersection_results = [
        _make_result("AMMN", flow_score=1, confirmed=False),
        _make_result("MDKA", flow_score=1, confirmed=False),
    ]

    result = _call_gate(intersection_results, [],
                        _mock_firm_module(lambda c: [approved, degraded]),
                        _mock_config_module(is_active=True, get_enforce=True))

    assert {r["ticker"] for r in result} == {"AMMN"}, \
        "approve promotes; degraded non-flow-confirmed is dropped"


def test_enforce_degraded_flow_confirmed_is_kept(monkeypatch):
    """degraded on a flow-confirmed ticker falls back to flow → kept."""
    import engine.fail_open_alarm as fa
    monkeypatch.setattr(fa, "fail_open_alarm", lambda *a, **k: "")
    degraded = MagicMock(ticker="BBRI", decision="degraded")

    flow_confirmed = [_make_result("BBRI", flow_score=3, confirmed=True)]
    intersection_results = list(flow_confirmed)

    result = _call_gate(intersection_results, flow_confirmed,
                        _mock_firm_module(lambda c: [degraded]),
                        _mock_config_module(is_active=True, get_enforce=True))

    assert {r["ticker"] for r in result} == {"BBRI"}


def test_enforce_veto_drops_flow_confirmed(monkeypatch):
    """Explicit veto wins over the flow gate — a flow-confirmed veto is dropped."""
    import engine.fail_open_alarm as fa
    monkeypatch.setattr(fa, "fail_open_alarm", lambda *a, **k: "")
    vetoed = MagicMock(ticker="MDKA", decision="veto")
    approved = MagicMock(ticker="BBRI", decision="approve")

    flow_confirmed = [
        _make_result("MDKA", flow_score=3, confirmed=True),
        _make_result("BBRI", flow_score=3, confirmed=True),
    ]
    intersection_results = list(flow_confirmed)

    result = _call_gate(intersection_results, flow_confirmed,
                        _mock_firm_module(lambda c: [vetoed, approved]),
                        _mock_config_module(is_active=True, get_enforce=True))

    assert {r["ticker"] for r in result} == {"BBRI"}


def test_enforce_outage_fires_fail_open_alarm(monkeypatch):
    """Any degraded/bypassed present → a single visible fail-open alarm fires."""
    import engine.fail_open_alarm as fa
    calls = []
    monkeypatch.setattr(fa, "fail_open_alarm",
                        lambda *a, **k: calls.append((a, k)) or "")
    degraded = MagicMock(ticker="MDKA", decision="degraded")
    bypassed = MagicMock(ticker="ANTM", decision="bypassed")

    intersection_results = [
        _make_result("MDKA", flow_score=1, confirmed=False),
        _make_result("ANTM", flow_score=1, confirmed=False),
    ]

    _call_gate(intersection_results, [],
               _mock_firm_module(lambda c: [degraded, bypassed]),
               _mock_config_module(is_active=True, get_enforce=True))

    assert len(calls) == 1, "outage must alarm exactly once per gate call"
