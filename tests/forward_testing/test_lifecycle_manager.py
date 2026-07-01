"""LifecycleManager tests: legal move, idempotency, illegal rejection + audit."""
import sqlite3
import pytest

from forward_testing.lifecycle.states import SignalState, TransitionError
from forward_testing.lifecycle.manager import LifecycleManager


def _seed_generated(repo):
    sid = repo.insert_signal("2026-06-27", "BBCA", "TFB", "SHADOW")
    repo.init_signal_state(sid, SignalState.GENERATED.value)
    return sid


def test_legal_transition_updates_state_and_logs(repo):
    sid = _seed_generated(repo)
    mgr = LifecycleManager(repo)
    new = mgr.transition(sid, SignalState.CANDIDATE, "2026-06-27",
                         actor="ranker", reason="passed-dedupe")
    assert new == SignalState.CANDIDATE
    assert repo.get_signal_state(sid) == "CANDIDATE"
    assert repo.count_transitions(sid) == 1


def test_transition_to_current_state_is_idempotent(repo):
    sid = _seed_generated(repo)
    mgr = LifecycleManager(repo)
    mgr.transition(sid, SignalState.CANDIDATE, "2026-06-27")
    mgr.transition(sid, SignalState.CANDIDATE, "2026-06-27")  # no-op
    assert repo.count_transitions(sid) == 1  # no extra log row


def test_illegal_transition_raises_and_logs_violation(repo, ft_db):
    sid = _seed_generated(repo)
    repo.write_transition(sid, "GENERATED", "ARCHIVED", "2026-06-27")  # fast-forward to ARCHIVED
    mgr = LifecycleManager(repo)
    with pytest.raises(TransitionError):
        mgr.transition(sid, SignalState.HOLDING, "2026-06-27")
    # state must NOT have changed ...
    assert repo.get_signal_state(sid) == "ARCHIVED"
    # ... but a violation row must have been logged
    conn = sqlite3.connect(ft_db)
    v = conn.execute(
        "SELECT COUNT(*) FROM ft_transition_log WHERE signal_id=? AND violation='ILLEGAL'",
        (sid,),
    ).fetchone()[0]
    conn.close()
    assert v == 1


def test_transition_accepts_string_state(repo):
    sid = _seed_generated(repo)
    mgr = LifecycleManager(repo)
    mgr.transition(sid, "CANDIDATE", "2026-06-27")  # string, not enum
    assert repo.get_signal_state(sid) == "CANDIDATE"


def test_current_state_returns_enum(repo):
    sid = _seed_generated(repo)
    mgr = LifecycleManager(repo)
    assert mgr.current_state(sid) == SignalState.GENERATED
