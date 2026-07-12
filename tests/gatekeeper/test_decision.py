"""Phase C decision state machine (spec §5/§6): reduce [StageResult] to one
FinalState. Rule: any FAIL -> REJECT (first failing stage); else any WATCH ->
WATCHLIST; else PROMOTE_TO_FORWARD_TEST."""
from research.gatekeeper import decision as dec
from research.gatekeeper.models import FinalState, StageResult, Verdict


def _sr(stage, verdict):
    return StageResult(stage=stage, verdict=verdict, statistic={}, threshold={})


def test_all_pass_promotes():
    results = [_sr(f"s{i}", Verdict.PASS) for i in range(8)]
    state, failing = dec.decide(results, config=None)
    assert state == FinalState.PROMOTE
    assert failing is None


def test_any_watch_without_fail_is_watchlist():
    results = [_sr("s1", Verdict.PASS), _sr("s2", Verdict.WATCH),
               _sr("s5", Verdict.PASS)]
    state, failing = dec.decide(results, config=None)
    assert state == FinalState.WATCHLIST
    assert failing is None


def test_any_fail_rejects_with_first_failing_stage():
    results = [_sr("s1", Verdict.PASS), _sr("multiplicity", Verdict.FAIL),
               _sr("psr", Verdict.FAIL)]
    state, failing = dec.decide(results, config=None)
    assert state == FinalState.REJECT
    assert failing == "multiplicity"          # first fail wins


def test_fail_takes_precedence_over_watch():
    results = [_sr("s1", Verdict.WATCH), _sr("s2", Verdict.FAIL)]
    state, failing = dec.decide(results, config=None)
    assert state == FinalState.REJECT
    assert failing == "s2"
