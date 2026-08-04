"""Persistence tests for stockbit_ownership.py's new ownership_composition
table — separate from every existing table (not overloaded)."""
import json
import sqlite3

from stockbit_ownership import (
    init_db,
    save_ownership_composition,
    run_and_persist_ownership,
)


def _sample_rows(ticker="BBCA", report_date="2026-07-31"):
    return [
        {"ticker": ticker, "report_date": report_date, "holder_label": "DWIMURIA INVESTAMA ANDALAN",
         "rank": 1, "shares": 67729950000, "percentage": 54.94213954891927,
         "total_shares": 123275050000, "raw": {"colors": {"light": "#0BA16B"}}},
        {"ticker": ticker, "report_date": report_date, "holder_label": "Mutual Funds",
         "rank": 2, "shares": 19723748161, "percentage": 15.999789220122,
         "total_shares": 123275050000, "raw": {"colors": {"light": "#1FD795"}}},
    ]


def test_init_db_creates_ownership_composition_table(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "ownership_composition" in tables


def test_init_db_does_not_touch_other_collector_tables(tmp_path):
    """Guards 'do not overload any existing tables' at the schema level."""
    db_path = str(tmp_path / "wf.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE broker_period_summary (ticker TEXT)")
    conn.execute("CREATE TABLE corporate_action_events (ticker TEXT)")
    conn.execute("INSERT INTO broker_period_summary VALUES ('BBCA')")
    conn.execute("INSERT INTO corporate_action_events VALUES ('BBCA')")
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    bps_cols = {r[1] for r in conn.execute("PRAGMA table_info(broker_period_summary)")}
    cae_cols = {r[1] for r in conn.execute("PRAGMA table_info(corporate_action_events)")}
    bps_rows = conn.execute("SELECT * FROM broker_period_summary").fetchall()
    cae_rows = conn.execute("SELECT * FROM corporate_action_events").fetchall()
    conn.close()
    assert bps_cols == {"ticker"}
    assert cae_cols == {"ticker"}
    assert len(bps_rows) == 1
    assert len(cae_rows) == 1


def test_init_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    init_db(db_path)  # must not raise


def test_save_inserts_one_row_per_holder(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    n = save_ownership_composition(conn, "2026-08-05", _sample_rows())
    conn.commit()
    rows = conn.execute(
        "SELECT ticker, report_date, holder_label, rank, shares, percentage, total_shares, raw_json, fetch_date "
        "FROM ownership_composition ORDER BY rank"
    ).fetchall()
    conn.close()
    assert n == 2
    assert len(rows) == 2
    assert rows[0][:7] == ("BBCA", "2026-07-31", "DWIMURIA INVESTAMA ANDALAN", 1,
                           67729950000, 54.94213954891927, 123275050000)
    assert json.loads(rows[0][7])["colors"]["light"] == "#0BA16B"
    assert rows[0][8] == "2026-08-05"


def test_save_rerun_same_ticker_and_report_date_does_not_duplicate(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_ownership_composition(conn, "2026-08-05", _sample_rows())
    conn.commit()

    updated = _sample_rows()
    updated[0]["percentage"] = 99.0
    save_ownership_composition(conn, "2026-08-06", updated)  # different fetch_date, same report_date
    conn.commit()

    rows = conn.execute(
        "SELECT holder_label, percentage, fetch_date FROM ownership_composition "
        "WHERE holder_label='DWIMURIA INVESTAMA ANDALAN'"
    ).fetchall()
    conn.close()
    assert len(rows) == 1  # still 1, not 2
    assert rows[0][1] == 99.0  # latest value wins
    assert rows[0][2] == "2026-08-06"


def test_save_new_report_date_adds_new_rows_not_overwrite(tmp_path):
    """Unlike corporate_action_events (stable event log keyed without a
    date), ownership_composition IS keyed by report_date — a new monthly
    snapshot must be preserved alongside the old one, not replace it."""
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_ownership_composition(conn, "2026-08-05", _sample_rows(report_date="2026-06-30"))
    save_ownership_composition(conn, "2026-09-05", _sample_rows(report_date="2026-07-31"))
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM ownership_composition").fetchone()[0]
    report_dates = {r[0] for r in conn.execute("SELECT DISTINCT report_date FROM ownership_composition")}
    conn.close()
    assert count == 4  # 2 holders x 2 distinct report_dates
    assert report_dates == {"2026-06-30", "2026-07-31"}


def test_save_different_tickers_both_kept(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_ownership_composition(conn, "2026-08-05", _sample_rows(ticker="BBCA"))
    save_ownership_composition(conn, "2026-08-05", _sample_rows(ticker="BRPT"))
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM ownership_composition").fetchone()[0]
    conn.close()
    assert count == 4


def test_run_and_persist_ownership_end_to_end(tmp_path, monkeypatch):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)

    import stockbit_ownership as so

    def _fake_fetch(token, ticker):
        assert ticker == "BBCA"
        return _sample_rows()

    monkeypatch.setattr(so, "fetch_ownership_composition", _fake_fetch)

    summary = so.run_and_persist_ownership("BBCA", token="tok", db_path=db_path,
                                           fetch_date="2026-08-05")

    assert summary == {"ticker": "BBCA", "fetch_date": "2026-08-05",
                       "report_date": "2026-07-31", "count": 2}
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM ownership_composition").fetchone()[0]
    conn.close()
    assert count == 2


def test_run_and_persist_ownership_raises_on_fetch_failure(tmp_path, monkeypatch):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    import stockbit_ownership as so
    monkeypatch.setattr(so, "fetch_ownership_composition", lambda *a, **k: None)

    try:
        so.run_and_persist_ownership("BBCA", token="tok", db_path=db_path,
                                     fetch_date="2026-08-05")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
