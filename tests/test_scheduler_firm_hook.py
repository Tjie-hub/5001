"""Tests for run_agent_firm_gate() in scheduler/scanner.py.

REMOVED 2026-09-15: universe-wide per-scan-cycle LLM gating (up to 20
candidates, up to 5x/day) was retired in favor of the strict 2-invocations-
per-trading-day contract (engine.agent_firm_daily; see
tests/test_agent_firm_daily.py and tests/test_eod_trade_plan_job.py /
tests/test_premarket_firm_scan.py for its coverage). run_agent_firm_gate()
is now a pure pass-through kept only so scheduled_multi_strategy_scan()'s
call site needs no change — these tests prove exactly that, and that it
never imports or calls the firm (so it can never make a billable LLM call).
"""
import sys

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


def test_gate_always_passes_flow_confirmed_through_unchanged():
    flow_confirmed = [_make_result("BBRI", flow_score=3, confirmed=True)]
    intersection_results = [_make_result("BBCA", flow_score=-2, confirmed=False)] + flow_confirmed

    result = run_agent_firm_gate(intersection_results, flow_confirmed,
                                 "2026-06-05", "08:00")

    assert result == flow_confirmed


def test_gate_passes_through_even_with_many_candidates():
    """No universe-wide scanning remains — a large intersection_results must not
    change the pass-through behavior (there is no cap to hit, because there is
    no evaluation at all anymore)."""
    intersection_results = [_make_result(f"TK{i:02d}", 1) for i in range(30)]
    flow_confirmed = intersection_results[:2]

    result = run_agent_firm_gate(intersection_results, flow_confirmed,
                                 "2026-06-05", "08:00")

    assert result == flow_confirmed


def test_gate_never_imports_or_touches_the_firm_module(monkeypatch):
    """Regression guard: the gate must not be able to make an LLM call, even by
    accident. A None entry in sys.modules makes any `from engine.agent_firm
    import firm` raise ImportError — the old body's try/except would have
    swallowed that as fail-open, but the new body never enters the import at
    all, so this must simply succeed and return flow_confirmed unchanged."""
    monkeypatch.setitem(sys.modules, "engine.agent_firm.firm", None)
    result = run_agent_firm_gate([_make_result("BBCA", 1)], [], "2026-06-05", "08:00")
    assert result == []
