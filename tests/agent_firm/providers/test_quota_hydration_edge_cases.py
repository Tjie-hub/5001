"""Edge-case & regression-breaker tests for quota-hold hydration
(audit 2026-07-21, post-deploy investigation).

These deliberately try to BREAK the hydration: corrupted timestamps, missing
DB, stale holds that should expire, duplicate session-limit rows, repeated
hydration calls, multi-tick simulation, provider restart mid-window, and
clock skew. If any of these expose a real defect in the patch, the test
fails LOUD here — before any claim of correctness.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import AsyncMock, Mock

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker
from engine.agent_firm.providers.errors import ProviderUnavailable
from engine.agent_firm.providers.events import ProviderEvent, log_provider_event
from engine.agent_firm.providers.router import (
    ProviderRouter, _hydrate_quota_holds, _parse_utc,
)


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path):
    p = tmp_path / "edge.db"
    conn = sqlite3.connect(p)
    conn.executescript("""
        CREATE TABLE provider_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL, provider TEXT NOT NULL,
            model TEXT, reason TEXT, duration_s REAL, request_id TEXT,
            failover INTEGER DEFAULT 0, reset_time TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    return p


@pytest.fixture
def clock(monkeypatch):
    from engine.agent_firm.providers import router as rm
    state = {"now": datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(rm, "_now", lambda: state["now"])
    return state


def _seed(db, *, provider, event_type, reset_time=None, created_at=None):
    log_provider_event(ProviderEvent(
        event_type=event_type, timestamp=created_at or datetime.now(timezone.utc),
        provider=provider, reason="x", reset_time=reset_time,
    ), db_path=str(db))


# ── NEGATIVE: empty / missing / corrupt ──────────────────────────────────────

def test_empty_provider_events_returns_no_holds(db):
    assert _hydrate_quota_holds(str(db)) == {}


def test_missing_db_file_returns_empty_and_does_not_raise(tmp_path):
    missing = tmp_path / "does_not_exist.db"
    assert _hydrate_quota_holds(str(missing)) == {}


def test_missing_table_returns_empty_and_does_not_raise(tmp_path):
    """A DB with no provider_events table (pre-Phase-1 schema) must degrade
    silently to in-memory-only behavior."""
    p = tmp_path / "notable.db"
    sqlite3.connect(p).close()
    assert _hydrate_quota_holds(str(p)) == {}


def test_corrupted_reset_time_does_not_crash(db, clock):
    """A garbage reset_time string must not crash hydration — it is treated
    as no-reset (fallback window)."""
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO provider_events (event_type, provider, reset_time, created_at) "
        "VALUES ('provider_session_limit', 'claude', 'not-a-timestamp', "
        "'2026-07-21 11:55:00')")
    conn.commit()
    conn.close()
    # Must not raise; result is the fallback hold (failure_time + 900s).
    # `clock` freezes _now() to 12:00 UTC so the 11:55 + 900s = 12:10 hold
    # is unambiguously in the future and deterministic.
    holds = _hydrate_quota_holds(str(db))
    assert "claude" in holds


def test_corrupted_created_at_does_not_crash(db, clock):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO provider_events (event_type, provider, reset_time, created_at) "
        "VALUES ('provider_session_limit', 'claude', '2026-07-21 14:00:00', 'GARBAGE')")
    conn.commit()
    conn.close()
    holds = _hydrate_quota_holds(str(db))  # must not raise
    # reset_time is valid and in the future (relative to the frozen clock,
    # 12:00 UTC) -> hold is reconstructed from it despite the garbage
    # created_at. Without freezing `_now()` this assertion silently rots the
    # moment the wall clock passes 2026-07-21 14:00 UTC (found 2026-07-22).
    assert "claude" in holds


def test_parse_utc_rejects_garbage():
    assert _parse_utc(None) is None
    assert _parse_utc("") is None
    assert _parse_utc("garbage") is None
    assert _parse_utc("2026-07-21 12:00:00") == datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)


# ── EXPIRED / STALE holds ────────────────────────────────────────────────────

