"""FTRepo tests: insert idempotency, state init, transition audit."""
import sqlite3
from forward_testing.storage.repo import FTRepo


def test_insert_signal_is_idempotent_and_returns_id(repo, ft_db):
    sid1 = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    sid2 = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")  # dup
    assert sid1 == sid2  # same row
    conn = sqlite3.connect(ft_db)
    n = conn.execute("SELECT COUNT(*) FROM ft_signal").fetchone()[0]
    conn.close()
    assert n == 1


def test_insert_signal_distinct_tracks_are_separate_rows(repo, ft_db):
    a = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    b = repo.insert_signal("2026-06-27", "BBCA", "TFB", "PORTFOLIO")
    assert a != b
    conn = sqlite3.connect(ft_db)
    n = conn.execute("SELECT COUNT(*) FROM ft_signal").fetchone()[0]
    conn.close()
    assert n == 2


def test_get_signal_state_none_until_initialised(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    assert repo.get_signal_state(sid) is None


def test_init_signal_state_sets_generated(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    repo.init_signal_state(sid, "GENERATED")
    assert repo.get_signal_state(sid) == "GENERATED"


def test_init_signal_state_idempotent(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    repo.init_signal_state(sid, "GENERATED")
    repo.init_signal_state(sid, "GENERATED")  # no error, no change
    assert repo.get_signal_state(sid) == "GENERATED"


def test_write_transition_updates_state_and_logs(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    repo.init_signal_state(sid, "GENERATED")
    repo.write_transition(sid, "GENERATED", "CANDIDATE", "2026-06-27",
                          actor="manager", reason="dedupe-ok")
    assert repo.get_signal_state(sid) == "CANDIDATE"
    assert repo.count_transitions(sid) == 1


def test_create_run_and_finish_run(repo, ft_db):
    rid = repo.create_run("2026-06-27", kind="EOD")
    repo.finish_run(rid, "OK")
    conn = sqlite3.connect(ft_db)
    row = conn.execute("SELECT status FROM ft_run WHERE id=?", (rid,)).fetchone()
    conn.close()
    assert row[0] == "OK"


def test_get_signals_by_state_filters_track_and_state(repo, ft_db):
    conn = sqlite3.connect(ft_db)
    sid = repo.insert_signal("2026-06-26", "BBCA", "vol_weighted", "SHADOW")
    repo.init_signal_state(sid, "GENERATED")
    pid = repo.insert_signal("2026-06-26", "TLKM", "vol_weighted", "PORTFOLIO")
    repo.init_signal_state(pid, "GENERATED")
    conn.close()

    rows = repo.get_signals_by_state("GENERATED", track="SHADOW")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "BBCA"
    assert set(rows[0].keys()) >= {"id", "signal_date", "ticker", "strategy", "direction"}


def test_open_shadow_position_and_get(repo):
    repo.open_shadow_position(
        signal_id=1, ticker="BBCA", strategy="vol_weighted", direction="LONG",
        entry_date="2026-06-27", entry_price=100.0, atr14=1.0,
        sl_price=99.0, tp_price=102.0, trail_atr_mult=None, trail_anchor=100.0,
        highest_seen=100.0, lowest_seen=100.0,
    )
    pos = repo.get_shadow_position(1)
    assert pos["status"] == "OPEN"
    assert pos["entry_price"] == 100.0


def test_open_shadow_position_is_idempotent(repo):
    kwargs = dict(signal_id=1, ticker="BBCA", strategy="vol_weighted", direction="LONG",
                  entry_date="2026-06-27", entry_price=100.0, atr14=1.0,
                  sl_price=99.0, tp_price=102.0, trail_atr_mult=None, trail_anchor=100.0,
                  highest_seen=100.0, lowest_seen=100.0)
    repo.open_shadow_position(**kwargs)
    repo.open_shadow_position(**kwargs)   # duplicate PK -> ignored, no error
    assert repo.get_shadow_position(1)["entry_price"] == 100.0


def test_get_open_positions_update_and_close(repo):
    for sid in (1, 2):
        repo.open_shadow_position(
            signal_id=sid, ticker=f"T{sid}", strategy="vol_weighted", direction="LONG",
            entry_date="2026-06-27", entry_price=100.0, atr14=1.0,
            sl_price=99.0, tp_price=102.0, trail_atr_mult=None, trail_anchor=100.0,
            highest_seen=100.0, lowest_seen=100.0,
        )
    assert {r["signal_id"] for r in repo.get_open_shadow_positions()} == {1, 2}

    repo.update_shadow_position(1, highest_seen=101.0, lowest_seen=99.5, hold_days=2,
                                last_eval_date="2026-06-28")
    assert repo.get_shadow_position(1)["highest_seen"] == 101.0
    assert repo.get_shadow_position(1)["last_eval_date"] == "2026-06-28"

    repo.close_shadow_position(1, exit_date="2026-06-29", exit_price=102.0, exit_reason="TP")
    assert repo.get_shadow_position(1)["status"] == "CLOSED"
    assert repo.get_shadow_position(1)["exit_reason"] == "TP"
    assert repo.get_shadow_position(1)["last_eval_date"] == "2026-06-29"   # watermark = exit bar
    assert {r["signal_id"] for r in repo.get_open_shadow_positions()} == {2}


def test_insert_shadow_trade_is_idempotent(repo):
    kwargs = dict(signal_id=1, ticker="BBCA", strategy="vol_weighted", direction="LONG",
                  signal_date="2026-06-26", entry_date="2026-06-27", entry_price=100.0,
                  exit_date="2026-06-28", exit_price=102.0, exit_reason="TP",
                  pnl_pct=0.02, r_multiple=2.0, hold_days=2, mae_pct=-0.005, mfe_pct=0.02)
    repo.insert_shadow_trade(**kwargs)
    repo.insert_shadow_trade(**kwargs)     # duplicate -> ignored
    assert repo.get_shadow_trade(1)["r_multiple"] == 2.0
    conn = sqlite3.connect(repo.db_path)
    n = conn.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0]
    conn.close()
    assert n == 1
