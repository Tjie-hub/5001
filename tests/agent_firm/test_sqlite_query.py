import sqlite3

import pytest

from engine.agent_firm.tools.sqlite_query import query


def _seed_ohlcv(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume REAL
        )
    """)
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) "
        "VALUES (?,?,?,?,?,?,?)",
        [
            ("BBRI", "2026-05-19", 5000, 5100, 4950, 5050, 1000000),
            ("BBRI", "2026-05-16", 4900, 5000, 4880, 5000, 950000),
            ("BMRI", "2026-05-19", 7000, 7100, 6950, 7080, 800000),
        ],
    )
    conn.commit()
    conn.close()


def test_query_returns_rows_as_dicts(tmp_path):
    db = tmp_path / "t.db"
    _seed_ohlcv(db)
    rows = query(db, "SELECT ticker, close FROM ohlcv WHERE ticker = ?", ("BBRI",))
    assert len(rows) == 2
    assert rows[0] == {"ticker": "BBRI", "close": 5050}


def test_query_rejects_non_select(tmp_path):
    db = tmp_path / "t.db"
    _seed_ohlcv(db)
    with pytest.raises(ValueError, match="SELECT"):
        query(db, "DELETE FROM ohlcv", ())


def test_query_rejects_select_with_destructive_chain(tmp_path):
    db = tmp_path / "t.db"
    _seed_ohlcv(db)
    with pytest.raises(ValueError):
        query(db, "  drop table ohlcv  ", ())


def test_query_with_no_params(tmp_path):
    db = tmp_path / "t.db"
    _seed_ohlcv(db)
    rows = query(db, "SELECT COUNT(*) AS c FROM ohlcv")
    assert rows[0]["c"] == 3
