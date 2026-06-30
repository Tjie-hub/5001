"""Connection + schema bootstrap tests.

Task 1: ft_get_db (row factory, busy_timeout).
Task 2: init_ft_tables (table creation, idempotency, unique constraint, WAL).
"""
import sqlite3

import pytest

from forward_testing.storage.db import ft_get_db, init_ft_tables


# ── Task 1: connection helper ─────────────────────────────────────────────────

def test_ft_get_db_sets_row_factory_and_busy_timeout(tmp_path):
    db_path = str(tmp_path / "ft.db")
    conn = ft_get_db(db_path)
    try:
        assert conn.row_factory is sqlite3.Row
        bt = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert bt == 30000
    finally:
        conn.close()


def test_ft_get_db_enforces_foreign_keys(tmp_path):
    # The schema declares REFERENCES but SQLite ignores them unless foreign_keys
    # is ON per-connection. An orphan child (no parent ft_signal) must be rejected.
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = ft_get_db(db_path)
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO ft_signal_state (signal_id, state) VALUES (424242, 'GENERATED')"
            )
    finally:
        conn.close()


# ── Task 2: schema bootstrap ──────────────────────────────────────────────────

EXPECTED_TABLES = {
    "ft_strategy_version", "ft_signal", "ft_signal_state",
    "ft_transition_log", "ft_run", "ft_run_log",
}


def test_init_ft_tables_creates_all_phase1_tables(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    names = {r[0] for r in rows}
    missing = EXPECTED_TABLES - names
    assert not missing, f"missing tables: {missing}"


def test_init_ft_tables_is_idempotent(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    init_ft_tables(db_path)  # second call must not error
    conn = sqlite3.connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ft_signal)")}
    conn.close()
    assert {"signal_date", "ticker", "strategy", "track"}.issubset(cols)


def test_init_ft_tables_enables_wal(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)  # _ensure_wal runs here
    conn = sqlite3.connect(db_path)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode.lower() == "wal"


def test_ft_signal_unique_constraint(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO ft_signal (signal_date, ticker, strategy, track, direction) "
        "VALUES (?,?,?,?,?)",
        ("2026-06-27", "BBCA", "TFB", "SHADOW", "LONG"),
    )
    try:
        conn.execute(
            "INSERT INTO ft_signal (signal_date, ticker, strategy, track, direction) "
            "VALUES (?,?,?,?,?)",
            ("2026-06-27", "BBCA", "TFB", "SHADOW", "LONG"),
        )
        collided = False
    except sqlite3.IntegrityError:
        collided = True
    conn.commit()
    conn.close()
    assert collided


def test_init_db_creates_ft_tables(tmp_path, monkeypatch):
    # Point data.db at a temp DB so init_db() bootstraps in isolation.
    db_path = str(tmp_path / "init.db")
    import data.db as data_db
    monkeypatch.setattr(data_db, "DB_PATH", db_path)

    # init_db() also calls init_agent_firm_tables(); that is fine on a fresh DB.
    data_db.init_db()

    conn = sqlite3.connect(db_path)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "ft_signal" in names
    assert "ft_transition_log" in names


# ── Phase 2: shadow position/trade tables ──────────────────────────────────────

PHASE2_TABLES = {"ft_shadow_position", "ft_shadow_trade"}


def test_init_ft_tables_creates_phase2_tables(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    conn = sqlite3.connect(db_path)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert PHASE2_TABLES.issubset(names)


def test_init_ft_tables_phase2_idempotent(tmp_path):
    db_path = str(tmp_path / "ft.db")
    init_ft_tables(db_path)
    init_ft_tables(db_path)  # re-run must not error
    conn = sqlite3.connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ft_shadow_position)")}
    conn.close()
    assert {"signal_id", "direction", "entry_price", "status"}.issubset(cols)


def test_init_db_creates_phase2_tables(tmp_path, monkeypatch):
    db_path = str(tmp_path / "init.db")
    import data.db as data_db
    monkeypatch.setattr(data_db, "DB_PATH", db_path)
    data_db.init_db()
    conn = sqlite3.connect(db_path)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "ft_shadow_position" in names
    assert "ft_shadow_trade" in names
