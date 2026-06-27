"""Phase-1 end-to-end: source -> adapter -> lifecycle, with audit + idempotency."""
import sqlite3

from forward_testing.adapters.signal_adapter import SignalAdapter
from forward_testing.lifecycle.manager import LifecycleManager
from forward_testing.lifecycle.states import SignalState


def test_full_phase1_flow(ft_db, repo):
    # seed two screener signals for the day
    conn = sqlite3.connect(ft_db)
    conn.executemany(
        "INSERT INTO scheduled_signals "
        "(scan_time, ticker, strategies, flow_score, signal_direction) VALUES (?,?,?,?,?)",
        [
            ("2026-06-27 16:15", "BBCA", "TFB", 60, "BUY"),
            ("2026-06-27 16:15", "TLKM", "MTF_REVERSAL", 45, "BUY"),
        ],
    )
    conn.commit()
    conn.close()

    run_id = repo.create_run("2026-06-27", kind="EOD")
    adapter = SignalAdapter(repo, ft_db)
    mgr = LifecycleManager(repo)

    ingested = adapter.ingest("2026-06-27")
    assert ingested == 2

    # both start at GENERATED
    conn = sqlite3.connect(ft_db)
    sids = [r[0] for r in conn.execute(
        "SELECT id FROM ft_signal ORDER BY ticker").fetchall()]
    conn.close()
    assert [mgr.current_state(s) for s in sids] == [SignalState.GENERATED,
                                                     SignalState.GENERATED]

    # advance both to CANDIDATE
    for s in sids:
        mgr.transition(s, SignalState.CANDIDATE, "2026-06-27", actor="ranker")
    assert [mgr.current_state(s) for s in sids] == [SignalState.CANDIDATE,
                                                     SignalState.CANDIDATE]

    # re-ingest must be a no-op (idempotent)
    assert adapter.ingest("2026-06-27") == 0

    # every signal has exactly: 1 GENERATED (adapter) + 1 CANDIDATE (manager) = 2 transitions
    for s in sids:
        assert repo.count_transitions(s) == 2

    repo.finish_run(run_id, "OK")
    conn = sqlite3.connect(ft_db)
    status = conn.execute("SELECT status FROM ft_run WHERE id=?", (run_id,)).fetchone()[0]
    conn.close()
    assert status == "OK"
