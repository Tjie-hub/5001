"""Pure lifecycle rules: legal forward transitions, illegal reversals, terminal."""
from forward_testing.lifecycle.states import (
    SignalState, LEGAL_TRANSITIONS, TransitionError, is_legal,
)


def test_all_forward_transitions_legal():
    assert is_legal(SignalState.GENERATED, SignalState.CANDIDATE)
    assert is_legal(SignalState.CANDIDATE, SignalState.CONFIRMED)
    assert is_legal(SignalState.CONFIRMED, SignalState.OPENED)
    assert is_legal(SignalState.OPENED, SignalState.HOLDING)
    assert is_legal(SignalState.HOLDING, SignalState.EXITED)
    assert is_legal(SignalState.EXITED, SignalState.ARCHIVED)
    assert is_legal(SignalState.ARCHIVED, SignalState.REVIEWED)


def test_reversal_transitions_illegal():
    assert not is_legal(SignalState.CONFIRMED, SignalState.GENERATED)
    assert not is_legal(SignalState.ARCHIVED, SignalState.HOLDING)
    assert not is_legal(SignalState.REVIEWED, SignalState.ARCHIVED)


def test_skip_transitions_illegal():
    # cannot jump GENERATED straight to HOLDING
    assert not is_legal(SignalState.GENERATED, SignalState.HOLDING)


def test_suspension_round_trip_legal():
    assert is_legal(SignalState.HOLDING, SignalState.SUSPENDED)
    assert is_legal(SignalState.SUSPENDED, SignalState.HOLDING)
    assert is_legal(SignalState.SUSPENDED, SignalState.EXITED)


def test_reviewed_is_terminal():
    assert LEGAL_TRANSITIONS[SignalState.REVIEWED] == set()
    assert not is_legal(SignalState.REVIEWED, SignalState.GENERATED)


def test_enum_is_string():
    assert SignalState.GENERATED == "GENERATED"


def test_generated_to_opened_is_legal_shadow_bypass():
    # §3.4 dual-track: SHADOW signals go GENERATED -> OPENED directly (no CONFIRMED).
    assert is_legal(SignalState.GENERATED, SignalState.OPENED)


def test_generated_to_holding_still_illegal():
    # OPENED is allowed; HOLDING is still not (must pass through OPENED).
    assert not is_legal(SignalState.GENERATED, SignalState.HOLDING)
