"""Phase C pipeline orchestration (spec §3/§5) + the golden NR7 regression.

Candidates are built from fixture trades whose net returns land the target band;
we assert the DECISION, which is robust to small cost offsets. The NR7-representative
case pins the frozen posture: CI straddles the bar + DSR collapses under the full
family => WATCHLIST (never auto-PROMOTE; the forward test decides)."""
import json

import numpy as np

from research import nr7_study as ns
from research.gatekeeper import candidate as cand
from research.gatekeeper import pipeline
from research.gatekeeper.config import load_config
from research.gatekeeper.models import FinalState, ScanCell

CFG = load_config()
_FLAT = ns.round_trip_net_pct(100.0, 100.0)     # net % of a flat round-trip (= -costs)


def _net_exact(mean, sd, n, seed=0):
    """Sample forced to EXACT sample mean/sd, so CI bands are deterministic."""
    z = np.random.default_rng(seed).normal(0.0, 1.0, n)
    z = (z - z.mean()) / z.std()
    return list(mean + sd * z)


def _trades_with_net(net_values, regime="BULL", ticker="AAA"):
    """Back-solve raw_exit (entry=100) so round-trip net == each target exactly.
    round_trip_net_pct is linear in exit: net = A*exit - 100 with A = (100+_FLAT)/100,
    so exit = (net + 100) * 100 / (100 + _FLAT)."""
    out = []
    for i, t in enumerate(net_values):
        raw_exit = (t + 100.0) * 100.0 / (100.0 + _FLAT)
        out.append({"ticker": ticker, "entry_date": f"2025-01-{(i % 27) + 1:02d}",
                    "raw_entry": 100.0, "raw_exit": raw_exit, "regime": regime})
    return out


def _candidate(net_values, scan_sharpes, regime="BULL"):
    trades = _trades_with_net(net_values, regime=regime)
    return cand.assemble_candidate(
        strategy_fn="NR7 Breakout", trades=trades,
        scan_family=[ScanCell(f"c{i}", s, 50) for i, s in enumerate(scan_sharpes)],
        wf={"consistency_pct": 75, "pooled_oos_exp": 1.2, "n_windows": 16},
        oos={"retention": 0.8, "late_exp": 1.0, "late_n": 200},
        target_regime=regime, strategy_config_hash="nr7cfg")


def test_run_gate_promotes_a_clean_strong_candidate(tmp_path):
    net = _net_exact(3.0, 1.0, 400)
    d = pipeline.run_gate(_candidate(net, [0.05, 0.06, 0.07]),
                          CFG, db_path=str(tmp_path / "g.db"))
    assert d.final_state == FinalState.PROMOTE
    assert d.forward_test_rule["min_n"] == 15          # frozen rule attached


def test_run_gate_watchlists_nr7_representative_candidate(tmp_path):
    # NR7 BULL profile: point ~+1.2%/trade, 95% CI ~[+0.32,+2.06] (mean 1.2, sd ~8.2)
    # -> CI straddles +0.50%; 42-cell dispersed family collapses DSR.
    net = _net_exact(1.2, 8.2, 333)
    scan = list(np.random.default_rng(1).normal(0.1, 0.15, 42))
    d = pipeline.run_gate(_candidate(net, scan), CFG, db_path=str(tmp_path / "g.db"))
    assert d.final_state == FinalState.WATCHLIST
    verdicts = {r.stage: r.verdict for r in d.stage_results}
    assert verdicts["confidence_interval"] == "WATCH"
    assert verdicts["deflated_sharpe"] == "WATCH"
    assert verdicts["multiplicity"] == "PASS"          # edge still significant vs 0
    assert d.forward_test_rule is None                 # not promoted


def test_run_gate_rejects_when_sample_insufficient(tmp_path):
    d = pipeline.run_gate(_candidate([2.0] * 20, [0.05, 0.06]),
                          CFG, db_path=str(tmp_path / "g.db"))
    assert d.final_state == FinalState.REJECT
    assert d.failing_stage == "min_sample"


def test_run_gate_is_deterministic(tmp_path):
    net = list(np.random.default_rng(7).normal(0.9, 5.0, 333))
    scan = list(np.random.default_rng(1).normal(0.1, 0.15, 42))
    c = _candidate(net, scan)
    from research.gatekeeper.report import evidence_json
    a = evidence_json(pipeline.run_gate(c, CFG, db_path=str(tmp_path / "a.db")))
    b = evidence_json(pipeline.run_gate(c, CFG, db_path=str(tmp_path / "b.db")))
    a.pop("run_id"); b.pop("run_id")                   # run_id is provenance, not stats
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_run_gate_persists_decision_and_tracks_run(tmp_path):
    from data.db import connect
    db = str(tmp_path / "g.db")
    net = _net_exact(3.0, 1.0, 400)
    d = pipeline.run_gate(_candidate(net, [0.05, 0.06, 0.07]), CFG, db_path=db)
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) FROM gate_decisions").fetchone()[0] == 1
    kinds = [r[0] for r in conn.execute("SELECT kind FROM research_runs")]
    assert "gate-eval" in kinds
    assert d.run_id is not None
    conn.close()
