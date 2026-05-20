import json
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from engine.agent_firm.schemas import SignalCandidate


def _seed(db_path):
    """Seed minimal ohlcv rows and create agent_firm tables."""
    from data.db import init_agent_firm_tables
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume REAL
        )
    """)
    rows = [("BBRI", f"2026-05-{d:02d}", 5000+d, 5100+d, 4950+d, 5050+d, 1e6) for d in range(1, 20)]
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    init_agent_firm_tables()


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
    fake_client = AsyncMock()
    fake_client.chat.side_effect = [
        # Technical
        {"content": json.dumps({
            "verdict": "BULLISH", "conviction": 0.7,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "uptrend",
        }), "tokens_in": 1200, "tokens_out": 60, "cost_usd": 0.0006, "duration_s": 3.0},
        # Risk
        {"content": json.dumps({
            "decision": "approve", "confidence": 0.7, "size_hint": 1.0,
            "rationale": "Risk: ok.\nBull/Bear: bull edges out",
        }), "tokens_in": 1500, "tokens_out": 80, "cost_usd": 0.0007, "duration_s": 4.0},
    ]
    decisions = await firm.evaluate_async([candidate], client=fake_client)
    assert len(decisions) == 1
    d = decisions[0]
    assert d.decision == "approve"
    assert d.confidence == 0.7
    assert d.tokens_in == 2700
    assert d.tokens_out == 140
    assert d.cost_usd == pytest.approx(0.0013, abs=1e-4)
    assert len(d.traces) == 2

    conn = sqlite3.connect(tmp_path / "t.db")
    rows = conn.execute("SELECT decision, confidence FROM agent_decisions").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "approve"
    trace_count = conn.execute("SELECT COUNT(*) FROM agent_traces").fetchone()[0]
    assert trace_count == 2


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
    fake_client = AsyncMock()
    fake_client.chat.side_effect = [
        # Technical ok
        {"content": json.dumps({
            "verdict": "BULLISH", "conviction": 0.7,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "uptrend",
        }), "tokens_in": 1200, "tokens_out": 60, "cost_usd": 0.0006, "duration_s": 3.0},
        # Risk fails: raises
        RuntimeError("deepseek 500"),
    ]
    decisions = await firm.evaluate_async([candidate], client=fake_client)
    assert decisions[0].decision == "degraded"
    assert "degraded" in (decisions[0].rationale or "").lower()
