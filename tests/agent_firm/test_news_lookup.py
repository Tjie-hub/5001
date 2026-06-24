import json
import sqlite3
from datetime import date, timedelta

import pytest

from engine.agent_firm.tools.news_lookup import lookup


@pytest.fixture
def news_db(tmp_path):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE news_mentions (
            ticker TEXT, date TEXT, count INTEGER,
            headlines_json TEXT, updated_at TEXT
        )
    """)
    # Dates are anchored to "today" so the relative ``date('now', '-N days')``
    # window in lookup() always covers them (avoids a time-bomb as real time passes).
    d0 = date.today().isoformat()
    d1 = (date.today() - timedelta(days=1)).isoformat()
    conn.executemany(
        "INSERT INTO news_mentions VALUES (?,?,?,?,?)",
        [
            ("BBRI", d0, 3,
             json.dumps(["Headline A", "Headline B", "Headline C"]),
             f"{d0} 20:00"),
            ("BBRI", d1, 2,
             json.dumps(["Headline D", "Headline E"]),
             f"{d1} 20:00"),
            ("BBCA", d0, 1,
             json.dumps(["Headline F"]),
             f"{d0} 20:00"),
        ]
    )
    conn.commit()
    conn.close()
    return str(db)


def test_lookup_returns_rows_for_ticker(news_db):
    rows = lookup(news_db, "BBRI", days=30)
    assert len(rows) == 2
    assert all(r["ticker"] == "BBRI" for r in rows)


def test_lookup_parses_headlines_json(news_db):
    rows = lookup(news_db, "BBRI", days=30)
    assert isinstance(rows[0]["headlines"], list)
    assert "Headline A" in rows[0]["headlines"]


def test_lookup_returns_empty_for_unknown_ticker(news_db):
    rows = lookup(news_db, "ZZXX", days=30)
    assert rows == []


def test_lookup_caps_at_20_rows(tmp_path):
    db = tmp_path / "big.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE news_mentions (ticker TEXT, date TEXT, count INTEGER, headlines_json TEXT, updated_at TEXT)")
    conn.executemany(
        "INSERT INTO news_mentions VALUES (?,?,?,?,?)",
        [("BBRI", f"2026-01-{i:02d}", 1, json.dumps([f"h{i}"]), "") for i in range(1, 26)]
    )
    conn.commit()
    conn.close()
    rows = lookup(str(db), "BBRI", days=365)
    assert len(rows) <= 20
