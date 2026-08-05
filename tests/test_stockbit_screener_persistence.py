"""Persistence layer for screener/stockbit_screener.py (guru templates).

Added to schedule the existing on-demand collector (fetch_template/run_screener,
both untouched here) into the daily scheduler — see scheduler/jobs.py's
run_stockbit_screener_fetch(). Table + save function are new; the fetch logic
they wrap is not.
"""
import json
import sqlite3

from screener.stockbit_screener import (
    init_db,
    save_screener_results,
    run_and_persist_screener,
)


def _sample_results():
    return [
        {"symbol": "BBCA", "name": "Bank Central Asia", "volume": 1000, "volume_display": "1,000"},
        {"symbol": "TLKM", "name": "Telkom Indonesia", "volume": 2000, "volume_display": "2,000"},
    ]


def test_init_db_creates_table(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "stockbit_screener_results" in tables


def test_init_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    init_db(db_path)  # must not raise on second call


def test_save_screener_results_inserts_one_row_per_ticker(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    n = save_screener_results(conn, template_id=63, template_name="high_volume_breakout",
                              fetch_date="2026-08-04", results=_sample_results())
    conn.commit()
    rows = conn.execute(
        "SELECT template_id, ticker, fetch_date, name, metrics_json FROM stockbit_screener_results "
        "ORDER BY ticker"
    ).fetchall()
    conn.close()
    assert n == 2
    assert len(rows) == 2
    assert rows[0][:4] == (63, "BBCA", "2026-08-04", "Bank Central Asia")
    metrics = json.loads(rows[0][4])
    assert metrics["volume"] == 1000


def test_save_screener_results_rerun_same_date_does_not_duplicate(tmp_path):
    """Idempotency requirement: rerunning the same trading date must not create
    duplicate rows — PRIMARY KEY(template_id, ticker, fetch_date) + INSERT OR
    REPLACE, matching the existing stockbit_keystats/broker_flow pattern."""
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_screener_results(conn, 63, "high_volume_breakout", "2026-08-04", _sample_results())
    conn.commit()

    # Rerun same date with updated metrics (simulates a same-day scheduler retry)
    updated = _sample_results()
    updated[0]["volume"] = 9999
    save_screener_results(conn, 63, "high_volume_breakout", "2026-08-04", updated)
    conn.commit()

    rows = conn.execute(
        "SELECT ticker, metrics_json FROM stockbit_screener_results ORDER BY ticker"
    ).fetchall()
    conn.close()
    assert len(rows) == 2  # still 2, not 4
    assert json.loads(rows[0][1])["volume"] == 9999  # latest value wins


def test_save_screener_results_different_dates_both_kept(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    save_screener_results(conn, 63, "high_volume_breakout", "2026-08-03", _sample_results())
    save_screener_results(conn, 63, "high_volume_breakout", "2026-08-04", _sample_results())
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM stockbit_screener_results").fetchone()[0]
    conn.close()
    assert count == 4  # 2 tickers x 2 distinct dates, no cross-date collision


def test_run_and_persist_screener_persists_all_guru_templates(tmp_path, monkeypatch):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)

    import screener.stockbit_screener as sb
    monkeypatch.setattr(sb, "fetch_template", lambda template_id, template_type="TEMPLATE_TYPE_GURU", token=None: _sample_results())
    monkeypatch.setattr(sb, "_fetch_keystats", lambda tickers, db_path: {})

    summary = run_and_persist_screener("high_volume_breakout", db_path=db_path, fetch_date="2026-08-04")

    assert summary["template_name"] == "high_volume_breakout"
    assert summary["count"] == 2

    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM stockbit_screener_results").fetchone()[0]
    conn.close()
    assert count == 2


def test_run_and_persist_screener_unknown_template_raises(tmp_path):
    db_path = str(tmp_path / "wf.db")
    init_db(db_path)
    try:
        run_and_persist_screener("does_not_exist", db_path=db_path)
        assert False, "expected ValueError for unknown template name"
    except ValueError:
        pass
