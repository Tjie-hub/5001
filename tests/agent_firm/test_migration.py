import sqlite3


def test_agent_decisions_table_exists(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_decisions)")}
    expected = {
        "id", "scan_time", "ticker", "strategy", "quant_score",
        "decision", "confidence", "size_hint", "rationale",
        "overridden", "tokens_in", "tokens_out", "cost_usd",
        "duration_s", "created_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_agent_traces_table_exists(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_traces)")}
    expected = {
        "id", "decision_id", "role", "prompt_version",
        "output", "tools_called", "tokens_in", "tokens_out",
        "duration_s", "created_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_scheduled_signals_has_agent_decision_id(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(scheduled_signals)")}
    assert "agent_decision_id" in cols


def test_indexes_exist(tmp_db):
    conn = sqlite3.connect(tmp_db)
    idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_agent_decisions_ticker_date" in idx
    assert "idx_agent_traces_decision" in idx
