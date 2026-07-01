"""SignalAdapter tests: ingest, dedupe, strategy/direction mapping, idempotency."""
import sqlite3

from forward_testing.adapters.signal_adapter import SignalAdapter


def _seed_signal(conn, scan_time, ticker, strategies, flow_score, direction="BUY"):
    conn.execute(
        "INSERT INTO scheduled_signals "
        "(scan_time, ticker, strategies, flow_score, signal_direction) "
        "VALUES (?,?,?,?,?)",
        (scan_time, ticker, strategies, flow_score, direction),
    )


def test_ingest_creates_shadow_signals_at_generated(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB,Swing", 60)
    _seed_signal(conn, "2026-06-27 16:15", "TLKM", "MTF_REVERSAL", 45)
    conn.commit()
    conn.close()

    n = SignalAdapter(repo, ft_db).ingest("2026-06-27")
    assert n == 2

    conn = sqlite3.connect(ft_db)
    rows = conn.execute(
        "SELECT ticker, strategy, track, direction FROM ft_signal ORDER BY ticker"
    ).fetchall()
    states = conn.execute("SELECT state FROM ft_signal_state").fetchall()
    conn.close()
    assert [r[0] for r in rows] == ["BBCA", "TLKM"]
    assert all(r[2] == "SHADOW" for r in rows)
    assert all(r[1] for r in rows)  # strategy resolved
    assert {s[0] for s in states} == {"GENERATED"}


def test_ingest_takes_first_strategy_from_comma_list(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB,Swing,Panic", 60)
    conn.commit()
    conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-27")
    conn = sqlite3.connect(ft_db)
    strat = conn.execute("SELECT strategy FROM ft_signal").fetchone()[0]
    conn.close()
    assert strat == "TFB"


def test_ingest_maps_direction(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB", 60, direction="SELL")
    conn.commit()
    conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-27")
    conn = sqlite3.connect(ft_db)
    d = conn.execute("SELECT direction FROM ft_signal").fetchone()[0]
    conn.close()
    assert d == "SHORT"


def test_ingest_is_idempotent(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB", 60)
    conn.commit()
    conn.close()
    adapter = SignalAdapter(repo, ft_db)
    assert adapter.ingest("2026-06-27") == 1
    assert adapter.ingest("2026-06-27") == 0  # re-run: nothing new
    conn = sqlite3.connect(ft_db)
    n_signals = conn.execute("SELECT COUNT(*) FROM ft_signal").fetchone()[0]
    n_trans = conn.execute("SELECT COUNT(*) FROM ft_transition_log").fetchone()[0]
    conn.close()
    assert n_signals == 1
    assert n_trans == 1  # only the GENERATED entry, not duplicated


def test_ingest_records_source_link(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB", 60)
    conn.commit()
    src_id = conn.execute("SELECT id FROM scheduled_signals").fetchone()[0]
    conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-27")
    conn = sqlite3.connect(ft_db)
    row = conn.execute(
        "SELECT source_table, source_id, conviction FROM ft_signal"
    ).fetchone()
    conn.close()
    assert row[0] == "scheduled_signals"
    assert row[1] == src_id
    assert row[2] == 60


def test_ingest_filters_by_run_date_only(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    _seed_signal(conn, "2026-06-27 16:15", "BBCA", "TFB", 60)
    _seed_signal(conn, "2026-06-28 16:15", "TLKM", "TFB", 60)  # different day
    conn.commit()
    conn.close()
    n = SignalAdapter(repo, ft_db).ingest("2026-06-27")
    assert n == 1  # only the 27th
