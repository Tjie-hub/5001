"""Phase 9 test — no future tick visibility in intraday ORB replay (fix C-4).

check_orb_intraday_signal previously read the session's LAST tick regardless
of the simulated clock, so an as_of_time replay saw the close of day. After
the fix: a replay at T can only observe ticks with time <= T; T1 < T2 implies
T1 never sees a tick occurring after T1.
"""
import sqlite3

import pytest

from data.db import connect as db_connect


@pytest.fixture
def ticks_db(tmp_path):
    path = str(tmp_path / "replay.db")
    conn = db_connect(path)
    conn.execute("CREATE TABLE ticks (ticker TEXT, date TEXT, time TEXT, "
                 "price REAL, volume REAL)")
    rows = []
    # Five prior sessions (opening-window ticks) so the OR-vol history passes:
    for i, d in enumerate(["2026-08-24", "2026-08-25", "2026-08-26",
                           "2026-08-27", "2026-08-28"]):
        rows.append(("X", d, "09:10:00", 100.0 + i, 100.0))
    # Replay day: full OR window (09:00–09:30), then LATER ticks the earlier
    # replays must never see:
    rows += [
        ("X", "2026-08-31", "09:01:00", 100.0, 100.0),
        ("X", "2026-08-31", "09:02:00", 100.5, 100.0),
        ("X", "2026-08-31", "09:03:00", 99.5, 100.0),
        ("X", "2026-08-31", "09:04:00", 100.0, 100.0),
        ("X", "2026-08-31", "09:05:00", 100.0, 100.0),
        ("X", "2026-08-31", "10:00:00", 110.0, 100.0),
        ("X", "2026-08-31", "15:00:00", 120.0, 100.0),
    ]
    conn.executemany("INSERT INTO ticks VALUES (?,?,?,?,?)", rows)
    conn.commit()
    yield path
    conn.close()


def _replay(db_path, as_of_time):
    from engine.strategies import check_orb_intraday_signal
    return check_orb_intraday_signal(
        "X", opening_minutes=30, lookback_days=20, db_path=db_path,
        as_of_date="2026-08-31", as_of_time=as_of_time)


def test_replay_at_t1_never_sees_later_ticks(ticks_db):
    res = _replay(ticks_db, "10:30")
    assert res["details"]["current_price"] == 110.0     # 15:00 tick invisible


def test_replay_monotonicity_t1_t2(ticks_db):
    """T1 < T2: the T1 view is a prefix of the T2 view — no future leak."""
    r1030 = _replay(ticks_db, "10:30")
    r1400 = _replay(ticks_db, "14:00")
    r1530 = _replay(ticks_db, "15:30")
    assert r1400["details"]["current_price"] == 110.0   # 15:00 still invisible
    assert r1530["details"]["current_price"] == 120.0   # 15:00 now visible
    assert r1030["details"]["current_price"] == r1400["details"]["current_price"]


def test_replay_before_opening_window_complete_is_refused(ticks_db):
    res = _replay(ticks_db, "09:15")
    assert res["has_signal"] is False
    assert "belum lengkap" in res["reason"]
