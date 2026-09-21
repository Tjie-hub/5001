"""Validation scenarios A–E for the provider dispatch infrastructure
(audit 2026-07-21).

Each scenario simulates the REAL lifecycle: the firm's ``evaluate_staged()``
constructs a brand-new ProviderRouter on every scheduler tick, so any quota
state not recovered from the persisted provider_events table is lost. These
tests build router #1 (tick 1), let it run and persist events, then build
router #2 (tick 2) against the SAME db_path and assert router #2 makes the
correct dispatch decision without re-probing an exhausted provider.

Scenarios:
  A. Provider available            -> dispatch
  B. Quota exhausted               -> DO NOT dispatch; failover
  C. Repeated quota failures       -> stays held across ticks (no re-probe storm)
  D. Recovery after reset          -> single probe succeeds; restored
  E. All providers unavailable     -> no probes; PROVIDERS DOWN alert
"""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import AsyncMock, Mock

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker
from engine.agent_firm.providers.errors import (
    ProviderException, ProviderSessionLimit, ProviderUnavailable,
)
from engine.agent_firm.providers.router import ProviderRouter


# ── shared fixtures ──────────────────────────────────────────────────────────

def _resp(provider):
    return ProviderResponse(
        content="ok", provider=provider, model="m", runtime_version="v",
        tokens_in=1, tokens_out=1, cost_usd=0.0, duration_s=0.1,
        timestamp=datetime.now(timezone.utc),
    )


def _fake(name, *, error=None, result=None):
    p = AsyncMock()
    p.name = name
    p.model = Mock(return_value="m")
    p.capabilities = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=True, supports_tools=True)
    if error is not None:
        p.generate.side_effect = error
    else:
        p.generate.return_value = result or _resp(name)
    return p


@pytest.fixture
def events_db(tmp_path):
    db = tmp_path / "scenarios.db"
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


