"""Phase-1 exit criterion (Audit/REMEDIATION_PLAN.md): Research = Paper = Live.

One synthetic momentum trade driven through all three execution paths:
  (a) backtest  — engine.strategies.run_strategy (kernel exits, net P&L)
  (b) SHADOW    — forward_testing ShadowPositionManager (kernel exits, net P&L)
  (c) paper     — paper_trade open_trade/close_trade at the same raw fills
All three must report the same net return.

Scenario A (TP): flat 1000s, signal bar 18, entry bar 19 @ open 1000,
bar 20 high 1060 hits TP = entry_net + 2.4xATR(20) = 1050.5 -> fill 1050.5.
Scenario B (gap SL): bar 20 opens 940, gapping through SL 978.5 -> fill 940.
"""
import sqlite3

import numpy as np
import pandas as pd
import pytest


ENTRY_RAW = 1000.0


def _bars(scenario):
    """21 daily bars: 0-18 flat (ATR14 = 20), signal at 18, entry bar 19,
    decision bar 20."""
    n = 21
    dates = [f"2026-03-{d:02d}" for d in range(1, n + 1)]
    bars = []
    for i in range(n):
        bars.append([dates[i], 1000.0, 1010.0, 990.0, 1000.0, 1_000_000.0])
    bars[19] = [dates[19], 1000.0, 1010.0, 990.0, 1005.0, 1_000_000.0]  # entry bar
    if scenario == "TP":
        bars[20] = [dates[20], 1030.0, 1060.0, 1020.0, 1055.0, 1_000_000.0]
    else:  # gap SL
        bars[20] = [dates[20], 940.0, 950.0, 930.0, 945.0, 1_000_000.0]
    return dates, bars


def _df(bars):
    return pd.DataFrame(
        [b[1:] for b in bars],
        columns=["open", "high", "low", "close", "volume"],
    ).assign(date=pd.to_datetime([b[0] for b in bars]))


def _backtest_return(bars):
    from engine.strategies import run_strategy
    df = _df(bars)
    signals = pd.Series(False, index=df.index)
    signals.iloc[18] = True
    res = run_strategy(df, signals, atr_sl_mult=1.2, atr_tp_mult=2.4,
                       min_rr=2.0, trail_sl=True, strategy_name="momentum")
    assert len(res["trades"]) == 1, res["trades"]
    t = res["trades"][0]
    return t.pnl_pct / 100.0, t.exit_reason


def _shadow_return(tmp_path, dates, bars):
    from forward_testing.storage.db import init_ft_tables
    from forward_testing.storage.repo import FTRepo
    from forward_testing.adapters.signal_adapter import SignalAdapter
    from forward_testing.positions.market_data import MarketDataResolver
    from forward_testing.positions.shadow_manager import ShadowPositionManager
    from forward_testing.lifecycle.manager import LifecycleManager
    from engine.exits import ExitPolicyRegistry
    from engine.exits.costs import Costs

    db = str(tmp_path / "conf.db")
    init_ft_tables(db)
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT, ticker TEXT, strategies TEXT,
            flow_score INTEGER, flow_verdict TEXT, smart_money TEXT,
            signal_reasons TEXT, signal_direction TEXT DEFAULT 'BUY'
        );
        CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL,
                            low REAL, close REAL, volume REAL);
        CREATE TABLE suspension_events (ticker TEXT, last_normal_date TEXT,
            resume_date TEXT, missing_td INTEGER, gap_pct REAL,
            classification TEXT, detected_at TEXT);
    """)
    conn.executemany("INSERT INTO ohlcv VALUES ('CONF',?,?,?,?,?,?)",
                     [tuple(b) for b in bars])
    conn.execute(
        "INSERT INTO scheduled_signals (scan_time, ticker, strategies, flow_score)"
        " VALUES (?, 'CONF', 'momentum', 1)", (f"{dates[18]} 16:00",))
    conn.commit()
    conn.close()

    repo = FTRepo(db)
    SignalAdapter(repo, db).ingest(dates[18])
    mgr = ShadowPositionManager(repo, MarketDataResolver(db),
                                ExitPolicyRegistry(), LifecycleManager(repo),
                                db, costs=Costs())
    mgr.run(dates[19])
    mgr.run(dates[20])

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT pnl_pct, exit_reason FROM ft_shadow_trade WHERE ticker='CONF'"
    ).fetchone()
    conn.close()
    assert row is not None, "shadow trade did not close"
    return float(row[0]), row[1]


def _paper_return(tmp_path, monkeypatch, exit_raw):
    import paper_trade as pt
    db = str(tmp_path / "paper.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL,"
                 " high REAL, low REAL, close REAL, volume REAL)")
    for i in range(20):   # ATR14 = 20, same as the research bars
        conn.execute("INSERT INTO ohlcv VALUES ('CONF',?,1000,1010,990,1000,1000000)",
                     (f"2026-02-{i+1:02d}",))
    conn.commit()
    conn.close()
    res = pt.open_trade("CONF", ENTRY_RAW, strategy="momentum", notify=False)
    assert "error" not in res, res
    out = pt.close_trade(res["id"], exit_raw, "CONFORMANCE", notify=False)
    return out["pnl_pct"] / 100.0


@pytest.mark.parametrize("scenario,exit_reason,exit_raw", [
    ("TP", "TP", None),          # fill = TP level, computed below
    # momentum's policy trails from entry (trail_enable=True), so the kernel
    # labels the initial-stop gap-out TRAIL, not SL — in both engines.
    ("GAPSL", "TRAIL", 940.0),   # gap through stop -> fill at open
])
def test_backtest_shadow_paper_conform(tmp_path, monkeypatch,
                                       scenario, exit_reason, exit_raw):
    dates, bars = _bars(scenario)

    bt_ret, bt_reason = _backtest_return(bars)
    sh_ret, sh_reason = _shadow_return(tmp_path, dates, bars)

    assert bt_reason == exit_reason
    assert sh_reason == exit_reason
    # Research == SHADOW to float precision (same kernel, same costs, same
    # next-open entry, same entry-bar evaluation).
    assert bt_ret == pytest.approx(sh_ret, rel=1e-9)

    # Paper at the SAME raw fills must report the same net return
    # (paper rounds pnl_pct to 2dp -> tolerance 0.01pp).
    if exit_raw is None:
        from engine.exits.costs import apply_costs
        entry_net = apply_costs(ENTRY_RAW, "BUY")           # 1002.5
        exit_raw_fill = entry_net + 2.4 * 20.0              # TP level = 1050.5
    else:
        exit_raw_fill = exit_raw
    pp_ret = _paper_return(tmp_path, monkeypatch, exit_raw_fill)
    assert pp_ret == pytest.approx(bt_ret, abs=1e-4)
