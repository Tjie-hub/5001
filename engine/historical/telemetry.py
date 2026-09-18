"""engine/historical/telemetry.py — machine-readable rejection telemetry.

Phase 8 review §5 / Phase 9 §14: every rejection or skip in a historical run
must produce a machine-readable reason, and a run that produces zero trades must
expose the complete rejection histogram. Without this, "the history genuinely
produces few signals" is indistinguishable from "the engine ate the signals".

The reason strings are a stable contract (tests pin them). Additions are
allowed; renames are not.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RejectionReason(str, Enum):
    # Tasking minimum set:
    INSUFFICIENT_HISTORY = "insufficient_history"
    NR7_FALSE = "nr7_false"
    NR4_FALSE = "nr4_false"
    NOT_INSIDE_DAY = "not_inside_day"
    TIE_REJECTED = "tie_rejected"
    INVALID_SESSION = "invalid_session"
    TRIGGER_NOT_REACHED = "trigger_not_reached"
    INSUFFICIENT_INTRADAY_DATA = "insufficient_intraday_data"
    # The requested Opening Range is FINER than the intraday source can
    # resolve (audit C-8: the recovered OR is thirty seconds). Rejecting is
    # mandatory — silently widening the window to whatever the data can
    # serve would substitute an engine convention for a recovered rule.
    INSUFFICIENT_INTRADAY_RESOLUTION = "insufficient_intraday_resolution"
    AMBIGUITY = "ambiguity"
    CAPITAL_UNAVAILABLE = "capital_unavailable"
    INVALID_CONFIGURATION = "invalid_configuration"
    # Kernel extensions (allowed; "at minimum" set above is unchanged):
    GAP_CANCELLED = "gap_cancelled"
    OCO_CANCELLED = "oco_cancelled"


@dataclass(frozen=True)
class Rejection:
    date: str
    reason: RejectionReason
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"date": self.date, "reason": self.reason.value, "details": dict(self.details)}


class RejectionLog:
    """Append-only rejection collector. `histogram()` is the machine-readable
    aggregate exposed on every run result."""

    def __init__(self):
        self._items: list[Rejection] = []

    def record(self, date: str, reason: RejectionReason, **details: Any) -> Rejection:
        rej = Rejection(date=date, reason=RejectionReason(reason), details=dict(details))
        self._items.append(rej)
        return rej

    def extend(self, other: "RejectionLog") -> None:
        self._items.extend(other._items)

    @property
    def items(self) -> list[Rejection]:
        return list(self._items)

    def histogram(self) -> dict:
        """reason string -> count, sorted by reason name for determinism."""
        hist: dict[str, int] = {}
        for r in self._items:
            hist[r.reason.value] = hist.get(r.reason.value, 0) + 1
        return dict(sorted(hist.items()))

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self._items]

    def __len__(self) -> int:
        return len(self._items)
