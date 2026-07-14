"""Phase E ingestion (spec §5). Hybrid failure feed: auto-derive one failure per
gate REJECT decision (idempotent, deduped on the decision's fingerprint), plus a
manual channel for pre-gate / non-gate deaths."""
from __future__ import annotations

from research.knowledge import storage
from research.knowledge.models import FailureRecord


def ingest_gate_rejects(conn, resolve=None) -> int:
    """Scan gate_decisions for final_state='REJECT'. For each not already in the
    failure_registry, append a failure row (source='gate', fingerprint=decision_id
    so re-ingest is a no-op) and, when `resolve(row)->hypothesis_id` returns an id,
    link both the failure and the gate decision to it. Returns the count of new
    failures. `resolve` defaults to None (unlinked failure, hypothesis_id NULL)."""
    rows = conn.execute(
        "SELECT decision_id, failing_stage, strategy_fn FROM gate_decisions "
        "WHERE final_state='REJECT'").fetchall()
    created = 0
    for decision_id, failing_stage, strategy_fn in rows:
        hyp = resolve({"decision_id": decision_id, "strategy_fn": strategy_fn,
                       "failing_stage": failing_stage}) if resolve else None
        f = FailureRecord(
            hypothesis_id=hyp,
            reject_reason=f"gate REJECT at {failing_stage}" if failing_stage
            else "gate REJECT",
            source="gate", failing_stage=failing_stage,
            evidence_ref=decision_id, fingerprint=decision_id)
        fid = storage.insert_failure(conn, f)
        if fid is not None:
            created += 1
            if hyp:
                storage.add_link(conn, hyp, "failure_registry", fid, decision_id)
        if hyp:
            storage.add_link(conn, hyp, "gate_decisions", decision_id)
    return created


def record_failure(conn, hypothesis_id, reject_reason, failing_stage=None,
                   evidence_ref=None, fingerprint=None):
    """Manual failure channel (source='manual'). Returns the failure_id, or None on
    a dedup no-op. Links to the hypothesis when one is supplied."""
    f = FailureRecord(hypothesis_id=hypothesis_id, reject_reason=reject_reason,
                      source="manual", failing_stage=failing_stage,
                      evidence_ref=evidence_ref, fingerprint=fingerprint)
    fid = storage.insert_failure(conn, f)
    if fid is not None and hypothesis_id:
        storage.add_link(conn, hypothesis_id, "failure_registry", fid, fingerprint)
    return fid
