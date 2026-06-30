"""ShadowPositionManager: open pass (next-open fill, policy levels, lifecycle)."""
import sqlite3
from forward_testing.storage.repo import FTRepo
from forward_testing.lifecycle.manager import LifecycleManager
from forward_testing.positions.market_data import MarketDataResolver
from forward_testing.positions.exit_policy import ExitPolicyRegistry
from forward_testing.positions.costs import Costs
from forward_testing.positions.shadow_manager import ShadowPositionManager
from forward_testing.adapters.signal_adapter import SignalAdapter
from tests.forward_testing.conftest import seed_ohlcv, seed_signal

# Flat bars (100, 100.5, 99.5, 100): TR = 1 -> ATR14 = 1. vol_weighted LONG -> sl 99, tp 102.
FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]


def _mgr(ft_db, costs=None):
    return ShadowPositionManager(
        repo=FTRepo(ft_db), resolver=MarketDataResolver(ft_db),
        registry=ExitPolicyRegistry(), lifecycle=LifecycleManager(FTRepo(ft_db)),
        db_path=ft_db, costs=costs or Costs.zero(),
    )


def _ingest_one(ft_db, repo, ticker, strategy, direction):
    conn = sqlite3.connect(ft_db)
    seed_signal(conn, "2026-06-26 16:15", ticker, strategy, direction=direction)
    conn.commit(); conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-26")
    return repo.get_signals_by_state("GENERATED", track="SHADOW")[0]["id"]


def test_open_pass_fills_at_next_open_and_sets_levels(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")

    _mgr(ft_db).run("2026-06-27")

    pos = repo.get_shadow_position(sid)
    assert pos["status"] == "OPEN"
    assert pos["entry_date"] == "2026-06-27"
    assert pos["entry_price"] == 100.0          # zero costs
    assert pos["atr14"] == 1.0
    assert pos["sl_price"] == 99.0              # 100 - 1.0*1
    assert pos["tp_price"] == 102.0             # 100 + 2.0*1


def test_open_pass_transitions_lifecycle_to_opened(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    _mgr(ft_db).run("2026-06-27")
    assert repo.get_signal_state(sid) == "OPENED"


def test_open_pass_skips_when_next_open_not_yet_available(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT)              # no 06-27 bar
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    _mgr(ft_db).run("2026-06-26")               # D+1 not available
    assert repo.get_signal_state(sid) == "GENERATED"   # deferred
    assert repo.get_shadow_position(sid) is None


def test_open_pass_skips_when_atr_history_insufficient(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    # only ~7 bars up to 06-26 -> atr14 None; but 06-27 bar exists (so next_open resolves)
    seed_ohlcv(conn, "BBCA",
               [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(20, 28)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    _mgr(ft_db).run("2026-06-27")
    assert repo.get_shadow_position(sid) is None        # not opened blind
    assert repo.get_signal_state(sid) == "GENERATED"    # stays deferred


def test_exit_pass_closes_on_tp_and_writes_trade(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),    # entry bar; no exit
        ("2026-06-28", 100, 102.5, 99.5, 102, 1000)])    # high 102.5 >= tp 102 -> TP
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")

    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")   # opens at 100
    mgr.run("2026-06-28")   # TP hit
    trade = repo.get_shadow_trade(sid)
    assert trade["exit_reason"] == "TP"
    assert trade["exit_price"] == 102.0
    assert round(trade["r_multiple"], 6) == 2.0          # (102-100)/1
    assert round(trade["pnl_pct"], 6) == round((102 - 100) / 100, 6)
    assert repo.get_signal_state(sid) == "EXITED"
    assert repo.get_shadow_position(sid)["status"] == "CLOSED"


def test_shadow_trade_records_original_signal_date_not_entry_date(ft_db, repo):
    # The trade ledger must keep the ORIGINAL signal date distinct from the fill
    # date, or the signal->entry latency is lost.
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),     # entry/fill bar
        ("2026-06-28", 100, 102.5, 99.5, 102, 1000)])    # TP
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")   # signal_date 2026-06-26
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")   # fills at 06-27
    mgr.run("2026-06-28")   # TP
    trade = repo.get_shadow_trade(sid)
    assert trade["signal_date"] == "2026-06-26"   # the signal, not the fill
    assert trade["entry_date"] == "2026-06-27"    # fill date is distinct


def test_exit_pass_holds_then_updates_extremes_when_no_exit(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 101, 99.8, 100.5, 1000)])     # no SL/TP hit
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-06-28")
    pos = repo.get_shadow_position(sid)
    assert pos["status"] == "OPEN"
    assert pos["highest_seen"] == 101.0
    assert pos["hold_days"] == 2


def test_missing_bar_holds_without_force_exit(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])  # no 06-28 bar
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-06-28")   # no ohlcv bar -> hold
    assert repo.get_shadow_position(sid)["status"] == "OPEN"
    assert repo.get_shadow_trade(sid) is None


def test_suspended_ticker_holds(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 200, 99.5, 199, 1000)])       # would TP hugely, but suspended
    conn.execute("INSERT INTO suspension_events (ticker,last_normal_date,resume_date,classification) "
                 "VALUES ('BBCA','2026-06-27','2026-07-05','suspension')")
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")   # 06-27 not suspended yet (strict > last_normal_date) -> opens
    mgr.run("2026-06-28")   # suspended -> hold despite TP-bar
    assert repo.get_shadow_position(sid)["status"] == "OPEN"
    assert repo.get_shadow_trade(sid) is None


