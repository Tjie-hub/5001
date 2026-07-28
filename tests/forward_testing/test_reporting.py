"""Tests for forward_testing.reporting — the Telegram reporting layer over
existing forward-testing outputs (audit 2026-07-28 Phase 3).

Covers the validation matrix from the Phase 3 spec: no forward-test results,
first execution, new positions, closed positions, continuing positions,
deterministic report generation, empty database, historical replay.
"""
import sqlite3

import pytest

from forward_testing.adapters.signal_adapter import SignalAdapter
from forward_testing.lifecycle.manager import LifecycleManager
from forward_testing.positions.costs import Costs
from forward_testing.positions.exit_policy import ExitPolicyRegistry
from forward_testing.positions.market_data import MarketDataResolver
from forward_testing.positions.shadow_manager import ShadowPositionManager
from forward_testing.reporting import (
    best_worst_trades,
    build_forward_test_message,
    build_forward_test_report,
    get_active_candidate_count,
    get_all_closed_trades,
    get_positions_opened_on,
    get_trades_closed_on,
    win_loss_summary,
)
from tests.forward_testing.conftest import seed_ohlcv, seed_signal


def _open_position(repo, signal_id, ticker, entry_date, entry_price=100.0,
                   highest=None, lowest=None, hold_days=0, direction="LONG"):
    repo.open_shadow_position(
        signal_id=signal_id, ticker=ticker, strategy="TFB", direction=direction,
        entry_date=entry_date, entry_price=entry_price, atr14=1.0,
        sl_price=entry_price - 3, tp_price=entry_price + 6,
        trail_atr_mult=3.0, trail_anchor=entry_price,
        highest_seen=highest if highest is not None else entry_price,
        lowest_seen=lowest if lowest is not None else entry_price,
        signal_date=entry_date, raw_entry_price=entry_price,
    )
    if hold_days:
        repo.update_shadow_position(signal_id, highest or entry_price,
                                    lowest or entry_price, hold_days, entry_date)


def _close_trade(repo, signal_id, ticker, entry_date, exit_date, entry_price,
                 exit_price, exit_reason, hold_days, direction="LONG"):
    pnl = (exit_price - entry_price) / entry_price
    r_mult = pnl / 0.03   # arbitrary but consistent 1R = 3%
    repo.insert_shadow_trade(
        signal_id=signal_id, ticker=ticker, strategy="TFB", direction=direction,
        signal_date=entry_date, entry_date=entry_date, entry_price=entry_price,
        exit_date=exit_date, exit_price=exit_price, exit_reason=exit_reason,
        pnl_pct=pnl, r_multiple=r_mult, hold_days=hold_days,
        mae_pct=min(0.0, pnl), mfe_pct=max(0.0, pnl),
    )


class TestEmptyDatabaseAndFirstExecution:
    def test_empty_database_report_does_not_crash(self, ft_db, repo):
        msg = build_forward_test_report(ft_db, "2026-07-28", repo=repo)
        assert "FORWARD TEST SUMMARY" in msg
        assert "Active Positions: 0" in msg
        assert "New: 0" in msg
        assert "Closed: 0" in msg
        assert "n/a (no closed trades yet)" in msg
        for marker in ("🟢 NEW", "🔴 CLOSED", "🟡 ACTIVE", "📈 BEST", "📉 WORST"):
            assert marker not in msg

    def test_first_execution_has_zero_candidates(self, ft_db, repo):
        assert get_active_candidate_count(repo) == 0

    def test_win_loss_summary_none_with_no_trades(self):
        assert win_loss_summary([]) is None

    def test_best_worst_empty_with_no_trades(self):
        assert best_worst_trades([]) == ([], [])

    def test_message_has_no_lifecycle_sections_when_nothing_happened(self):
        msg = build_forward_test_message("2026-07-28", [], [], [], None, [], [])
        for marker in ("🟢 NEW", "🔴 CLOSED", "🟡 ACTIVE", "📈 BEST", "📉 WORST"):
            assert marker not in msg


