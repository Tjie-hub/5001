"""engine/unified_watchlist.py — merge reversal + premover + bear-dip watchlists.

Weighted union: every flagged ticker appears once. Each source is normalized to a
0-100 strength. When >=2 sources agree on a direction the row gets a +15 confluence
bonus (capped at 100); when sources disagree the row is flagged (conflict) and the
higher-strength source's direction is shown without a merge bonus.

Each source is read in its own try/except so a missing or empty table degrades
gracefully (the source is skipped, never failing the whole panel).
"""
import logging
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)

PREMOVER_FLOOR = 55.0       # min premover score to include (cuts noise)
CONFLUENCE_BONUS = 15.0     # added when >=2 sources agree on direction
BEAR_BASE = 50.0            # bear dip-scout has no native 0-100 score
BEAR_PROMOTED_BONUS = 15.0  # promoted entries rank above merely-active ones


def _conn(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def _latest_reversal_date(conn: sqlite3.Connection) -> Optional[str]:
    try:
        row = conn.execute("SELECT MAX(scan_date) FROM reversal_watchlist").fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def _read_reversal(conn, scan_date):
    if not scan_date:
        return []
    try:
        rows = conn.execute(
            "SELECT ticker, direction, conviction, close, smart_money, verdict "
            "FROM reversal_watchlist WHERE scan_date=?", (scan_date,)
        ).fetchall()
    except sqlite3.Error as e:
        logger.warning("unified_watchlist: reversal source skipped: %s", e)
        return []
    return [{
        "ticker": r["ticker"], "source": "REVERSAL",
        "direction": (r["direction"] or "long").lower(),
        "strength": float(r["conviction"] or 0.0),
        "close": r["close"],
        "raw": {"conviction": r["conviction"], "smart_money": r["smart_money"],
                "verdict": r["verdict"]},
    } for r in rows]


def _read_premover(conn):
    try:
        rows = conn.execute(
            "SELECT ticker, score, close_price, pattern_type FROM watchlist_premover "
            "WHERE detected_at = (SELECT MAX(detected_at) FROM watchlist_premover) "
            "AND score >= ?", (PREMOVER_FLOOR,)
        ).fetchall()
    except sqlite3.Error as e:
        logger.warning("unified_watchlist: premover source skipped: %s", e)
        return []
    return [{
        "ticker": r["ticker"], "source": "PREMOVER",
        "direction": "long",
        "strength": float(r["score"] or 0.0),
        "close": r["close_price"],
        "raw": {"score": r["score"], "pattern_type": r["pattern_type"]},
    } for r in rows]


def _read_bear(conn):
    try:
        rows = conn.execute(
            "SELECT ticker, status, bt_win_rate FROM regime_watchlist "
            "WHERE status IN ('active','promoted')"
        ).fetchall()
    except sqlite3.Error as e:
        logger.warning("unified_watchlist: bear source skipped: %s", e)
        return []
    out = []
    for r in rows:
        strength = BEAR_BASE + (BEAR_PROMOTED_BONUS if r["status"] == "promoted" else 0.0)
        out.append({
            "ticker": r["ticker"], "source": "BEAR_DIP",
            "direction": "long", "strength": strength, "close": None,
            "raw": {"status": r["status"], "bt_win_rate": r["bt_win_rate"]},
        })
    return out


def build_unified_watchlist(db_path: str, scan_date: Optional[str] = None) -> list[dict]:
    """Merge the three watchlist sources into one ranked, de-duplicated list.

    scan_date: reversal EOD date to read. When None, uses the latest scan_date
    present in reversal_watchlist.
    """
    conn = _conn(db_path)
    try:
        if scan_date is None:
            scan_date = _latest_reversal_date(conn)
        rows = _read_reversal(conn, scan_date) + _read_premover(conn) + _read_bear(conn)
    finally:
        conn.close()

    by_ticker: dict[str, list] = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], []).append(row)

    result = []
    for ticker, group in by_ticker.items():
        dominant = max(group, key=lambda x: x["strength"])
        direction = dominant["direction"]
        agree = [g for g in group if g["direction"] == direction]
        conflict = any(g["direction"] != direction for g in group)
        confluence = len(agree) >= 2
        strength = dominant["strength"]
        if confluence:
            strength = min(100.0, strength + CONFLUENCE_BONUS)

        close = None
        for g in group:
            if g["source"] == "REVERSAL" and g["close"] is not None:
                close = g["close"]
                break
        if close is None:
            for g in group:
                if g["close"] is not None:
                    close = g["close"]
                    break

        result.append({
            "ticker": ticker,
            "direction": direction,
            "strength": round(strength, 1),
            "sources": sorted({g["source"] for g in group}),
            "confluence": confluence,
            "conflict": conflict,
            "close": close,
            "detail": {g["source"].lower(): g["raw"] for g in group},
        })

    result.sort(key=lambda x: (-x["strength"], x["ticker"]))
    return result
