"""Bear dip-scout watchlist — add, promote, expire, and query functions.

The watchlist captures oversold quality tickers detected in BEAR regime
so they can be prioritised when their regime flips back to BULL.
"""

import sqlite3
from typing import List


_DDL = """
CREATE TABLE IF NOT EXISTS regime_watchlist (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker            TEXT NOT NULL,
    added_date        TEXT NOT NULL,
    regime_at_add     TEXT NOT NULL DEFAULT 'BEAR',
    rsi_at_add        REAL,
    close_vs_ma50_pct REAL,
    wf_score          REAL,
    status            TEXT NOT NULL DEFAULT 'active',
    promoted_date     TEXT,
    created_at        TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rwl_ticker_status
    ON regime_watchlist(ticker, status);
"""

RSI_THRESHOLD  = 35.0     # oversold gate
WF_SCORE_MIN   = 60.0     # quality gate


def ensure_table(conn: sqlite3.Connection) -> None:
    """Create regime_watchlist table if it does not exist."""
    conn.executescript(_DDL)
    conn.commit()


def compute_rsi(close, period: int = 14) -> float:
    """RSI-14 for the last bar of a pandas Series of closing prices."""
    import pandas as pd
    close = pd.Series(close)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    avg_gain = gain.iloc[-1]
    avg_loss = loss.iloc[-1]
    if pd.isna(avg_gain) or pd.isna(avg_loss):
        return float('nan')
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else float('nan')
    rs  = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))


def add_to_watchlist(
    conn: sqlite3.Connection,
    ticker: str,
    rsi: float,
    close_vs_ma50_pct: float,
    wf_score: float,
    scan_date: str,
) -> bool:
    """
    Add ticker to watchlist if all criteria pass. Returns True if inserted.

    Criteria (all must hold):
    - Not already 'active' in watchlist
    - Not currently OPEN in paper_trades
    """
    # Guard: already active
    existing = conn.execute(
        "SELECT id FROM regime_watchlist WHERE ticker=? AND status='active'",
        (ticker,),
    ).fetchone()
    if existing:
        return False

    # Guard: open trade
    open_trade = conn.execute(
        "SELECT id FROM paper_trades WHERE ticker=? AND status='OPEN'",
        (ticker,),
    ).fetchone()
    if open_trade:
        return False

    conn.execute(
        """INSERT INTO regime_watchlist
           (ticker, added_date, rsi_at_add, close_vs_ma50_pct, wf_score, status)
           VALUES (?, ?, ?, ?, ?, 'active')""",
        (ticker, scan_date, rsi, close_vs_ma50_pct, wf_score),
    )
    conn.commit()
    return True


def promote_watchlist(
    conn: sqlite3.Connection,
    tickers_flipped_bull: List[str],
    scan_date: str,
) -> List[str]:
    """
    Mark active watchlist entries for bull-flipped tickers as 'promoted'.
    Returns list of tickers actually promoted.
    """
    promoted = []
    for ticker in tickers_flipped_bull:
        cur = conn.execute(
            """UPDATE regime_watchlist
               SET status='promoted', promoted_date=?
               WHERE ticker=? AND status='active'""",
            (scan_date, ticker),
        )
        if cur.rowcount > 0:
            promoted.append(ticker)
    conn.commit()
    return promoted


def expire_stale(
    conn: sqlite3.Connection,
    scan_date: str,
    max_calendar_days: int = 30,
) -> List[str]:
    """
    Expire active entries older than max_calendar_days.
    Returns list of expired tickers.
    """
    cur = conn.execute(
        """UPDATE regime_watchlist
           SET status='expired'
           WHERE status='active'
             AND julianday(?) - julianday(added_date) > ?
           RETURNING ticker""",
        (scan_date, max_calendar_days),
    )
    expired = [row[0] for row in cur.fetchall()]
    conn.commit()
    return expired


def priority_tickers(conn: sqlite3.Connection) -> List[str]:
    """Return tickers promoted from bear watchlist (priority for bull entry scan)."""
    rows = conn.execute(
        "SELECT ticker FROM regime_watchlist WHERE status='promoted' ORDER BY promoted_date DESC"
    ).fetchall()
    return [r[0] for r in rows]
