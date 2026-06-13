import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _seed(db_path):
    """Seed minimal tables and create agent_firm tables."""
    from data.db import init_agent_firm_tables
    conn = sqlite3.connect(db_path)
    for ddl in [
        """CREATE TABLE IF NOT EXISTS ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume REAL)""",
        """CREATE TABLE IF NOT EXISTS stockbit_flow (
            ticker TEXT, trade_date TEXT, buy_lot INTEGER, sell_lot INTEGER,
            net_lot INTEGER, net_value INTEGER, verdict TEXT, smart_money TEXT,
            foreign_score REAL, composite_score INTEGER, updated_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS broker_flow (
            ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT,
            lot_value INTEGER, investor_type TEXT)""",
        """CREATE TABLE IF NOT EXISTS stockbit_flow_bars (
            ticker TEXT, trade_date TEXT, bar_time TEXT, buy_lot INTEGER,
            sell_lot INTEGER, delta INTEGER, net_value INTEGER)""",
        """CREATE TABLE IF NOT EXISTS wf_scores (
            ticker TEXT, strategy TEXT, consistency_pct REAL,
            avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL)""",
        """CREATE TABLE IF NOT EXISTS daily_screen (
            id INTEGER PRIMARY KEY, date TEXT, ticker TEXT, close INTEGER,
            vol_ratio REAL, signal TEXT, vpin_label TEXT)""",
        """CREATE TABLE IF NOT EXISTS news_mentions (
            ticker TEXT, date TEXT, count INTEGER, headlines_json TEXT, updated_at TEXT)""",
        """CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY, ticker TEXT, status TEXT,
            entry_price REAL, lots INTEGER, tp_price REAL, sl_price REAL)""",
    ]:
        conn.execute(ddl)
    rows = [("BBRI", f"2026-05-{d:02d}", 5000+d, 5100+d, 4950+d, 5050+d, 1e6) for d in range(1, 20)]
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    init_agent_firm_tables()


def _ok(role):
    return AgentResult(role=role, status="ok", output={"verdict": "ok"},
                       tokens_in=100, tokens_out=50, duration_s=1.0)


def test_evaluate_returns_bypassed_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "false")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from engine.agent_firm import config, firm
    importlib.reload(config); importlib.reload(firm)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    out = firm.evaluate([candidate])
    assert len(out) == 1
    assert out[0].decision == "bypassed"


@pytest.mark.asyncio
async def test_evaluate_async_runs_full_pipeline_and_persists(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    from engine.agent_firm import config, firm
    importlib.reload(config); importlib.reload(firm)

    _seed(tmp_path / "t.db")

    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )

    with patch("engine.agent_firm.agents.technical.run", return_value=_ok("technical")), \
         patch("engine.agent_firm.agents.flow.run",      return_value=_ok("flow")), \
         patch("engine.agent_firm.agents.regime.run",    return_value=_ok("regime")), \
         patch("engine.agent_firm.agents.news.run",      return_value=_ok("news")), \
         patch("engine.agent_firm.agents.bull.run",      return_value=_ok("bull")), \
         patch("engine.agent_firm.agents.bear.run",      return_value=_ok("bear")), \
         patch("engine.agent_firm.agents.risk.run",
               return_value=AgentResult(
                   role="risk", status="ok",
                   output={"decision": "approve", "confidence": 0.7,
                           "size_hint": 1.0, "rationale": "Risk: ok.\nBull/Bear: bull edges out"},
                   tokens_in=1500, tokens_out=80, duration_s=4.0)):
        decisions = await firm.evaluate_async([candidate])

    assert len(decisions) == 1
    d = decisions[0]
    assert d.decision == "approve"
    assert d.confidence == 0.7
    assert len(d.traces) == 7

    conn = sqlite3.connect(tmp_path / "t.db")
    rows = conn.execute("SELECT decision, confidence FROM agent_decisions").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "approve"
    trace_count = conn.execute("SELECT COUNT(*) FROM agent_traces").fetchone()[0]
    assert trace_count == 7


@pytest.mark.asyncio
async def test_evaluate_async_marks_degraded_when_risk_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    from engine.agent_firm import config, firm
    importlib.reload(config); importlib.reload(firm)

    _seed(tmp_path / "t.db")

    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )

    with patch("engine.agent_firm.agents.technical.run", return_value=_ok("technical")), \
         patch("engine.agent_firm.agents.flow.run",      return_value=_ok("flow")), \
         patch("engine.agent_firm.agents.regime.run",    return_value=_ok("regime")), \
         patch("engine.agent_firm.agents.news.run",      return_value=_ok("news")), \
         patch("engine.agent_firm.agents.bull.run",      return_value=_ok("bull")), \
         patch("engine.agent_firm.agents.bear.run",      return_value=_ok("bear")), \
         patch("engine.agent_firm.agents.risk.run",
               return_value=AgentResult(
                   role="risk", status="failed",
                   error="deepseek 500",
                   tokens_in=0, tokens_out=0, duration_s=0.0)):
        decisions = await firm.evaluate_async([candidate])

    assert decisions[0].decision == "degraded"
    assert "degraded" in (decisions[0].rationale or "").lower()


def test_evaluate_bypasses_when_daily_spend_cap_reached(monkeypatch, tmp_path):
    """Once today's persisted cost >= the cap, evaluate() short-circuits to bypassed
    without making any LLM calls."""
    db_file = tmp_path / "t.db"
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("AGENT_FIRM_DAILY_CAP", "1.0")
    monkeypatch.setenv("DB_PATH", str(db_file))
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    from engine.agent_firm import config, firm
    importlib.reload(config); importlib.reload(firm)

    _seed(db_file)

    # Seed a prior decision today whose cost already exceeds the $1.00 cap.
    import datetime
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(db_file)
    conn.execute(
        "INSERT INTO agent_decisions (scan_time, ticker, strategy, decision, cost_usd, created_at) "
        "VALUES (?,?,?,?,?,?)",
        ("2026-05-19 09:00", "AAAA", "x", "approve", 2.5, f"{today} 09:00:00"),
    )
    conn.commit()
    conn.close()

    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )

    # If the cap were ignored the firm would try a real LLM call and raise; the
    # cap must short-circuit before any agent runs.
    out = firm.evaluate([candidate])
    assert len(out) == 1
    assert out[0].decision == "bypassed"
    assert "cap" in (out[0].rationale or "").lower()

    out_staged = firm.evaluate_staged([candidate])
    assert out_staged[0].decision == "bypassed"
