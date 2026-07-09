import json
import sqlite3
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import technical
from engine.agent_firm.providers.base import ProviderResponse
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


def _response(content: str, tokens_in=1200, tokens_out=80) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0006, duration_s=3.2,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_technical_returns_ok_result_on_success(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "verdict": "BULLISH",
        "conviction": 0.75,
        "key_levels": {"support": 5000, "resistance": 5200},
        "reasoning": "Higher highs and rising volume",
    }))
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
    fake_client.generate.return_value = _response("not valid json", tokens_in=100, tokens_out=5)
    result = await technical.run(candidate, fake_client, str(db))
    assert result.status == "failed"
    assert "json" in result.error.lower() or "decode" in result.error.lower()
    # client.generate() succeeded (real, billable call happened) before the
    # JSON parse failed — the failed result must still carry resp's real
    # cost/token/provider data, not schema defaults.
    assert result.tokens_in == 100
    assert result.tokens_out == 5
    assert result.cost_usd == 0.0006
    assert result.provider == "zai"
    assert result.model == "glm-5.2"
    assert result.runtime_version == "1.0.0"


@pytest.mark.asyncio
async def test_technical_returns_failed_on_client_exception(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("network down")
    result = await technical.run(candidate, fake_client, str(db))
    assert result.status == "failed"
    assert "network down" in result.error
    # generate() itself raised — no response was ever received, so defaults hold.
    assert result.tokens_in == 0
    assert result.cost_usd == 0.0
    assert result.provider == ""
