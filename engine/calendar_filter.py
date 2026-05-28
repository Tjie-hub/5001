"""
calendar_filter.py — IDX Economic Calendar & Trading Blackout Dates
====================================================================
Defines BI Rate RDG and FOMC meeting dates for 2026.
Blackout window: H-1 and H+1 around each event.
New entries are paused during blackout to avoid event-driven whipsaw.

Also defines IDX market holidays (exchange closed) for 2026 so
schedulers can skip scans on non-trading days.
Update IDX_MARKET_HOLIDAYS_2026 each year from the official BEI
trading calendar (https://www.idx.co.id).
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

# ─── IDX Market Holidays 2026 ─────────────────────────────────────────────────
# BEI (Bursa Efek Indonesia) is closed on these dates.
# Sources: Hari Libur Nasional + Cuti Bersama SKB Pemerintah 2026.
# Islamic calendar dates (Idul Fitri, Idul Adha, etc.) are moon-sighting
# dependent — verify against official BEI announcement each year.
IDX_MARKET_HOLIDAYS_2026: Dict[str, str] = {
    # ── Januari ──────────────────────────────────────────────────────────────
    "2026-01-01": "Tahun Baru Masehi",
    "2026-01-27": "Isra Mi'raj Nabi Muhammad SAW 1447 H",
    "2026-01-29": "Tahun Baru Imlek 2577 Kongzili",
    # ── Maret (Idul Fitri 1447 H + Nyepi) ───────────────────────────────────
    "2026-03-19": "Cuti Bersama Idul Fitri 1447 H",
    "2026-03-20": "Hari Raya Idul Fitri 1447 H (Hari ke-1)",
    "2026-03-21": "Hari Raya Idul Fitri 1447 H (Hari ke-2)",
    "2026-03-23": "Cuti Bersama Idul Fitri 1447 H",
    "2026-03-24": "Cuti Bersama Idul Fitri 1447 H",
    "2026-03-28": "Hari Suci Nyepi — Tahun Baru Saka 1948",
    # ── April ────────────────────────────────────────────────────────────────
    "2026-04-03": "Wafat Isa Al Masih (Good Friday)",
    # ── Mei ──────────────────────────────────────────────────────────────────
    "2026-05-01": "Hari Buruh Internasional",
    "2026-05-14": "Kenaikan Isa Al Masih",
    "2026-05-15": "Cuti Bersama Kenaikan Isa Al Masih",
    "2026-05-22": "Hari Raya Waisak 2570 BE",
    "2026-05-27": "Hari Raya Idul Adha 1447 H",
    "2026-05-28": "Cuti Bersama Idul Adha 1447 H",
    # ── Juni ─────────────────────────────────────────────────────────────────
    "2026-06-01": "Hari Lahir Pancasila",
    "2026-06-17": "Tahun Baru Islam 1448 H",
    # ── Agustus ──────────────────────────────────────────────────────────────
    "2026-08-17": "Hari Kemerdekaan Republik Indonesia",
    # ── September ────────────────────────────────────────────────────────────
    "2026-09-04": "Maulid Nabi Muhammad SAW 1448 H",
    # ── Desember ─────────────────────────────────────────────────────────────
    "2026-12-25": "Hari Raya Natal",
    "2026-12-26": "Cuti Bersama Natal",
}

_MARKET_HOLIDAYS: Dict[date, str] = {
    date.fromisoformat(k): v for k, v in IDX_MARKET_HOLIDAYS_2026.items()
}

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


def is_trading_day(check_date: date = None) -> Tuple[bool, str]:
    """Returns (is_open, reason). False when IDX is closed (weekend or holiday)."""
    if check_date is None:
        check_date = date.today()
    if check_date.weekday() >= 5:
        return False, f"Weekend ({check_date.strftime('%A')})"
    if check_date in _MARKET_HOLIDAYS:
        return False, _MARKET_HOLIDAYS[check_date]
    return True, "trading day"


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
