"""Tests for check_flow_coverage() — daily stockbit_flow coverage monitor.

The monitor flags a flow-fetch outage (the 2026-04-22/23 gap) while the data is
still retrievable, since the Stockbit tradebook API cannot serve a historical
date once the session has passed (backfill is only possible same-day).
"""
import sqlite3

from scheduler.jobs import check_flow_coverage


def _mk_db(tmp_path):
    db = str(tmp_path / "cov.db")
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, "
        "PRIMARY KEY(ticker, trade_date))"
    )
    conn.commit()
    conn.close()
    return db


def _seed(db, trade_date, n):
    conn = sqlite3.connect(db)
    conn.executemany(
        "INSERT OR REPLACE INTO stockbit_flow(ticker, trade_date) VALUES (?, ?)",
        [(f"T{i:04d}", trade_date) for i in range(n)],
    )
    conn.commit()
    conn.close()


def test_healthy_full_coverage(tmp_path):
    db = _mk_db(tmp_path)
    for d in ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19"]:
        _seed(db, d, 870)
    _seed(db, "2026-06-22", 873)
    cov = check_flow_coverage(db, "2026-06-22")
    assert cov["healthy"] is True
    assert cov["severity"] == "ok"
    assert cov["count"] == 873
    assert cov["baseline"] == 870


def test_total_outage_is_critical(tmp_path):
    """The actual 2026-04-22 case: zero tickers for the date."""
    db = _mk_db(tmp_path)
    _seed(db, "2026-04-20", 79)
    _seed(db, "2026-04-21", 79)
    # 2026-04-22 has NO rows at all.
    cov = check_flow_coverage(db, "2026-04-22")
    assert cov["healthy"] is False
    assert cov["severity"] == "critical"
    assert cov["count"] == 0


def test_severe_partial_is_warning(tmp_path):
    db = _mk_db(tmp_path)
    for d in ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-19"]:
        _seed(db, d, 870)
    _seed(db, "2026-06-22", 120)  # ~14% of baseline
    cov = check_flow_coverage(db, "2026-06-22")
    assert cov["healthy"] is False
    assert cov["severity"] == "warning"


def test_watchlist_era_not_flagged_against_itself(tmp_path):
    """Cold-start ramp: a steady 79-ticker watchlist day is normal vs its own
    baseline and must not produce a false alarm."""
    db = _mk_db(tmp_path)
    for d in ["2026-04-14", "2026-04-15", "2026-04-16"]:
        _seed(db, d, 79)
    _seed(db, "2026-04-20", 79)
    cov = check_flow_coverage(db, "2026-04-20")
    assert cov["healthy"] is True
    assert cov["severity"] == "ok"


def test_cold_start_below_floor_is_warning(tmp_path):
    """No prior baseline and a tiny count → flag it (likely a broken first run)."""
    db = _mk_db(tmp_path)
    _seed(db, "2026-04-10", 5)
    cov = check_flow_coverage(db, "2026-04-10")
    assert cov["healthy"] is False
    assert cov["severity"] == "warning"
    assert cov["baseline"] is None