def test_expired_reset_time_is_not_hydrated(db, clock):
    """A session-limit whose reset_time is ALREADY in the past must NOT pin
    the provider (no stale-hold-forever)."""
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=clock["now"] - timedelta(hours=1))  # past
    assert _hydrate_quota_holds(str(db)) == {}


def test_expired_fallback_window_is_not_hydrated(db, clock):
    """z.ai no-reset case: created_at + 900s already elapsed -> no hold."""
    _seed(db, provider="zai", event_type="provider_session_limit",
          reset_time=None, created_at=clock["now"] - timedelta(hours=1))
    assert _hydrate_quota_holds(str(db)) == {}


def test_no_stale_hold_forever_when_reset_time_far_future(db, clock, monkeypatch):
    """Cap must prevent a far-future reset from benching a provider forever.
    QUOTA_MAX_HOLD_S default = 6h; a reset 30 days out must still expire at
    failure_time + 6h."""
    from engine.agent_firm import config as cfg
    monkeypatch.setattr(cfg, "QUOTA_MAX_HOLD_S", 6 * 3600)
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=clock["now"] + timedelta(days=30),
          created_at=clock["now"])
    holds = _hydrate_quota_holds(str(db))
    # Hold exists now (within the 6h cap)...
    assert "claude" in holds
    # ...but advancing past failure_time+6h must drop it.
    clock["now"] = clock["now"] + timedelta(hours=6, minutes=5)
    assert _hydrate_quota_holds(str(db)) == {}


# ── provider_restored clears the hold ────────────────────────────────────────

def test_restored_after_session_limit_clears_hold(db, clock):
    """If the most recent event for a provider is provider_restored, the
    provider is available — even if an earlier session_limit had a future
    reset_time. (No 'hold never restored'.)"""
    reset = clock["now"] + timedelta(hours=2)
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=reset, created_at=clock["now"] - timedelta(minutes=10))
    _seed(db, provider="claude", event_type="provider_restored",
          created_at=clock["now"] - timedelta(minutes=1))
    assert _hydrate_quota_holds(str(db)) == {}


def test_new_session_limit_after_restore_re_holds(db, clock):
    """A provider that recovered and then re-exhausted must be held based on
    the LATEST session_limit, not the restored event."""
    reset = clock["now"] + timedelta(hours=2)
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=clock["now"] - timedelta(hours=5),
          created_at=clock["now"] - timedelta(hours=5))
    _seed(db, provider="claude", event_type="provider_restored",
          created_at=clock["now"] - timedelta(hours=4))
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=reset, created_at=clock["now"] - timedelta(minutes=5))
    holds = _hydrate_quota_holds(str(db))
    assert "claude" in holds
    assert holds["claude"]["reset_time"] == reset


# ── DUPLICATED holds / repeated hydration ────────────────────────────────────

def test_many_duplicate_session_limit_rows_yield_one_hold(db, clock):
    """A parallel fan-out can write N session_limit rows in the same second
    (the 09:40 burst wrote 17). Hydration must collapse to ONE hold, keyed
    by the latest (highest id)."""
    reset = clock["now"] + timedelta(hours=2)
    for _ in range(17):
        _seed(db, provider="claude", event_type="provider_session_limit",
              reset_time=reset, created_at=clock["now"])
    holds = _hydrate_quota_holds(str(db))
    assert list(holds.keys()) == ["claude"]
    assert holds["claude"]["reset_time"] == reset


def test_repeated_hydration_is_idempotent(db, clock):
    """Calling _hydrate_quota_holds twice must yield identical results — no
    accumulated state (it's a pure function of the DB)."""
    reset = clock["now"] + timedelta(hours=2)
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=reset)
    h1 = _hydrate_quota_holds(str(db))
    h2 = _hydrate_quota_holds(str(db))
    assert h1 == h2


def test_multiple_providers_hydrated_independently(db, clock):
    """Two providers with different reset horizons are both held, each with
    its own horizon."""
    claude_reset = clock["now"] + timedelta(hours=2)
    zai_created = clock["now"] - timedelta(seconds=60)  # fallback hold applies
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=claude_reset)
    _seed(db, provider="zai", event_type="provider_session_limit",
          reset_time=None, created_at=zai_created)
    holds = _hydrate_quota_holds(str(db))
    assert set(holds.keys()) == {"claude", "zai"}
    assert holds["claude"]["reset_time"] == claude_reset
    assert holds["zai"]["reset_time"] is None


