"""Audit 2026-07-10 P-2: provider events must be persisted to SQLite so
providers/metrics.py reads real data instead of a permanently-empty table."""
import sqlite3
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker
from engine.agent_firm.providers.errors import ProviderUnavailable
from engine.agent_firm.providers.events import ProviderEvent, log_provider_event
from engine.agent_firm.providers.metrics import provider_stats
from engine.agent_firm.providers.router import ProviderRouter


@pytest.fixture
def events_db(tmp_path):
    db = tmp_path / "events.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE provider_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT, reason TEXT, duration_s REAL, request_id TEXT,
            failover INTEGER DEFAULT 0,
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


def _event(**kw):
    base = dict(event_type="provider_selected",
                timestamp=datetime.now(timezone.utc), provider="zai")
    base.update(kw)
    return ProviderEvent(**base)


def _rows(db):
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT event_type, provider, failover FROM provider_events ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def test_event_persisted_when_db_path_given(events_db):
    log_provider_event(_event(model="glm", duration_s=1.5, failover=True),
                       db_path=str(events_db))
    assert _rows(events_db) == [("provider_selected", "zai", 1)]


def test_no_db_write_when_db_path_omitted(events_db):
    log_provider_event(_event())          # log-only path (hermetic default)
    assert _rows(events_db) == []


def test_persist_failure_never_raises(tmp_path, caplog):
    empty = tmp_path / "no_table.db"
    sqlite3.connect(empty).close()        # DB exists, table doesn't
    log_provider_event(_event(), db_path=str(empty))  # must not raise


def _resp(provider):
    return ProviderResponse(
        content="ok", provider=provider, model="m", runtime_version="v",
        tokens_in=1, tokens_out=1, cost_usd=0.0, duration_s=0.1,
        timestamp=datetime.now(timezone.utc),
    )


def _fake(name, error=None):
    p = AsyncMock()
    p.name = name
    p.capabilities = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=True, supports_tools=True)
    if error is not None:
        p.generate.side_effect = error
    else:
        p.generate.return_value = _resp(name)
    return p


@pytest.mark.asyncio
async def test_zai_to_claude_failover_persists_event_chain(events_db):
    router = ProviderRouter(
        [(_fake("zai", error=ProviderUnavailable("429")), CircuitBreaker()),
         (_fake("claude"), CircuitBreaker())],
        db_path=str(events_db))
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude" and resp.failover is True
    assert _rows(events_db) == [
        ("provider_failed", "zai", 0),
        ("provider_failover", "claude", 1),
    ]


@pytest.mark.asyncio
async def test_claude_to_zai_failover_persists_event_chain(events_db):
    router = ProviderRouter(
        [(_fake("claude", error=ProviderUnavailable("cli down")), CircuitBreaker()),
         (_fake("zai"), CircuitBreaker())],
        db_path=str(events_db))
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai" and resp.failover is True
    assert _rows(events_db) == [
        ("provider_failed", "claude", 0),
        ("provider_failover", "zai", 1),
    ]


@pytest.mark.asyncio
async def test_circuit_open_and_close_events_persisted(events_db):
    failing = _fake("zai", error=ProviderUnavailable("down"))
    breaker = CircuitBreaker(failure_threshold=2, cooldown_s=0.0)
    router = ProviderRouter([(failing, breaker)], db_path=str(events_db))

    for _ in range(2):                      # trip the breaker (threshold=2)
        with pytest.raises(ProviderUnavailable):
            await router.generate([{"role": "user", "content": "x"}])
    assert ("provider_circuit_open", "zai", 0) in _rows(events_db)

    failing.generate.side_effect = None     # provider recovers
    failing.generate.return_value = _resp("zai")
    resp = await router.generate([{"role": "user", "content": "x"}])  # HALF_OPEN trial
    assert resp.provider == "zai"
    assert ("provider_circuit_closed", "zai", 0) in _rows(events_db)


@pytest.mark.asyncio
async def test_exhausted_router_error_carries_provider_attribution(events_db):
    router = ProviderRouter(
        [(_fake("zai", error=ProviderUnavailable("429")), CircuitBreaker())],
        db_path=str(events_db))
    with pytest.raises(ProviderUnavailable) as exc_info:
        await router.generate([{"role": "user", "content": "x"}])
    assert getattr(exc_info.value, "provider", None) == "zai"


@pytest.mark.asyncio
async def test_metrics_read_real_failover_data(events_db):
    router = ProviderRouter(
        [(_fake("zai", error=ProviderUnavailable("429")), CircuitBreaker()),
         (_fake("claude"), CircuitBreaker())],
        db_path=str(events_db))
    await router.generate([{"role": "user", "content": "x"}])

    stats = provider_stats(str(events_db), "zai", since="2020-01-01")
    assert stats.circuit_state in ("CLOSED", "OPEN", "HALF_OPEN")
    conn = sqlite3.connect(events_db)
    n = conn.execute("SELECT COUNT(*) FROM provider_events").fetchone()[0]
    conn.close()
    assert n == 2, "metrics now have real rows to read (was permanently 0)"


# --- RCA 2026-07-10: session-limit events carry the advertised reset time ----

def test_session_limit_event_persists_reset_time(events_db):
    reset = datetime(2026, 7, 10, 11, 20, tzinfo=timezone.utc)
    log_provider_event(
        _event(event_type="provider_session_limit", provider="claude",
               model="sonnet", reason="session limit", reset_time=reset),
        db_path=str(events_db))
    conn = sqlite3.connect(events_db)
    row = conn.execute(
        "SELECT event_type, provider, reset_time FROM provider_events").fetchone()
    conn.close()
    assert row == ("provider_session_limit", "claude", "2026-07-10 11:20:00")


def test_persist_self_heals_missing_reset_time_column(tmp_path):
    """Prod DBs created before this change lack the column; the writer must
    add it on first use instead of silently dropping telemetry."""
    db = tmp_path / "old_schema.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE provider_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL, provider TEXT NOT NULL,
            model TEXT, reason TEXT, duration_s REAL, request_id TEXT,
            failover INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit(); conn.close()

    log_provider_event(
        _event(event_type="provider_session_limit", provider="claude",
               reset_time=datetime(2026, 7, 10, 11, 20, tzinfo=timezone.utc)),
        db_path=str(db))
    conn = sqlite3.connect(db)
    row = conn.execute("SELECT event_type, reset_time FROM provider_events").fetchone()
    conn.close()
    assert row == ("provider_session_limit", "2026-07-10 11:20:00")


def test_skip_and_restore_event_types_accepted(events_db):
    log_provider_event(_event(event_type="provider_skipped", provider="claude",
                              reason="session limit hold"), db_path=str(events_db))
    log_provider_event(_event(event_type="provider_restored", provider="claude"),
                       db_path=str(events_db))
    assert [r[0] for r in _rows(events_db)] == ["provider_skipped", "provider_restored"]


def test_init_agent_firm_tables_adds_reset_time_column(tmp_path, monkeypatch):
    import importlib
    from data import db as data_db
    monkeypatch.setenv("DB_PATH", str(tmp_path / "fresh.db"))
    importlib.reload(data_db)
    data_db.init_agent_firm_tables()
    conn = sqlite3.connect(tmp_path / "fresh.db")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(provider_events)")}
    conn.close()
    assert "reset_time" in cols
