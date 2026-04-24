"""
calendar_filter.py — IDX Economic Calendar & Trading Blackout Dates
====================================================================
Defines BI Rate RDG and FOMC meeting dates for 2026.
Blackout window: H-1 and H+1 around each event.
New entries are paused during blackout to avoid event-driven whipsaw.
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple

# ─── BI Rate RDG (Rapat Dewan Gubernur) 2026 ─────────────────────────────────
# Update this list when BI releases/revises the annual schedule.
BI_RATE_DATES_2026: List[str] = [
    "2026-01-15",
    "2026-02-19",
    "2026-03-19",
    "2026-04-23",
    "2026-05-21",
    "2026-06-18",
    "2026-07-16",
    "2026-08-20",
    "2026-09-17",
    "2026-10-15",
    "2026-11-19",
    "2026-12-17",
]

# ─── FOMC 2026 ────────────────────────────────────────────────────────────────
# Fed rate decision dates impact USD/IDR → IDX sentiment.
FOMC_DATES_2026: List[str] = [
    "2026-01-28",
    "2026-03-18",
    "2026-04-29",
    "2026-06-17",
    "2026-07-29",
    "2026-09-16",
    "2026-10-28",
    "2026-12-16",
]

# ─── Custom one-off blackout dates ───────────────────────────────────────────
# Add snap elections, special holidays, etc. here.
OTHER_BLACKOUT_DATES: List[str] = []

# Blackout window around each event
BLACKOUT_DAYS_BEFORE = 1
BLACKOUT_DAYS_AFTER  = 1

# ─── Build master event dict ──────────────────────────────────────────────────
_ALL_EVENTS: Dict[str, str] = {}
for _d in BI_RATE_DATES_2026:
    _ALL_EVENTS[_d] = "BI Rate RDG"
for _d in FOMC_DATES_2026:
    _ALL_EVENTS[_d] = "FOMC"
for _d in OTHER_BLACKOUT_DATES:
    _ALL_EVENTS[_d] = "Custom"


def _build_blackout_set() -> Dict[date, str]:
    out: Dict[date, str] = {}
    for date_str, label in _ALL_EVENTS.items():
        try:
            ev = date.fromisoformat(date_str)
        except ValueError:
            continue
        for offset in range(-BLACKOUT_DAYS_BEFORE, BLACKOUT_DAYS_AFTER + 1):
            d = ev + timedelta(days=offset)
            if d not in out:
                if offset < 0:
                    tag = f"H{offset} before {label} ({date_str})"
                elif offset > 0:
                    tag = f"H+{offset} after {label} ({date_str})"
                else:
                    tag = f"{label} ({date_str})"
                out[d] = tag
    return out


_BLACKOUT: Dict[date, str] = _build_blackout_set()


def is_blackout_day(check_date: date = None) -> Tuple[bool, str]:
    """Returns (is_blackout, reason). Pass None to check today."""
    if check_date is None:
        check_date = date.today()
    if check_date in _BLACKOUT:
        return True, _BLACKOUT[check_date]
    return False, "clear"


def get_upcoming_events(n_days: int = 30) -> List[Dict]:
    """Events within the next N days from today."""
    today = date.today()
    events = []
    for date_str, label in _ALL_EVENTS.items():
        try:
            ev = date.fromisoformat(date_str)
        except ValueError:
            continue
        days_away = (ev - today).days
        if 0 <= days_away <= n_days:
            events.append({
                "date":           date_str,
                "label":          label,
                "days_away":      days_away,
                "blackout_start": (ev - timedelta(days=BLACKOUT_DAYS_BEFORE)).isoformat(),
                "blackout_end":   (ev + timedelta(days=BLACKOUT_DAYS_AFTER)).isoformat(),
            })
    events.sort(key=lambda x: x["days_away"])
    return events


def get_all_events() -> List[Dict]:
    """All events in the calendar, sorted by date."""
    today = date.today()
    events = []
    for date_str, label in _ALL_EVENTS.items():
        try:
            ev = date.fromisoformat(date_str)
        except ValueError:
            continue
        days_away = (ev - today).days
        events.append({
            "date":           date_str,
            "label":          label,
            "days_away":      days_away,
            "past":           days_away < 0,
            "blackout_start": (ev - timedelta(days=BLACKOUT_DAYS_BEFORE)).isoformat(),
            "blackout_end":   (ev + timedelta(days=BLACKOUT_DAYS_AFTER)).isoformat(),
        })
    events.sort(key=lambda x: x["date"])
    return events
