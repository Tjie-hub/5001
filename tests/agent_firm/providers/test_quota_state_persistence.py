"""Audit 2026-07-21: quota/exhaustion state must survive between scheduler
ticks. The firm rebuilds the ProviderRouter on every evaluate_staged() call,
so any state held only in the router's in-memory ``_quota_holds`` is lost the
moment a tick ends. The provider_events table already records every
session-limit event WITH its advertised reset_time (RCA 2026-07-10); a fresh
router must hydrate its holds from that table instead of starting empty.

These tests assert the OBSERVED-BROKEN behavior first (red), then the fixed
behavior once the hydration is in place.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import AsyncMock, Mock

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker
from engine.agent_firm.providers.errors import (
    ProviderSessionLimit, ProviderUnavailable,
)
from engine.agent_firm.providers.events import ProviderEvent, log_provider_event
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
    p.model = Mock(return_value="m")
    p.capabilities = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=True, supports_tools=True)
    if generate_error is not None:
        p.generate.side_effect = generate_error
    else:
        p.generate.return_value = generate_result or _resp(name)
    return p


@pytest.fixture
def events_db(tmp_path):
    db = tmp_path / "events.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE provider_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL, provider TEXT NOT NULL,
            model TEXT, reason TEXT, duration_s REAL, request_id TEXT,
            failover INTEGER DEFAULT 0, reset_time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE agent_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER, role TEXT, prompt_version TEXT, output TEXT,
            tools_called TEXT, tokens_in INTEGER, tokens_out INTEGER,
            cost_usd REAL, duration_s REAL, provider TEXT, model TEXT,
            runtime_version TEXT, failover INTEGER DEFAULT 0, error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    return db


def _seed_session_limit(db, provider, reset_time_utc, *, created_at_utc=None):
    """Write a provider_session_limit row exactly as the Router does."""
    log_provider_event(ProviderEvent(
        event_type="provider_session_limit",
        timestamp=created_at_utc or datetime.now(timezone.utc),
        provider=provider, model="m", reason="session limit",
        reset_time=reset_time_utc,
    ), db_path=str(db))


# --- The core regression: a fresh router must honor persisted holds --------

@pytest.mark.asyncio
async def test_fresh_router_honors_persisted_session_limit_hold(events_db, monkeypatch):
    """A session-limit event persisted by a PREVIOUS router instance (the
    previous scheduler tick) with a reset_time still in the future must keep
    the provider out of rotation when a NEW router is built against the same
    DB. This is the exact gap that caused the 2026-07-21 incident: each tick
    re-probed an exhausted provider because the in-memory hold was discarded.
    """
    from engine.agent_firm.providers import router as router_mod
    from engine.agent_firm import config as cfg

    now = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(router_mod, "_now", lambda: now)

    # Previous tick wrote this: claude exhausted, resets in 2h.
    reset = now + timedelta(hours=2)
    _seed_session_limit(events_db, "claude", reset)

    claude = _fake_provider("claude")
    zai = _fake_provider("zai")
    # A brand-new router built the way build_router() builds it.
    router = ProviderRouter(
        [(claude, CircuitBreaker()), (zai, CircuitBreaker())],
        db_path=str(events_db),
    )

    resp = await router.generate([{"role": "user", "content": "x"}])

    assert resp.provider == "zai"
    claude.generate.assert_not_called(), \
        "claude is held by the persisted session-limit event; must NOT be probed"


@pytest.mark.asyncio
async def test_persisted_hold_expires_at_reset_time(events_db, monkeypatch):
    """Once the persisted reset_time has passed, the provider is probed again
    (RECOVERING -> single probe). Recovery after reset must work across the
    rebuild boundary."""
    from engine.agent_firm.providers import router as router_mod

    state = {"now": datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(router_mod, "_now", lambda: state["now"])

    reset = state["now"] + timedelta(hours=2)
    _seed_session_limit(events_db, "claude", reset)

    claude = _fake_provider("claude")
    zai = _fake_provider("zai")
    router = ProviderRouter(
        [(claude, CircuitBreaker()), (zai, CircuitBreaker())],
        db_path=str(events_db),
    )

    # Advance past reset + buffer.
    state["now"] = reset + timedelta(minutes=5)
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"
    assert claude.generate.call_count == 1


@pytest.mark.asyncio
async def test_all_providers_persisted_held_fires_all_down(events_db, monkeypatch):
    """Scenario E: when every provider has a persisted, un-expired
    session-limit hold, a fresh router must (a) not probe any of them and
    (b) page PROVIDERS DOWN. This is what should have happened immediately
    during the incident instead of N minutes of re-probing."""
    from engine.agent_firm.providers import router as router_mod
    from engine.agent_firm.providers import alerts
    alerts.reset_state()
    sent = []
    monkeypatch.setattr(alerts, "send_telegram", lambda msg, **kw: sent.append(msg))

    now = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(router_mod, "_now", lambda: now)
    reset = now + timedelta(hours=2)
    _seed_session_limit(events_db, "claude", reset)
    _seed_session_limit(events_db, "zai", reset)

    claude = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    zai = _fake_provider("zai", generate_error=ProviderUnavailable("down"))
    router = ProviderRouter(
        [(claude, CircuitBreaker()), (zai, CircuitBreaker())],
        db_path=str(events_db),
    )
    with pytest.raises(ProviderUnavailable):
        await router.generate([{"role": "user", "content": "x"}])

    claude.generate.assert_not_called()
    zai.generate.assert_not_called()
    assert any("PROVIDERS DOWN" in m for m in sent)


@pytest.mark.asyncio
async def test_expired_persisted_hold_does_not_block(events_db, monkeypatch):
    """A stale session_limit row whose reset_time is already in the past must
    NOT hold the provider (no stale availability state)."""
    from engine.agent_firm.providers import router as router_mod

    now = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(router_mod, "_now", lambda: now)
    # Reset was an hour ago.
    _seed_session_limit(events_db, "claude", now - timedelta(hours=1))

    claude = _fake_provider("claude")
    router = ProviderRouter([(claude, CircuitBreaker())], db_path=str(events_db))
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"
    assert claude.generate.call_count == 1


@pytest.mark.asyncio
async def test_zai_no_reset_uses_persisted_fallback_hold(events_db, monkeypatch):
    """Scenario C (repeated quota failures): z.ai reports session-limit with
    NO reset_time. The previous tick persisted the event (reset_time NULL).
    A fresh router must apply QUOTA_FALLBACK_HOLD_S from the event timestamp
    so z.ai isn't re-probed on the very next tick."""
    from engine.agent_firm.providers import router as router_mod
    from engine.agent_firm import config as cfg

    state = {"now": datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(router_mod, "_now", lambda: state["now"])
    monkeypatch.setattr(cfg, "QUOTA_FALLBACK_HOLD_S", 900.0)

    # Previous tick: z.ai exhausted at state["now"], no reset_time.
    _seed_session_limit(events_db, "zai", None, created_at_utc=state["now"])

    # z.ai is the PREFERRED (first) provider — only the hold should skip it.
    zai = _fake_provider("zai")
    claude = _fake_provider("claude")
    router = ProviderRouter(
        [(zai, CircuitBreaker()), (claude, CircuitBreaker())],
        db_path=str(events_db),
    )

    # 5 minutes later — still inside the 900s fallback hold.
    state["now"] = state["now"] + timedelta(seconds=300)
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"
    zai.generate.assert_not_called(), \
        "zai is held by the persisted fallback window; must not be re-probed"
