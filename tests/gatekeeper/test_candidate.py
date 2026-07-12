"""Phase C candidate assembly + ctx bridge (spec §3/§6). Pure pieces tested with a
synthetic candidate — no DB, no backtest."""
from research.gatekeeper import candidate as cand
from research.gatekeeper.config import load_config
from research.gatekeeper.models import Candidate, ScanCell

CFG = load_config()


def _trade(ticker, date, entry, exit_, regime):
    return {"ticker": ticker, "entry_date": date, "raw_entry": entry,
            "raw_exit": exit_, "regime": regime}


def _candidate():
    trades = ([_trade("AAA", "2025-01-01", 100, 110, "BULL") for _ in range(5)]
              + [_trade("BBB", "2025-02-01", 100, 99, "BEAR") for _ in range(3)]
              + [_trade("CCC", "2025-03-01", 100, 98, "SIDEWAYS") for _ in range(4)])
    return cand.assemble_candidate(
        strategy_fn="NR7 Breakout", trades=trades,
        scan_family=[ScanCell("BULL", 0.15, 5), ScanCell("BEAR", 0.04, 3),
                     ScanCell("SIDEWAYS", -0.15, 4)],
        wf={"consistency_pct": 70, "pooled_oos_exp": 1.1, "n_windows": 16},
        oos={"retention": 0.7, "late_exp": 0.9, "late_n": 120},
        target_regime="BULL", strategy_config_hash="deadbeef")


def test_assemble_groups_trades_into_regime_cells():
    c = _candidate()
    assert isinstance(c, Candidate)
    assert set(c.regime_cells) == {"BULL", "BEAR", "SIDEWAYS"}
    assert len(c.regime_cells["BULL"]) == 5
    assert c.meta["target_regime"] == "BULL"


def test_candidate_hash_is_deterministic_and_sensitive():
    c1, c2 = _candidate(), _candidate()
    assert cand.candidate_hash(c1) == cand.candidate_hash(c2)
    c2.meta["strategy_config_hash"] = "different"
    assert cand.candidate_hash(c1) != cand.candidate_hash(c2)


def test_build_ctx_targets_governing_cell_and_full_family():
    ctx = cand.build_ctx(_candidate(), CFG)
    assert ctx["governing_cell"] == "BULL"
    assert len(ctx["claim_net"]) == 5                     # BULL cell only
    assert ctx["n_overall"] == 12
    assert ctx["cell_n"]["BULL"] == 5
    # family spans the pre-registered regimes; governing_index points at BULL
    fam = CFG.multiplicity["family"]["regimes"]
    assert len(ctx["family_pvalues"]) == len(fam)
    assert ctx["governing_index"] == fam.index("BULL")
    assert ctx["scan_sharpes"] == [0.15, 0.04, -0.15]
    assert ctx["wf"]["consistency_pct"] == 70 and ctx["oos"]["retention"] == 0.7
