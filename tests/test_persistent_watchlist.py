"""Tests for engine.persistent_watchlist — the multi-day accumulated
approved-ticker registry (distinct from engine.trade_plan's watchlist_snapshot,
which is a per-day-only snapshot with no cross-day streak tracking, and from
engine.watchlist_report's candidate_watchlist_snapshot, which tracks the
PRE-firm candidate universe, not firm-approved tickers).

Pure DB/data + string-formatting functions only (no LLM, no network) —
callers supply today's already-decided approved-ticker set (the same
`ranked` list scheduler.jobs.run_eod_trade_plan already computes) and this
module only persists/updates/formats it.
"""
import sqlite3

import pytest

from engine.persistent_watchlist import build_message, ensure_table, update_watchlist


def _row(conn, ticker):
    r = conn.execute(
        "SELECT ticker, first_added_date, last_seen_date, status, "
        "consecutive_days, total_appearances FROM persistent_watchlist WHERE ticker=?",
        (ticker,),
    ).fetchone()
    if r is None:
        return None
    return {"ticker": r[0], "first_added_date": r[1], "last_seen_date": r[2],
            "status": r[3], "consecutive_days": r[4], "total_appearances": r[5]}


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


class TestEnsureTable:
    def test_creates_schema(self, conn):
        ensure_table(conn)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(persistent_watchlist)")}
        expected = {"ticker", "first_added_date", "last_seen_date", "status",
                    "consecutive_days", "total_appearances"}
        assert expected <= cols

    def test_is_idempotent(self, conn):
        ensure_table(conn)
        ensure_table(conn)  # must not raise

    def test_does_not_touch_existing_watchlist_tables(self, conn):
        """Additive-only: creating persistent_watchlist must not collide with
        or alter engine.trade_plan's watchlist_snapshot or
        engine.watchlist_report's candidate_watchlist_snapshot schemas."""
        conn.execute("CREATE TABLE watchlist_snapshot (date TEXT, strategy TEXT, ticker TEXT)")
        conn.execute("CREATE TABLE candidate_watchlist_snapshot (date TEXT, ticker TEXT)")
        ensure_table(conn)
        # Both pre-existing tables are untouched (still exist with their own columns).
        wl_cols = {r[1] for r in conn.execute("PRAGMA table_info(watchlist_snapshot)")}
        cwl_cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_watchlist_snapshot)")}
        assert wl_cols == {"date", "strategy", "ticker"}
        assert cwl_cols == {"date", "ticker"}


class TestFirstInsertion:
    def test_new_ticker_is_inserted_active(self, conn):
        result = update_watchlist(conn, "2026-08-01", {"BBCA"})
        row = _row(conn, "BBCA")
        assert row == {"ticker": "BBCA", "first_added_date": "2026-08-01",
                       "last_seen_date": "2026-08-01", "status": "ACTIVE",
                       "consecutive_days": 1, "total_appearances": 1}
        assert result["added"] == ["BBCA"]
        assert result["reactivated"] == []
        assert result["removed"] == []
        assert result["active_count"] == 1


