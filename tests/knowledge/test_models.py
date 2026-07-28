"""Phase E models: Status vocabulary + Hypothesis / FailureRecord dataclasses."""
from research.knowledge.models import FailureRecord, Hypothesis, Status


def test_status_values_match_config_vocabulary():
    assert Status.PROPOSED == "PROPOSED"
    assert {s.value for s in Status} == {
        "PROPOSED", "UNDER_TEST", "WATCHLIST",
        "FORWARD_TESTING", "REJECTED", "VALIDATED"}


def test_hypothesis_defaults():
    h = Hypothesis(hypothesis_id="NR7_BULL_v1", title="NR7 BULL breakout edge")
    assert h.status == Status.PROPOSED
    assert h.origin == "manual"
    assert h.rationale == ""


def test_failure_record_requires_source():
    f = FailureRecord(hypothesis_id="H1", reject_reason="no edge", source="manual")
    assert f.failing_stage is None
    assert f.source == "manual"
