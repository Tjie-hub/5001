"""Corporate-action persistence in data/fetcher._save_actions.

Pins the 2026-09-19 fix: the previous implementation wrapped the entire loop in
`except Exception: pass`, so a schema fault or one bad row was indistinguishable
from "this ticker paid no dividends" -- and that silence is what let a gap go
unnoticed. Failures must now be logged and must not abort the remaining rows,
while still never raising into the OHLCV fetch.
"""
import logging
import sqlite3

import pandas as pd

from data import fetcher


def _conn():
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE corporate_actions (
        ticker TEXT, date TEXT, action TEXT, value REAL, source TEXT,
        PRIMARY KEY (ticker,date,action))""")
    return c


def _df(rows):
    return pd.DataFrame(rows)


def test_persists_dividends_and_splits():
    c = _conn()
    n = fetcher._save_actions(c, "BBCA", _df([
        {"date": "2026-01-05", "dividends": 100.0, "splits": 0.0},
        {"date": "2026-02-05", "dividends": 0.0, "splits": 5.0},
        {"date": "2026-03-05", "dividends": 0.0, "splits": 0.0},
    ]))
    assert n == 2
    got = dict(c.execute("SELECT action, value FROM corporate_actions").fetchall())
    assert got == {"dividend": 100.0, "split": 5.0}


def test_nan_and_zero_are_skipped():
    c = _conn()
    n = fetcher._save_actions(c, "TLKM", _df([
        {"date": "2026-01-05", "dividends": float("nan"), "splits": 0.0},
        {"date": "2026-01-06", "dividends": 0.0, "splits": 0.0},
    ]))
    assert n == 0
    assert c.execute("SELECT COUNT(*) FROM corporate_actions").fetchone()[0] == 0


def test_one_bad_row_does_not_lose_the_others(caplog):
    """The regression that mattered: a single failure used to abort the loop
    silently, discarding every action after it."""
    c = _conn()
    rows = _df([
        {"date": "2026-01-05", "dividends": 10.0, "splits": 0.0},
        {"date": "2026-01-06", "dividends": "not-a-number", "splits": 0.0},
        {"date": "2026-01-07", "dividends": 30.0, "splits": 0.0},
    ])
    with caplog.at_level(logging.WARNING):
        n = fetcher._save_actions(c, "ASII", rows)
    assert n == 2, "rows after the bad one must still persist"
    dates = [r[0] for r in c.execute("SELECT date FROM corporate_actions ORDER BY date")]
    assert dates == ["2026-01-05", "2026-01-07"]
    assert any("actions" in r.message or "actions" in r.getMessage() for r in caplog.records), \
        "a failure must be logged, never swallowed"


def test_never_raises_into_the_ohlcv_fetch():
    """A corporate-action problem must not take down an OHLCV fetch."""
    broken = sqlite3.connect(":memory:")   # no corporate_actions table at all
    n = fetcher._save_actions(broken, "BMRI", _df([
        {"date": "2026-01-05", "dividends": 10.0, "splits": 0.0},
    ]))
    assert n == 0
