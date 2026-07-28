"""Shared value types for the gatekeeper (spec §6).

State/verdict names are plain strings so they serialize directly into the
gate_decisions / gate_evidence TEXT columns and the evidence JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class FinalState:
    REJECT = "REJECT"
    WATCHLIST = "WATCHLIST"
    PROMOTE = "PROMOTE_TO_FORWARD_TEST"


class Verdict:
    PASS = "PASS"
    WATCH = "WATCH"
    FAIL = "FAIL"


@dataclass
class ScanCell:
    """One cell of the pre-registered scan family; `sharpe` from statistics.sharpe.
    The set of these supplies the REAL Deflated-Sharpe distribution (retires the
    Phase B 3-cell proxy)."""
    label: str
    sharpe: float
    n: int


@dataclass
class StageResult:
    stage: str
    verdict: str            # Verdict.*
    statistic: dict
    threshold: dict


@dataclass
class Candidate:
    strategy_fn: str
    trades: list                       # [{ticker, entry_date, raw_entry, raw_exit, regime}]
    regime_cells: dict                 # {regime: [trades]}
    scan_family: list                  # [ScanCell]
    meta: dict = field(default_factory=dict)   # strategy_config_hash, universe, corpus_as_of


@dataclass
class GateDecision:
    final_state: str                   # FinalState.*
    failing_stage: str | None
    stage_results: list                # [StageResult]
    candidate_hash: str
    config_hash: str
    dataset_fingerprint: str
    git_commit: str | None
    seed: int
    forward_test_rule: dict | None
    run_id: str | None = None
    strategy_fn: str = ""
