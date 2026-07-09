import sqlite3

from engine.agent_firm.providers.metrics import provider_stats


def _seed_traces(db_path, rows):
    conn = sqlite3.connect(db_path)
    for provider, duration_s, error, created_at in rows:
        conn.execute(
            "INSERT INTO agent_traces (role, provider, duration_s, error, created_at) "
            "VALUES ('technical', ?, ?, ?, ?)",
            (provider, duration_s, error, created_at),
        )
    conn.commit()
    conn.close()


def test_provider_stats_basic_rates(tmp_db):
    _seed_traces(tmp_db, [
        ("claude", 1.0, None, "2026-07-08 09:00:00"),
        ("claude", 2.0, None, "2026-07-08 09:01:00"),
        ("claude", 3.0, "claude CLI timed out after 75s", "2026-07-08 09:02:00"),
        ("claude", 4.0, "some other failure", "2026-07-08 09:03:00"),
    ])
    stats = provider_stats(str(tmp_db), "claude", since="2026-07-08 00:00:00")
    assert stats.calls == 4
    assert stats.failures == 2
    assert stats.timeouts == 1
    assert stats.success_rate == 0.5
    assert stats.failure_rate == 0.5
    assert stats.timeout_rate == 0.25
    assert stats.avg_latency_s == 2.5


def test_provider_stats_empty_defaults_to_healthy():
    import tempfile
    from data.db import init_agent_firm_tables
    import os
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DB_PATH"] = db_path
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    init_agent_firm_tables()
    stats = provider_stats(db_path, "claude", since="2026-07-08 00:00:00")
    assert stats.calls == 0
    assert stats.success_rate == 1.0
    assert stats.failure_rate == 0.0
    assert stats.circuit_state == "CLOSED"


def test_provider_stats_circuit_state_from_latest_event(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "INSERT INTO provider_events (event_type, provider, created_at) "
        "VALUES ('provider_circuit_open', 'claude', '2026-07-08 09:00:00')"
    )
    conn.commit()
    conn.close()
    stats = provider_stats(str(tmp_db), "claude", since="2026-07-08 00:00:00")
    assert stats.circuit_state == "OPEN"


def test_provider_stats_zai_includes_cost_and_tokens(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "INSERT INTO agent_traces (role, provider, duration_s, cost_usd, tokens_in, "
        "tokens_out, created_at) VALUES ('technical', 'zai', 1.0, 0.001, 100, 50, "
        "'2026-07-08 09:00:00')"
    )
    conn.commit()
    conn.close()
    stats = provider_stats(str(tmp_db), "zai", since="2026-07-08 00:00:00")
    assert stats.cost_usd == 0.001
    assert stats.tokens_in == 100
    assert stats.tokens_out == 50


def test_provider_stats_claude_cost_is_none(tmp_db):
    _seed_traces(tmp_db, [("claude", 1.0, None, "2026-07-08 09:00:00")])
    stats = provider_stats(str(tmp_db), "claude", since="2026-07-08 00:00:00")
    assert stats.cost_usd is None
