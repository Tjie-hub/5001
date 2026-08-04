"""Persistence tests for stockbit_broker_period.py's new broker_period_summary
table — separate from broker_flow (not overloaded, not modified)."""
import json
import sqlite3

from stockbit_broker_period import (
    init_db,
    save_broker_period_summary,
    run_and_persist_broker_period,
)


def _sample_rows():
    return [
        {"broker_code": "DX", "investor_type": "Pemerintah", "buy_volume": 100, "buy_value": 1000,
         "sell_volume": 0, "sell_value": 0, "net_value": 1000, "rank": 1, "raw": {"buy": {"x": 1}, "sell": None}},
        {"broker_code": "BK", "investor_type": "Asing", "buy_volume": 0, "buy_value": 0,
         "sell_volume": 50, "sell_value": 500, "net_value": -500, "rank": 2, "raw": {"buy": None, "sell": {"y": 2}}},
    ]


def test_init_db_creates_broker_period_summary_table(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "broker_period_summary" in tables


def test_init_db_does_not_touch_broker_flow_table(tmp_path):
    """Guards the 'do not overload broker_flow' constraint at the schema level."""
    db_path = str(tmp_path / "wf.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, side TEXT)")
    conn.execute("INSERT INTO broker_flow VALUES ('BBCA','2026-08-04','DX','BUY')")
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(broker_flow)")}
    row = conn.execute("SELECT * FROM broker_flow").fetchall()
    conn.close()
    assert cols == {"ticker", "trade_date", "broker_code", "side"}  # unchanged
    assert len(row) == 1  # untouched


def test_init_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    init_db(db_path)  # must not raise


def test_save_inserts_one_row_per_broker(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    n = save_broker_period_summary(conn, "BBCA", "LAST_7_DAYS", "2026-08-04",
                                   "2026-07-29", "2026-08-04", _sample_rows())
    conn.commit()
    rows = conn.execute(
        "SELECT ticker, period, fetch_date, broker_code, buy_value, sell_value, net_value, rank, raw_json "
        "FROM broker_period_summary ORDER BY broker_code"
    ).fetchall()
    conn.close()
    assert n == 2
    assert len(rows) == 2
    assert rows[0][:8] == ("BBCA", "LAST_7_DAYS", "2026-08-04", "BK", 0, 500, -500, 2)
    assert json.loads(rows[0][8])["sell"] == {"y": 2}


def test_save_rerun_same_ticker_period_date_does_not_duplicate(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_broker_period_summary(conn, "BBCA", "LAST_7_DAYS", "2026-08-04",
                               "2026-07-29", "2026-08-04", _sample_rows())
    conn.commit()

    updated = _sample_rows()
    updated[0]["net_value"] = 999999
    save_broker_period_summary(conn, "BBCA", "LAST_7_DAYS", "2026-08-04",
                               "2026-07-29", "2026-08-04", updated)
    conn.commit()

    rows = conn.execute(
        "SELECT broker_code, net_value FROM broker_period_summary ORDER BY broker_code"
    ).fetchall()
    conn.close()
    assert len(rows) == 2  # still 2, not 4
    assert dict(rows)["DX"] == 999999  # latest value wins


def test_save_different_periods_for_same_ticker_and_date_both_kept(tmp_path):
    """(ticker, period, fetch_date, broker_code) is the key — LAST_7_DAYS and
    LAST_1_MONTH snapshots taken the same day must not collide."""
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_broker_period_summary(conn, "BBCA", "LAST_7_DAYS", "2026-08-04",
                               "2026-07-29", "2026-08-04", _sample_rows())
    save_broker_period_summary(conn, "BBCA", "LAST_1_MONTH", "2026-08-04",
                               "2026-07-04", "2026-08-04", _sample_rows())
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM broker_period_summary").fetchone()[0]
    conn.close()
    assert count == 4  # 2 brokers x 2 periods, no collision


def test_run_and_persist_broker_period_end_to_end(tmp_path, monkeypatch):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)

    import stockbit_broker_period as sbp

    def _fake_fetch(token, ticker, period_from, period_to):
        assert ticker == "BBCA"
        return {"ticker": ticker, "period_from": period_from, "period_to": period_to,
                "rows": _sample_rows()}

    monkeypatch.setattr(sbp, "fetch_broker_period_summary", _fake_fetch)

    summary = sbp.run_and_persist_broker_period(
        "BBCA", "LAST_7_DAYS", token="tok", db_path=db_path, fetch_date="2026-08-04"
    )

    assert summary == {
        "ticker": "BBCA", "period": "LAST_7_DAYS", "fetch_date": "2026-08-04",
        "period_from": "2026-07-29", "period_to": "2026-08-04", "count": 2,
    }
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM broker_period_summary").fetchone()[0]
    conn.close()
    assert count == 2


def test_run_and_persist_broker_period_raises_on_fetch_failure(tmp_path, monkeypatch):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    import stockbit_broker_period as sbp
    monkeypatch.setattr(sbp, "fetch_broker_period_summary", lambda *a, **k: None)

    try:
        sbp.run_and_persist_broker_period("BBCA", "LAST_7_DAYS", token="tok",
                                          db_path=db_path, fetch_date="2026-08-04")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
