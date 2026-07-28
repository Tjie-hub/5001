"""The gate decision state machine (spec §6).

Reduces the ordered stage results to exactly one FinalState:
- any FAIL  -> REJECT (naming the first failing stage)
- else any WATCH -> WATCHLIST
- else PROMOTE_TO_FORWARD_TEST

Pure: no I/O, no statistics. The stages already encoded PASS/WATCH/FAIL; this only
combines them, so the promotion rule lives in one obvious place.
"""
from __future__ import annotations

from research.gatekeeper.models import FinalState, Verdict


def decide(stage_results, config=None):
    """Return (final_state, failing_stage). `config` is accepted for a stable
    signature and future rule parametrisation; the base rule needs no thresholds."""
    for r in stage_results:
        if r.verdict == Verdict.FAIL:
            return FinalState.REJECT, r.stage
    for r in stage_results:
        if r.verdict == Verdict.WATCH:
            return FinalState.WATCHLIST, None
    return FinalState.PROMOTE, None
