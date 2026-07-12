"""Phase C reporting (spec §5 outputs): a machine-readable evidence bundle and a
human-readable markdown validation report."""
import json

from research.gatekeeper import report
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)


def _decision(state=FinalState.WATCHLIST):
    results = [StageResult("min_sample", Verdict.PASS, {"n_overall": 500}, {}),
               StageResult("confidence_interval", Verdict.WATCH,
                           {"lo": 0.324, "hi": 2.056, "point": 1.197},
                           {"promotion_bar_pct": 0.5}),
               StageResult("deflated_sharpe", Verdict.WATCH,
                           {"dsr": 0.6, "n_trials": 42}, {"min": 0.9})]
    return GateDecision(
        final_state=state, failing_stage=None, stage_results=results,
        candidate_hash="cand123", config_hash="cfg456",
        dataset_fingerprint="fp789", git_commit="abc", seed=20260711,
        forward_test_rule=None, run_id="run1", strategy_fn="NR7 Breakout")


def test_evidence_json_carries_state_provenance_and_every_stage():
    j = report.evidence_json(_decision())
    assert j["final_state"] == FinalState.WATCHLIST
    assert j["strategy_fn"] == "NR7 Breakout"
    assert j["config_hash"] == "cfg456" and j["dataset_fingerprint"] == "fp789"
    stages = {s["stage"] for s in j["stages"]}
    assert stages == {"min_sample", "confidence_interval", "deflated_sharpe"}


def test_evidence_json_is_deterministic():
    a = json.dumps(report.evidence_json(_decision()), sort_keys=True)
    b = json.dumps(report.evidence_json(_decision()), sort_keys=True)
    assert a == b


def test_write_report_emits_markdown_with_verdict_and_stages(tmp_path):
    path = tmp_path / "gate.md"
    report.write_report(_decision(), str(path))
    text = path.read_text()
    assert "WATCHLIST" in text
    assert "NR7 Breakout" in text
    assert "confidence_interval" in text and "deflated_sharpe" in text
