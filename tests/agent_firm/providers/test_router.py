from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker
from engine.agent_firm.providers.errors import (
    ProviderException, ProviderTimeout, ProviderUnavailable,
)
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
    p.model = Mock(return_value="m")  # real FirmLLMProvider.model() is sync
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


# --- RCA 2026-07-10: quota-aware routing (session-limit hold) ----------------

from datetime import timedelta

from engine.agent_firm.providers import router as router_mod
from engine.agent_firm.providers.errors import ProviderSessionLimit

_T0 = datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def frozen_now(monkeypatch):
    state = {"now": _T0}
    monkeypatch.setattr(router_mod, "_now", lambda: state["now"])
    return state


@pytest.fixture(autouse=True)
def _quiet_alerts(monkeypatch):
    from engine.agent_firm.providers import alerts
    alerts.reset_state()
    monkeypatch.setattr(alerts, "send_telegram", lambda msg: None)
    yield
    alerts.reset_state()


@pytest.mark.asyncio
async def test_session_limit_puts_provider_on_hold_until_reset(frozen_now):
    reset = _T0 + timedelta(hours=2)
    p1 = _fake_provider("claude", generate_error=ProviderSessionLimit("limit", reset_time=reset))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])

    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    assert p1.generate.call_count == 1

    # Second request while still inside the window: claude must be SKIPPED
    # without spawning the CLI at all.
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    assert p1.generate.call_count == 1  # not called again


@pytest.mark.asyncio
async def test_provider_resumes_automatically_after_reset(frozen_now):
    reset = _T0 + timedelta(hours=2)
    p1 = _fake_provider("claude", generate_error=ProviderSessionLimit("limit", reset_time=reset))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    await router.generate([{"role": "user", "content": "x"}])

    # Advance past reset + buffer: claude is tried again and succeeds.
    frozen_now["now"] = reset + timedelta(minutes=5)
    p1.generate.side_effect = None
    p1.generate.return_value = _resp("claude")
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"
    assert p1.generate.call_count == 2


@pytest.mark.asyncio
async def test_session_limit_without_reset_uses_fallback_hold(frozen_now, monkeypatch):
    from engine.agent_firm import config as cfg
    monkeypatch.setattr(cfg, "QUOTA_FALLBACK_HOLD_S", 900.0)
    p1 = _fake_provider("zai", generate_error=ProviderSessionLimit("1308", reset_time=None))
    p2 = _fake_provider("claude")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    await router.generate([{"role": "user", "content": "x"}])

    frozen_now["now"] = _T0 + timedelta(seconds=899)
    await router.generate([{"role": "user", "content": "x"}])
    assert p1.generate.call_count == 1  # still held

    frozen_now["now"] = _T0 + timedelta(seconds=901)
    p1.generate.side_effect = None
    p1.generate.return_value = _resp("zai")
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"


@pytest.mark.asyncio
async def test_hold_capped_at_max(frozen_now, monkeypatch):
    from engine.agent_firm import config as cfg
    monkeypatch.setattr(cfg, "QUOTA_MAX_HOLD_S", 3600.0)
    absurd_reset = _T0 + timedelta(days=30)
    p1 = _fake_provider("claude", generate_error=ProviderSessionLimit("limit", reset_time=absurd_reset))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    await router.generate([{"role": "user", "content": "x"}])

    frozen_now["now"] = _T0 + timedelta(seconds=3601)
    p1.generate.side_effect = None
    p1.generate.return_value = _resp("claude")
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"  # cap expired, provider retried


@pytest.mark.asyncio
async def test_quota_hold_disabled_by_config(frozen_now, monkeypatch):
    from engine.agent_firm import config as cfg
    monkeypatch.setattr(cfg, "QUOTA_HOLD_ENABLED", False)
    reset = _T0 + timedelta(hours=2)
    p1 = _fake_provider("claude", generate_error=ProviderSessionLimit("limit", reset_time=reset))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    await router.generate([{"role": "user", "content": "x"}])
    await router.generate([{"role": "user", "content": "x"}])
    assert p1.generate.call_count == 2  # pre-change behavior preserved


@pytest.mark.asyncio
async def test_session_limit_still_records_breaker_failure(frozen_now):
    reset = _T0 + timedelta(hours=2)
    breaker = CircuitBreaker(failure_threshold=1, cooldown_s=999)
    p1 = _fake_provider("claude", generate_error=ProviderSessionLimit("limit", reset_time=reset))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, breaker), (p2, CircuitBreaker())])
    await router.generate([{"role": "user", "content": "x"}])
    assert breaker.state == "OPEN"  # coexists with the circuit breaker


