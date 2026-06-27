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