class TestNewPositions:
    def test_position_opened_today_is_reported(self, ft_db, repo):
        sid = repo.insert_signal("2026-07-27", "BBCA", "TFB", "SHADOW")
        repo.init_signal_state(sid, "GENERATED")
        _open_position(repo, sid, "BBCA", "2026-07-28", entry_price=4500.0)

        new = get_positions_opened_on(ft_db, "2026-07-28")
        assert len(new) == 1 and new[0]["ticker"] == "BBCA"

        msg = build_forward_test_report(ft_db, "2026-07-28", repo=repo)
        assert "New: 1" in msg
        assert "🟢 NEW" in msg
        assert "BBCA" in msg.split("🟢 NEW")[1]

    def test_position_opened_yesterday_is_not_in_todays_new(self, ft_db, repo):
        sid = repo.insert_signal("2026-07-26", "BBCA", "TFB", "SHADOW")
        repo.init_signal_state(sid, "GENERATED")
        _open_position(repo, sid, "BBCA", "2026-07-27")
        assert get_positions_opened_on(ft_db, "2026-07-28") == []


class TestClosedPositions:
    def test_trade_closed_today_is_reported(self, ft_db, repo):
        sid = repo.insert_signal("2026-07-20", "BBRI", "TFB", "SHADOW")
        _close_trade(repo, sid, "BBRI", "2026-07-21", "2026-07-28", 100.0, 106.0, "TP", 7)

        closed = get_trades_closed_on(ft_db, "2026-07-28")
        assert len(closed) == 1 and closed[0]["exit_reason"] == "TP"

        msg = build_forward_test_report(ft_db, "2026-07-28", repo=repo)
        assert "Closed: 1" in msg
        assert "🔴 CLOSED" in msg
        section = msg.split("🔴 CLOSED")[1]
        assert "BBRI" in section and "TP" in section and "+6.00%" in section

    def test_exit_reason_vocabulary_is_verbatim_not_translated(self, ft_db, repo):
        """'STALE' must appear as-is -- no invented completed/stopped taxonomy."""
        sid = repo.insert_signal("2026-07-01", "GOTO", "TFB", "SHADOW")
        _close_trade(repo, sid, "GOTO", "2026-07-02", "2026-07-28", 100.0, 80.0, "STALE", 26)
        msg = build_forward_test_report(ft_db, "2026-07-28", repo=repo)
        assert "STALE" in msg
        assert "completed" not in msg.lower() and "stopped" not in msg.lower()


class TestActivePositions:
    def test_open_position_is_reported_as_active_with_unrealized_excursion(self, ft_db, repo):
        sid = repo.insert_signal("2026-07-20", "ASII", "TFB", "SHADOW")
        repo.init_signal_state(sid, "GENERATED")
        _open_position(repo, sid, "ASII", "2026-07-21", entry_price=5000.0,
                       highest=5200.0, lowest=4900.0, hold_days=5)

        active = repo.get_open_shadow_positions()
        assert len(active) == 1

        msg = build_forward_test_report(ft_db, "2026-07-28", repo=repo)
        assert "Active Positions: 1" in msg
        assert "🟡 ACTIVE" in msg
        section = msg.split("🟡 ACTIVE")[1]
        assert "ASII" in section
        assert "best +4.00%" in section     # (5200-5000)/5000
        assert "worst -2.00%" in section    # (4900-5000)/5000

    def test_active_position_still_active_after_being_opened_days_ago(self, ft_db, repo):
        sid = repo.insert_signal("2026-06-01", "TLKM", "TFB", "SHADOW")
        _open_position(repo, sid, "TLKM", "2026-06-02", hold_days=40)
        # not opened "today" and not closed -> must still show as ACTIVE, not NEW
        assert get_positions_opened_on(ft_db, "2026-07-28") == []
        active = repo.get_open_shadow_positions()
        assert [p["ticker"] for p in active] == ["TLKM"]


