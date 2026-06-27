"""LifecycleManager — the only component that decides a transition may proceed.

Guarded: rejects illegal transitions (after logging a violation).
Idempotent: transitioning to the current state is a no-op (no log row).
"""
from forward_testing.lifecycle.states import (
    SignalState, TransitionError, is_legal,
)


class LifecycleManager:
    def __init__(self, repo):
        self.repo = repo

    def current_state(self, signal_id):
        s = self.repo.get_signal_state(signal_id)
        return SignalState(s) if s else None

    def transition(self, signal_id, to_state, run_date, actor=None, reason=None):
        """Move signal_id to to_state.

        Returns the new SignalState. Raises TransitionError on illegal moves.
        Idempotent: if the signal is already in to_state, returns it with no log.
        """
        to_state = SignalState(to_state)
        current = self.current_state(signal_id)
        if current is None:
            raise TransitionError(f"signal {signal_id} has no state row")
        if current == to_state:
            return current  # idempotent no-op
        if not is_legal(current, to_state):
            self.repo.log_violation(
                signal_id, current.value, to_state.value, run_date,
                actor=actor, reason=reason,
            )
            raise TransitionError(
                f"illegal transition {current.value} -> {to_state.value} "
                f"for signal {signal_id}"
            )
        self.repo.write_transition(
            signal_id, current.value, to_state.value, run_date,
            actor=actor, reason=reason,
        )
        return to_state
