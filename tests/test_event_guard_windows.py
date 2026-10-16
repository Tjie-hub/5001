"""2026-10-16 brief Z2: the event guard reads a DATED calendar (paper_config event_guard_windows,
seeded from MSCI's published Index Review calendar + the migrated June 2026 window) instead of one
hardcoded 2026-06 window. The October consultation shock passed with the guard off because the
only configured window had expired in June."""
import json
import sqlite3

import scheduler.scanner as scanner
import engine.forward_window as forward_window


WINDOWS = [
    {"id": "w-a", "start": "2026-11-11", "end": "2026-12-01", "size_mult": 0.5, "source": "test"},
    {"id": "w-b", "start": "2026-11-20", "end": "2026-11-25", "size_mult": 0.3, "source": "test"},
    {"id": "w-c", "start": "2027-02-09", "end": "2027-03-01", "size_mult": 0.5, "source": "test"},
]


def test_seeding_is_idempotent_and_an_owner_edit_wins(tmp_path, monkeypatch):
    import paper_trade
    db = str(tmp_path / "paper.db")
    monkeypatch.setattr(paper_trade, "DB_PATH", db)
    for _ in range(2):                                   # startup runs on every boot
        paper_trade.init_paper_table()
    conn = sqlite3.connect(db)
    seeded = json.loads(conn.execute(
        "SELECT value FROM paper_config WHERE key='event_guard_windows'").fetchone()[0])
    conn.close()
    assert seeded == paper_trade.DEFAULT_EVENT_GUARD_WINDOWS
    conn = sqlite3.connect(db)                           # an owner edit must survive a reboot
    conn.execute("UPDATE paper_config SET value='[]' WHERE key='event_guard_windows'")
    conn.commit(); conn.close()
    paper_trade.init_paper_table()
    conn = sqlite3.connect(db)
    assert json.loads(conn.execute(
        "SELECT value FROM paper_config WHERE key='event_guard_windows'").fetchone()[0]) == []
    conn.close()


def test_seeded_calendar_dates_match_the_msci_release():
    """The bounds as published in MSCI's 'next eight Index Review dates' release of 2026-08-12
    (primary source, fetched 2026-10-16) -- a fat-finger edit to the seeded list fails here."""
    import paper_trade
    by_id = {w["id"]: w for w in paper_trade.DEFAULT_EVENT_GUARD_WINDOWS}
    assert by_id["msci-2026-06-review"]["start"] == "2026-06-15"      # migrated legacy window
    assert by_id["msci-2026-06-review"]["end"] == "2026-06-24"
    assert (by_id["msci-ir-2026-11"]["start"], by_id["msci-ir-2026-11"]["end"]) == \
        ("2026-11-11", "2026-12-01")
    assert (by_id["msci-ir-2028-08"]["start"], by_id["msci-ir-2028-08"]["end"]) == \
        ("2028-08-14", "2028-09-01")
    assert len(paper_trade.DEFAULT_EVENT_GUARD_WINDOWS) == 9          # June + 8 reviews


def test_guard_bounds_are_inclusive_and_default_mult(monkeypatch):
    monkeypatch.setattr(scanner, "_load_event_guard_windows", lambda: WINDOWS)
    monkeypatch.setattr(scanner, "_shock_guard_active", lambda: False)
    for day in ("2026-11-11", "2026-12-01", "2026-11-20"):
        assert scanner._event_guard_status(day)["active"] is True
    for day in ("2026-11-10", "2026-12-02", "2026-10-16"):
        s = scanner._event_guard_status(day)
        assert s == {"active": False, "size_mult": 0.5, "source": None}


def test_overlapping_windows_take_the_most_restrictive_mult(monkeypatch):
    monkeypatch.setattr(scanner, "_load_event_guard_windows", lambda: WINDOWS)
    monkeypatch.setattr(scanner, "_shock_guard_active", lambda: False)
    s = scanner._event_guard_status("2026-11-21")       # inside w-a (0.5) and w-b (0.3)
    assert s["active"] is True and s["size_mult"] == 0.3
    assert s["source"].startswith("w-a ")               # earliest-starting window names the source
    assert scanner._event_guard_status("2026-11-13")["size_mult"] == 0.5


def test_shock_rule_names_itself_when_no_window_matches(monkeypatch):
    monkeypatch.setattr(scanner, "_load_event_guard_windows", lambda: WINDOWS)
    monkeypatch.setattr(scanner, "_shock_guard_active", lambda: True)
    s = scanner._event_guard_status("2026-10-16")
    assert s["active"] is True and "shock rule" in s["source"]


def test_bad_config_rows_are_skipped_not_fatal(monkeypatch):
    import paper_trade
    monkeypatch.setattr(paper_trade, "get_config",
                        lambda: {"event_guard_windows": "not-json{"})
    assert scanner._load_event_guard_windows() == []
    monkeypatch.setattr(paper_trade, "get_config", lambda: {
        "event_guard_windows": json.dumps(
            [{"id": "ok", "start": "2026-11-11", "end": "2026-11-12"},
             {"no": "start here"}, 5])})
    assert [w["id"] for w in scanner._load_event_guard_windows()] == ["ok"]


def test_forward_window_freezes_the_calendar(tmp_path):
    """The calendar is part of the forward-test frozen config: editing it must roll open
    windows (engine/forward_window), the designed response to a regime change."""
    conn = sqlite3.connect(str(tmp_path / "w.db"))
    conn.execute("CREATE TABLE paper_config (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO paper_config VALUES ('event_guard_windows','[]')")
    conn.execute("INSERT INTO paper_config VALUES ('capital','50000000')")
    cfg = forward_window._paper_config(conn)
    conn.close()
    assert cfg == {"event_guard_windows": "[]"}         # capital is NOT frozen; the calendar is
