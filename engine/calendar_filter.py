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

# ─── IDX Market Holidays 2024 ─────────────────────────────────────────────────
# Source: SKB 3 Menteri Tahun 2024 (17 libur nasional + 10 cuti bersama).
# Verified 2026-05-29 against
# https://setkab.go.id/inilah-skb-3-menteri-libur-nasional-dan-cuti-bersama-2024/
# Feb-2024 SKB Perubahan only renamed Christian-holiday nomenclature; no dates
# were added/removed.
IDX_MARKET_HOLIDAYS_2024: Dict[str, str] = {
    # ── Januari ──────────────────────────────────────────────────────────────
    "2024-01-01": "Tahun Baru 2024 Masehi",
    # ── Februari (Imlek 2575) ────────────────────────────────────────────────
    "2024-02-08": "Isra Mikraj Nabi Muhammad SAW",
    "2024-02-09": "Cuti Bersama Tahun Baru Imlek 2575 Kongzili",
    "2024-02-10": "Tahun Baru Imlek 2575 Kongzili",
    # ── Maret (Nyepi + Paskah) ───────────────────────────────────────────────
    "2024-03-11": "Hari Suci Nyepi (Tahun Baru Saka 1946)",
    "2024-03-12": "Cuti Bersama Hari Suci Nyepi",
    "2024-03-29": "Wafat Yesus Kristus (Wafat Isa Al Masih)",
    "2024-03-31": "Kebangkitan Yesus Kristus (Paskah)",
    # ── April (Idul Fitri 1445 H) ────────────────────────────────────────────
    "2024-04-08": "Cuti Bersama Idul Fitri 1445 H",
    "2024-04-09": "Cuti Bersama Idul Fitri 1445 H",
    "2024-04-10": "Hari Raya Idul Fitri 1445 H (Hari ke-1)",
    "2024-04-11": "Hari Raya Idul Fitri 1445 H (Hari ke-2)",
    "2024-04-12": "Cuti Bersama Idul Fitri 1445 H",
    "2024-04-15": "Cuti Bersama Idul Fitri 1445 H",
    # ── Mei ──────────────────────────────────────────────────────────────────
    "2024-05-01": "Hari Buruh Internasional",
    "2024-05-09": "Kenaikan Yesus Kristus (Kenaikan Isa Al Masih)",
    "2024-05-10": "Cuti Bersama Kenaikan Yesus Kristus",
    "2024-05-23": "Hari Raya Waisak 2568 BE",
    "2024-05-24": "Cuti Bersama Hari Raya Waisak",
    # ── Juni ─────────────────────────────────────────────────────────────────
    "2024-06-01": "Hari Lahir Pancasila",
    "2024-06-17": "Hari Raya Idul Adha 1445 H",
    "2024-06-18": "Cuti Bersama Idul Adha 1445 H",
    # ── Juli ─────────────────────────────────────────────────────────────────
    "2024-07-07": "1 Muharam Tahun Baru Islam 1446 H",
    # ── Agustus ──────────────────────────────────────────────────────────────
    "2024-08-17": "Proklamasi Kemerdekaan Republik Indonesia",
    # ── September ────────────────────────────────────────────────────────────
    "2024-09-16": "Maulid Nabi Muhammad SAW",
    # ── Desember (Natal) ─────────────────────────────────────────────────────
    "2024-12-25": "Hari Raya Natal",
    "2024-12-26": "Cuti Bersama Hari Raya Natal",
}


# ─── IDX Market Holidays 2025 ─────────────────────────────────────────────────
# Source: SKB 3 Menteri Nomor 1 Tahun 2025 (17 libur nasional + 10 cuti bersama)
# plus SKB Perubahan adding 2025-08-18 (HUT RI 80 cuti bersama). Verified
# 2026-05-29 against https://setkab.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025/
IDX_MARKET_HOLIDAYS_2025: Dict[str, str] = {
    # ── Januari ──────────────────────────────────────────────────────────────
    "2025-01-01": "Tahun Baru 2025 Masehi",
    "2025-01-27": "Isra Mikraj Nabi Muhammad SAW",
    "2025-01-28": "Cuti Bersama Tahun Baru Imlek 2576 Kongzili",
    "2025-01-29": "Tahun Baru Imlek 2576 Kongzili",
    # ── Maret (Nyepi + Idul Fitri 1446 H) ────────────────────────────────────
    "2025-03-28": "Cuti Bersama Hari Suci Nyepi",
    "2025-03-29": "Hari Suci Nyepi (Tahun Baru Saka 1947)",
    "2025-03-31": "Hari Raya Idul Fitri 1446 H (Hari ke-1)",
    # ── April (Idul Fitri lanjutan + Paskah) ─────────────────────────────────
    "2025-04-01": "Hari Raya Idul Fitri 1446 H (Hari ke-2)",
    "2025-04-02": "Cuti Bersama Idul Fitri 1446 H",
    "2025-04-03": "Cuti Bersama Idul Fitri 1446 H",
    "2025-04-04": "Cuti Bersama Idul Fitri 1446 H",
    "2025-04-07": "Cuti Bersama Idul Fitri 1446 H",
    "2025-04-18": "Wafat Yesus Kristus (Wafat Isa Al Masih)",
    "2025-04-20": "Kebangkitan Yesus Kristus (Paskah)",
    # ── Mei ──────────────────────────────────────────────────────────────────
    "2025-05-01": "Hari Buruh Internasional",
    "2025-05-12": "Hari Raya Waisak 2569 BE",
    "2025-05-13": "Cuti Bersama Hari Raya Waisak",
    "2025-05-29": "Kenaikan Yesus Kristus (Kenaikan Isa Al Masih)",
    "2025-05-30": "Cuti Bersama Kenaikan Yesus Kristus",
    # ── Juni ─────────────────────────────────────────────────────────────────
    "2025-06-01": "Hari Lahir Pancasila",
    "2025-06-06": "Hari Raya Idul Adha 1446 H",
    "2025-06-09": "Cuti Bersama Idul Adha 1446 H",
    "2025-06-27": "1 Muharam Tahun Baru Islam 1447 H",
    # ── Agustus ──────────────────────────────────────────────────────────────
    "2025-08-17": "Proklamasi Kemerdekaan Republik Indonesia",
    "2025-08-18": "Cuti Bersama HUT ke-80 Kemerdekaan RI (SKB Perubahan)",
    # ── September ────────────────────────────────────────────────────────────
    "2025-09-05": "Maulid Nabi Muhammad SAW",
    # ── Desember (Natal) ─────────────────────────────────────────────────────
    "2025-12-25": "Hari Raya Natal",
    "2025-12-26": "Cuti Bersama Hari Raya Natal",
}


