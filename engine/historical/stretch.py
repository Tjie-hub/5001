"""engine/historical/stretch.py — the Crabel Stretch, exactly from the recovered text.

RECOVERED PRIMARY FORMULATION (Crabel 1990, Ch. 1 — DIRECTLY VERIFIED by the
2026-09-03 provenance closure audit):

    "The Stretch is determined by looking at the previous ten days and averaging
     the sum of the differences between the open for each day and the closest
     extreme to the open on each day."

Restated verbatim in the S&C publisher records for Parts 7 and 8 of the 1988–89
Opening Range Breakout series: "the 10-day average of the differences between
the open for each day and the closest extreme to the open on each day."

So, per day d:      stretch_d = min(|O_d − H_d|, |O_d − L_d|)
and the Stretch is the mean of that quantity over ten days.

WHAT IS *NOT* RECOVERED — THE ANCHOR (audit finding C-5)
--------------------------------------------------------
The primary text says "the previous ten days" and never names the day the
window ends on. Read on the execution day, "the previous ten days" ends at the
setup day (t-9 … t); read on the setup day, it ends the day before (t-10 …
t-1). Both are faithful readings of the same sentence.

The previous implementation asserted t-9 … t as recovered primary evidence.
It is not. `StretchAnchor` makes the choice an explicit, hashed ENGINE
CONVENTION. The FORMULA is untouched and remains DIRECT PRIMARY.
"""
from enum import Enum

from engine.historical.telemetry import RejectionLog, RejectionReason

STRETCH_LOOKBACK = 10   # recovered value ("the previous ten days")


class StretchAnchor(str, Enum):
    """ENGINE CONVENTION — which day the recovered "previous ten days" window
    ends on. PRIMARY SOURCE NOT RECOVERED."""
    INCLUDE_SETUP_DAY = "include_setup_day"
    EXCLUDE_SETUP_DAY = "exclude_setup_day"


StretchAnchor.INCLUDE_SETUP_DAY.__doc__ = (
    "Window t-9 … t — inclusive of the setup day, exclusive of the execution "
    "day. 'Previous ten days' read on the execution day; the Stretch is "
    "computable before that session opens.")
StretchAnchor.EXCLUDE_SETUP_DAY.__doc__ = (
    "Window t-10 … t-1 — 'previous ten days' read on the setup day itself, so "
    "the setup day contributes to the pattern but not to the Stretch.")


def _window(setup_t: int, lookback: int, anchor: StretchAnchor) -> tuple[int, int]:
    """[start, end) indices for the Stretch average. The execution day (t+1) is
    never inside either window."""
    if anchor is StretchAnchor.INCLUDE_SETUP_DAY:
        return setup_t - lookback + 1, setup_t + 1
    if anchor is StretchAnchor.EXCLUDE_SETUP_DAY:
        return setup_t - lookback, setup_t
    raise ValueError(f"unknown stretch anchor: {anchor!r}")


def stretch_at_setup(opens, highs, lows, setup_t: int,
                     lookback: int = STRETCH_LOOKBACK,
                     anchor: StretchAnchor = StretchAnchor.INCLUDE_SETUP_DAY) -> float:
    """Stretch value used on execution day setup_t + 1.

    `lookback=10` is the recovered value; it remains a parameter only so the
    tests can prove the indexing. `anchor` is an engine convention (see module
    docstring) and is part of rule identity.

    Raises ValueError('insufficient_history') when the window would start
    before index 0 or end beyond the data.
    """
    start, end = _window(setup_t, lookback, anchor)
    if start < 0 or end > len(opens) or setup_t >= len(opens):
        raise ValueError("insufficient_history")
    distances = []
    for d in range(start, end):
        o, h, l = float(opens[d]), float(highs[d]), float(lows[d])
        distances.append(min(abs(o - h), abs(o - l)))
    return sum(distances) / float(lookback)


def stretch_series_ready(opens, highs, lows, setup_t: int, lookback: int,
                         log: RejectionLog, date: str,
                         anchor: StretchAnchor = StretchAnchor.INCLUDE_SETUP_DAY) -> float | None:
    """Convenience wrapper: returns the Stretch or records insufficient_history."""
    try:
        return stretch_at_setup(opens, highs, lows, setup_t, lookback, anchor)
    except ValueError:
        log.record(date, RejectionReason.INSUFFICIENT_HISTORY,
                   what="stretch", setup_t=setup_t, lookback=lookback,
                   stretch_anchor=anchor.value)
        return None
