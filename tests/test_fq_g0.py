"""Tests for the {FQ} E/P G0 script in docs/research_programs/P-M/fq/ (synthetic inputs only).

g0_fq_ep_breadth.py must never read a price after D for a formation at D; test_build_never_reads_later_prices
poisons every later price and checks month D is unchanged. Availability follows D-111 (deadlines, R4 COVID
overrides, R5 withholding, R7 fiscal-year exceptions) with D11 applied at month-end granularity."""
import importlib.util
import os
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "docs", "research_programs", "P-M", "fq", "g0_fq_ep_breadth.py")


@pytest.fixture(scope="module")
def G():
    spec = importlib.util.spec_from_file_location("g0_fq_ep_breadth", PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- D-111 deadlines

@pytest.mark.parametrize("pe,fy,expected", [
    (date(2025, 3, 31), None, date(2025, 4, 30)),      # Q1, unattested path
    (date(2025, 6, 30), None, date(2025, 9, 30)),      # H1, audited path (D1)
    (date(2025, 9, 30), None, date(2025, 10, 31)),     # Q3
    (date(2025, 12, 31), None, date(2026, 3, 31)),     # FY
    (date(2019, 12, 31), None, date(2020, 5, 31)),     # R4 COVID override
    (date(2022, 3, 31), None, date(2022, 6, 30)),      # R4 [U] row
    (date(2025, 3, 31), "31-Mar", date(2025, 6, 30)),  # R7: Mar fiscal-year end takes month 3
    (date(2025, 9, 30), "31-Mar", date(2025, 12, 31)), # R7: its H1 takes month 3
    (date(2025, 6, 30), "31-Mar", date(2025, 9, 30)),  # R7: other periods keep R3
    (date(2025, 3, 31), "31-Jan", None),               # R7: off-quarter fiscal year excluded
])
def test_deadline_for(G, pe, fy, expected):
    assert G.deadline_for(pe, fy) == expected


# ---------------------------------------------------------------- D11 at month-end granularity

def test_first_qualifying_traded_deadline_and_traded_next_month_end(G):
    k = {(2025, 9): date(2025, 9, 30), (2025, 10): date(2025, 10, 31), (2025, 11): date(2025, 11, 28)}
    assert G.first_qualifying(date(2025, 9, 30), k) == date(2025, 10, 31)


def test_first_qualifying_next_month_end_not_a_trading_day(G):
    # Q1-2025: deadline 30 Apr traded; usable_from 31 May, but May's last session is the 28th -> June's date
    k = {(2025, 4): date(2025, 4, 30), (2025, 5): date(2025, 5, 28), (2025, 6): date(2025, 6, 30)}
    assert G.first_qualifying(date(2025, 4, 30), k) == date(2025, 6, 30)


def test_first_qualifying_shifted_deadline(G):
    # FY2024: 31 Mar 2025 not a session (Lebaran) -> deadline* in April -> usable_from in May -> May's date
    k = {(2025, 3): date(2025, 3, 27), (2025, 4): date(2025, 4, 30), (2025, 5): date(2025, 5, 28)}
    assert G.first_qualifying(date(2025, 3, 31), k) == date(2025, 5, 28)


def test_first_qualifying_weekend_deadline(G):
    # Q3-2026: 31 Oct 2026 is a Saturday -> deadline* 2 Nov -> usable 2 Dec -> December's date
    k = {(2026, 10): date(2026, 10, 30), (2026, 11): date(2026, 11, 30), (2026, 12): date(2026, 12, 30)}
    assert G.first_qualifying(date(2026, 10, 31), k) == date(2026, 12, 30)


# ---------------------------------------------------------------- currency

@pytest.mark.parametrize("s,d,expected", [
    (100.0, 100.0, "IDR"),
    (100.0, 55.0, "IDR"),                              # late-filer layout: parent equity / total equity
    (100.0, 140.0, "IDR"),                             # JATI-like ratio: same magnitude, so IDR
    (100.0, 1_672_000.0, "USD"),
    (100.0, 1_000.0, None),                            # neither magnitude
    (None, 100.0, None),
    (0.0, 100.0, None),
])
def test_classify_currency(G, s, d, expected):
    assert G.classify_currency(s, d) == expected


def test_carry_currency_fills_gaps_without_conflict(G):
    k = {date(2020, 3, 31): "USD", date(2020, 6, 30): None, date(2020, 9, 30): "USD",
         date(2020, 12, 31): None, date(2021, 3, 31): "IDR", date(2021, 6, 30): "AMB"}
    out = G.carry_currency(k)
    assert out[date(2020, 6, 30)] == "USD"            # both neighbours agree
    assert out[date(2020, 12, 31)] is None            # neighbours conflict (USD before, IDR after)
    assert out[date(2021, 6, 30)] == "AMB"            # ambiguous is never filled


# ---------------------------------------------------------------- TTM

def _q(ni, qual, ccy="IDR", rate=1.0, withheld=False):
    return {"ni": ni, "ccy": ccy, "rate": rate, "qual": qual, "withheld": withheld}


def _year(D_qual, ni=10.0, **kw):
    return {pe: _q(ni, D_qual, **kw) for pe in
            (date(2024, 3, 31), date(2024, 6, 30), date(2024, 9, 30), date(2024, 12, 31))}


def test_ttm_sums_four_quarters(G):
    assert G.ttm_at(date(2025, 6, 30), _year(date(2025, 5, 28))) == (40.0, "ok")


def test_ttm_usd_converted_at_each_quarters_rate(G):
    qs = _year(date(2025, 5, 28), ni=1.0, ccy="USD", rate=15000.0)
    assert G.ttm_at(date(2025, 6, 30), qs)[0] == pytest.approx(60000.0)


def test_ttm_not_usable_before_qual(G):
    assert G.ttm_at(date(2025, 4, 30), _year(date(2025, 5, 28))) == (None, "no_data")


def test_ttm_withheld_latest_quarter_falls_back_to_earlier_window(G):
    qs = _year(date(2025, 2, 27))
    qs[date(2023, 12, 31)] = _q(5.0, date(2025, 2, 27))
    qs[date(2024, 12, 31)] = _q(10.0, date(2025, 2, 27), withheld=True)
    total, why = G.ttm_at(date(2025, 6, 30), qs)
    assert why == "ok" and total == pytest.approx(35.0)   # Q4-23 + Q1..Q3-24


def test_ttm_withheld_without_fallback_reports_withheld(G):
    qs = _year(date(2025, 2, 27))
    qs[date(2024, 12, 31)]["withheld"] = True
    assert G.ttm_at(date(2025, 6, 30), qs) == (None, "withheld")


def test_ttm_ambiguous_currency(G):
    qs = _year(date(2025, 2, 27))
    qs[date(2024, 6, 30)]["ccy"] = None
    assert G.ttm_at(date(2025, 6, 30), qs)[1] == "ccy"


def test_ttm_stale(G):
    assert G.ttm_at(date(2026, 6, 30), _year(date(2025, 2, 27)))[1] == "stale"


# ---------------------------------------------------------------- universe

def test_universe_filters_and_ranks(G, monkeypatch):
    monkeypatch.setattr(G, "TOP_N", 2)
    d = {"AAAA": (10, 100.0), "BBBB": (10, 50.0), "CCCC": (10, 80.0), "DDDDP": (10, 999.0), "EEEE": (10, 0.0)}
    m1 = {"CCCC": (10, 80.0)}
    m2 = {"CCCC": (10, 80.0)}                            # CCCC stale for three month-ends
    assert [t for t, _ in G.universe_at(d, m1, m2)] == ["AAAA", "BBBB"]


# ---------------------------------------------------------------- power and refusal

def test_power_and_threshold(G):
    assert G.months_needed() == 129
    assert G.power(208 / 12) == pytest.approx(0.4295, abs=1e-3)
    assert G.power(128 / 12) < G.MIN_POWER <= G.power(129 / 12)


def test_main_refuses_until_frozen(G):
    assert G.FREEZE_SHA256 is None
    assert G.main([]) == 2


def test_period_labels(G):
    assert G.period_label_to_end("FY2024") == date(2024, 12, 31)
    assert G.period_label_to_end("Q1-2025") == date(2025, 3, 31)
    assert G.period_label_to_end("H1-2025") == date(2025, 6, 30)
    assert G.period_label_to_end("Q3-2024") == date(2024, 9, 30)
    assert G.period_label_to_end("junk") is None


# ---------------------------------------------------------------- no look-ahead

def _panel():
    import calendar
    by = {}
    for y in (2009, 2010):
        for m in range(1, 13):
            d = date(y, m, calendar.monthrange(y, m)[1])
            by[d] = {f"{chr(65 + i // 26)}{chr(65 + i % 26)}AA": (1000.0, 100.0 + i + m) for i in range(30)}
    return by


def _fin(by):
    fin = {}
    for t in next(iter(by.values())):
        qs = {}
        for y in (2008, 2009, 2010):
            for m in (3, 6, 9, 12):
                pe = date(y, m, {3: 31, 6: 30, 9: 30, 12: 31}[m])
                qs[pe] = {"ni": 5.0, "ccy": "IDR", "rate": 1.0, "deadline": None if y == 2010 and m == 12 else
                          {3: date(y, 4, 30), 6: date(y, 9, 30), 9: date(y, 10, 31), 12: date(y + 1, 3, 31)}[m],
                          "withheld": False}
        fin[t] = qs
    return fin


def test_build_never_reads_later_prices(G, monkeypatch):
    monkeypatch.setattr(G, "FIRST_D", (2009, 5))
    monkeypatch.setattr(G, "LAST_D", (2010, 12))
    monkeypatch.setattr(G, "MIN_VALID", 5)
    by = _panel()
    base = G.build(by, _fin(by))
    target = date(2009, 12, 31)
    poisoned = {d: ({t: (sec * 7, -1.0 if px else px) for t, (sec, px) in rows.items()} if d > target else rows)
                for d, rows in by.items()}
    again = G.build(poisoned, _fin(poisoned))
    keep = [m for m in base if m["D"] <= target.isoformat()]
    assert keep and keep == [m for m in again if m["D"] <= target.isoformat()]
    assert all(m["valid"] > 0 for m in keep if m["D"] >= "2009-06-30")


# ---------------------------------------------------------------- report-only additions

def test_fx_check_flags_deviation_beyond_tolerance(G):
    fin = {"AAAA": {date(2024, 12, 31): dict(_q(1.0, None, ccy="USD", rate=15500.0), vendor_r=15500.0),
                    date(2025, 3, 31): dict(_q(1.0, None, ccy="USD", rate=16300.0), vendor_r=17000.0)},
           "BBBB": {date(2024, 12, 31): _q(1.0, None)}}
    yahoo = {(2024, 12): 15500.0, (2025, 3): 16300.0}
    r = G.fx_check(fin, yahoo)
    assert r["usd_periods_checked"] == 2 and r["beyond_tol"] == 1
    assert r["worst"][0][1:] == ("AAAA", "2025-03-31")


def test_build_counts_valid_names_from_new_codes(G, monkeypatch):
    monkeypatch.setattr(G, "FIRST_D", (2009, 5))
    monkeypatch.setattr(G, "LAST_D", (2009, 12))
    monkeypatch.setattr(G, "MIN_VALID", 5)
    by = _panel()
    new = frozenset(list(next(iter(by.values())))[:3])
    months = G.build(by, _fin(by), new)
    assert all(m["valid_new_codes"] == (3 if m["valid"] else 0) for m in months)