# ── MULTI-TICK simulation: exactly the production lifecycle ─────────────────

def _resp(provider):
    return ProviderResponse(
        content="ok", provider=provider, model="m", runtime_version="v",
        tokens_in=1, tokens_out=1, cost_usd=0.0, duration_s=0.1,
        timestamp=datetime.now(timezone.utc),
    )


def _fake(name, *, error=None):
    from engine.agent_firm.providers.errors import ProviderSessionLimit
    p = AsyncMock()
    p.name = name
    p.model = Mock(return_value="m")
    p.capabilities = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=True, supports_tools=True)
    if error is not None:
        p.generate.side_effect = error
    else:
        p.generate.return_value = _resp(name)
    return p


@pytest.mark.asyncio
async def test_multi_tick_three_rebuilds_each_honor_hold(db, clock, monkeypatch):
    """Simulate 3 consecutive scheduler ticks (3 fresh routers) against the
    SAME db. Claude is held with a 2h reset. NONE of the 3 rebuilt routers
    may probe claude; all must failover to zai. This is the exact production
    lifecycle (firm.evaluate_staged rebuilds per tick)."""
    from engine.agent_firm.providers.errors import ProviderSessionLimit
    reset = clock["now"] + timedelta(hours=2)

    # Tick 0 (seed): an earlier tick wrote the session-limit event.
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=reset, created_at=clock["now"] - timedelta(minutes=1))

    claude_probe_count = 0
    for tick in range(3):
        claude = _fake("claude")  # fresh provider mock per tick
        zai = _fake("zai")
        router = ProviderRouter(
            [(claude, CircuitBreaker()), (zai, CircuitBreaker())],
            db_path=str(db),
        )
        resp = await router.generate([{"role": "user", "content": "x"}])
        assert resp.provider == "zai", f"tick {tick}: should failover to zai"
        claude_probe_count += claude.generate.call_count

    assert claude_probe_count == 0, \
        f"claude must never be probed across 3 ticks; got {claude_probe_count} probes"


@pytest.mark.asyncio
async def test_provider_recovery_after_process_restart(db, clock):
    """Provider 'restart' = a fresh router built after reset_time elapsed.
    The fresh router must probe claude exactly once and succeed."""
    reset = clock["now"]  # reset is NOW
    _seed(db, provider="claude", event_type="provider_session_limit",
          reset_time=reset, created_at=clock["now"] - timedelta(hours=2))
    _seed(db, provider="claude", event_type="provider_restored",
          created_at=clock["now"] - timedelta(seconds=1))

    claude = _fake("claude")
    router = ProviderRouter(
        [(claude, CircuitBreaker()), _fake("zai")], db_path=str(db))
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"
    assert claude.generate.call_count == 1


# ── CLOCK SKEW: hydration uses UTC strings consistently ─────────────────────

def test_clock_skew_hydration_uses_utc_consistently(db, monkeypatch):
    """Hydration compares _now() (UTC aware) against UTC-parsed persisted
    timestamps. Verify the comparison is timezone-correct by simulating a
    reset_time stored as UTC string vs _now in UTC."""
    from engine.agent_firm.providers import router as rm
    # _now() returns UTC. Persisted reset_time is a UTC '%Y-%m-%d %H:%M:%S'.
    state = {"now": datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(rm, "_now", lambda: state["now"])

    # reset 1h in the future (UTC string)
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO provider_events (event_type, provider, reset_time, created_at) "
        "VALUES ('provider_session_limit', 'claude', '2026-07-21 13:00:00', "
        "'2026-07-21 11:00:00')")
    conn.commit()
    conn.close()
    holds = _hydrate_quota_holds(str(db))
    assert "claude" in holds  # 13:00 > 12:00 now -> held
    assert holds["claude"]["reset_time"] == datetime(2026, 7, 21, 13, 0, tzinfo=timezone.utc)
