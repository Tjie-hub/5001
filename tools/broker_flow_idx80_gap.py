"""Universe, canonical calendar, and completion predicate for the IDX80
`broker_flow` backfill.

WHY A CONFIRMED-EMPTY MARKER
-----------------------------
The vendor endpoint (`marketdetectors/{ticker}`, see stockbit_fetcher.py::
fetch_broker_flow) can return HTTP 200 with genuinely empty
`broker_summary.brokers_buy/sell` arrays for a real trading session. A
bare "does broker_flow have any row" predicate can never distinguish
"legitimately no broker activity that day" from "not fetched yet", so it
would re-fetch a permanently-empty cell forever on every resume.

This module reuses `bandar_detector` (already keyed (ticker, trade_date),
already written by the fetch path) as that marker -- exactly the same role
`stockbit_flow`'s zero-activity summary row plays for the sibling
`stockbit_flow_bars` completion predicate in tools/flow_bars_gap.py. A row
with `value=0 AND volume=0` means "fetched, retried, genuinely empty"; any
other bandar_detector state without broker_flow rows is left INCOMPLETE
deliberately, so an anomalous partial result gets retried rather than
silently accepted.

WHY THE UNIVERSE IS A LIVE QUERY, NOT A CONSTANT
-------------------------------------------------
`idx_tickers.status='active' AND in_idx80=1` is queried fresh every call.
IDX80 membership changes (index reconstitution); a hardcoded ticker list
would silently drift from the real universe.

WHY CANONICAL DATES REQUIRE AN IHSG BAR
-----------------------------------------
`trading_calendar` has two independent writers (see
tools/agent_backfill_idx80.py's module docstring for the full precedent this
mirrors): `data/market_schema.py::build_trading_calendar` (source='IHSG',
canonical) and `screener/idx_scraper.py::save_ohlcv_to_db` (source=
'scraper_eod', a side effect of every finalized EOD save, not itself
evidence of a confirmed IDX session). A date is an expected IDX80 session
here only when BOTH a trading_calendar row AND an IHSG `ohlcv` bar exist for
it -- never the `source` column alone (first-writer-wins, so it can be
stale). No holiday list is maintained; weekends/holidays are excluded
implicitly because IHSG never has a bar on them.
"""
from typing import Optional


def idx80_universe(conn) -> list:
    """The live, active IDX80 ticker universe. Never hardcoded."""
    return [r[0] for r in conn.execute(
        "SELECT ticker FROM idx_tickers WHERE status='active' AND in_idx80=1 "
        "ORDER BY ticker"
    )]


def canonical_trading_dates(conn, date_from: str, date_to: str) -> tuple:
    """(confirmed_dates, non_ihsg_rows) for [date_from, date_to) -- EXCLUSIVE.

    confirmed_dates: trading_calendar row AND an IHSG ohlcv bar, ascending.
    non_ihsg_rows: [{"date":..., "source":...}] for calendar rows in the
    window with no IHSG bar -- reported, never silently dropped.
    """
    cal = [(r[0], r[1]) for r in conn.execute(
        "SELECT date, source FROM trading_calendar "
        "WHERE date >= ? AND date < ? ORDER BY date",
        (date_from, date_to),
    )]
    ihsg = {r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM ohlcv "
        "WHERE ticker = 'IHSG' AND date >= ? AND date < ?",
        (date_from, date_to),
    )}
    confirmed = [d for d, _ in cal if d in ihsg]
    non_ihsg = [{"date": d, "source": s} for d, s in cal if d not in ihsg]
    return confirmed, non_ihsg


_EMPTY_MARKER_SQL = """
    SELECT 1 FROM bandar_detector
    WHERE ticker = ? AND trade_date = ?
      AND COALESCE(value, 0)  = 0
      AND COALESCE(volume, 0) = 0
    LIMIT 1
"""

_BROKER_ROWS_SQL = """
    SELECT 1 FROM broker_flow
    WHERE ticker = ? AND trade_date = ?
    LIMIT 1
"""


def broker_cell_complete(conn, ticker: str, trade_date: str) -> bool:
    """True iff (ticker, trade_date) needs no further broker-flow fetch.

    Complete means either broker_flow rows are stored, or the session was
    fetched, retried, and confirmed genuinely empty (the bandar_detector
    zero-value marker). Anything else -- including a nonzero bandar_detector
    rollup with no broker_flow rows, an anomalous partial state -- is
    incomplete and must be (re)fetched.
    """
    if conn.execute(_BROKER_ROWS_SQL, (ticker, trade_date)).fetchone():
        return True
    return conn.execute(_EMPTY_MARKER_SQL, (ticker, trade_date)).fetchone() is not None


def missing_cells(conn, trade_date: str, tickers: list) -> list:
    """Subset of `tickers` still needing a broker-flow fetch for `trade_date`.

    Order-preserving so a resumed run walks the universe in a stable order.
    """
    return [t for t in tickers if not broker_cell_complete(conn, t, trade_date)]
