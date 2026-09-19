"""ticker_sector reference table (added 2026-09-19).

Context: the repo had no usable sector map -- candidate_watchlist_snapshot.sector
was 100% NULL and engine/sector_rotation.py covered 82 of 959 tickers. That made
sector concentration the largest untestable confound in P-M research; testing it
once labels existed cut the then-best candidate's t from 2.29 to 1.03.

This is REFERENCE data, not research output: production may read and write it,
so it is deliberately NOT in RESEARCH_TABLES.
"""
import sqlite3
import tempfile
from pathlib import Path

from data.market_schema import ensure_market_data_schema


def _tmpdb():
    d = tempfile.mkdtemp()
    return str(Path(d) / "t.db")


def test_table_is_created_idempotently():
    db = _tmpdb()
    ensure_market_data_schema(db)
    ensure_market_data_schema(db)          # must not raise on second call
    c = sqlite3.connect(db)
    cols = {r[1] for r in c.execute("PRAGMA table_info(ticker_sector)")}
    assert {"ticker", "sector", "industry", "source", "updated_at"} <= cols


def test_ticker_is_unique_and_upsertable():
    db = _tmpdb()
    ensure_market_data_schema(db)
    c = sqlite3.connect(db)
    ins = ("INSERT INTO ticker_sector (ticker,sector,industry,source)"
           " VALUES (?,?,?,'yfinance')"
           " ON CONFLICT(ticker) DO UPDATE SET sector=excluded.sector")
    c.execute(ins, ("BBCA", "Financial Services", "Banks - Regional"))
    c.execute(ins, ("BBCA", "Financials", "Banks"))
    c.commit()
    rows = c.execute("SELECT ticker, sector FROM ticker_sector").fetchall()
    assert rows == [("BBCA", "Financials")], "re-running the backfill must refresh in place"


def test_unlabelled_tickers_are_representable():
    """98.6% of IDX names resolve; the rest must be storable as NULL rather than
    silently dropped, so coverage can be measured."""
    db = _tmpdb()
    ensure_market_data_schema(db)
    c = sqlite3.connect(db)
    c.execute("INSERT INTO ticker_sector (ticker,sector,industry,source) VALUES (?,?,?,?)",
              ("XXXX", None, None, "yfinance"))
    c.commit()
    assert c.execute("SELECT COUNT(*) FROM ticker_sector WHERE sector IS NULL").fetchone()[0] == 1


def test_not_a_research_owned_table():
    """Reference data: production may write it, so it must stay out of the
    research write fence."""
    from tests.test_research_data_fence import RESEARCH_TABLES
    assert "ticker_sector" not in RESEARCH_TABLES
