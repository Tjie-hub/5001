"""Tests for G8: send_suspension_resume_alerts() in scheduler.py."""
import sqlite3
import pytest
from datetime import date

from scheduler import send_suspension_resume_alerts


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE suspension_events (
            ticker TEXT NOT NULL,
            last_normal_date TEXT NOT NULL,
            resume_date TEXT NOT NULL,
            missing_td INTEGER NOT NULL,
            gap_pct REAL NOT NULL,
            classification TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            PRIMARY KEY (ticker, resume_date)
        )
    """)
    conn.commit()
    conn.close()
    return path


def _insert(db_path, ticker, resume_date, missing_td, gap_pct, classification="suspension"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO suspension_events VALUES (?,?,?,?,?,?,?)",
        (ticker, "2026-05-10", resume_date, missing_td, gap_pct, classification, "2026-05-25T09:00:00"),
    )
    conn.commit()
    conn.close()


# ── alert firing ─────────────────────────────────────────────────────────────

def test_sends_alert_for_suspension_resumed_today(db):
    _insert(db, "BRPT", "2026-05-25", missing_td=5, gap_pct=-0.22)
    calls = []
    send_suspension_resume_alerts(db_path=db, send_fn=calls.append, as_of="2026-05-25")
    assert len(calls) == 1


def test_returns_count_of_alerts_sent(db):
    _insert(db, "BRPT", "2026-05-25", missing_td=5, gap_pct=-0.22)
    _insert(db, "DEWA", "2026-05-25", missing_td=3, gap_pct=-0.10)
    n = send_suspension_resume_alerts(db_path=db, send_fn=lambda _: None, as_of="2026-05-25")
    assert n == 2


def test_no_alert_when_nothing_resumed_today(db):
    calls = []
    n = send_suspension_resume_alerts(db_path=db, send_fn=calls.append, as_of="2026-05-25")
    assert n == 0
    assert calls == []


def test_no_alert_for_yesterday_resumption(db):
    _insert(db, "BRPT", "2026-05-24", missing_td=5, gap_pct=-0.22)
    calls = []
    send_suspension_resume_alerts(db_path=db, send_fn=calls.append, as_of="2026-05-25")
    assert calls == []


def test_skips_data_gap_events(db):
    _insert(db, "BRPT", "2026-05-25", missing_td=5, gap_pct=-0.22, classification="data_gap")
    calls = []
    send_suspension_resume_alerts(db_path=db, send_fn=calls.append, as_of="2026-05-25")
    assert calls == []


# ── message content ───────────────────────────────────────────────────────────

def test_alert_contains_ticker(db):
    _insert(db, "BRPT", "2026-05-25", missing_td=5, gap_pct=-0.22)
    msgs = []
    send_suspension_resume_alerts(db_path=db, send_fn=msgs.append, as_of="2026-05-25")
    assert "BRPT" in msgs[0]


def test_alert_contains_missing_td(db):
    _insert(db, "BRPT", "2026-05-25", missing_td=5, gap_pct=-0.22)
    msgs = []
    send_suspension_resume_alerts(db_path=db, send_fn=msgs.append, as_of="2026-05-25")
    assert "5" in msgs[0]


def test_alert_contains_gap_pct(db):
    _insert(db, "BRPT", "2026-05-25", missing_td=5, gap_pct=-0.22)
    msgs = []
    send_suspension_resume_alerts(db_path=db, send_fn=msgs.append, as_of="2026-05-25")
    assert "-22" in msgs[0] or "22%" in msgs[0] or "22.0" in msgs[0]


def test_alert_contains_caution_warning(db):
    _insert(db, "BRPT", "2026-05-25", missing_td=5, gap_pct=-0.22)
    msgs = []
    send_suspension_resume_alerts(db_path=db, send_fn=msgs.append, as_of="2026-05-25")
    assert "CAUTION" in msgs[0] or "caution" in msgs[0].lower()
