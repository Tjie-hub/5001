"""Phase-2 end-to-end: ingest -> open -> exit across a LONG (TP) and a SHORT (TRAIL)."""
import sqlite3
from forward_testing.adapters.signal_adapter import SignalAdapter
from forward_testing.positions.market_data import MarketDataResolver
from forward_testing.positions.exit_policy import ExitPolicyRegistry
from forward_testing.positions.costs import Costs
from forward_testing.positions.shadow_manager import ShadowPositionManager
from forward_testing.storage.repo import FTRepo
from forward_testing.lifecycle.manager import LifecycleManager
from tests.forward_testing.conftest import seed_ohlcv, seed_signal

LONG_FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]   # ATR 1
SHORT_FLAT = [("2026-06-%02d" % d, 200, 200.5, 199.5, 200, 1000) for d in range(1, 27)]  # ATR 1


def test_phase2_full_flow_long_tp_and_short_trail(ft_db, repo):
    conn = sqlite3.connect(ft_db)
    seed_signal(conn, "2026-06-26 16:15", "BBCA", "vol_weighted", direction="BUY")
    seed_signal(conn, "2026-06-26 16:15", "UNVR", "distribution", direction="SELL")
    # LONG: entry 100 on 06-27, TP 102 on 06-28.
    seed_ohlcv(conn, "BBCA", LONG_FLAT + [
        ("2026-06-27", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-28", 100, 102.5, 99.5, 102, 1000)])
    # SHORT distribution (trail 3xATR=3): entry 200 on 06-27; price falls (lowest 195 ->
    # stop 198) then rebounds; 06-28 high 199 >= 198 -> TRAIL at 198 (a small short win).
    seed_ohlcv(conn, "UNVR", SHORT_FLAT + [
        ("2026-06-27", 200, 196, 195, 195.5, 1000),   # lowest 195 -> stop 198; high 196<198 hold
        ("2026-06-28", 195.5, 199, 195, 198, 1000)])   # high 199 >= 198 -> TRAIL @ 198
    conn.commit(); conn.close()

    SignalAdapter(repo, ft_db).ingest("2026-06-26")   # 2 GENERATED SHADOW signals
    mgr = ShadowPositionManager(repo, MarketDataResolver(ft_db), ExitPolicyRegistry(),
                                LifecycleManager(repo), ft_db, costs=Costs.zero())
    mgr.run("2026-06-27")   # open both; entry-bar no exit
    mgr.run("2026-06-28")   # BBCA -> TP; UNVR -> TRAIL

    conn = sqlite3.connect(ft_db)
    conn.row_factory = sqlite3.Row
    trades = {r["ticker"]: dict(r) for r in conn.execute("SELECT * FROM ft_shadow_trade").fetchall()}
    conn.close()

    assert set(trades) == {"BBCA", "UNVR"}
    assert trades["BBCA"]["exit_reason"] == "TP"
    assert trades["BBCA"]["direction"] == "LONG"
    assert round(trades["BBCA"]["r_multiple"], 6) == 2.0
    assert trades["UNVR"]["exit_reason"] == "TRAIL"
    assert trades["UNVR"]["direction"] == "SHORT"
    assert round(trades["UNVR"]["exit_price"], 6) == 198.0
    assert round(trades["UNVR"]["r_multiple"], 6) == round((200 - 198) / 3, 6)   # +0.667R

    # idempotent re-run
    mgr.run("2026-06-28")
    conn = sqlite3.connect(ft_db)
    assert conn.execute("SELECT COUNT(*) FROM ft_shadow_trade").fetchone()[0] == 2
    conn.close()
