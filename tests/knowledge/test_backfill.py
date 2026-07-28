"""Phase E backfill (spec §8): seed NR7_BULL_v1 + NR7_BULL_LOWLIQ_v1, link their
existing gate_decisions/regime_profiles, and leave the seeded corpus orphan-free."""
from data.db import connect
from research.gatekeeper import storage as gk
from research.gatekeeper.models import (FinalState, GateDecision, StageResult,
                                        Verdict)
from research.knowledge import backfill, storage, trace
from research.regime import storage as rg


def _seeded_corpus(conn):
    # a NR7 REJECT gate decision + a NR7 regime profile (the real evidence shapes)
    gk.ensure_gate_tables(conn)
    d = GateDecision(final_state=FinalState.REJECT, failing_stage="walk_forward",
                     stage_results=[StageResult("walk_forward", Verdict.FAIL, {}, {})],
                     candidate_hash="c", config_hash="cfg", dataset_fingerprint="fp",
                     git_commit="g", seed=1, forward_test_rule=None, run_id="run1",
                     strategy_fn="NR7 Breakout")
    gk.persist_decision(conn, d)
    rg.ensure_profile_tables(conn)
    conn.execute("INSERT INTO regime_profiles (profile_id, strategy_fn, created_at) "
                 "VALUES ('prof1','NR7 Breakout','2026-07-10')")
    conn.commit()


def test_backfill_seeds_and_leaves_no_orphans(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    _seeded_corpus(conn)
    summary = backfill.seed_known_hypotheses(conn)
    assert summary["hypotheses"] >= 2
    # NR7_BULL_v1 traces to its gate decision + regime profile + failure
    bundle = trace.trace(conn, "NR7_BULL_v1")
    assert bundle["decisions"] and bundle["regime_profiles"] and bundle["failures"]
    # the seeded corpus has no orphan gate_decisions
    assert trace.orphan_report(conn)["gate_decisions"] == []
    conn.close()


def test_backfill_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    storage.ensure_knowledge_tables(conn)
    _seeded_corpus(conn)
    backfill.seed_known_hypotheses(conn)
    backfill.seed_known_hypotheses(conn)                # must not raise / duplicate
    n = conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0]
    assert n == 2
    conn.close()
