"""Regression tests for tools/flow_bars_gap.py.

Guards the defect found by the 2026-08-20 bounded soak: the bars backfill used
`stockbit_flow` (the summary table) as its completion predicate, so 9,341
(ticker, date) cells that had a summary row but no bars were skipped forever --
concentrated in the largest IDX80 names. See the module docstring in
tools/flow_bars_gap.py.
"""
import sqlite3

import pytest

from tools.flow_bars_gap import bars_cell_complete, missing_bars_cells

DATE = "2025-01-06"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE stockbit_flow_bars (
        ticker TEXT NOT NULL, trade_date TEXT NOT NULL, bar_time TEXT NOT NULL,
        buy_lot INTEGER, sell_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
        net_value INTEGER, price INTEGER, delta INTEGER,
        PRIMARY KEY (ticker, trade_date, bar_time)
    )""")
    c.execute("""CREATE TABLE stockbit_flow (
        ticker TEXT NOT NULL, trade_date TEXT NOT NULL,
        buy_lot INTEGER, sell_lot INTEGER, net_lot INTEGER,
        buy_freq INTEGER, sell_freq INTEGER, net_value INTEGER,
        last_price INTEGER, composite_score REAL, verdict TEXT,
        smart_money TEXT, updated_at TEXT,
        PRIMARY KEY (ticker, trade_date)
    )""")
    yield c
    c.close()


def _add_bars(conn, ticker, n=3):
    conn.executemany(
        "INSERT INTO stockbit_flow_bars (ticker, trade_date, bar_time) VALUES (?, ?, ?)",
        [(ticker, DATE, f"09:{i:02d}") for i in range(n)],
    )


def _add_summary(conn, ticker, buy_lot=0, sell_lot=0, buy_freq=0, sell_freq=0):
    conn.execute(
        """INSERT INTO stockbit_flow
           (ticker, trade_date, buy_lot, sell_lot, buy_freq, sell_freq)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (ticker, DATE, buy_lot, sell_lot, buy_freq, sell_freq),
    )


def test_bars_present_is_complete(conn):
    _add_bars(conn, "BBCA")
    assert bars_cell_complete(conn, "BBCA", DATE) is True


def test_nothing_at_all_is_incomplete(conn):
    assert bars_cell_complete(conn, "BBCA", DATE) is False


def test_summary_with_activity_but_no_bars_is_INCOMPLETE(conn):
    """THE DEFECT: the old predicate returned True here and skipped forever."""
    _add_summary(conn, "BBCA", buy_lot=1000, sell_lot=900, buy_freq=5, sell_freq=4)
    assert bars_cell_complete(conn, "BBCA", DATE) is False


def test_zero_activity_summary_is_complete_without_bars(conn):
    """A genuinely empty session must not be refetched on every resume pass."""
    _add_summary(conn, "ABDA")
    assert bars_cell_complete(conn, "ABDA", DATE) is True


def test_null_columns_do_not_read_as_activity(conn):
    conn.execute(
        "INSERT INTO stockbit_flow (ticker, trade_date) VALUES (?, ?)", ("ABDA", DATE)
    )
    assert bars_cell_complete(conn, "ABDA", DATE) is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"buy_lot": 1},
        {"sell_lot": 1},
        {"buy_freq": 1},
        {"sell_freq": 1},
    ],
)
def test_any_single_nonzero_field_means_incomplete(conn, kwargs):
    _add_summary(conn, "BBCA", **kwargs)
    assert bars_cell_complete(conn, "BBCA", DATE) is False


def test_bars_win_over_activity_summary(conn):
    """Bars present is sufficient regardless of what the summary row says."""
    _add_bars(conn, "BBCA")
    _add_summary(conn, "BBCA", buy_lot=1000, buy_freq=5)
    assert bars_cell_complete(conn, "BBCA", DATE) is True


def test_other_date_does_not_satisfy_completion(conn):
    conn.execute(
        "INSERT INTO stockbit_flow_bars (ticker, trade_date, bar_time) VALUES (?, ?, ?)",
        ("BBCA", "2025-01-07", "09:00"),
    )
    assert bars_cell_complete(conn, "BBCA", DATE) is False


def test_missing_bars_cells_selects_only_the_gaps(conn):
    _add_bars(conn, "TLKM")                                    # complete: has bars
    _add_summary(conn, "ABDA")                                 # complete: empty session
    _add_summary(conn, "BBCA", buy_lot=1000, buy_freq=5)       # INCOMPLETE: the defect
    # ASII: nothing at all -> incomplete
    universe = ["TLKM", "ABDA", "BBCA", "ASII"]
    assert missing_bars_cells(conn, DATE, universe) == ["BBCA", "ASII"]


def test_missing_bars_cells_preserves_order(conn):
    universe = ["ZYRX", "AALI", "MEDC"]
    assert missing_bars_cells(conn, DATE, universe) == universe
