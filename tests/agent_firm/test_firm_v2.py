import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

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
    rows = [("BBRI", f"2026-05-{d:02d}", 3000+d, 3100+d, 2950+d, 3050+d, 1e8) for d in range(1, 20)]
    conn.executemany("INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    init_agent_firm_tables()


def _ok(role):
    return AgentResult(role=role, status="ok", output={"verdict": "ok"},
                       tokens_in=100, tokens_out=50, duration_s=1.0)


@pytest.mark.asyncio
async def test_evaluate_async_v2_runs_all_7_agents_and_persists(monkeypatch, tmp_path):
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

    candidate = SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=4.0, scan_time="2026-05-20T10:00:00+07:00",
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
                   output={"decision": "approve", "confidence": 0.75,
                           "size_hint": 1.0, "rationale": "ok.\nok."},
                   tokens_in=500, tokens_out=100, duration_s=3.0)):
        decisions = await firm.evaluate_async([candidate])

    assert len(decisions) == 1
    d = decisions[0]
    assert d.decision == "approve"
    assert len(d.traces) == 7
    roles = [t.role for t in d.traces]
    assert "technical" in roles and "bull" in roles and "bear" in roles and "risk" in roles

    conn = sqlite3.connect(tmp_path / "t.db")
    rows = conn.execute("SELECT decision FROM agent_decisions").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "approve"
    trace_count = conn.execute("SELECT COUNT(*) FROM agent_traces").fetchone()[0]
    assert trace_count == 7


def test_evaluate_returns_bypassed_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "false")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    import importlib
    from engine.agent_firm import config, firm
    importlib.reload(config)
    importlib.reload(firm)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=4.0, scan_time="2026-05-20T10:00:00+07:00",
    )
    out = firm.evaluate([candidate])
    assert len(out) == 1
    assert out[0].decision == "bypassed"
