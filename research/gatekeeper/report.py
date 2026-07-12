"""Gate outputs (spec §5): a deterministic JSON evidence bundle and a markdown
validation report. Mirrors the shape of research/studies/nr7_generalization_study
._write_results so the artifacts read like the rest of the research corpus.
"""
from __future__ import annotations

import json
from datetime import datetime


def evidence_json(decision) -> dict:
    """Full machine-readable evidence bundle for one decision. Deterministic for a
    given decision (no timestamps inside)."""
    return {
        "final_state": decision.final_state,
        "failing_stage": decision.failing_stage,
        "strategy_fn": decision.strategy_fn,
        "candidate_hash": decision.candidate_hash,
        "config_hash": decision.config_hash,
        "dataset_fingerprint": decision.dataset_fingerprint,
        "git_commit": decision.git_commit,
        "seed": decision.seed,
        "forward_test_rule": decision.forward_test_rule,
        "run_id": decision.run_id,
        "stages": [{"stage": r.stage, "verdict": r.verdict,
                    "statistic": r.statistic, "threshold": r.threshold}
                   for r in decision.stage_results],
    }


def write_report(decision, path: str) -> None:
    """Human-readable markdown validation report."""
    lines = [
        "# Statistical Gatekeeper — Validation Report", "",
        f"Run: {datetime.now().isoformat(timespec='seconds')}", "",
        f"- **strategy:** {decision.strategy_fn}",
        f"- **DECISION: {decision.final_state}**"
        + (f" (failing stage: {decision.failing_stage})" if decision.failing_stage else ""),
        f"- config_hash `{decision.config_hash}` | dataset `{decision.dataset_fingerprint}`"
        f" | commit `{decision.git_commit}` | seed {decision.seed}", "",
        "## Stages", "",
        "| stage | verdict | statistic |", "|---|---|---|",
    ]
    for r in decision.stage_results:
        stat = json.dumps(r.statistic, default=float)
        lines.append(f"| {r.stage} | {r.verdict} | `{stat}` |")
    if decision.forward_test_rule:
        lines += ["", "## Forward-test rule (attached on PROMOTE)", "",
                  "```json", json.dumps(decision.forward_test_rule, indent=2), "```"]
    lines += ["", "## Evidence bundle", "",
              "```json", json.dumps(evidence_json(decision), indent=2, default=float), "```", ""]
    with open(path, "w") as f:
        f.write("\n".join(lines))
