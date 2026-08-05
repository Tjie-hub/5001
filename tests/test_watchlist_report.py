"""Tests for engine.watchlist_report — the pre-firm candidate watchlist
snapshot + standalone Telegram "Watchlist Update" report.

Distinct from engine.trade_plan's watchlist_snapshot (which tracks the
FIRM-APPROVED post-decision shortlist). This module snapshots the raw
unified long-candidate universe *before* firm review.

Pure DB/data + string-formatting functions only (no LLM, no network).
"""
import sqlite3

import pytest

from engine.watchlist_report import (
    build_message,
    diff_snapshot,
    ensure_table,
    record_snapshot,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


def _cands(*tickers, reason=None):
    """Minimal candidate dicts shaped like engine.trade_plan.gather_long_candidates
    output — only the fields this module reads."""
    out = []
    for t in tickers:
        d = {"ticker": t, "sources": ["R"], "conviction": 50.0,
             "vol_ratio": 0.0, "reason": ""}
        if reason and t in reason:
            d["reason"] = reason[t]
        out.append(d)
    return out


class TestRecordAndFirstSnapshot:
    def test_first_snapshot_has_no_prior_diff(self, conn):
        cands = _cands("BBCA", "BMRI")
        record_snapshot(conn, "2026-08-03", cands)
        assert diff_snapshot(conn, "2026-08-03", cands) is None

    def test_first_snapshot_persists_rows(self, conn):
        record_snapshot(conn, "2026-08-03", _cands("BBCA", "BMRI"))
        ensure_table(conn)
        rows = conn.execute(
            "SELECT ticker FROM candidate_watchlist_snapshot WHERE date=? ORDER BY ticker",
            ("2026-08-03",),
        ).fetchall()
        assert [r[0] for r in rows] == ["BBCA", "BMRI"]


class TestSecondSnapshotDiff:
    def test_second_snapshot_finds_prior_date(self, conn):
        record_snapshot(conn, "2026-08-03", _cands("BBCA", "BMRI"))
        cands = _cands("BBCA", "BMRI")
        diff = diff_snapshot(conn, "2026-08-04", cands)
        record_snapshot(conn, "2026-08-04", cands)
        assert diff is not None
        assert diff["prior_date"] == "2026-08-03"


class TestAddedRemovedRetained:
    def test_added_ticker_detected(self, conn):
        record_snapshot(conn, "2026-08-03", _cands("BBCA"))
        cands = _cands("BBCA", "GPSO")
        diff = diff_snapshot(conn, "2026-08-04", cands)
        record_snapshot(conn, "2026-08-04", cands)
        assert diff["added"] == ["GPSO"]

    def test_removed_ticker_detected(self, conn):
        record_snapshot(conn, "2026-08-03", _cands("BBCA", "GTSI"))
        cands = _cands("BBCA")
        diff = diff_snapshot(conn, "2026-08-04", cands)
        record_snapshot(conn, "2026-08-04", cands)
        assert diff["removed"] == ["GTSI"]

    def test_retained_ticker_detected(self, conn):
        record_snapshot(conn, "2026-08-03", _cands("BBCA", "BMRI"))
        cands = _cands("BBCA", "BMRI", "GPSO")
        diff = diff_snapshot(conn, "2026-08-04", cands)
        record_snapshot(conn, "2026-08-04", cands)
        assert diff["retained"] == ["BBCA", "BMRI"]

    def test_diff_treats_watchlists_as_sets_not_order(self, conn):
        record_snapshot(conn, "2026-08-03", _cands("ZULA", "AKRA"))
        cands = _cands("AKRA", "ZULA")
        diff = diff_snapshot(conn, "2026-08-04", cands)
        record_snapshot(conn, "2026-08-04", cands)
        assert diff["added"] == []
        assert diff["removed"] == []
        assert diff["retained"] == ["AKRA", "ZULA"]


class TestNoChanges:
    def test_identical_watchlists_produce_no_added_or_removed(self, conn):
        record_snapshot(conn, "2026-08-03", _cands("BBCA", "BMRI"))
        cands = _cands("BBCA", "BMRI")
        diff = diff_snapshot(conn, "2026-08-04", cands)
        record_snapshot(conn, "2026-08-04", cands)
        assert diff["added"] == []
        assert diff["removed"] == []
        assert diff["retained"] == ["BBCA", "BMRI"]


class TestIdempotentRerun:
    def test_same_day_rerun_does_not_duplicate_rows(self, conn):
        record_snapshot(conn, "2026-08-04", _cands("BBCA", "BMRI"))
        record_snapshot(conn, "2026-08-04", _cands("BBCA", "BMRI"))
        rows = conn.execute(
            "SELECT COUNT(*) FROM candidate_watchlist_snapshot WHERE date=?",
            ("2026-08-04",),
        ).fetchone()
        assert rows[0] == 2

    def test_same_day_rerun_updates_in_place(self, conn):
        record_snapshot(conn, "2026-08-04", _cands("BBCA"))
        record_snapshot(conn, "2026-08-04", _cands("BBCA", "GPSO"))
        rows = conn.execute(
            "SELECT ticker FROM candidate_watchlist_snapshot WHERE date=? ORDER BY ticker",
            ("2026-08-04",),
        ).fetchall()
        assert [r[0] for r in rows] == ["BBCA", "GPSO"]


class TestMissingPreviousSnapshot:
    def test_diff_skips_gap_to_most_recent_prior_date(self, conn):
        record_snapshot(conn, "2026-08-01", _cands("BBCA"))
        # 2026-08-02/03 never ran (holiday/outage) — diff must still find 08-01.
        cands = _cands("BBCA", "GPSO")
        diff = diff_snapshot(conn, "2026-08-04", cands)
        record_snapshot(conn, "2026-08-04", cands)
        assert diff["prior_date"] == "2026-08-01"
        assert diff["added"] == ["GPSO"]

    def test_diff_none_when_no_snapshot_ever_recorded(self, conn):
        assert diff_snapshot(conn, "2026-08-04", _cands("BBCA")) is None


class TestEmptyWatchlist:
    def test_record_empty_candidate_list_does_not_error(self, conn):
        record_snapshot(conn, "2026-08-04", [])
        ensure_table(conn)
        rows = conn.execute(
            "SELECT COUNT(*) FROM candidate_watchlist_snapshot WHERE date=?",
            ("2026-08-04",),
        ).fetchone()
        assert rows[0] == 0

    def test_diff_when_today_watchlist_is_empty(self, conn):
        record_snapshot(conn, "2026-08-03", _cands("BBCA"))
        diff = diff_snapshot(conn, "2026-08-04", [])
        record_snapshot(conn, "2026-08-04", [])
        assert diff["added"] == []
        assert diff["removed"] == ["BBCA"]
        assert diff["retained"] == []


class TestTelegramFormatting:
    def test_no_prior_snapshot_message(self, conn):
        msg = build_message("2026-08-04", None, 5)
        assert "WATCHLIST UPDATE" in msg
        assert "2026-08-04" in msg
        assert "Current Watchlist: 5" in msg

    def test_no_changes_message(self, conn):
        diff = {"prior_date": "2026-08-03", "added": [], "removed": [],
                "retained": ["BBCA", "BMRI"], "movements": {}}
        msg = build_message("2026-08-04", diff, 2)
        assert "No watchlist changes today." in msg

    def test_added_removed_retained_sections_rendered(self, conn):
        diff = {"prior_date": "2026-08-03", "added": ["GPSO", "FORE"],
                "removed": ["GTSI"], "retained": ["BBCA"], "movements": {}}
        msg = build_message("2026-08-04", diff, 3)
        assert "Added (2)" in msg
        assert "+ GPSO" in msg
        assert "+ FORE" in msg
        assert "Removed (1)" in msg
        assert "- GTSI" in msg
        assert "Retained (1)" in msg
        assert "BBCA" in msg
        assert "Current Watchlist: 3" in msg

    def test_reason_bullet_shown_for_added_ticker_when_available(self, conn):
        diff = {"prior_date": "2026-08-03", "added": ["GPSO"], "removed": [],
                "retained": [], "movements": {}}
        msg = build_message("2026-08-04", diff, 1, reasons={"GPSO": "Volume expansion"})
        assert "Volume expansion" in msg

    def test_no_fabricated_reason_when_unavailable(self, conn):
        diff = {"prior_date": "2026-08-03", "added": ["GPSO"], "removed": [],
                "retained": [], "movements": {}}
        msg = build_message("2026-08-04", diff, 1)
        # No reasons dict passed — must not invent one.
        lines = msg.splitlines()
        added_idx = next(i for i, l in enumerate(lines) if l.startswith("+ GPSO"))
        assert added_idx == len(lines) - 1 or not lines[added_idx + 1].strip().startswith("•")

    def test_score_movement_shown_for_retained_ticker(self, conn):
        diff = {"prior_date": "2026-08-03", "added": [], "removed": [],
                "retained": ["GPSO"], "movements": {"GPSO": (2.10, 3.40)}}
        msg = build_message("2026-08-04", diff, 1)
        assert "2.10" in msg and "3.40" in msg
