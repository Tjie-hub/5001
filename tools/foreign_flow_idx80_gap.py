"""Universe, canonical calendar, and the foreign-flow (`Asing`) completion
predicate for the IDX80 `broker_flow` dataset.

WHY THIS IS NOT A NEW DATASET
------------------------------
There is no separate "foreign flow" vendor endpoint or table. `broker_flow`
(schema: stockbit_fetcher.py::init_flow_db) already stores every investor
type in one place -- stockbit_fetcher.py::fetch_broker_flow() calls the SAME
`marketdetectors/{ticker}` endpoint with `investor_type=INVESTOR_TYPE_ALL`,
and a single response returns Asing/Lokal/Pemerintah broker rows together,
written atomically in one `executemany()` (see
tools/backfill_broker_flow_idx80.py::_write_populated). "Foreign flow" is
the `investor_type='Asing'` slice of that same table -- every production
consumer already reads it that way (engine/dashboard.py, routes/flow.py,
engine/agent_firm_context.py, scheduler/jobs.py, flow_filter.py all filter
`broker_flow WHERE investor_type='Asing'`). docs/governance/
DATA_FEASIBILITY_STUDY.md documents `broker_flow` itself as "Broker summary
... by investor type (Asing/Lokal/Pemerintah)", and
stockbit_broker_period.py's endpoint-investigation docstring (2026-08-04)
records that this codebase already ruled out every other broker/foreign
candidate endpoint. This module does not invent a schema or endpoint; it
adds foreign-specific visibility into data broker_flow already stores.

WHY A DEDICATED GAP DETECTOR STILL EARNS ITS PLACE
-----------------------------------------------------
tools/broker_flow_idx80_gap.py's `broker_cell_complete()` only asks "does
ANY broker_flow row exist" -- it cannot tell a caller whether a completed
cell had real foreign activity, zero foreign activity in an otherwise-active
session, or a session with no broker activity of any kind. Because the
vendor fetch is atomic across investor types, those three states (plus "not
yet fetched") are already fully determined by data in the DB; this module's
`foreign_cell_state()` surfaces that breakdown for research use without
fetching or storing anything new.

`foreign_cell_complete()` is a direct delegate to
`broker_flow_idx80_gap.broker_cell_complete()` -- NOT a reimplementation --
so the two predicates can never drift. They are set-equal by construction
(a ticker-day is broker-complete iff it is foreign-complete, because the one
vendor call that would populate either populates both): see
tests/test_foreign_flow_idx80_gap.py for the equivalence assertion.

WHY THE UNIVERSE AND CALENDAR ARE RE-EXPORTED, NOT DUPLICATED
-----------------------------------------------------------------
`idx80_universe()` and `canonical_trading_dates()` are IDX80/calendar
concerns, not foreign-flow concerns -- re-exported from
tools/broker_flow_idx80_gap.py so there is exactly one implementation of
"live IDX80 universe" and "IHSG-confirmed trading date" in the repo.

NO FROZEN FIXTURE
------------------
tools/agent_backfill_broker_flow_idx80.py's own docstring records that
broker_flow was deliberately built "trimmed to what broker_flow actually
needs: no frozen fixture". The 2025-04-14 Day-1 discrimination fixture
belongs exclusively to the `stockbit_flow_bars` dataset
(tools/backfill_flow_bars.py::FROZEN_FIXTURE_DATES,
tools/agent_backfill_idx80.py) and is never referenced here. Since
foreign-flow is a slice of broker_flow, not a new collection surface, this
module carries forward that same "no frozen fixture" position rather than
inventing a barrier broker_flow itself doesn't have.
"""
from tools.broker_flow_idx80_gap import (  # noqa: F401 -- re-exported
    idx80_universe,
    canonical_trading_dates,
    broker_cell_complete,
)

FOREIGN_INVESTOR_TYPE = "Asing"

STATE_PRESENT = "PRESENT"
STATE_CONFIRMED_EMPTY_FOREIGN_ONLY = "CONFIRMED_EMPTY_FOREIGN_ONLY"
STATE_CONFIRMED_EMPTY_SESSION = "CONFIRMED_EMPTY_SESSION"
STATE_MISSING = "MISSING"

_FOREIGN_ROWS_SQL = """
    SELECT 1 FROM broker_flow
    WHERE ticker = ? AND trade_date = ? AND investor_type = ?
    LIMIT 1
"""

_ANY_BROKER_ROWS_SQL = """
    SELECT 1 FROM broker_flow
    WHERE ticker = ? AND trade_date = ?
    LIMIT 1
"""

_EMPTY_MARKER_SQL = """
    SELECT 1 FROM bandar_detector
    WHERE ticker = ? AND trade_date = ?
      AND COALESCE(value, 0)  = 0
      AND COALESCE(volume, 0) = 0
    LIMIT 1
"""


def foreign_cell_state(conn, ticker: str, trade_date: str) -> str:
    """Foreign-flow-specific breakdown of one (ticker, trade_date) cell.

    PRESENT: at least one investor_type='Asing' broker_flow row exists --
        genuine foreign broker activity was recorded.
    CONFIRMED_EMPTY_FOREIGN_ONLY: broker_flow has rows for this cell (some
        other investor type) but genuinely zero Asing rows -- real trading
        happened that day, just not by foreign brokers. This is NOT a gap:
        the atomic vendor fetch already checked Asing and found nothing.
    CONFIRMED_EMPTY_SESSION: no broker_flow rows at all, but the
        bandar_detector zero-value marker shows the runner fetched,
        retried, and confirmed the WHOLE session (Asing included) had no
        broker activity.
    MISSING: none of the above -- not yet fetched, or an anomalous partial
        state (mirrors broker_cell_complete's own incomplete-by-default
        posture for anything unrecognized).
    """
    if conn.execute(
        _FOREIGN_ROWS_SQL, (ticker, trade_date, FOREIGN_INVESTOR_TYPE)
    ).fetchone():
        return STATE_PRESENT
    if conn.execute(_ANY_BROKER_ROWS_SQL, (ticker, trade_date)).fetchone():
        return STATE_CONFIRMED_EMPTY_FOREIGN_ONLY
    if conn.execute(_EMPTY_MARKER_SQL, (ticker, trade_date)).fetchone():
        return STATE_CONFIRMED_EMPTY_SESSION
    return STATE_MISSING


def foreign_cell_complete(conn, ticker: str, trade_date: str) -> bool:
    """True iff (ticker, trade_date) needs no further foreign-flow fetch.

    Delegates to broker_flow_idx80_gap.broker_cell_complete() rather than
    reimplementing it -- see this module's docstring for why the two
    predicates are set-equal by construction.
    """
    return broker_cell_complete(conn, ticker, trade_date)


def missing_cells(conn, trade_date: str, tickers: list) -> list:
    """Subset of `tickers` still needing a foreign-flow fetch for `trade_date`.

    Order-preserving so a resumed run walks the universe in a stable order.
    """
    return [t for t in tickers if not foreign_cell_complete(conn, t, trade_date)]
