"""engine/historical/nr7.py — narrow-range setup detection, exactly from the recovered text.

RECOVERED PRIMARY DEFINITIONS (Crabel 1990, Glossary p. 285 — DIRECTLY VERIFIED
by the 2026-09-03 provenance closure audit):

    "NR7 — is a daily range that is narrower than the previous six days
     compared individually to the day in question."

    "NR4 — is a daily range that is narrower than the previous three days
     compared individually to the day in question."

Corroborated in Raschke & Connors, Street Smarts Ch. 19: "An NR4 is a trading
day with the narrowest daily range of the last four days." N in NR-N counts the
day in question itself, so the comparison set is the previous N−1 sessions.

TIE HANDLING IS NOW SETTLED (audit finding C-2). The recovered definition says
"narrower than … compared individually": a range EQUAL to a prior day's range is
not narrower, so ties are excluded by the definition itself. `STRICT_LESS` is
therefore the historical reading. `MIN_INCLUSIVE` survives only as an explicitly
ahistorical legacy-parity mode — it is what engine/strategies.py's legacy NR7
Breakout hardcodes, and keeping it lets the legacy behavior be reproduced and
compared without pretending it is history.

The setup day is day t; the comparison window is t-(N-1) … t-1; the trade, if
any, happens on the NEXT session (t+1). A setup never trades on its own day.
"""
from enum import Enum

NR7_LOOKBACK = 7
NR4_LOOKBACK = 4


class TiePolicy(str, Enum):
    STRICT_LESS = "strict_less"
    MIN_INCLUSIVE = "min_inclusive"


# Member docstrings, set explicitly so they survive at runtime (a bare string
# literal under an Enum member is discarded by the interpreter).
TiePolicy.STRICT_LESS.__doc__ = (
    "HISTORICAL. Current range strictly less than EACH of the previous N-1 "
    "ranges; ties disqualify. This is the recovered wording — 'narrower than "
    "the previous six days compared individually to the day in question' "
    "(Crabel 1990, Glossary p. 285).")
TiePolicy.MIN_INCLUSIVE.__doc__ = (
    "AHISTORICAL — legacy-parity only. Current range equal to the minimum of "
    "the window still qualifies (<=). This CONTRADICTS the recovered "
    "definition and must never be presented as a historical interpretation; "
    "it exists so the legacy hardcoded behavior in engine/strategies.py can be "
    "reproduced and compared.")

#: The only tie policy the recovered primary definition supports.
HISTORICAL_TIE_POLICIES = frozenset({TiePolicy.STRICT_LESS})


def is_historical_tie_policy(policy: TiePolicy) -> bool:
    """True when `policy` matches the recovered 'narrower than' semantics."""
    return TiePolicy(policy) in HISTORICAL_TIE_POLICIES


def nr7_range(high: float, low: float) -> float:
    """Recovered: range = High − Low (absolute daily range; NOT True Range)."""
    return float(high) - float(low)


#: Same quantity, neutral name — NR4 and NR7 read the identical daily range.
daily_range = nr7_range


def evaluate_narrow_range(ranges, t: int, lookback: int, tie_policy: TiePolicy) -> str:
    """'ok' | 'narrow_range_false' | 'tie_rejected' for setup day index t.

    `lookback` is N in NR-N (7 or 4): the day in question is compared
    individually against the previous N−1 sessions.

    'tie_rejected' means the setup day's range EQUALS the minimum of the
    comparison set but the configured tie policy disqualifies it — the one case
    where rejection is attributable to the tie convention rather than to the
    pattern. Telemetry distinguishes the two.

    Raises ValueError('insufficient_history') when t < lookback - 1.
    """
    compare_n = lookback - 1
    if t < compare_n:
        raise ValueError("insufficient_history")
    current = float(ranges[t])
    previous = [float(ranges[j]) for j in range(t - compare_n, t)]
    if tie_policy is TiePolicy.STRICT_LESS:
        if all(current < r for r in previous):
            return "ok"
        if current == min(previous):
            return "tie_rejected"
        return "narrow_range_false"
    if tie_policy is TiePolicy.MIN_INCLUSIVE:
        return "ok" if current <= min(previous) else "narrow_range_false"
    raise ValueError(f"unknown tie policy: {tie_policy!r}")


def evaluate_nr7(ranges, t: int, tie_policy: TiePolicy) -> str:
    """'ok' | 'nr7_false' | 'tie_rejected' for setup day index t.

    The window is ranges[t-6 … t] (inclusive of t); the comparison set is the
    previous six, ranges[t-6 … t-1].
    """
    verdict = evaluate_narrow_range(ranges, t, NR7_LOOKBACK, tie_policy)
    return "nr7_false" if verdict == "narrow_range_false" else verdict


def evaluate_nr4(ranges, t: int, tie_policy: TiePolicy) -> str:
    """'ok' | 'nr4_false' | 'tie_rejected' for setup day index t."""
    verdict = evaluate_narrow_range(ranges, t, NR4_LOOKBACK, tie_policy)
    return "nr4_false" if verdict == "narrow_range_false" else verdict


def is_nr7(ranges, t: int, tie_policy: TiePolicy) -> bool:
    """NR7 test for setup day index `t`. Raises ValueError('insufficient_history')
    when t < 6 — the caller converts this into rejection reason
    `insufficient_history`."""
    return evaluate_nr7(ranges, t, tie_policy) == "ok"


def detect_nr7_days(ranges, tie_policy: TiePolicy):
    """All indices t where is_nr7 holds. Useful for tests and histograms."""
    out = []
    for t in range(len(ranges)):
        try:
            if is_nr7(ranges, t, tie_policy):
                out.append(t)
        except ValueError:
            continue
    return out