@pytest.fixture
def clock(monkeypatch):
    """Frozen clock so reset horizons are deterministic."""
    from engine.agent_firm.providers import router as router_mod
    state = {"now": datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(router_mod, "_now", lambda: state["now"])
    return state


@pytest.fixture(autouse=True)
def _quiet_alerts(monkeypatch):
    from engine.agent_firm.providers import alerts
    alerts.reset_state()
    yield
    alerts.reset_state()


def _build(providers, db_path):
    """Build a router the same way factory.build_router() does."""
    return ProviderRouter(
        [(p, CircuitBreaker()) for p in providers], db_path=str(db_path),
    )


# ── Scenario A: provider available → dispatch ────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_A_provider_available_dispatches(events_db, clock):
    """Baseline: a healthy provider is dispatched to on the first call, on
    every tick. No hold, no failover."""
    claude = _fake("claude")
    router1 = _build([claude], events_db)
    resp1 = await router1.generate([{"role": "user", "content": "x"}])
    assert resp1.provider == "claude" and resp1.failover is False

    # Tick 2: fresh router, same DB, no session-limit events → still available.
    claude2 = _fake("claude")
    router2 = _build([claude2], events_db)
    resp2 = await router2.generate([{"role": "user", "content": "x"}])
    assert resp2.provider == "claude"
    assert claude2.generate.call_count == 1


# ── Scenario B: quota exhausted → DO NOT dispatch, failover ──────────────────

@pytest.mark.asyncio
async def test_scenario_B_quota_exhausted_failover_across_rebuild(events_db, clock):
    """Tick 1: claude returns a session limit (resets in 2h). The router
    fails over to zai and persists the event. Tick 2: a NEW router is built
    — claude must NOT be probed again (the persisted hold is honored); zai
    serves the request."""
    reset = clock["now"] + timedelta(hours=2)
    claude1 = _fake("claude", error=ProviderSessionLimit("limit", reset_time=reset))
    zai1 = _fake("zai")
    router1 = _build([claude1, zai1], events_db)
    resp1 = await router1.generate([{"role": "user", "content": "x"}])
    assert resp1.provider == "zai" and resp1.failover is True
    assert claude1.generate.call_count == 1  # probed once, then held

    # Tick 2 — fresh router; claude's hold must be recovered from the DB.
    claude2 = _fake("claude")
    zai2 = _fake("zai")
    router2 = _build([claude2, zai2], events_db)
    resp2 = await router2.generate([{"role": "user", "content": "x"}])
    assert resp2.provider == "zai"
    claude2.generate.assert_not_called(), \
        "persisted session-limit hold must keep claude out of rotation on rebuild"


# ── Scenario C: repeated quota failures → no re-probe storm ──────────────────

@pytest.mark.asyncio
async def test_scenario_C_repeated_quota_failures_no_reprobe_storm(events_db, clock, monkeypatch):
    """z.ai reports session-limit with NO reset_time (its real-world behavior
    — 'usage limit reached for 5 hour' carries no timestamp). Pre-fix: every
    new router waited QUOTA_FALLBACK_HOLD_S (15m), then re-probed, failed, and
    re-held — looping every 15 minutes for the entire 5-hour window. Post-fix:
    the persisted event anchors the fallback to the FAILURE time, so z.ai is
    held for one contiguous 15-minute window per exhaustion, not re-probed
    per tick."""
    from engine.agent_firm import config as cfg
    monkeypatch.setattr(cfg, "QUOTA_FALLBACK_HOLD_S", 900.0)

    # Tick 1 at t=0: zai (preferred) exhausted, no reset_time.
    zai1 = _fake("zai", error=ProviderSessionLimit("1308", reset_time=None))
    claude1 = _fake("claude")
    router1 = _build([zai1, claude1], events_db)
    resp1 = await router1.generate([{"role": "user", "content": "x"}])
    assert resp1.provider == "claude"

    # Tick 2 at t=5min: fresh router. zai must STILL be held (fallback anchored
    # to the failure time, not to this tick's now).
    clock["now"] = clock["now"] + timedelta(seconds=300)
    zai2 = _fake("zai", error=ProviderSessionLimit("1308", reset_time=None))
    claude2 = _fake("claude")
    router2 = _build([zai2, claude2], events_db)
    resp2 = await router2.generate([{"role": "user", "content": "x"}])
    assert resp2.provider == "claude"
    zai2.generate.assert_not_called(), \
        "zai's persisted fallback hold (anchored to failure time) must suppress the re-probe"


# ── Scenario D: recovery after reset → single probe succeeds ─────────────────

@pytest.mark.asyncio
async def test_scenario_D_recovery_after_reset(events_db, clock):
    """Tick 1: claude exhausted, resets in 1h. Tick 2 (still inside window):
    claude held, zai serves. Tick 3 (past reset+buffer): claude is probed
    once and succeeds; a provider_restored event is persisted."""
    reset = clock["now"] + timedelta(hours=1)
    claude1 = _fake("claude", error=ProviderSessionLimit("limit", reset_time=reset))
    zai1 = _fake("zai")
    router1 = _build([claude1, zai1], events_db)
    await router1.generate([{"role": "user", "content": "x"}])

    # Tick 2 inside the window — claude held.
    clock["now"] = reset - timedelta(minutes=5)
    claude2 = _fake("claude")
    zai2 = _fake("zai")
    router2 = _build([claude2, zai2], events_db)
    resp2 = await router2.generate([{"role": "user", "content": "x"}])
    assert resp2.provider == "zai"
    claude2.generate.assert_not_called()

    # Tick 3 past reset + buffer — claude probed and recovers.
    clock["now"] = reset + timedelta(minutes=5)
    claude3 = _fake("claude")  # healthy now
    router3 = _build([claude3, _fake("zai")], events_db)
    resp3 = await router3.generate([{"role": "user", "content": "x"}])
    assert resp3.provider == "claude"
    assert claude3.generate.call_count == 1  # single probe (RECOVERING semantics)

    # The restored event was persisted — a subsequent rebuild sees no hold.
    router4 = _build([_fake("claude"), _fake("zai")], events_db)
    assert "claude" not in router4._quota_holds


# ── Scenario E: all providers unavailable → no probes, PROVIDERS DOWN ─────────

@pytest.mark.asyncio
async def test_scenario_E_all_providers_unavailable(events_db, clock, monkeypatch):
    """Both providers quota-held. Tick 2 must not spawn a single subprocess /
    HTTP call for either, and must page PROVIDERS DOWN immediately — instead
    of the observed multi-minute re-probe-then-fail loop."""
    from engine.agent_firm.providers import alerts
    sent = []
    monkeypatch.setattr(alerts, "send_telegram", lambda msg: sent.append(msg))

    reset = clock["now"] + timedelta(hours=2)
    claude1 = _fake("claude", error=ProviderSessionLimit("limit", reset_time=reset))
    zai1 = _fake("zai", error=ProviderSessionLimit("1308", reset_time=reset))
    router1 = _build([claude1, zai1], events_db)
    with pytest.raises(ProviderException):
        await router1.generate([{"role": "user", "content": "x"}])

    # Tick 2 — fresh router; both holds recovered from DB; no probing.
    claude2 = _fake("claude", error=ProviderUnavailable("down"))
    zai2 = _fake("zai", error=ProviderUnavailable("down"))
    router2 = _build([claude2, zai2], events_db)
    with pytest.raises(ProviderUnavailable):
        await router2.generate([{"role": "user", "content": "x"}])

    claude2.generate.assert_not_called()
    zai2.generate.assert_not_called()
    assert any("PROVIDERS DOWN" in m for m in sent), \
        "all-providers-unavailable must page immediately on the rebuild"
