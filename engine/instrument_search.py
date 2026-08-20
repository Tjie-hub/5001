"""Instrument search — pure data layer for the Search Workspace's instrument
lookup (Production OS Slice 5). SEARCH_DESIGN_SPEC_v1.0_FROZEN.md §12:
"Backend Owns Relevance", "Search Never Decides" -- relevance here is
exact-match, then prefix-match, then substring-match, alphabetical within
each tier; nothing that resembles ranking/recommendation logic.

Searches idx_tickers.ticker only -- that table has no company-name column,
so this never pretends to match on a name it doesn't have.
"""
from data.db import connect as db_connect


def search_instruments(db_path: str, query: str, limit: int = 20) -> list[dict]:
    q = (query or "").strip().upper()
    if not q:
        return []

    conn = db_connect(db_path)
    try:
        rows = conn.execute(
            "SELECT ticker, in_idx30, in_lq45, in_idx80 FROM idx_tickers "
            "WHERE status='active' AND ticker LIKE ?",
            (f"%{q}%",),
        ).fetchall()
    finally:
        conn.close()

    def _rank(ticker: str) -> int:
        if ticker == q:
            return 0
        if ticker.startswith(q):
            return 1
        return 2

    rows.sort(key=lambda r: (_rank(r[0]), r[0]))

    return [
        {
            "ticker": r[0],
            "in_idx30": bool(r[1]),
            "in_lq45": bool(r[2]),
            "in_idx80": bool(r[3]),
        }
        for r in rows[:limit]
    ]
