"""Stage-1 result reuse (2026-09-16 cost fix).

Production audit (2026-09-15 EOD run) found every Stage-1 survivor cost 9 LLM calls:
Stage 1 (technical + regime, 2 calls) whose results were discarded, then Stage 2
(technical + flow + regime + news + bull + bear + risk, 7 calls) recomputing technical/
regime from scratch. This suite locks in the fix: for a survivor, Stage 1's own
technical/regime AgentResult objects are carried into Stage 2's graph state and reused
verbatim (firm.py::_run_analysts()'s reuse check, wired via firm.py::_run_stage2()) --
Stage 2 only makes 5 new calls (flow, news, bull, bear, risk), for 7 total per survivor.

Both-bearish auto-veto (no Stage 2 at all) and the plain evaluate()/evaluate_async() path
(exit-veto, callers with no Stage 1) are unchanged -- covered here as regressions.
"""
import sqlite3

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _seed_db(db_path):
    from data.db import init_agent_firm_tables
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS ohlcv (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, date TEXT,
        open REAL, high REAL, low REAL, close REAL, volume REAL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS stockbit_flow (
        ticker TEXT, trade_date TEXT, buy_lot INTEGER, sell_lot INTEGER,
        net_lot INTEGER, net_value INTEGER, verdict TEXT, smart_money TEXT,
        foreign_score REAL, composite_score INTEGER, updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS broker_flow (
        ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT,
        lot_value INTEGER, investor_type TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS stockbit_flow_bars (
        ticker TEXT, trade_date TEXT, bar_time TEXT, buy_lot INTEGER,
        sell_lot INTEGER, delta INTEGER, net_value INTEGER)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS wf_scores (
        ticker TEXT, strategy TEXT, consistency_pct REAL,
        avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_screen (
        id INTEGER PRIMARY KEY, date TEXT, ticker TEXT, close INTEGER,
        vol_ratio REAL, signal TEXT, vpin_label TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS news_mentions (
        ticker TEXT, date TEXT, count INTEGER, headlines_json TEXT, updated_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY, ticker TEXT, status TEXT,
        entry_price REAL, lots INTEGER, tp_price REAL, sl_price REAL)""")
    conn.commit()
    conn.close()
    init_agent_firm_tables()


def _ok(role, output=None, **kw):
    return AgentResult(role=role, status="ok", output=output or {"verdict": "ok"},
                       tokens_in=kw.pop("tokens_in", 10), tokens_out=kw.pop("tokens_out", 5),
                       duration_s=0.1, **kw)


def _candidates(n=3):
    tickers = ["KBLM", "KBLI", "SCCO"][:n]
    return [
        SignalCandidate(ticker=t, strategy="eod", score=0.0,
                        scan_time="2026-09-16T16:40:00+07:00")
        for t in tickers
    ]


@pytest.fixture
def firm_module(monkeypatch, tmp_path):
    """Fresh, enabled firm module bound to an isolated DB, per test_firm_v2.py's pattern."""
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("TAVILY_API_KEY", "")
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    from engine.agent_firm import config, firm
    importlib.reload(config)
    importlib.reload(firm)
    _seed_db(tmp_path / "t.db")
    return firm


def _risk_approve():
    return AgentResult(role="risk", status="ok",
                       output={"decision": "approve", "confidence": 0.6,
                               "size_tier": "normal", "rationale": "ok.\nok."},
                       tokens_in=50, tokens_out=10, duration_s=0.2)


@pytest.mark.asyncio
async def test_three_survivors_make_exactly_7_calls_per_ticker_not_9(monkeypatch, firm_module):
    """3 bullish-surviving candidates -> technical/regime called once each (Stage 1 only,
    reused by Stage 2), flow/news/bull/bear/risk called once each per ticker -> 21 total
    LLM-node calls, not 27."""
    firm = firm_module
    candidates = _candidates(3)

    technical_mock = AsyncMock(return_value=_ok("technical", {"verdict": "BULLISH"}))
    regime_mock = AsyncMock(return_value=_ok("regime", {"regime_call": "BULL"}))
    flow_mock = AsyncMock(return_value=_ok("flow"))
    news_mock = AsyncMock(return_value=_ok("news"))
    bull_mock = AsyncMock(return_value=_ok("bull"))
    bear_mock = AsyncMock(return_value=_ok("bear"))
    risk_mock = AsyncMock(return_value=_risk_approve())

    monkeypatch.setattr("engine.agent_firm.agents.technical.run", technical_mock)
    monkeypatch.setattr("engine.agent_firm.agents.regime.run", regime_mock)
    monkeypatch.setattr("engine.agent_firm.agents.flow.run", flow_mock)
    monkeypatch.setattr("engine.agent_firm.agents.news.run", news_mock)
    monkeypatch.setattr("engine.agent_firm.agents.bull.run", bull_mock)
    monkeypatch.setattr("engine.agent_firm.agents.bear.run", bear_mock)
    monkeypatch.setattr("engine.agent_firm.agents.risk.run", risk_mock)

    decisions = await firm.evaluate_staged_async(candidates)

    assert len(decisions) == 3
    assert all(d.decision == "approve" for d in decisions)

    # The audit's headline number: technical/regime called ONCE per ticker (Stage 1 only),
    # not twice (Stage 1 + Stage 2 recompute).
    assert technical_mock.call_count == 3
    assert regime_mock.call_count == 3
    assert flow_mock.call_count == 3
    assert news_mock.call_count == 3
    assert bull_mock.call_count == 3
    assert bear_mock.call_count == 3
    assert risk_mock.call_count == 3

    total_calls = sum(m.call_count for m in (
        technical_mock, regime_mock, flow_mock, news_mock, bull_mock, bear_mock, risk_mock,
    ))
    assert total_calls == 21, f"expected 21 LLM-node calls for 3 survivors (7/ticker), got {total_calls}"

    # Every decision still carries all 7 persisted trace roles.
    for d in decisions:
        assert len(d.traces) == 7
        assert {t.role for t in d.traces} == {
            "technical", "flow", "regime", "news", "bull", "bear", "risk",
        }


@pytest.mark.asyncio
async def test_stage1_technical_regime_results_are_reused_not_recomputed(monkeypatch, firm_module):
    """The exact AgentResult objects Stage 1 produces must be the ones that end up in the
    final decision's traces -- proof of reuse, not just equal call counts."""
    firm = firm_module
    candidates = _candidates(1)

    stage1_technical = _ok("technical", {"verdict": "BULLISH", "marker": "stage1-technical"})
    stage1_regime = _ok("regime", {"regime_call": "BULL", "marker": "stage1-regime"})

    technical_mock = AsyncMock(return_value=stage1_technical)
    regime_mock = AsyncMock(return_value=stage1_regime)
    monkeypatch.setattr("engine.agent_firm.agents.technical.run", technical_mock)
    monkeypatch.setattr("engine.agent_firm.agents.regime.run", regime_mock)
    monkeypatch.setattr("engine.agent_firm.agents.flow.run", AsyncMock(return_value=_ok("flow")))
    monkeypatch.setattr("engine.agent_firm.agents.news.run", AsyncMock(return_value=_ok("news")))
    monkeypatch.setattr("engine.agent_firm.agents.bull.run", AsyncMock(return_value=_ok("bull")))
    monkeypatch.setattr("engine.agent_firm.agents.bear.run", AsyncMock(return_value=_ok("bear")))
    monkeypatch.setattr("engine.agent_firm.agents.risk.run",
                        AsyncMock(return_value=_risk_approve()))

    decisions = await firm.evaluate_staged_async(candidates)

    assert len(decisions) == 1
    traces_by_role = {t.role: t for t in decisions[0].traces}
    # Identity, not just equality: the same object Stage 1 produced flows straight into
    # the persisted decision, with no intervening second call.
    assert traces_by_role["technical"] is stage1_technical
    assert traces_by_role["regime"] is stage1_regime
    assert traces_by_role["technical"].output["marker"] == "stage1-technical"
    assert traces_by_role["regime"].output["marker"] == "stage1-regime"
    # The identity check alone is insufficient proof with a fixed return_value mock (it would
    # return the same object on a second call too) -- call_count is the real proof there was
    # no Stage-2 recomputation.
    assert technical_mock.call_count == 1
    assert regime_mock.call_count == 1


@pytest.mark.asyncio
async def test_both_bearish_stage1_still_autovetoes_without_stage2(monkeypatch, firm_module):
    """Unchanged behavior: technical BEARISH + regime BEAR auto-vetoes at Stage 1 -- no
    flow/news/bull/bear/risk call is ever made for that ticker."""
    firm = firm_module
    candidates = _candidates(1)

    flow_mock = AsyncMock(return_value=_ok("flow"))
    news_mock = AsyncMock(return_value=_ok("news"))
    bull_mock = AsyncMock(return_value=_ok("bull"))
    bear_mock = AsyncMock(return_value=_ok("bear"))
    risk_mock = AsyncMock(return_value=_risk_approve())

    monkeypatch.setattr("engine.agent_firm.agents.technical.run",
                        AsyncMock(return_value=_ok("technical", {"verdict": "BEARISH"})))
    monkeypatch.setattr("engine.agent_firm.agents.regime.run",
                        AsyncMock(return_value=_ok("regime", {"regime_call": "BEAR"})))
    monkeypatch.setattr("engine.agent_firm.agents.flow.run", flow_mock)
    monkeypatch.setattr("engine.agent_firm.agents.news.run", news_mock)
    monkeypatch.setattr("engine.agent_firm.agents.bull.run", bull_mock)
    monkeypatch.setattr("engine.agent_firm.agents.bear.run", bear_mock)
    monkeypatch.setattr("engine.agent_firm.agents.risk.run", risk_mock)

    decisions = await firm.evaluate_staged_async(candidates)

    assert len(decisions) == 1
    assert decisions[0].decision == "veto"
    assert "Stage 1 pre-screen" in decisions[0].rationale
    assert len(decisions[0].traces) == 2  # technical + regime only

    for m in (flow_mock, news_mock, bull_mock, bear_mock, risk_mock):
        assert m.call_count == 0


@pytest.mark.asyncio
async def test_stage2_decision_semantics_compatible_with_plain_evaluate_async(monkeypatch, firm_module):
    """A survivor's persisted decision/DB shape (agent_decisions + agent_traces row counts,
    decision literal, size_tier) must be identical to the pre-existing (non-staged)
    evaluate_async() output shape -- only the call count behind it changed."""
    firm = firm_module
    candidates = _candidates(1)

    monkeypatch.setattr("engine.agent_firm.agents.technical.run",
                        AsyncMock(return_value=_ok("technical", {"verdict": "BULLISH"})))
    monkeypatch.setattr("engine.agent_firm.agents.regime.run",
                        AsyncMock(return_value=_ok("regime", {"regime_call": "BULL"})))
    monkeypatch.setattr("engine.agent_firm.agents.flow.run", AsyncMock(return_value=_ok("flow")))
    monkeypatch.setattr("engine.agent_firm.agents.news.run", AsyncMock(return_value=_ok("news")))
    monkeypatch.setattr("engine.agent_firm.agents.bull.run", AsyncMock(return_value=_ok("bull")))
    monkeypatch.setattr("engine.agent_firm.agents.bear.run", AsyncMock(return_value=_ok("bear")))
    monkeypatch.setattr("engine.agent_firm.agents.risk.run",
                        AsyncMock(return_value=_risk_approve()))

    decisions = await firm.evaluate_staged_async(candidates)

    assert len(decisions) == 1
    d = decisions[0]
    assert d.decision == "approve"
    assert d.size_tier == "normal"
    assert len(d.traces) == 7

    import data.db as _db
    conn = sqlite3.connect(_db.DB_PATH)
    dec_rows = conn.execute("SELECT decision FROM agent_decisions").fetchall()
    assert len(dec_rows) == 1 and dec_rows[0][0] == "approve"
    trace_count = conn.execute("SELECT COUNT(*) FROM agent_traces").fetchone()[0]
    assert trace_count == 7  # unchanged persisted shape -- still one row per role
    conn.close()


@pytest.mark.asyncio
async def test_provider_failover_metadata_survives_stage1_reuse(monkeypatch, firm_module):
    """If Stage 1's technical call itself failed over to the fallback provider, that
    provider attribution must still reach the final decision's providers_used/tokens/cost
    even though Stage 2 never re-calls technical -- reuse must not drop failover metadata."""
    firm = firm_module
    candidates = _candidates(1)

    stage1_technical = _ok("technical", {"verdict": "BULLISH"},
                           provider="zai", failover=True, tokens_in=200, tokens_out=80)
    stage1_regime = _ok("regime", {"regime_call": "BULL"}, provider="claude", failover=False)

    technical_mock = AsyncMock(return_value=stage1_technical)
    regime_mock = AsyncMock(return_value=stage1_regime)
    monkeypatch.setattr("engine.agent_firm.agents.technical.run", technical_mock)
    monkeypatch.setattr("engine.agent_firm.agents.regime.run", regime_mock)
    monkeypatch.setattr("engine.agent_firm.agents.flow.run",
                        AsyncMock(return_value=_ok("flow", provider="claude")))
    monkeypatch.setattr("engine.agent_firm.agents.news.run",
                        AsyncMock(return_value=_ok("news", provider="claude")))
    monkeypatch.setattr("engine.agent_firm.agents.bull.run",
                        AsyncMock(return_value=_ok("bull", provider="claude")))
    monkeypatch.setattr("engine.agent_firm.agents.bear.run",
                        AsyncMock(return_value=_ok("bear", provider="claude")))
    monkeypatch.setattr("engine.agent_firm.agents.risk.run",
                        AsyncMock(return_value=AgentResult(
                            role="risk", status="ok",
                            output={"decision": "approve", "confidence": 0.6,
                                    "size_tier": "normal", "rationale": "ok.\nok."},
                            tokens_in=50, tokens_out=10, duration_s=0.2, provider="claude")))

    decisions = await firm.evaluate_staged_async(candidates)

    assert len(decisions) == 1
    d = decisions[0]
    # Stage 1's zai failover on `technical` is still reflected in the aggregated decision --
    # failover routing behavior (which provider served which role) is unaffected by reuse.
    assert d.providers_used == ["claude", "zai"]
    assert d.tokens_in >= 200  # Stage 1's technical tokens weren't dropped
    trace_providers = {t.role: t.provider for t in d.traces}
    assert trace_providers["technical"] == "zai"
    assert trace_providers["regime"] == "claude"
    # Proof this is reuse, not a second (coincidentally identical) provider round-trip.
    assert technical_mock.call_count == 1
    assert regime_mock.call_count == 1
