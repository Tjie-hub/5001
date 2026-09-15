"""AF-2 WP2 (Context Producer Migration) — historically covered scheduler/scanner.py's two
SignalCandidate construction sites (run_agent_firm_gate, rank_bear_watchlist_and_notify)
populating Tier 1 context via engine.agent_firm_context.build_candidate_context() before
calling evaluate_staged().

REMOVED 2026-09-15: both call sites were neutered to pure pass-throughs/no-ops (universe-
wide per-scan-cycle LLM gating was retired — see tests/test_scheduler_firm_hook.py and
tests/test_bear_watchlist_ranking.py) — neither constructs a SignalCandidate or calls
build_candidate_context() anymore, so there is no Tier 1 context wiring left to verify at
these two sites. Tier 1 context wiring for the two call sites that remain in the strict
2-invocations-per-day contract (scheduler.jobs.run_eod_trade_plan /
run_premarket_firm_scan) is covered by tests/test_eod_trade_plan_job.py and
tests/test_premarket_firm_scan.py; engine.agent_firm_context's own producer-mapping
correctness is covered directly by tests/test_agent_firm_context.py, unaffected by this
change.
"""
import engine.agent_firm_context as afc
from scheduler.scanner import run_agent_firm_gate, rank_bear_watchlist_and_notify


def _make_result(ticker, flow_score=3):
    return {
        "ticker": ticker,
        "strategies": ["vol_weighted"],
        "flow": {"score": flow_score, "verdict": "BUY", "smart_money": "YES", "confirmed": True},
        "signal_reasons": ["vol_weighted: signal"],
        "signal_details": {"vol_weighted": {"price": 1000}},
    }


def test_run_agent_firm_gate_never_builds_context(monkeypatch):
    calls = []
    monkeypatch.setattr(afc, "build_candidate_context",
                        lambda *a, **k: calls.append(1) or {})
    run_agent_firm_gate([_make_result("BBRI")], [], "2026-07-29", "10:00", market_risk_score=42.0)
    assert calls == []


def test_rank_bear_watchlist_never_builds_context(monkeypatch):
    calls = []
    monkeypatch.setattr(afc, "build_candidate_context",
                        lambda *a, **k: calls.append(1) or {})
    rank_bear_watchlist_and_notify(["MDKA"], "2026-07-29", "10:00", market_risk_score=17.5)
    assert calls == []
