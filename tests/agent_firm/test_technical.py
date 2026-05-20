import json
import sqlite3

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import technical
from engine.agent_firm.schemas import SignalCandidate


def _seed(db_path):
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


@pytest.mark.asyncio
async def test_technical_returns_ok_result_on_success(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": json.dumps({
            "verdict": "BULLISH",
            "conviction": 0.75,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "Higher highs and rising volume",
        }),
        "tokens_in": 1200, "tokens_out": 80, "cost_usd": 0.0006, "duration_s": 3.2,
    }
    result = await technical.run(candidate, fake_client, str(db))
    assert result.role == "technical"
    assert result.status == "ok"
    assert result.output["verdict"] == "BULLISH"
    assert result.tokens_in == 1200
    assert result.tools_called[0]["tool"] == "sqlite_query"
    assert result.tools_called[0]["rows"] == 19


@pytest.mark.asyncio
async def test_technical_returns_failed_on_invalid_json(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.return_value = {
        "content": "not valid json",
        "tokens_in": 100, "tokens_out": 5, "cost_usd": 0.0, "duration_s": 1.0,
    }
    result = await technical.run(candidate, fake_client, str(db))
    assert result.status == "failed"
    assert "json" in result.error.lower() or "decode" in result.error.lower()


@pytest.mark.asyncio
async def test_technical_returns_failed_on_client_exception(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.chat.side_effect = RuntimeError("network down")
    result = await technical.run(candidate, fake_client, str(db))
    assert result.status == "failed"
    assert "network down" in result.error
