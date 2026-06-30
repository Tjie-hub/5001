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