def test_delisted_position_force_closed_after_staleness_window(ft_db, repo):
    # H2: a ticker that stops producing bars (delisted) must not leave its position
    # OPEN forever -- that never books the loss (survivorship leak). After the
    # staleness window with no new bar, force-close at the last known close.
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "DEAD", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])  # last bar 06-27
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "DEAD", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")                     # opens; ticker then goes dark
    assert repo.get_shadow_position(sid)["status"] == "OPEN"

    mgr.run("2026-07-20")                     # 23 days, no new bars -> delisted -> force-close
    pos = repo.get_shadow_position(sid)
    assert pos["status"] == "CLOSED"
    trade = repo.get_shadow_trade(sid)
    assert trade["exit_reason"] == "STALE"
    assert trade["exit_date"] == "2026-06-27"   # last day it actually traded
    assert trade["exit_price"] == 100.0         # last known close (zero costs in test)
    assert repo.get_signal_state(sid) == "EXITED"


def test_stale_window_not_exceeded_holds(ft_db, repo):
    # Within the staleness window (e.g. a long weekend / holiday cluster), a quiet
    # ticker must NOT be force-closed.
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "QUIET", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "QUIET", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-07-04")                     # 7 days, under the window -> hold
    assert repo.get_shadow_position(sid)["status"] == "OPEN"
    assert repo.get_shadow_trade(sid) is None


def test_suspended_ticker_not_force_closed_even_when_stale(ft_db, repo):
    # A long but ACTIVE suspension must hold (it may resume), not force-close.
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "SUSP", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.execute("INSERT INTO suspension_events (ticker,last_normal_date,resume_date,classification) "
                 "VALUES ('SUSP','2026-06-27','2026-08-30','suspension')")
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "SUSP", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-07-20")                     # stale by days, but suspension still active -> hold
    assert repo.get_shadow_position(sid)["status"] == "OPEN"
    assert repo.get_shadow_trade(sid) is None


def test_open_pass_expires_stale_signal_instead_of_backdating_entry(ft_db, repo):
    # A signal whose fill bar (next_open) falls BEFORE run_date means the engine
    # was not running when the entry should have filled. Opening now at that
    # backdated price fabricates a fill we could not have gotten -> the signal must
    # EXPIRE (archived), not open. (Exits still backfill; entries must be timely.)
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-29", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-30", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")   # signal_date 2026-06-26

    _mgr(ft_db).run("2026-06-30")   # next_open(06-26)=06-29, which is < run_date 06-30

    assert repo.get_shadow_position(sid) is None          # not opened at a backdated price
    assert repo.get_signal_state(sid) == "ARCHIVED"       # expired, not OPENED


def test_open_pass_opens_when_fill_bar_is_run_date(ft_db, repo):
    # Timely fill: signal from the prior session fills at run_date's open. Guard
    # must NOT expire this -- it is the normal daily path.
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-29", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")   # signal_date 2026-06-26

    _mgr(ft_db).run("2026-06-29")   # next_open(06-26)=06-29 == run_date -> open

    assert repo.get_shadow_position(sid) is not None
    assert repo.get_signal_state(sid) == "OPENED"


def test_exit_pass_backfills_skipped_trading_days(ft_db, repo):
    # C2: the engine is run on 06-27 (open) then NOT again until 06-29, skipping
    # the 06-28 bar entirely. The TP on 06-28 must still be detected and booked on
    # 06-28 -- a missed scheduler day must not silently swallow an exit.
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),     # entry bar; no exit
        ("2026-06-28", 100, 102.5, 99.5, 102, 1000),     # high 102.5 >= tp 102 -> TP (SKIPPED run)
        ("2026-06-29", 100, 100.5, 99.5, 100, 1000)])    # flat; would NOT trigger anything
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")

    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")   # opens at 100
    mgr.run("2026-06-29")   # 06-28 never had its own run -> must be backfilled here

    trade = repo.get_shadow_trade(sid)
    assert trade is not None, "skipped 06-28 bar was never evaluated -> TP lost"
    assert trade["exit_reason"] == "TP"
    assert trade["exit_date"] == "2026-06-28"     # booked on the bar that triggered, not 06-29
    assert trade["exit_price"] == 102.0
    assert repo.get_signal_state(sid) == "EXITED"


def test_rerun_same_open_day_does_not_double_count_hold_days(ft_db, repo):
    # H1/C2 watermark: re-running the SAME date on an open position must be a no-op,
    # not a second hold-day increment (duplicate scheduler execution).
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 101, 99.8, 100.5, 1000)])     # no SL/TP -> hold
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-06-28")
    mgr.run("2026-06-28")   # duplicate run of the same date
    pos = repo.get_shadow_position(sid)
    assert pos["status"] == "OPEN"
    assert pos["hold_days"] == 2          # entry bar (1) + 06-28 (2); NOT 3
    assert pos["highest_seen"] == 101.0


def test_rerun_is_idempotent(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 102.5, 99.5, 102, 1000)])
    conn.commit(); conn.close()
    sid = _ingest_one(ft_db, repo, "BBCA", "vol_weighted", "BUY")
    mgr = _mgr(ft_db)
    mgr.run("2026-06-27")
    mgr.run("2026-06-28")   # closes on TP
    mgr.run("2026-06-28")   # re-run -> no-op
    conn = sqlite3.connect(ft_db)
    n_trades = conn.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0]
    conn.close()
    assert n_trades == 1
    assert repo.get_signal_state(sid) == "EXITED"