class TestWinLossSummaryAndScoreboard:
    def test_win_loss_summary_computes_from_stored_columns(self):
        trades = [
            {"pnl_pct": 0.06, "r_multiple": 2.0, "hold_days": 7},
            {"pnl_pct": -0.03, "r_multiple": -1.0, "hold_days": 3},
            {"pnl_pct": 0.09, "r_multiple": 3.0, "hold_days": 10},
        ]
        wl = win_loss_summary(trades)
        assert wl["n"] == 3 and wl["wins"] == 2 and wl["losses"] == 1
        assert wl["win_rate"] == pytest.approx(2 / 3)
        assert wl["avg_pnl_pct"] == pytest.approx((0.06 - 0.03 + 0.09) / 3)
        assert wl["avg_hold_days"] == pytest.approx((7 + 3 + 10) / 3)

    def test_best_worst_trades_sorted_by_pnl(self):
        trades = [
            {"ticker": "A", "pnl_pct": 0.10, "r_multiple": 3.0, "hold_days": 5, "exit_reason": "TP"},
            {"ticker": "B", "pnl_pct": -0.05, "r_multiple": -1.5, "hold_days": 2, "exit_reason": "SL"},
            {"ticker": "C", "pnl_pct": 0.02, "r_multiple": 0.5, "hold_days": 1, "exit_reason": "TIME"},
        ]
        best, worst = best_worst_trades(trades, n=2)
        assert [t["ticker"] for t in best] == ["A", "C"]
        assert [t["ticker"] for t in worst] == ["B", "C"]

    def test_best_worst_do_not_crash_with_single_trade(self):
        trades = [{"ticker": "A", "pnl_pct": 0.05, "r_multiple": 1.0, "hold_days": 1, "exit_reason": "TP"}]
        best, worst = best_worst_trades(trades, n=3)
        assert best == trades and worst == trades

    def test_cumulative_scoreboard_reflected_in_report(self, ft_db, repo):
        sid1 = repo.insert_signal("2026-07-01", "AAAA", "TFB", "SHADOW")
        sid2 = repo.insert_signal("2026-07-02", "BBBB", "TFB", "SHADOW")
        _close_trade(repo, sid1, "AAAA", "2026-07-01", "2026-07-10", 100.0, 110.0, "TP", 9)
        _close_trade(repo, sid2, "BBBB", "2026-07-02", "2026-07-11", 100.0, 95.0, "SL", 9)

        msg = build_forward_test_report(ft_db, "2026-07-28", repo=repo)
        assert "1/2 win" in msg and "50% WR" in msg
        assert "📈 BEST" in msg and "AAAA" in msg.split("📈 BEST")[1].split("📉 WORST")[0]
        assert "📉 WORST" in msg and "BBBB" in msg.split("📉 WORST")[1]


class TestDeterminism:
    def test_same_inputs_produce_identical_report(self, ft_db, repo):
        sid = repo.insert_signal("2026-07-20", "BBCA", "TFB", "SHADOW")
        repo.init_signal_state(sid, "GENERATED")
        _open_position(repo, sid, "BBCA", "2026-07-21", entry_price=100.0,
                       highest=104.0, lowest=98.0, hold_days=7)

        msg1 = build_forward_test_report(ft_db, "2026-07-28", repo=repo)
        msg2 = build_forward_test_report(ft_db, "2026-07-28", repo=repo)
        assert msg1 == msg2


class TestHistoricalReplay:
    """Full multi-day pipeline (SignalAdapter -> ShadowPositionManager), same
    pattern as tests/forward_testing/test_phase2_e2e.py, then verify the
    reporting layer reflects the real outcome without recomputing anything."""

    LONG_FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]

    def test_replay_reports_new_then_closed_across_days(self, ft_db, repo):
        conn = sqlite3.connect(ft_db)
        seed_signal(conn, "2026-06-26 16:15", "BBCA", "vol_weighted", direction="BUY")
        seed_ohlcv(conn, "BBCA", self.LONG_FLAT + [
            ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
            ("2026-06-28", 100, 102.5, 99.5, 102, 1000)])   # gap up -> TP
        conn.commit(); conn.close()

        SignalAdapter(repo, ft_db).ingest("2026-06-26")
        mgr = ShadowPositionManager(repo, MarketDataResolver(ft_db), ExitPolicyRegistry(),
                                    LifecycleManager(repo), ft_db, costs=Costs.zero())
        mgr.run("2026-06-27")   # opens (entry_date 06-27)

        msg_open_day = build_forward_test_report(ft_db, "2026-06-27", repo=repo)
        assert "New: 1" in msg_open_day and "Closed: 0" in msg_open_day
        assert "Active Positions: 1" in msg_open_day

        mgr.run("2026-06-28")   # TP exit

        msg_close_day = build_forward_test_report(ft_db, "2026-06-28", repo=repo)
        assert "New: 0" in msg_close_day and "Closed: 1" in msg_close_day
        assert "Active Positions: 0" in msg_close_day
        assert "TP" in msg_close_day.split("🔴 CLOSED")[1]
        assert "1/1 win" in msg_close_day and "100% WR" in msg_close_day
