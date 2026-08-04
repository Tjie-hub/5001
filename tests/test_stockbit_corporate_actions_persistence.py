"""Persistence tests for stockbit_corporate_actions.py's new
corporate_action_events table — separate from the existing yfinance-sourced
corporate_actions table (not overloaded, not modified)."""
import json
import sqlite3

from stockbit_corporate_actions import (
    init_db,
    save_corporate_actions,
    run_and_persist_corporate_actions,
)


def _sample_rows():
    return [
        {"ticker": "BBCA", "action_type": "dividend", "event_id": "117860",
         "event_date": "2026-06-17", "raw": {"dividend_value": "20"}},
        {"ticker": "BBCA", "action_type": "rups", "event_id": "1460182",
         "event_date": "2026-03-12", "raw": {"rups_venue": "Menara BCA"}},
    ]


def test_init_db_creates_corporate_action_events_table(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "corporate_action_events" in tables


def test_init_db_does_not_touch_existing_corporate_actions_table(tmp_path):
    """Guards the 'do not overload existing tables' constraint at the
    schema level — the yfinance-sourced corporate_actions table (dividends/
    splits only) must be untouched by this collector's schema init."""
    db_path = str(tmp_path / "wf.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE corporate_actions (ticker TEXT, date TEXT, action TEXT, value REAL, source TEXT)")
    conn.execute("INSERT INTO corporate_actions VALUES ('BBCA','2026-06-17','dividend',20,'yfinance')")
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(corporate_actions)")}
    rows = conn.execute("SELECT * FROM corporate_actions").fetchall()
    conn.close()
    assert cols == {"ticker", "date", "action", "value", "source"}  # unchanged
    assert len(rows) == 1  # untouched


def test_init_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    init_db(db_path)  # must not raise


def test_save_inserts_one_row_per_event(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    n = save_corporate_actions(conn, "BBCA", "2026-08-05", _sample_rows())
    conn.commit()
    rows = conn.execute(
        "SELECT ticker, action_type, event_id, event_date, raw_json, fetch_date "
        "FROM corporate_action_events ORDER BY action_type"
    ).fetchall()
    conn.close()
    assert n == 2
    assert len(rows) == 2
    assert rows[0][:5] == ("BBCA", "dividend", "117860", "2026-06-17",
                           json.dumps({"dividend_value": "20"}))
    assert rows[0][5] == "2026-08-05"


def test_save_skips_events_with_no_resolvable_event_id(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    rows = _sample_rows() + [
        {"ticker": "BBCA", "action_type": "mystery", "event_id": None,
         "event_date": None, "raw": {"note": "no id"}},
    ]
    n = save_corporate_actions(conn, "BBCA", "2026-08-05", rows)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM corporate_action_events").fetchone()[0]
    conn.close()
    assert n == 2  # only the 2 resolvable events counted
    assert count == 2


def test_save_rerun_same_event_updates_in_place_not_duplicated(tmp_path):
    """Idempotency: corporate actions are a stable event log keyed by
    (ticker, action_type, event_id) — NOT a dated snapshot series like
    broker_period_summary. Rerunning must update the existing row, not add
    a new one for a new fetch_date."""
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_corporate_actions(conn, "BBCA", "2026-08-05", _sample_rows())
    conn.commit()

    updated = _sample_rows()
    updated[0]["raw"] = {"dividend_value": "999", "note": "value corrected"}
    save_corporate_actions(conn, "BBCA", "2026-08-06", updated)  # different fetch_date, same event
    conn.commit()

    rows = conn.execute(
        "SELECT event_id, raw_json, fetch_date FROM corporate_action_events "
        "WHERE action_type='dividend'"
    ).fetchall()
    conn.close()
    assert len(rows) == 1  # still 1, not 2 — despite the different fetch_date
    assert json.loads(rows[0][1])["dividend_value"] == "999"  # latest wins
    assert rows[0][2] == "2026-08-06"  # fetch_date tracks last refresh, not part of the key


def test_save_different_tickers_and_action_types_both_kept(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_corporate_actions(conn, "BBCA", "2026-08-05", _sample_rows())
    save_corporate_actions(conn, "BRPT", "2026-08-05", [
        {"ticker": "BRPT", "action_type": "dividend", "event_id": "118025",
         "event_date": "2026-07-06", "raw": {"dividend_value": "1.63"}},
    ])
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM corporate_action_events").fetchone()[0]
    conn.close()
    assert count == 3


def test_run_and_persist_corporate_actions_end_to_end(tmp_path, monkeypatch):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)

    import stockbit_corporate_actions as sca

    def _fake_fetch(token, ticker):
        assert ticker == "BBCA"
        return _sample_rows()

    monkeypatch.setattr(sca, "fetch_corporate_actions", _fake_fetch)

    summary = sca.run_and_persist_corporate_actions("BBCA", token="tok", db_path=db_path,
                                                     fetch_date="2026-08-05")

    assert summary == {"ticker": "BBCA", "fetch_date": "2026-08-05", "count": 2}
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM corporate_action_events").fetchone()[0]
    conn.close()
    assert count == 2


def test_run_and_persist_corporate_actions_raises_on_fetch_failure(tmp_path, monkeypatch):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    import stockbit_corporate_actions as sca
    monkeypatch.setattr(sca, "fetch_corporate_actions", lambda *a, **k: None)

    try:
        sca.run_and_persist_corporate_actions("BBCA", token="tok", db_path=db_path,
                                              fetch_date="2026-08-05")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
