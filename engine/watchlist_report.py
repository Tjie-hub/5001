"""Pre-firm candidate watchlist snapshot + standalone Telegram "Watchlist
Update" report.

Distinct from engine.trade_plan's watchlist_snapshot table (which tracks the
FIRM-APPROVED post-decision shortlist embedded in the EOD/Premarket
messages). This module snapshots the raw unified long-candidate universe
*before* firm review — the set the engine is actively watching, not what it
has approved — so a name that never reaches the firm's shortlist (or gets
vetoed) is still visible day over day.

Pure DB/data + string-formatting functions only (no LLM, no network, no
candidate-generation logic) — callers supply an already-computed candidate
list (engine.trade_plan.gather_long_candidates output) and this module only
persists/diffs/formats it. Reporting-only: never feeds back into ranking,
firm decisions, or trading logic.
"""
from __future__ import annotations

import html
import sqlite3
from typing import Any, Optional

WATCHLIST_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS candidate_watchlist_snapshot (
    date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    status TEXT NOT NULL,
    score REAL,
    rank INTEGER NOT NULL,
    sector TEXT,
    industry TEXT,
    regime TEXT,
    entry_type TEXT,
    risk_score REAL,
    PRIMARY KEY (date, ticker)
)
"""

SCORE_MOVE_THRESHOLD = 0.01  # ignore float-noise-level score deltas
_MAX_ROWS = 20  # cap per section so a large watchlist doesn't blow the message


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(WATCHLIST_TABLE_DDL)
    conn.commit()


def record_snapshot(conn: sqlite3.Connection, date_str: str,
                    candidates: list[dict[str, Any]],
                    regime: Optional[str] = None) -> None:
    """Persist today's pre-firm candidate watchlist. `candidates` is
    engine.trade_plan.gather_long_candidates() output (or any dicts with at
    least a "ticker" key). Ranked by engine.trade_plan.candidate_score,
    descending. INSERT OR REPLACE keyed by (date, ticker) — idempotent
    same-day rerun; never touches other days' rows (append-only across
    days)."""
    from engine.trade_plan import candidate_score

    ensure_table(conn)
    ranked = sorted(candidates, key=candidate_score, reverse=True)
    for i, c in enumerate(ranked, 1):
        conn.execute(
            "INSERT OR REPLACE INTO candidate_watchlist_snapshot "
            "(date, ticker, status, score, rank, sector, industry, regime, "
            "entry_type, risk_score) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (date_str, c["ticker"], "ACTIVE", candidate_score(c), i,
             c.get("sector"), c.get("industry"), regime,
             c.get("entry_type"), c.get("risk_score")),
        )
    conn.commit()


def diff_snapshot(conn: sqlite3.Connection, date_str: str,
                  candidates: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Diff today's watchlist against the most recent prior day's persisted
    snapshot (skipping any gap — holiday, outage, first run after a pause).
    Returns None when there's no prior snapshot at all.

    `candidates` is today's in-memory candidate list (the same one passed to
    record_snapshot) — mirrors engine.trade_plan.diff_watchlist's contract of
    taking today's data as a parameter rather than reading it back from the
    DB, so the caller may diff BEFORE persisting today's row without a
    read-your-own-write ordering dependency.

    Set-based (order-independent membership), never derived from rank/position.
    """
    from engine.trade_plan import candidate_score

    ensure_table(conn)
    row = conn.execute(
        "SELECT MAX(date) FROM candidate_watchlist_snapshot WHERE date<?",
        (date_str,),
    ).fetchone()
    prior_date = row[0] if row else None
    if not prior_date:
        return None

    prior = dict(conn.execute(
        "SELECT ticker, score FROM candidate_watchlist_snapshot WHERE date=?",
        (prior_date,)).fetchall())
    current = {c["ticker"]: candidate_score(c) for c in candidates}

    added = sorted(set(current) - set(prior))
    removed = sorted(set(prior) - set(current))
    retained = sorted(set(current) & set(prior))

    movements: dict[str, tuple[float, float]] = {}
    for t in retained:
        p, c = prior[t], current[t]
        if p is not None and c is not None and abs(c - p) >= SCORE_MOVE_THRESHOLD:
            movements[t] = (p, c)

    return {"prior_date": prior_date, "added": added, "removed": removed,
            "retained": retained, "movements": movements}


def list_snapshot_inventory(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Ticker count per date, newest first -- the metadata layer for the
    API v1 Snapshot endpoints (Workstream 2C Task 2C-2). A GROUP BY over
    the same table record_snapshot already owns; no new business rule."""
    ensure_table(conn)
    rows = conn.execute(
        "SELECT date, COUNT(*) FROM candidate_watchlist_snapshot "
        "GROUP BY date ORDER BY date DESC"
    ).fetchall()
    return [{"date": d, "ticker_count": n} for d, n in rows]


def build_message(date_str: str, diff: Optional[dict[str, Any]],
                  watchlist_size: int,
                  reasons: Optional[dict[str, str]] = None) -> str:
    """Standalone Telegram HTML message for the Watchlist Update report. No
    raw <,>,& in dynamic text (tickers/reasons are escaped), so HTML
    parse_mode is safe.

    diff: result of diff_snapshot() — None when there's no prior snapshot
    (first run ever, or after a long gap).
    reasons: optional {ticker: reason} for newly-Added tickers, sourced by
    the caller from today's candidate data (e.g. reversal-watchlist
    reasons). Never fabricated here — omitted tickers show no bullet.
    """
    reasons = reasons or {}

    if diff is None:
        return (f"<b>📈 WATCHLIST UPDATE — {date_str}</b>\n\n"
                f"Current Watchlist: {watchlist_size}\n\n"
                f"<i>No prior snapshot to compare against.</i>")

    added, removed, retained = diff["added"], diff["removed"], diff["retained"]
    movements = diff.get("movements") or {}
    if not added and not removed and not movements:
        return "<b>📈 WATCHLIST UPDATE</b>\n\nNo watchlist changes today."

    L = [f"<b>📈 WATCHLIST UPDATE — {date_str}</b>", "",
         f"Current Watchlist: {watchlist_size}", ""]

    if added:
        L.append(f"<b>Added ({len(added)})</b>")
        for t in added[:_MAX_ROWS]:
            L.append(f"+ {html.escape(t)}")
            reason = reasons.get(t)
            if reason:
                L.append(f"  • {html.escape(reason)}")
        if len(added) > _MAX_ROWS:
            L.append(f"…+{len(added) - _MAX_ROWS} more")
        L.append("")

    if removed:
        L.append(f"<b>Removed ({len(removed)})</b>")
        for t in removed[:_MAX_ROWS]:
            L.append(f"- {html.escape(t)}")
        if len(removed) > _MAX_ROWS:
            L.append(f"…+{len(removed) - _MAX_ROWS} more")
        L.append("")

    if retained:
        L.append(f"<b>Retained ({len(retained)})</b>")
        for t in retained[:_MAX_ROWS]:
            L.append(html.escape(t))
            mv = movements.get(t)
            if mv:
                L.append(f"{mv[0]:.2f} → {mv[1]:.2f}")
        if len(retained) > _MAX_ROWS:
            L.append(f"…+{len(retained) - _MAX_ROWS} more")

    return "\n".join(L).rstrip()
