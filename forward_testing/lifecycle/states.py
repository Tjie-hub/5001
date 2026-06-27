"""Forward-testing signal lifecycle: states, legal transitions, errors.

Pure module — no I/O. The LifecycleManager (manager.py) is the only caller
that decides whether a transition may proceed.
"""
from enum import Enum


class SignalState(str, Enum):
    GENERATED = "GENERATED"
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    OPENED = "OPENED"
    HOLDING = "HOLDING"
    SUSPENDED = "SUSPENDED"
    EXITED = "EXITED"
    ARCHIVED = "ARCHIVED"
    REVIEWED = "REVIEWED"


# Forward-only legal transitions: from_state -> {allowed to_states}.
# Matches the blueprint §3.1 state machine.
LEGAL_TRANSITIONS = {
    SignalState.GENERATED: {SignalState.CANDIDATE, SignalState.ARCHIVED},
    SignalState.CANDIDATE: {SignalState.CONFIRMED, SignalState.ARCHIVED},
    SignalState.CONFIRMED: {SignalState.OPENED, SignalState.ARCHIVED},
    SignalState.OPENED:    {SignalState.HOLDING, SignalState.EXITED},
    SignalState.HOLDING:   {SignalState.EXITED, SignalState.SUSPENDED},
    SignalState.SUSPENDED: {SignalState.HOLDING, SignalState.EXITED},
    SignalState.EXITED:    {SignalState.ARCHIVED},
    SignalState.ARCHIVED:  {SignalState.REVIEWED},
    SignalState.REVIEWED:  set(),
}

INITIAL_STATE = SignalState.GENERATED


class TransitionError(Exception):
    """Raised when an illegal state transition is attempted."""


def is_legal(from_state, to_state) -> bool:
    if from_state not in LEGAL_TRANSITIONS:
        return False
    return to_state in LEGAL_TRANSITIONS[from_state]
