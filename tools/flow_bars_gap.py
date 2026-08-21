"""Completion predicate for a `stockbit_flow_bars` historical backfill.

WHY THIS EXISTS
---------------
The bars backfill runners (`scratchpad/backfill_history.py`,
`scratchpad/backfill_flow_5liquid.py`) originally decided "this (ticker, date)
is already done" with:

    SELECT 1 FROM stockbit_flow WHERE ticker=? AND trade_date=?

That is the *summary* table, not the bars table. `stockbit_flow` already carries
a completed, certified backfill (122 dates x 79 IDX80 names, July 2026) whose
`stockbit_flow_bars` rows were never written -- so every one of those cells
tested "complete" and was skipped, permanently.

Measured blast radius (bounded soak, 2026-08-20): **9,341** (ticker, date) cells
in the 2025-01-02..2026-04-27 window would have been silently skipped while still
missing bars, and they are concentrated in the largest/most liquid IDX80 names --
i.e. a full backfill would have completed, reported success, and handed back a
panel with the biggest names systematically absent. See
`docs/audit/STOCKBIT_FLOW_BARS_BACKFILL_STATE_2026-08-20.md`.

WHY NOT JUST CHECK stockbit_flow_bars
-------------------------------------
Because a genuinely empty session has no bars and never will. On the soak date
116 of 958 cells were valid fetches of illiquid names that simply did not trade.
A bars-only predicate would re-fetch those on every single resume pass, forever.

The vendor's own data makes the distinction safe: across the whole window,
"summary row records zero activity" and "no bars rows" agree exactly (0
disagreements). So a zero-activity summary row is trustworthy proof that the
session was fetched and was legitimately empty -- while a *non-zero* summary row
with no bars means the bars were never stored, which is precisely the defect.

No fake/sentinel bar rows are written to represent an empty session.
"""

_BARS_SQL = """
    SELECT 1 FROM stockbit_flow_bars
    WHERE ticker = ? AND trade_date = ?
    LIMIT 1
"""

# A summary row is only accepted as proof of completion when it records a
# genuinely empty session. COALESCE so a NULL column never reads as "activity".
_EMPTY_SESSION_SQL = """
    SELECT 1 FROM stockbit_flow
    WHERE ticker = ? AND trade_date = ?
      AND COALESCE(buy_lot, 0)  = 0
      AND COALESCE(sell_lot, 0) = 0
      AND COALESCE(buy_freq, 0) = 0
      AND COALESCE(sell_freq, 0) = 0
    LIMIT 1
"""


def bars_cell_complete(conn, ticker, trade_date):
    """True iff (ticker, trade_date) needs no further bars fetch.

    Complete means either bars are stored, or the session was fetched and was
    genuinely empty. Anything else -- including "summary row exists but shows
    real trading activity and no bars" -- is incomplete and must be refetched.
    """
    if conn.execute(_BARS_SQL, (ticker, trade_date)).fetchone():
        return True
    return conn.execute(_EMPTY_SESSION_SQL, (ticker, trade_date)).fetchone() is not None


def missing_bars_cells(conn, trade_date, tickers):
    """Return the subset of `tickers` still needing a bars fetch for `trade_date`.

    Order-preserving, so a resumed run walks the universe in a stable order.
    """
    return [t for t in tickers if not bars_cell_complete(conn, t, trade_date)]
