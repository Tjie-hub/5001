"""Phase E data models (spec §4, §7). str-valued enum so DB rows and comparisons
stay plain text; dataclasses carry the row shape for the writers in storage.py."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    PROPOSED = "PROPOSED"
    UNDER_TEST = "UNDER_TEST"
    WATCHLIST = "WATCHLIST"
    FORWARD_TESTING = "FORWARD_TESTING"
    REJECTED = "REJECTED"
    VALIDATED = "VALIDATED"


@dataclass
class Hypothesis:
    hypothesis_id: str
    title: str
    status: str = Status.PROPOSED
    rationale: str = ""
    origin: str = "manual"
    dataset_fingerprint: str = None
    config_hash: str = None
    git_commit: str = None
    prereg_ref: str = None
    proposed_at: str = None
    notes: dict = None


@dataclass
class FailureRecord:
    hypothesis_id: str          # may be None for a pre-hypothesis failure
    reject_reason: str
    source: str                 # 'gate' | 'manual'
    failing_stage: str = None
    evidence_ref: str = None    # decision_id (gate) or free ref (manual)
    fingerprint: str = None     # dedupe key
