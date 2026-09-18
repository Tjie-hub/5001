"""engine/historical/id_nr4.py — the ID/NR4 setup, exactly from the recovered text.

RECOVERED PRIMARY DEFINITION (Raschke & Connors, Street Smarts, Ch. 19
"Range Contraction" — DIRECTLY VERIFIED by the 2026-09-03 closure audit):

    "An NR4 is a trading day with the narrowest daily range of the last four
     days. An inside day has a higher low than the previous day's low and a
     lower high than the previous day's high. Combining the two conditions sets
     up an ID/NR4 day."

Corroborated by Crabel 1990's own inside-day definition ("its daily range
completely within the previous daily range", Glossary p. 283) and his NR4
("narrower than the previous three days compared individually", p. 285).

WHY THIS MODULE EXISTS AT ALL: the closure audit established that Street Smarts
contains NO standalone NR7 rule set — NR7 appears there once, as a bias filter
Raschke attributes to Crabel. The numbered rule set (one-tick entry, opposite
extreme stop, stop-and-reverse, two-day MOC) is stated for ID/NR4 and only for
ID/NR4. This module is the setup half of the genuine Raschke system; putting it
here rather than widening nr7.py keeps the two setups from blurring again.
"""
from engine.historical.nr7 import (NR4_LOOKBACK, TiePolicy, evaluate_nr4,
                                   nr7_range)

daily_range = nr7_range


def is_inside_day(highs, lows, t: int) -> bool:
    """Recovered: "a higher low than the previous day's low and a lower high
    than the previous day's high" (Street Smarts Ch. 19).

    Raises ValueError('insufficient_history') when t < 1.
    """
    if t < 1:
        raise ValueError("insufficient_history")
    return float(highs[t]) < float(highs[t - 1]) and float(lows[t]) > float(lows[t - 1])


def evaluate_id_nr4(highs, lows, ranges, t: int, tie_policy: TiePolicy) -> str:
    """'ok' | 'not_inside_day' | 'nr4_false' | 'tie_rejected' for setup day t.

    Both conditions must hold. The inside-day test is evaluated first so that
    telemetry attributes a rejection to the condition that actually failed.

    Raises ValueError('insufficient_history') when there is not enough history
    for either leg (NR4 needs t >= 3, inside day needs t >= 1).
    """
    if t < NR4_LOOKBACK - 1:
        raise ValueError("insufficient_history")
    if not is_inside_day(highs, lows, t):
        return "not_inside_day"
    return evaluate_nr4(ranges, t, tie_policy)


def detect_id_nr4_days(highs, lows, ranges, tie_policy: TiePolicy):
    """All indices t where the ID/NR4 setup holds."""
    out = []
    for t in range(len(ranges)):
        try:
            if evaluate_id_nr4(highs, lows, ranges, t, tie_policy) == "ok":
                out.append(t)
        except ValueError:
            continue
    return out