@pytest.mark.asyncio
async def test_provider_status_snapshot_explains_unavailability(frozen_now):
    reset = _T0 + timedelta(hours=2)
    p1 = _fake_provider("claude", generate_error=ProviderSessionLimit("limit", reset_time=reset))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    await router.generate([{"role": "user", "content": "x"}])

    status = {s["provider"]: s for s in router.provider_status()}
    assert status["claude"]["available"] is False
    assert "session limit" in status["claude"]["reason"]
    assert status["claude"]["quota_hold_until"] is not None
    assert status["zai"]["available"] is True
    assert status["zai"]["reason"] is None
    assert status["zai"]["circuit_state"] == "CLOSED"


@pytest.mark.asyncio
async def test_restored_after_hold_emits_restored_alert(frozen_now, monkeypatch):
    from engine.agent_firm.providers import alerts
    sent = []
    monkeypatch.setattr(alerts, "send_telegram", lambda msg: sent.append(msg))
    reset = _T0 + timedelta(hours=2)
    p1 = _fake_provider("claude", generate_error=ProviderSessionLimit("limit", reset_time=reset))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker(failure_threshold=99)), (p2, CircuitBreaker())])
    await router.generate([{"role": "user", "content": "x"}])
    assert any("session limit" in m.lower() for m in sent)

    frozen_now["now"] = reset + timedelta(minutes=5)
    p1.generate.side_effect = None
    p1.generate.return_value = _resp("claude")
    await router.generate([{"role": "user", "content": "x"}])
    assert any("restored" in m.lower() for m in sent)


# --- RCA 2026-07-13: don't page "all providers down" on a transient burst -----

@pytest.mark.asyncio
async def test_burst_failure_does_not_fire_all_down_alert(frozen_now, monkeypatch):
    """A single request failing through both providers under load is NOT an
    outage — circuits recover within cooldown. Only page when every provider
    is in a lasting unavailable state (quota hold / OPEN circuit)."""
    from engine.agent_firm.providers import alerts
    sent = []
    monkeypatch.setattr(alerts, "send_telegram", lambda msg: sent.append(msg))
    # Both fail once (transient), but their circuits stay CLOSED below threshold.
    p1 = _fake_provider("claude", generate_error=ProviderUnavailable("burst fail"))
    p2 = _fake_provider("zai", generate_error=ProviderUnavailable("burst fail"))
    # failure_threshold=99 keeps the breaker CLOSED after a single failure, so
    # provider_status() still reports both as available → no all-down page.
    router = ProviderRouter([
        (p1, CircuitBreaker(failure_threshold=99)),
        (p2, CircuitBreaker(failure_threshold=99)),
    ])
    with pytest.raises(ProviderUnavailable):
        await router.generate([{"role": "user", "content": "x"}])
    assert not any("PROVIDERS DOWN" in m for m in sent), \
        "transient burst should not page 'all providers down'"


@pytest.mark.asyncio
async def test_all_down_alert_fires_when_every_provider_quota_held(frozen_now, monkeypatch):
    """When both providers are genuinely out (quota-held), the page must fire."""
    from engine.agent_firm.providers import alerts
    sent = []
    monkeypatch.setattr(alerts, "send_telegram", lambda msg: sent.append(msg))
    reset = _T0 + timedelta(hours=2)
    p1 = _fake_provider("claude", generate_error=ProviderSessionLimit("limit", reset_time=reset))
    p2 = _fake_provider("zai", generate_error=ProviderSessionLimit("limit", reset_time=reset))
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    with pytest.raises(ProviderException):
        await router.generate([{"role": "user", "content": "x"}])
    assert any("PROVIDERS DOWN" in m for m in sent)


@pytest.mark.asyncio
async def test_all_down_alert_fires_when_every_circuit_open(frozen_now, monkeypatch):
    """When every provider's circuit is OPEN (hard failures past threshold),
    that's also a real outage worth paging."""
    from engine.agent_firm.providers import alerts
    sent = []
    monkeypatch.setattr(alerts, "send_telegram", lambda msg: sent.append(msg))
    # Pre-open both circuits so provider_status() reports both unavailable.
    b1 = CircuitBreaker(failure_threshold=1, cooldown_s=999)
    b1.record_failure()
    b2 = CircuitBreaker(failure_threshold=1, cooldown_s=999)
    b2.record_failure()
    p1 = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    p2 = _fake_provider("zai", generate_error=ProviderUnavailable("down"))
    router = ProviderRouter([(p1, b1), (p2, b2)])
    with pytest.raises(ProviderUnavailable):
        await router.generate([{"role": "user", "content": "x"}])
    assert any("PROVIDERS DOWN" in m for m in sent)
