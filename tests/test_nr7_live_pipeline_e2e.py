"""Phase 5 fire drill (spec 2026-07-08): drive a synthetic ticker through the
REAL NR7 pipeline — registry → regime → checker → gates → open_trade → monitor
exit — proving the path stays connected (audit C-1 regression guard).

Honesty contract: every gate passes on MERIT (data crafted to satisfy it);
mocks exist only at network seams (flow fetch, agent firm, telegram)."""
import json
import sqlite3
from datetime import date

import numpy as np
import pandas as pd
import pytest
import yaml


def _drill_df(n=260, base=1000.0):
    """Uptrend satisfying detect_regime→BULL (ADX>25, MA-slope>+1%) and
    check_trend→UPTREND, ending with an NR7 setup:
    bar[-2] = narrowest range of trailing 7 with volume >= 0.8x avg5;
    bar[-1] = opens above bar[-2] high (breakout) with volume spike."""
    rng = np.random.default_rng(42)
    closes = base * np.cumprod(1 + 0.004 + rng.normal(0, 0.002, n))
    o = closes * 0.998
    h = closes * 1.012
    l = closes * 0.988
    v = np.full(n, 1_000_000.0)
    df = pd.DataFrame({
        'date': pd.date_range('2025-07-01', periods=n, freq='B').astype(str),
        'open': o, 'high': h, 'low': l, 'close': closes, 'volume': v})
    # bar[-2]: NR7 — squeeze the range to clearly narrowest of trailing 7
    i = n - 2
    c = df.loc[i, 'close']
    df.loc[i, 'high'] = c * 1.001
    df.loc[i, 'low'] = c * 0.999
    df.loc[i, 'open'] = c * 0.9995
    df.loc[i, 'volume'] = 1_000_000.0          # >= 0.8x avg5
    # bar[-1]: breakout — opens above NR7 high, closes higher, volume spike
    j = n - 1
    df.loc[j, 'open'] = c * 1.004
    df.loc[j, 'close'] = c * 1.012
    df.loc[j, 'high'] = c * 1.015
    df.loc[j, 'low'] = c * 1.002
    df.loc[j, 'volume'] = 2_500_000.0
    return df


def test_fixture_regime_is_bull_band():
    from engine.regime_filter import detect_regime
    from engine.indicators import calc_adx
    df = _drill_df()
    assert detect_regime(df) == 'BULL'
    assert float(calc_adx(df, 14).iloc[-1]) > 25


def test_fixture_fires_nr7_checker():
    from engine.strategies import check_nr7_signal
    sig = check_nr7_signal(_drill_df())
    assert sig['has_signal'] is True, sig.get('reason')
    assert sig['details'].get('price') or sig['details'].get('entry')


@pytest.fixture()
def drill_env(tmp_path, monkeypatch):
    """Fixture DB + test registry governing DRILL; production DB_PATHs repointed."""
    import paper_trade as pt
    import monitor as mon
    import scheduler.scanner as scanner
    import engine.registry_loader as rl
    import data.loaders as dl

    db = str(tmp_path / "drill.db")
    for mod in (pt, mon, scanner):
        monkeypatch.setattr(mod, "DB_PATH", db)
    monkeypatch.setattr(dl, "DB_PATH", db)

    # Macro-panic gate: module-level per-day cache — reset so THIS fixture's
    # IHSG decides (a prior test's panic verdict must not leak in).
    monkeypatch.setattr(scanner, "_macro_panic_cache", {})

    pt.init_paper_table()
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE IF NOT EXISTS ohlcv (ticker TEXT, date TEXT, open REAL,"
                 " high REAL, low REAL, close REAL, volume REAL)")
    df = _drill_df()
    df.assign(ticker="DRILL")[['ticker', 'date', 'open', 'high', 'low', 'close',
                               'volume']].to_sql('ohlcv', conn, if_exists='append',
                                                 index=False)
    # Calm IHSG (above 200MA, low vol) so the Daniel-Moskowitz panic gate
    # passes on MERIT (honesty contract: gate 0 of the gauntlet).
    df.assign(ticker="IHSG")[['ticker', 'date', 'open', 'high', 'low', 'close',
                              'volume']].to_sql('ohlcv', conn, if_exists='append',
                                                index=False)
    conn.execute("CREATE TABLE IF NOT EXISTS wf_edge "
                 "(ticker TEXT, strategy TEXT, expectancy_pct REAL)")
    conn.commit(); conn.close()

    # test registry: DRILL in NR7's frozen universe
    reg = tmp_path / "registry"; (reg / "artifacts").mkdir(parents=True)
    (reg / "artifacts" / "u.json").write_text(json.dumps({"tickers": ["DRILL"]}))
    entry = [dict(id="NR7_BULL", version=1, status="APPROVED",
                  strategy_fn="NR7 Breakout", regimes=["BULL_MODERATE", "BULL_STRONG"],
                  universe_artifact="artifacts/u.json", risk_category="t", owner="t",
                  approved="2026-07-08", manifest="m.yaml",
                  requires=dict(data_schema=1, exit_kernel=1, regime_model=1,
                                engine_version=1), changelog="drill")]
    (reg / "edge_registry.yaml").write_text(yaml.safe_dump(entry))
    monkeypatch.setattr(rl, "REGISTRY_PATH", str(reg / "edge_registry.yaml"))
    rl._reset_cache()
    yield {"db": db, "df": df}
    rl._reset_cache()


