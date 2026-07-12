"""Phase C live-corpus builder assembly (spec §3). collect_fn is injected so the
grouping / scan-family / target-selection / wf+oos derivation is tested without a
5-year backtest."""
from research.gatekeeper import candidate as cand
from research.gatekeeper.config import load_config
from research.gatekeeper.models import Candidate

CFG = load_config()


def _mk(n, regime, base_exit, ticker, month):
    # entry dates spread across the month so cv_split has an early/late boundary
    return [{"ticker": ticker, "entry_date": f"2025-{month:02d}-{(i % 27) + 1:02d}",
             "raw_entry": 100.0, "raw_exit": base_exit, "regime": regime}
            for i in range(n)]


def test_build_candidate_groups_scans_and_targets_best_regime():
    # BULL clearly positive (exit 105), SIDEWAYS clearly negative (exit 97)
    bull = _mk(150, "BULL", 105.0, "AAA", 1) + _mk(150, "BULL", 106.0, "AAA", 6)
    side = _mk(120, "SIDEWAYS", 97.0, "BBB", 2)

    def fake_collect(conn, ticker, config):
        return bull if ticker == "AAA" else (side if ticker == "BBB" else [])

    c = cand.build_candidate(conn=None, strategy_fn="NR7 Breakout",
                             universe=["AAA", "BBB", "CCC"], config=CFG,
                             collect_fn=fake_collect)

    assert isinstance(c, Candidate)
    assert set(c.regime_cells) == {"BULL", "SIDEWAYS"}
    assert c.meta["target_regime"] == "BULL"                  # best pooled expectancy
    assert {s.label for s in c.scan_family} == {"BULL", "SIDEWAYS"}
    # scan family carries the per-cell Sharpe count = the real trial count (no proxy)
    assert len(c.scan_family) == 2
    assert "consistency_pct" in c.meta["wf"] and "pooled_oos_exp" in c.meta["wf"]
    assert "retention" in c.meta["oos"] and "late_exp" in c.meta["oos"]


def test_build_candidate_scopes_wf_oos_to_governing_regime():
    # BULL positive, SIDEWAYS a big negative drag. WF/OOS must judge the SAME claim
    # the CI/PSR/DSR stages do (the governing BULL cell), not the unscoped pool —
    # otherwise a regime-scoped edge is judged on regimes it never trades.
    bull = _mk(150, "BULL", 105.0, "AAA", 1) + _mk(150, "BULL", 106.0, "AAA", 6)
    side = _mk(400, "SIDEWAYS", 90.0, "BBB", 2)      # heavy negative pool drag

    def fake_collect(conn, ticker, config):
        return bull if ticker == "AAA" else (side if ticker == "BBB" else [])

    c = cand.build_candidate(conn=None, strategy_fn="NR7 Breakout",
                             universe=["AAA", "BBB"], config=CFG, collect_fn=fake_collect)
    assert c.meta["target_regime"] == "BULL"
    assert c.meta["wf"]["pooled_oos_exp"] > 0        # BULL-scoped, not dragged negative
    assert c.meta["oos"]["late_exp"] > 0


def test_wf_summary_uses_real_window_units_engine_consistency():
    # Engine definition: consistency = profitable windows / windows tested, a window
    # profitable if its pooled return > 0. Three quarterly windows, 2 up / 1 down.
    def win(tag, exit_):
        return [{"ticker": "AAA", "entry_date": "2025-01-01", "raw_entry": 100.0,
                 "raw_exit": exit_, "regime": "BULL", "window": tag} for _ in range(5)]
    trades = (win("AAA@2025-01-01", 105.0) + win("AAA@2025-04-01", 106.0)
              + win("AAA@2025-07-01", 97.0))          # last window loses
    r = cand._wf_summary(trades)
    assert r["windows_tested"] == 3                   # real windows, NOT one calendar month
    assert r["windows_profitable"] == 2
    assert round(r["consistency_pct"], 1) == 66.7
