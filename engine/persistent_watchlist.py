"""Persistent multi-day accumulated approved-ticker watchlist.

Distinct from engine.trade_plan's `watchlist_snapshot` (a per-day snapshot,
diffed only against the single most recent prior day — no cross-day streak
tracking, and a ticker that drops out simply has no row for that day) and
from engine.watchlist_report's `candidate_watchlist_snapshot` (tracks the
PRE-firm candidate universe, not firm-approved tickers). This module tracks,
per ticker, how long it has continuously held a spot on the firm-APPROVED
EOD watchlist, across an unbounded number of trading days, and never
deletes history — a ticker that drops out is marked REMOVED, not erased.

Pure DB/data + string-formatting functions only (no LLM, no network) —
callers supply today's already-decided approved-ticker set (the same
`ranked` list scheduler.jobs.run_eod_trade_plan already computes) and this
module only persists/updates/formats it. Reporting-only: never feeds back
into ranking, firm decisions, or trading logic.
"""
from __future__ import annotations

import html
import sqlite3
from typing import Any, Iterable, Optional

PERSISTENT_WATCHLIST_DDL = """
CREATE TABLE IF NOT EXISTS persistent_watchlist (
    ticker              TEXT NOT NULL PRIMARY KEY,
    first_added_date    TEXT NOT NULL,
    last_seen_date      TEXT NOT NULL,
    status              TEXT NOT NULL,
    consecutive_days    INTEGER NOT NULL,
    total_appearances   INTEGER NOT NULL
)
"""


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(PERSISTENT_WATCHLIST_DDL)
    conn.commit()


def update_watchlist(conn: sqlite3.Connection, date_str: str,
                     today_tickers: Iterable[str]) -> dict[str, Any]:
    """Update the persistent watchlist for `date_str` against `today_tickers`
    (the firm-approved ticker set for that day). Idempotent — calling twice
    with the same (date_str, today_tickers) leaves the DB unchanged on the
    second call (guarded by last_seen_date == date_str) and never inserts a
    duplicate row (ticker is the PRIMARY KEY).

    Per ticker present today:
      - not previously seen  -> INSERT, status=ACTIVE, consecutive_days=1
      - ACTIVE, not yet processed today -> consecutive_days += 1
      - REMOVED               -> reactivate: status=ACTIVE, consecutive_days
        RESET to 1, first_added_date PRESERVED (never rewritten)
    Per ticker absent today that is still ACTIVE: mark REMOVED. The row is
    never deleted -- first_added_date/last_seen_date/consecutive_days as of
    the removal are frozen in place, preserving history.
    """
    ensure_table(conn)
    today_tickers = set(today_tickers)

    rows = conn.execute(
        "SELECT ticker, first_added_date, last_seen_date, status, "
        "consecutive_days, total_appearances FROM persistent_watchlist"
    ).fetchall()
    existing = {
        r[0]: {"first_added_date": r[1], "last_seen_date": r[2], "status": r[3],
               "consecutive_days": r[4], "total_appearances": r[5]}
        for r in rows
    }

    added: list[str] = []
    reactivated: list[str] = []

    for ticker in today_tickers:
        row = existing.get(ticker)
        if row is None:
            conn.execute(
                "INSERT INTO persistent_watchlist (ticker, first_added_date, "
                "last_seen_date, status, consecutive_days, total_appearances) "
                "VALUES (?,?,?,?,1,1)",
                (ticker, date_str, date_str, "ACTIVE"),
            )
            added.append(ticker)
        elif row["last_seen_date"] == date_str:
            continue  # idempotent same-day rerun: already processed, no-op
        elif row["status"] == "ACTIVE":
            conn.execute(
                "UPDATE persistent_watchlist SET last_seen_date=?, "
                "consecutive_days=?, total_appearances=? WHERE ticker=?",
                (date_str, row["consecutive_days"] + 1,
                 row["total_appearances"] + 1, ticker),
            )
        else:  # REMOVED -> reactivate
            conn.execute(
                "UPDATE persistent_watchlist SET last_seen_date=?, "
                "status='ACTIVE', consecutive_days=1, total_appearances=? "
                "WHERE ticker=?",
                (date_str, row["total_appearances"] + 1, ticker),
            )
            reactivated.append(ticker)

    removed: list[str] = []
    for ticker, row in existing.items():
        if ticker not in today_tickers and row["status"] == "ACTIVE":
            conn.execute(
                "UPDATE persistent_watchlist SET status='REMOVED' WHERE ticker=?",
                (ticker,),
            )
            removed.append(ticker)

    conn.commit()

    active_rows = conn.execute(
        "SELECT ticker, consecutive_days FROM persistent_watchlist "
        "WHERE status='ACTIVE' ORDER BY consecutive_days DESC, ticker ASC"
    ).fetchall()
    added_or_reactivated = set(added) | set(reactivated)
    existing_list = [
        {"ticker": t, "consecutive_days": d} for t, d in active_rows
        if t not in added_or_reactivated
    ]
    longest_held = (
        {"ticker": active_rows[0][0], "consecutive_days": active_rows[0][1]}
        if active_rows else None
    )

    return {
        "added": sorted(added), "reactivated": sorted(reactivated),
        "removed": sorted(removed), "existing": existing_list,
        "active_count": len(active_rows), "longest_held": longest_held,
    }


def build_message(date_str: str, result: dict[str, Any]) -> str:
    """Telegram HTML section for the persistent multi-day watchlist, meant to
    be appended after engine.trade_plan.build_message()'s existing output
    (the Daily Summary / Trade Plan section is untouched — this is additive
    text, never a replacement). No raw <,>,& in dynamic text (tickers are
    escaped), so HTML parse_mode stays safe.

    `result` is update_watchlist()'s return dict. A sub-section (New/
    Existing/Reactivated/Removed) is omitted entirely when empty, matching
    the convention already used by engine.watchlist_report.build_message and
    engine.trade_plan._build_diff_section; the header, Current Active line,
    and Statistics block always show.
    """
    added = result.get("added") or []
    reactivated = result.get("reactivated") or []
    removed = result.get("removed") or []
    existing = result.get("existing") or []
    active_count = result.get("active_count") or 0
    longest_held = result.get("longest_held")

    L = ["<b>📋 ACTIVE WATCHLIST</b>", "", f"Current Active: {active_count}"]

    if added:
        L += ["", "<b>🆕 New Today</b>"]
        L += [html.escape(t) for t in added]

    if existing:
        L += ["", "<b>📌 Existing</b>", "<i>(sorted by consecutive_days descending)</i>", ""]
        L += [f"{html.escape(e['ticker'])} ({e['consecutive_days']}d)" for e in existing]

    if reactivated:
        L += ["", "<b>♻️ Reactivated</b>"]
        L += [html.escape(t) for t in reactivated]

    if removed:
        L += ["", "<b>👋 Removed Today</b>"]
        L += [html.escape(t) for t in removed]

    longest_txt = (
        f"{html.escape(longest_held['ticker'])} ({longest_held['consecutive_days']}d)"
        if longest_held else "—"
    )
    L += ["", "<b>📊 Statistics</b>", "", f"Current Active: {active_count}",
         f"Added Today: {len(added)}", f"Reactivated: {len(reactivated)}",
         f"Removed Today: {len(removed)}", f"Longest Held: {longest_txt}"]

    return "\n".join(L)
