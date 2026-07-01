"""Purge script clears the shadow cohort and resets affected signals to GENERATED."""
import sqlite3

from forward_testing.adapters.signal_adapter import SignalAdapter
from forward_testing.positions.market_data import MarketDataResolver
from forward_testing.positions.exit_policy import ExitPolicyRegistry
from forward_testing.positions.shadow_manager import ShadowPositionManager
from forward_testing.lifecycle.manager import LifecycleManager
from forward_testing.positions.costs import Costs
from tests.forward_testing.conftest import seed_ohlcv, seed_signal

# 26 flat bars -> ATR 1, plus a D+1 open bar so the position fills.
FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]


def _open_one_position(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_signal(conn, "2026-06-26 16:15", "BBCA", "vol_weighted", direction="BUY")
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()
    SignalAdapter(repo, ft_db).ingest("2026-06-26")
    mgr = ShadowPositionManager(repo, MarketDataResolver(ft_db), ExitPolicyRegistry(),
                                LifecycleManager(repo), ft_db, costs=Costs())
    mgr.run("2026-06-27")  # fill bar 06-27 == run_date -> timely open (not look-ahead)


def test_purge_clears_positions_and_resets_state(ft_db, repo):
    from scripts.ft_purge_smoke_cohort import purge_smoke_cohort
    _open_one_position(ft_db, repo)
    assert len(repo.get_open_shadow_positions()) == 1  # precondition

    n_reset = purge_smoke_cohort(ft_db)

    assert n_reset == 1
    assert repo.get_open_shadow_positions() == []
    with sqlite3.connect(ft_db) as c:
        assert c.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM ft_shadow_position").fetchone()[0] == 0
        states = [r[0] for r in c.execute("SELECT state FROM ft_signal_state").fetchall()]
    assert states == ["GENERATED"]


def test_purge_is_idempotent_on_empty_db(ft_db, repo):
    from scripts.ft_purge_smoke_cohort import purge_smoke_cohort
    assert purge_smoke_cohort(ft_db) == 0  # nothing to purge -> no error