# ─── IDX Market Holidays 2026 ─────────────────────────────────────────────────
# BEI (Bursa Efek Indonesia) is closed on these dates.
# Sources: Hari Libur Nasional + Cuti Bersama SKB Pemerintah 2026.
# Islamic calendar dates (Idul Fitri, Idul Adha, etc.) are moon-sighting
# dependent — verify against official BEI announcement each year.
IDX_MARKET_HOLIDAYS_2026: Dict[str, str] = {
    # Source: SKB 3 Menteri Nomor 1497 / 2 / 5 Tahun 2025
    # (17 libur nasional + 8 cuti bersama). Verified 2026-05-28 against
    # https://setneg.go.id/baca/index/inilah_skb_3_menteri_libur_nasional_dan_cuti_bersama_2026
    # ── Januari ──────────────────────────────────────────────────────────────
    "2026-01-01": "Tahun Baru 2026 Masehi",
    "2026-01-16": "Isra Mikraj Nabi Muhammad SAW",
    # ── Februari (Tahun Baru Imlek 2577 Kongzili) ───────────────────────────
    "2026-02-16": "Cuti Bersama Tahun Baru Imlek 2577 Kongzili",
    "2026-02-17": "Tahun Baru Imlek 2577 Kongzili",
    # ── Maret (Nyepi + Idul Fitri 1447 H) ────────────────────────────────────
    "2026-03-18": "Cuti Bersama Hari Suci Nyepi",
    "2026-03-19": "Hari Suci Nyepi (Tahun Baru Saka 1948)",
    "2026-03-20": "Cuti Bersama Idul Fitri 1447 H",
    "2026-03-21": "Hari Raya Idul Fitri 1447 H (Hari ke-1)",
    "2026-03-22": "Hari Raya Idul Fitri 1447 H (Hari ke-2)",
    "2026-03-23": "Cuti Bersama Idul Fitri 1447 H",
    "2026-03-24": "Cuti Bersama Idul Fitri 1447 H",
    # ── April (Paskah) ───────────────────────────────────────────────────────
    "2026-04-03": "Wafat Yesus Kristus (Wafat Isa Al Masih)",
    "2026-04-05": "Kebangkitan Yesus Kristus (Paskah)",
    # ── Mei ──────────────────────────────────────────────────────────────────
    "2026-05-01": "Hari Buruh Internasional",
    "2026-05-14": "Kenaikan Yesus Kristus (Kenaikan Isa Al Masih)",
    "2026-05-15": "Cuti Bersama Kenaikan Yesus Kristus",
    "2026-05-27": "Hari Raya Idul Adha 1447 H",
    "2026-05-28": "Cuti Bersama Idul Adha 1447 H",
    "2026-05-31": "Hari Raya Waisak 2570 BE",
    # ── Juni ─────────────────────────────────────────────────────────────────
    "2026-06-01": "Hari Lahir Pancasila",
    "2026-06-16": "1 Muharam Tahun Baru Islam 1448 H",
    # ── Agustus ──────────────────────────────────────────────────────────────
    "2026-08-17": "Proklamasi Kemerdekaan Republik Indonesia",
    "2026-08-25": "Maulid Nabi Muhammad SAW",
    # ── Desember (Natal) ─────────────────────────────────────────────────────
    "2026-12-24": "Cuti Bersama Hari Raya Natal",
    "2026-12-25": "Hari Raya Natal",
}

_MARKET_HOLIDAYS: Dict[date, str] = {
    date.fromisoformat(k): v
    for src in (IDX_MARKET_HOLIDAYS_2024, IDX_MARKET_HOLIDAYS_2025, IDX_MARKET_HOLIDAYS_2026)
    for k, v in src.items()
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
