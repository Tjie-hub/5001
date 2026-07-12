"""Append-only persistence for gate decisions (spec §7).

Two research-domain tables in walkforward.db, created idempotently:
- gate_decisions: one row per evaluation (provenance mirrors research_runs).
- gate_evidence:  one row per stage per decision (the "why").

Append-only by rule: no UPDATE, no DELETE. A superseding evaluation is a new
decision_id. Production may READ these (dashboards) but only research WRITES them
(CI-fenced by tests/test_research_data_fence.py).
"""
from __future__ import annotations

import json
import uuid

GATE_DECISIONS_DDL = """
CREATE TABLE IF NOT EXISTS gate_decisions (
    decision_id         TEXT PRIMARY KEY,
    run_id              TEXT,
    strategy_fn         TEXT,
    candidate_hash      TEXT,
    config_hash         TEXT,
    dataset_fingerprint TEXT,
    git_commit          TEXT,
    seed                INTEGER,
    final_state         TEXT NOT NULL,
    failing_stage       TEXT,
    forward_test_rule   TEXT,
    summary_json        TEXT,
    decided_at          TEXT NOT NULL
)
"""

GATE_EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS gate_evidence (
    evidence_id    TEXT PRIMARY KEY,
    decision_id    TEXT NOT NULL,
    stage          TEXT NOT NULL,
    verdict        TEXT NOT NULL,
    statistic_json TEXT,
    threshold_json TEXT
)
"""


def ensure_gate_tables(conn) -> None:
    conn.execute(GATE_DECISIONS_DDL)
    conn.execute(GATE_EVIDENCE_DDL)
    conn.commit()


def persist_decision(conn, decision) -> str:
    """Insert one gate_decisions row + one gate_evidence row per stage. Returns the
    freshly minted decision_id (a new one every call — append-only)."""
    from datetime import datetime

    decision_id = uuid.uuid4().hex
    summary = {r.stage: r.verdict for r in decision.stage_results}
    conn.execute(
        "INSERT INTO gate_decisions (decision_id, run_id, strategy_fn, "
        "candidate_hash, config_hash, dataset_fingerprint, git_commit, seed, "
        "final_state, failing_stage, forward_test_rule, summary_json, decided_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (decision_id, decision.run_id, decision.strategy_fn, decision.candidate_hash,
         decision.config_hash, decision.dataset_fingerprint, decision.git_commit,
         decision.seed, decision.final_state, decision.failing_stage,
         json.dumps(decision.forward_test_rule) if decision.forward_test_rule else None,
         json.dumps(summary),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    for r in decision.stage_results:
        conn.execute(
            "INSERT INTO gate_evidence (evidence_id, decision_id, stage, verdict, "
            "statistic_json, threshold_json) VALUES (?,?,?,?,?,?)",
            (uuid.uuid4().hex, decision_id, r.stage, r.verdict,
             json.dumps(r.statistic, default=float), json.dumps(r.threshold, default=float)))
    conn.commit()
    return decision_id
