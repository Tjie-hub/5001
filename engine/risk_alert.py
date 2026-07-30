# engine/risk_alert.py
"""Telegram alert routing by risk tier (C7).

CRITICAL : immediate alert
RED      : logged to market_risk_log; bundled hourly by scheduler
ORANGE   : logged to market_risk_log; EOD summary only
YELLOW   : logged only, no alert
GREEN    : silent (not logged)
"""
import json
import logging
import os
import sqlite3

from config import DB_PATH
from utils.telegram import send_telegram

_TIER_EMOJI = {
    'CRITICAL': '🚨', 'RED': '🔴', 'ORANGE': '🟠', 'YELLOW': '🟡', 'GREEN': '🟢',
}


def _ensure_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_risk_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT,
            date TEXT,
            time TEXT,
            tier TEXT,
            score REAL,
            sent INTEGER DEFAULT 0,
            components TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def route_risk_alert(
    conn: sqlite3.Connection,
    risk_result: dict,
    date_str: str,
    time_str: str,
):
    """Route risk alert to Telegram based on tier.

    CRITICAL → send immediately.
    RED/ORANGE/YELLOW → log to market_risk_log (sent=0).
    GREEN → do nothing.
    """
    tier = risk_result.get('tier', 'GREEN')
    score = risk_result.get('score', 0.0)
    components = risk_result.get('components', {})

    if tier == 'GREEN':
        return

    _ensure_table(conn)

    conn.execute(
        "INSERT INTO market_risk_log (scan_time, date, time, tier, score, sent, components) VALUES (?,?,?,?,?,?,?)",
        (f"{date_str} {time_str}", date_str, time_str, tier, score, 0, json.dumps(components)),
    )
    conn.commit()

    if tier == 'CRITICAL':
        emoji = _TIER_EMOJI.get(tier, '⚠️')
        msg = (
            f"{emoji} <b>Market Risk: {tier}</b> — Score {score:.1f}/100\n\n"
            f"VPIN: {components.get('vpin', '?'):.1f} | "
            f"AccDist: {components.get('accdist', '?'):.1f} | "
            f"Breadth: {components.get('breadth', '?'):.1f}\n"
            f"Technicals: {components.get('technicals', '?'):.1f} | "
            f"Foreign: {components.get('foreign_flow', '?'):.1f}\n\n"
            f"<i>Immediate action may be required.</i>"
        )
        send_telegram(msg)
        conn.execute(
            "UPDATE market_risk_log SET sent=1 WHERE date=? AND time=? AND tier='CRITICAL'",
            (date_str, time_str),
        )
        conn.commit()


def get_pending_risk_alerts(conn: sqlite3.Connection, date_str: str) -> list:
    """Return unsent market_risk_log rows for the given date."""
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT id, tier, score, time, components FROM market_risk_log "
        "WHERE date=? AND sent=0 ORDER BY id",
        (date_str,),
    ).fetchall()
    return [
        {'id': r[0], 'tier': r[1], 'score': r[2], 'time': r[3],
         'components': json.loads(r[4]) if r[4] else {}}
        for r in rows
    ]


def mark_alerts_sent(conn: sqlite3.Connection, ids: list):
    """Mark a list of market_risk_log IDs as sent."""
    if not ids:
        return
    placeholders = ','.join('?' * len(ids))
    conn.execute(f"UPDATE market_risk_log SET sent=1 WHERE id IN ({placeholders})", ids)


def build_risk_summary_message(alerts: list, date_str: str) -> str:
    """Build a Telegram summary message for a list of pending risk alerts."""
    if not alerts:
        return f"📊 <b>Market Risk Log — {date_str}</b>\n\nNo pending alerts."

    lines = [f"📊 <b>Market Risk Summary — {date_str}</b>\n"]
    for a in alerts:
        emoji = _TIER_EMOJI.get(a['tier'], '⚠️')
        lines.append(f"{emoji} <b>{a['tier']}</b> @ {a['time']} — Score {a['score']:.1f}")
    return "\n".join(lines)


def send_hourly_risk_bundle(date_str: str, time_str: str):
    """Send bundled RED alerts for the current hour. Called by scheduler."""
    conn = sqlite3.connect(DB_PATH)
    pending = [a for a in get_pending_risk_alerts(conn, date_str) if a['tier'] == 'RED']
    if pending:
        msg = build_risk_summary_message(pending, date_str)
        send_telegram(msg)
        mark_alerts_sent(conn, [a['id'] for a in pending])
        conn.commit()
        logging.info(f"[risk_alert] Sent {len(pending)} RED alerts (hourly bundle)")
    conn.close()


def send_eod_risk_summary(date_str: str):
    """Send ORANGE/YELLOW EOD summary. Called by end-of-day scheduler."""
    conn = sqlite3.connect(DB_PATH)
    pending = [
        a for a in get_pending_risk_alerts(conn, date_str)
        if a['tier'] in ('ORANGE', 'YELLOW')
    ]
    if pending:
        msg = build_risk_summary_message(pending, date_str)
        send_telegram(msg)
        mark_alerts_sent(conn, [a['id'] for a in pending])
        conn.commit()
        logging.info(f"[risk_alert] Sent {len(pending)} ORANGE/YELLOW alerts (EOD)")
    conn.close()