def test_e2e_signal_to_paper_trade(drill_env, monkeypatch):
    """The seven-gate gauntlet, every function production: selector → checker →
    firm gate (inactive) → check_trend → open_trade ⇒ a paper_trades row."""
    import paper_trade as pt
    from scheduler.scanner import adaptive_strategy_selector, run_agent_firm_gate
    from engine.strategies import check_current_entry_signal
    df = drill_env["df"]

    # Gate 1-2: registry universe + regime map + ADX band + edge gate
    strategies = adaptive_strategy_selector("DRILL", df)
    assert "NR7 Breakout" in strategies, f"selector gave {strategies}"

    # Gate 3: live checker (production dispatch)
    sig = check_current_entry_signal("DRILL", "NR7 Breakout", df)
    assert sig["has_signal"], sig.get("reason")
    entry_price = float(sig["details"]["price"])

    # Gate 4 (flow): network seam — signal arrives flow-confirmed
    result = {"ticker": "DRILL", "strategies": ["NR7 Breakout"],
              "flow": {"score": 3.0, "verdict": "BUY", "smart_money": "YES",
                       "confirmed": True},
              "signal_details": {"NR7 Breakout": sig["details"]}}

    # Gate 5 (agent firm): production gate, firm inactive → passthrough
    import engine.agent_firm as _pkg
    import engine.agent_firm.config  # noqa: F401  (bind submodule before patching)
    import engine.agent_firm.firm    # noqa: F401
    import sys as _sys
    from unittest.mock import MagicMock, patch
    cfg = MagicMock(); cfg.is_active = MagicMock(return_value=False)
    with patch.object(_pkg, "config", cfg), \
         patch.dict(_sys.modules, {"engine.agent_firm.config": cfg}):
        kept = run_agent_firm_gate([result], [result], "2026-07-08", "16:00")
    assert kept and kept[0]["ticker"] == "DRILL"

    # Gate 6: trend gate (production, reads fixture DB)
    assert pt.check_trend("DRILL") == "UPTREND"

    # Gate 7: open_trade — sizing off actual stop distance
    trade = pt.open_trade("DRILL", entry_price, notify=False,
                          strategy="NR7 Breakout")
    assert "error" not in trade, trade.get("error")
    conn = sqlite3.connect(drill_env["db"]); conn.row_factory = sqlite3.Row
    row = dict(conn.execute("SELECT * FROM paper_trades WHERE ticker='DRILL' "
                            "AND status='OPEN'").fetchone())
    conn.close()
    assert row["strategy"] == "NR7 Breakout"
    assert row["lots"] > 0 and row["sl_price"] < entry_price


def test_e2e_monitor_closes_with_net_pnl(drill_env, monkeypatch):
    """After opening, append a TP-hitting bar; monitor._check_trade (production)
    must close via the kernel with NET P&L consistent with the cost model."""
    import paper_trade as pt
    import monitor as mon
    from engine.strategies import check_current_entry_signal
    df = drill_env["df"]

    sig = check_current_entry_signal("DRILL", "NR7 Breakout", df)
    entry_price = float(sig["details"]["price"])
    trade = pt.open_trade("DRILL", entry_price, notify=False, strategy="NR7 Breakout")
    assert "error" not in trade

    conn = sqlite3.connect(drill_env["db"]); conn.row_factory = sqlite3.Row
    row = dict(conn.execute("SELECT * FROM paper_trades WHERE ticker='DRILL' "
                            "AND status='OPEN'").fetchone())
    tp = float(row["tp_price"])
    # next session gaps through TP — dated today so the P0.E2.S1.T2 freshness
    # guard in monitor._check_trade doesn't treat it as a stale bar.
    conn.execute("INSERT INTO ohlcv VALUES ('DRILL', ?, ?, ?, ?, ?, 2000000)",
                 (date.today().isoformat(), tp * 1.001, tp * 1.02, tp * 0.999, tp * 1.01))
    conn.commit(); conn.close()

    res = mon._check_trade(row)
    assert res["should_close"] is True
    assert res["exit_reason"] in ("TP", "TRAIL", "SL", "MA_BREAK", "TIME")

    closed = pt.close_trade(row["id"], float(res["exit_price"]),
                            exit_reason=res["exit_reason"], notify=False)
    # NET P&L: costs on both legs already applied by close_trade (Phase 1C)
    gross_pct = (float(res["exit_price"]) - entry_price) / entry_price * 100
    assert closed["pnl_pct"] < gross_pct            # net < gross, always
    assert closed["pnl_pct"] == pytest.approx(gross_pct - 0.60, abs=0.25)
