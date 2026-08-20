"""Tests for engine/instrument_search.py -- pure data layer backing the
Search Workspace's instrument search (Production OS Slice 5).

SEARCH_DESIGN_SPEC_v1.0_FROZEN.md §12: "Backend Owns Relevance", "Search
Never Decides" -- relevance is exact-match, then prefix-match, then
substring-match, alphabetical within each tier. No company-name search:
idx_tickers has no name column, so this never pretends to match on one.
"""
import sqlite3
import tempfile

import pytest

from engine.instrument_search import search_instruments


@pytest.fixture
def db_path():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.executescript("""
        CREATE TABLE idx_tickers (
            ticker TEXT PRIMARY KEY, status TEXT DEFAULT 'active',
            in_idx30 INTEGER DEFAULT 0, in_lq45 INTEGER DEFAULT 0,
            in_idx80 INTEGER DEFAULT 0
        );
    """)
    conn.executemany(
        "INSERT INTO idx_tickers (ticker, status, in_idx30, in_lq45, in_idx80) VALUES (?,?,?,?,?)",
        [
            ("BBCA", "active", 1, 1, 1),
            ("BBRI", "active", 1, 1, 1),
            ("BBNI", "active", 1, 1, 1),
            ("BB", "active", 0, 0, 0),  # exact-match case
            ("ABBA", "active", 0, 0, 0),  # substring, not prefix
            ("DELISTED", "delisted", 0, 0, 0),
        ],
    )
    conn.commit()
    conn.close()
    return tmp.name


class TestSearchInstruments:
    def test_empty_query_returns_no_results(self, db_path):
        assert search_instruments(db_path, "") == []
        assert search_instruments(db_path, "   ") == []

    def test_prefix_match(self, db_path):
        results = [r["ticker"] for r in search_instruments(db_path, "BB")]
        assert results[0] == "BB"  # exact match ranks first
        assert set(results) == {"BB", "BBCA", "BBRI", "BBNI", "ABBA"}

    def test_exact_match_ranks_before_prefix_and_substring(self, db_path):
        results = [r["ticker"] for r in search_instruments(db_path, "BB")]
        assert results[0] == "BB"
        assert results[1:4] == sorted(["BBCA", "BBRI", "BBNI"])
        assert results[4] == "ABBA"

    def test_is_case_insensitive(self, db_path):
        assert [r["ticker"] for r in search_instruments(db_path, "bbca")] == ["BBCA"]

    def test_excludes_inactive_tickers(self, db_path):
        results = [r["ticker"] for r in search_instruments(db_path, "DELISTED")]
        assert results == []

    def test_no_match_returns_empty_list_not_an_error(self, db_path):
        assert search_instruments(db_path, "ZZZNOPE") == []

    def test_includes_index_membership_flags(self, db_path):
        results = {r["ticker"]: r for r in search_instruments(db_path, "BBCA")}
        assert results["BBCA"] == {
            "ticker": "BBCA", "in_idx30": True, "in_lq45": True, "in_idx80": True,
        }

    def test_respects_limit(self, db_path):
        results = search_instruments(db_path, "B", limit=2)
        assert len(results) == 2
