"""Tests for C7 — Telegram alert routing by risk tier.

CRITICAL: immediate alert.
RED: bundled hourly (logged to market_risk_log, sent by hourly job).
ORANGE/YELLOW: end-of-day summary only.
GREEN: silent.
"""
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock

from engine.risk_alert import route_risk_alert, get_pending_risk_alerts, \
    mark_alerts_sent, build_risk_summary_message


def _make_db():
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    return tmp.name, conn


def _risk(tier, score=50.0):
    return {
        'tier': tier, 'score': score, 'label': tier,
        'components': {'vpin': 50, 'accdist': 50, 'breadth': 50,
                       'technicals': 50, 'foreign_flow': 50},
    }


# ── Immediate alert (CRITICAL) ────────────────────────────────────────────────

def test_critical_tier_sends_immediate_telegram():
    """CRITICAL risk → Telegram sent immediately, not queued."""
    db, conn = _make_db()
    sent = []
    with patch('engine.risk_alert.DB_PATH', db), \
         patch('engine.risk_alert.send_telegram', side_effect=lambda m: sent.append(m)):
        route_risk_alert(conn, _risk('CRITICAL', 90), '2026-06-05', '09:00')
    conn.close(); os.unlink(db)

    assert len(sent) == 1
    assert 'CRITICAL' in sent[0]


def test_red_tier_queues_but_does_not_send_immediately():
    """RED risk → logged to market_risk_log, no immediate Telegram."""
    db, conn = _make_db()
    sent = []
    with patch('engine.risk_alert.DB_PATH', db), \
         patch('engine.risk_alert.send_telegram', side_effect=lambda m: sent.append(m)):
        route_risk_alert(conn, _risk('RED', 78), '2026-06-05', '09:00')
    conn.close(); os.unlink(db)

    assert len(sent) == 0, "RED should not send immediately"


def test_orange_tier_does_not_send_immediately():
    """ORANGE risk → queued for EOD, no immediate alert."""
    db, conn = _make_db()
    sent = []
    with patch('engine.risk_alert.DB_PATH', db), \
         patch('engine.risk_alert.send_telegram', side_effect=lambda m: sent.append(m)):
        route_risk_alert(conn, _risk('ORANGE', 60), '2026-06-05', '09:00')
    conn.close(); os.unlink(db)

    assert len(sent) == 0


def test_green_tier_does_not_send_or_log():
    """GREEN risk → completely silent."""
    db, conn = _make_db()
    sent = []
    with patch('engine.risk_alert.DB_PATH', db), \
         patch('engine.risk_alert.send_telegram', side_effect=lambda m: sent.append(m)):
        route_risk_alert(conn, _risk('GREEN', 15), '2026-06-05', '09:00')
    # Check nothing was logged either
    try:
        rows = conn.execute("SELECT COUNT(*) FROM market_risk_log").fetchone()[0]
    except Exception:
        rows = 0
    conn.close(); os.unlink(db)

    assert len(sent) == 0
    assert rows == 0, "GREEN should not write to market_risk_log"


# ── market_risk_log persistence ───────────────────────────────────────────────

def test_red_alert_persisted_to_market_risk_log():
    """RED alert is logged to market_risk_log for hourly bundling."""
    db, conn = _make_db()
    with patch('engine.risk_alert.DB_PATH', db), \
         patch('engine.risk_alert.send_telegram', MagicMock()):
        route_risk_alert(conn, _risk('RED', 78), '2026-06-05', '10:30')

    rows = conn.execute("SELECT tier, score, sent FROM market_risk_log").fetchall()
    conn.close(); os.unlink(db)

    assert len(rows) == 1
    assert rows[0][0] == 'RED'
    assert rows[0][1] == 78.0
    assert rows[0][2] == 0  # not yet sent


def test_orange_alert_persisted_to_market_risk_log():
    db, conn = _make_db()
    with patch('engine.risk_alert.DB_PATH', db), \
         patch('engine.risk_alert.send_telegram', MagicMock()):
        route_risk_alert(conn, _risk('ORANGE', 62), '2026-06-05', '11:00')

    rows = conn.execute("SELECT tier FROM market_risk_log").fetchall()
    conn.close(); os.unlink(db)

    assert len(rows) == 1
    assert rows[0][0] == 'ORANGE'


# ── get_pending_risk_alerts ───────────────────────────────────────────────────

def test_get_pending_returns_unsent_alerts():
    db, conn = _make_db()
    conn.execute("""CREATE TABLE market_risk_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_time TEXT, date TEXT, time TEXT,
        tier TEXT, score REAL, sent INTEGER DEFAULT 0,
        components TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.executemany(
        "INSERT INTO market_risk_log (scan_time, date, time, tier, score, sent) VALUES (?,?,?,?,?,?)",
        [
            ('2026-06-05 09:00', '2026-06-05', '09:00', 'RED', 78, 0),
            ('2026-06-05 10:00', '2026-06-05', '10:00', 'RED', 80, 1),  # already sent
            ('2026-06-05 11:00', '2026-06-05', '11:00', 'ORANGE', 62, 0),
        ]
    )
    conn.commit()

    pending = get_pending_risk_alerts(conn, '2026-06-05')
    conn.close(); os.unlink(db)

    assert len(pending) == 2  # only unsent
    tiers = {r['tier'] for r in pending}
    assert 'RED' in tiers
    assert 'ORANGE' in tiers


def test_mark_alerts_sent_updates_flag():
    db, conn = _make_db()
    conn.execute("""CREATE TABLE market_risk_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_time TEXT, date TEXT, time TEXT,
        tier TEXT, score REAL, sent INTEGER DEFAULT 0,
        components TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("INSERT INTO market_risk_log (scan_time, date, time, tier, score) VALUES ('2026-06-05 09:00', '2026-06-05', '09:00', 'RED', 78)")
    conn.commit()

    ids = [conn.execute("SELECT id FROM market_risk_log").fetchone()[0]]
    mark_alerts_sent(conn, ids)
    conn.commit()

    row = conn.execute("SELECT sent FROM market_risk_log WHERE id=?", (ids[0],)).fetchone()
    conn.close(); os.unlink(db)
    assert row[0] == 1


# ── build_risk_summary_message ────────────────────────────────────────────────

def test_summary_message_contains_tiers():
    alerts = [
        {'tier': 'RED', 'score': 78.0, 'time': '09:00'},
        {'tier': 'ORANGE', 'score': 62.0, 'time': '11:00'},
    ]
    msg = build_risk_summary_message(alerts, '2026-06-05')
    assert 'RED' in msg
    assert 'ORANGE' in msg
    assert '2026-06-05' in msg


def test_summary_message_is_non_empty_string():
    msg = build_risk_summary_message([], '2026-06-05')
    assert isinstance(msg, str)
    assert len(msg) > 0
