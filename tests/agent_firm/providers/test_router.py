from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker
from engine.agent_firm.providers.errors import ProviderTimeout, ProviderUnavailable
from engine.agent_firm.providers.router import ProviderRouter


def _resp(provider="claude") -> ProviderResponse:
    return ProviderResponse(
        content="ok", provider=provider, model="m", runtime_version="v",
        tokens_in=1, tokens_out=1, cost_usd=0.0, duration_s=0.1,
        timestamp=datetime.now(timezone.utc),
    )


def _fake_provider(name, generate_result=None, generate_error=None):
    p = AsyncMock()
    p.name = name
    p.capabilities = ProviderCapabilities(supports_json_mode=True, supports_json_schema=True, supports_tools=True)
    if generate_error is not None:
        p.generate.side_effect = generate_error
    else:
        p.generate.return_value = generate_result or _resp(name)
    return p


@pytest.mark.asyncio
async def test_generate_uses_first_provider_on_success():
    p1 = _fake_provider("claude")
    router = ProviderRouter([(p1, CircuitBreaker())])
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"
    assert resp.failover is False


@pytest.mark.asyncio
async def test_generate_fails_over_to_second_provider_on_exception():
    p1 = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    assert resp.failover is True


@pytest.mark.asyncio
async def test_generate_raises_when_all_providers_fail():
    p1 = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    p2 = _fake_provider("zai", generate_error=ProviderTimeout("slow"))
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    with pytest.raises(ProviderTimeout):
        await router.generate([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_open_circuit_skips_provider_without_calling_generate():
    p1 = _fake_provider("claude")
    breaker = CircuitBreaker(failure_threshold=1, cooldown_s=999)
    breaker.record_failure()
    assert breaker.state == "OPEN"
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, breaker), (p2, CircuitBreaker())])
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    p1.generate.assert_not_called()


@pytest.mark.asyncio
async def test_single_provider_failure_propagates_with_no_fallback():
    p1 = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    router = ProviderRouter([(p1, CircuitBreaker())])
    with pytest.raises(ProviderUnavailable):
        await router.generate([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_claude_daily_cap_reached_skips_to_next_provider(tmp_path, monkeypatch):
    import datetime as _dt
    import sqlite3
    from data.db import init_agent_firm_tables

    db_path = tmp_path / "t.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    init_agent_firm_tables()

    conn = sqlite3.connect(db_path)
    today = _dt.date.today().isoformat()
    for _ in range(3):
        conn.execute(
            "INSERT INTO agent_traces (role, provider, created_at) VALUES (?,?,?)",
            ("technical", "claude", f"{today} 09:00:00"),
        )
    conn.commit()
    conn.close()

    from engine.agent_firm import config as _cfg
    monkeypatch.setattr(_cfg, "CLAUDE_MAX_CALLS_PER_DAY", 3)

    p1 = _fake_provider("claude")
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())], db_path=str(db_path))
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    p1.generate.assert_not_called()