class TestSecondDayPersistence:
    def test_ticker_present_second_day_keeps_first_added_date(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA"})
        result = update_watchlist(conn, "2026-08-02", {"BBCA"})
        row = _row(conn, "BBCA")
        assert row["first_added_date"] == "2026-08-01"
        assert row["last_seen_date"] == "2026-08-02"
        assert row["status"] == "ACTIVE"
        assert row["consecutive_days"] == 2
        assert row["total_appearances"] == 2
        assert result["added"] == []
        assert any(e["ticker"] == "BBCA" for e in result["existing"])


class TestMultipleConsecutiveDays:
    def test_consecutive_days_increments_each_day_present(self, conn):
        dates = ["2026-08-01", "2026-08-02", "2026-08-03", "2026-08-04"]
        for d in dates:
            update_watchlist(conn, d, {"BBCA"})
        row = _row(conn, "BBCA")
        assert row["consecutive_days"] == 4
        assert row["total_appearances"] == 4
        assert row["first_added_date"] == "2026-08-01"
        assert row["last_seen_date"] == "2026-08-04"


class TestRemoval:
    def test_absent_ticker_marked_removed_history_preserved(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA", "BMRI"})
        result = update_watchlist(conn, "2026-08-02", {"BBCA"})
        row = _row(conn, "BMRI")
        assert row is not None  # history preserved, never deleted
        assert row["status"] == "REMOVED"
        assert row["first_added_date"] == "2026-08-01"
        assert row["last_seen_date"] == "2026-08-01"  # last day it was actually seen
        assert result["removed"] == ["BMRI"]

    def test_removed_ticker_row_untouched_on_subsequent_days_it_stays_absent(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA", "BMRI"})
        update_watchlist(conn, "2026-08-02", {"BBCA"})
        update_watchlist(conn, "2026-08-03", {"BBCA"})
        row = _row(conn, "BMRI")
        assert row["status"] == "REMOVED"
        assert row["consecutive_days"] == 1  # frozen at removal time
        assert row["last_seen_date"] == "2026-08-01"


class TestReactivation:
    def test_reactivated_ticker_restarts_streak_keeps_first_added_date(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA", "BMRI"})
        update_watchlist(conn, "2026-08-02", {"BBCA"})            # BMRI removed
        result = update_watchlist(conn, "2026-08-03", {"BBCA", "BMRI"})  # BMRI back
        row = _row(conn, "BMRI")
        assert row["status"] == "ACTIVE"
        assert row["first_added_date"] == "2026-08-01"  # preserved, not reset
        assert row["last_seen_date"] == "2026-08-03"
        assert row["consecutive_days"] == 1              # restarted
        assert row["total_appearances"] == 2              # 08-01 + 08-03
        assert result["reactivated"] == ["BMRI"]
        assert result["added"] == []  # distinguishable from a first insertion

    def test_reactivation_distinct_from_first_insertion_in_same_batch(self, conn):
        update_watchlist(conn, "2026-08-01", {"BMRI"})
        update_watchlist(conn, "2026-08-02", {})  # BMRI removed
        result = update_watchlist(conn, "2026-08-03", {"BMRI", "GPSO"})
        assert result["reactivated"] == ["BMRI"]
        assert result["added"] == ["GPSO"]


class TestDuplicateDailyExecution:
    def test_rerun_same_day_same_tickers_does_not_double_increment(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA"})
        update_watchlist(conn, "2026-08-02", {"BBCA"})
        update_watchlist(conn, "2026-08-02", {"BBCA"})  # duplicate rerun, same day
        row = _row(conn, "BBCA")
        assert row["consecutive_days"] == 2
        assert row["total_appearances"] == 2

    def test_rerun_same_day_does_not_reprocess_removal(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA", "BMRI"})
        update_watchlist(conn, "2026-08-02", {"BBCA"})  # BMRI removed
        result2 = update_watchlist(conn, "2026-08-02", {"BBCA"})  # duplicate rerun
        assert result2["removed"] == []  # already processed, not re-reported
        row = _row(conn, "BMRI")
        assert row["status"] == "REMOVED"

    def test_rerun_same_day_no_duplicate_row(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA"})
        update_watchlist(conn, "2026-08-01", {"BBCA"})
        count = conn.execute(
            "SELECT COUNT(*) FROM persistent_watchlist WHERE ticker='BBCA'"
        ).fetchone()[0]
        assert count == 1


class TestEmptyWatchlist:
    def test_empty_today_marks_all_active_removed(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA", "BMRI"})
        result = update_watchlist(conn, "2026-08-02", set())
        assert set(result["removed"]) == {"BBCA", "BMRI"}
        assert result["active_count"] == 0
        assert result["longest_held"] is None

    def test_first_ever_call_with_empty_set_does_not_error(self, conn):
        result = update_watchlist(conn, "2026-08-01", set())
        assert result == {"added": [], "reactivated": [], "removed": [],
                          "existing": [], "active_count": 0, "longest_held": None}


class TestStatsAndSorting:
    def test_existing_sorted_by_consecutive_days_descending(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA", "BRIS", "ADRO"})
        update_watchlist(conn, "2026-08-02", {"BBCA", "BRIS", "ADRO"})
        update_watchlist(conn, "2026-08-03", {"BBCA", "BRIS"})
        result = update_watchlist(conn, "2026-08-04", {"BBCA"})
        # BBCA has been present all 4 days; only ticker left, so it's the lone entry.
        row = _row(conn, "BBCA")
        assert row["consecutive_days"] == 4

    def test_longest_held_reports_top_ticker(self, conn):
        update_watchlist(conn, "2026-08-01", {"BBCA"})
        update_watchlist(conn, "2026-08-02", {"BBCA", "GPSO"})
        result = update_watchlist(conn, "2026-08-03", {"BBCA", "GPSO"})
        assert result["longest_held"] == {"ticker": "BBCA", "consecutive_days": 3}


class TestBuildMessage:
    def test_header_and_current_active_always_present(self):
        result = {"added": [], "reactivated": [], "removed": [], "existing": [],
                  "active_count": 0, "longest_held": None}
        msg = build_message("2026-08-04", result)
        assert "📋 ACTIVE WATCHLIST" in msg
        assert "Current Active: 0" in msg

    def test_statistics_block_always_present_with_correct_counts(self):
        result = {"added": ["GPSO"], "reactivated": ["BMRI"], "removed": ["ADRO"],
                  "existing": [{"ticker": "BBCA", "consecutive_days": 7}],
                  "active_count": 3,
                  "longest_held": {"ticker": "BBCA", "consecutive_days": 7}}
        msg = build_message("2026-08-04", result)
        assert "📊 Statistics" in msg
        assert "Current Active: 3" in msg
        assert "Added Today: 1" in msg
        assert "Reactivated: 1" in msg
        assert "Removed Today: 1" in msg
        assert "Longest Held: BBCA (7d)" in msg

    def test_new_today_section_lists_added_tickers(self):
        result = {"added": ["GPSO", "FORE"], "reactivated": [], "removed": [],
                  "existing": [], "active_count": 2, "longest_held": None}
        msg = build_message("2026-08-04", result)
        assert "🆕 New Today" in msg
        assert "GPSO" in msg and "FORE" in msg

    def test_new_today_section_omitted_when_empty(self):
        result = {"added": [], "reactivated": [], "removed": [], "existing": [],
                  "active_count": 0, "longest_held": None}
        msg = build_message("2026-08-04", result)
        assert "🆕 New Today" not in msg

    def test_existing_section_sorted_by_consecutive_days_descending(self):
        result = {"added": [], "reactivated": [], "removed": [],
                  "existing": [{"ticker": "BBCA", "consecutive_days": 7},
                               {"ticker": "BRIS", "consecutive_days": 5},
                               {"ticker": "ADRO", "consecutive_days": 3}],
                  "active_count": 3, "longest_held": {"ticker": "BBCA", "consecutive_days": 7}}
        msg = build_message("2026-08-04", result)
        assert "📌 Existing" in msg
        assert "BBCA (7d)" in msg
        assert "BRIS (5d)" in msg
        assert "ADRO (3d)" in msg
        # Order preserved as given (caller already sorts descending).
        lines = msg.splitlines()
        i_bbca = next(i for i, l in enumerate(lines) if "BBCA (7d)" in l)
        i_bris = next(i for i, l in enumerate(lines) if "BRIS (5d)" in l)
        i_adro = next(i for i, l in enumerate(lines) if "ADRO (3d)" in l)
        assert i_bbca < i_bris < i_adro

    def test_existing_section_omitted_when_empty(self):
        result = {"added": ["GPSO"], "reactivated": [], "removed": [], "existing": [],
                  "active_count": 1, "longest_held": {"ticker": "GPSO", "consecutive_days": 1}}
        msg = build_message("2026-08-04", result)
        assert "📌 Existing" not in msg

    def test_reactivated_section_lists_tickers(self):
        result = {"added": [], "reactivated": ["BMRI"], "removed": [], "existing": [],
                  "active_count": 1, "longest_held": {"ticker": "BMRI", "consecutive_days": 1}}
        msg = build_message("2026-08-04", result)
        assert "♻️ Reactivated" in msg
        assert "BMRI" in msg

    def test_reactivated_section_omitted_when_empty(self):
        result = {"added": ["GPSO"], "reactivated": [], "removed": [], "existing": [],
                  "active_count": 1, "longest_held": {"ticker": "GPSO", "consecutive_days": 1}}
        msg = build_message("2026-08-04", result)
        assert "♻️ Reactivated" not in msg

    def test_removed_today_section_lists_tickers(self):
        result = {"added": [], "reactivated": [], "removed": ["ADRO"], "existing": [],
                  "active_count": 0, "longest_held": None}
        msg = build_message("2026-08-04", result)
        assert "👋 Removed Today" in msg
        assert "ADRO" in msg

    def test_removed_today_section_omitted_when_empty(self):
        result = {"added": ["GPSO"], "reactivated": [], "removed": [], "existing": [],
                  "active_count": 1, "longest_held": {"ticker": "GPSO", "consecutive_days": 1}}
        msg = build_message("2026-08-04", result)
        assert "👋 Removed Today" not in msg

    def test_longest_held_dash_when_no_active_tickers(self):
        result = {"added": [], "reactivated": [], "removed": ["ADRO"], "existing": [],
                  "active_count": 0, "longest_held": None}
        msg = build_message("2026-08-04", result)
        assert "Longest Held: —" in msg

    def test_tickers_are_html_escaped(self):
        result = {"added": ["<b>EVIL</b>"], "reactivated": [], "removed": [],
                  "existing": [], "active_count": 1,
                  "longest_held": {"ticker": "<b>EVIL</b>", "consecutive_days": 1}}
        msg = build_message("2026-08-04", result)
        assert "<b>EVIL</b>" not in msg
        assert "&lt;b&gt;EVIL&lt;/b&gt;" in msg
