"""Synthetic tests for extract_dividends.py (pattern: g0_fq_ep_breadth 52-test suite).

All data is synthetic; no return is ever computed. Run from anywhere:
  venv/bin/python3 -m pytest -q docs/research_programs/P-M/dy/test_extract_dividends.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_dividends as ex


class _FakeCon:
    """Stands in for the sqlite connection: row_labels() and sum_paid_rows() only need
    execute(sql, params) -> iterable of tuples. Keeps SQL entirely out of this test file."""

    def __init__(self, rows, values):
        self._rows, self._values = rows, values

    def execute(self, sql, params=()):
        if sql.startswith("select ticker, row_order"):
            return iter(self._rows)
        if "period_end, value" in sql:
            (t, ro) = params
            return iter((pe, v) for (tk, _, _, r, pe, v) in self._values if tk == t and r == ro)
        raise AssertionError(f"unexpected query in test: {sql[:40]}")


# ---- label classification ----

def test_include_canonical_payment_labels():
    for s in ("Payment Of Dividend", "Payment Of Dividends", "Payment Of Cash Dividends",
              "Payment Of Cash Dividend", "Payments Of Cash Dividends", "Dividend Payment",
              "Dividend Payments", "Cash Dividend Paid", "Dividen", "Dividen Kas",
              "Pembayaran Dividen", "Pembayaran Dividen Kas", "Pembayaran Deviden Tunai",
              "Pembayaran Dividen Kepada Pemegang Saham", "Pembagian Dividen Kas"):
        assert ex.is_parent_dividend_paid(s), s


def test_exclude_nci_subsidiary_and_received():
    for s in ("Payment Of Dividends To Non-Controlling Interests", "Dividends Paid To Minorities",
              "Pembayaran Dividen Kepada Kepentingan Non-Pengendali", "Dividend Payment Of A Subsidiary",
              "Dividend Payment Of An Investment Entity", "Cash Dividends From Subsidiaries",
              "Pembayaran Dividen Dari Entitas Asosiasi", "Cash Dividends Received",
              "Penerimaan Dividen Kas Dari Anak", "Pembayaran Pajak Dividen", "Uang Muka Dividen",
              "Pembayaran Utang Dividen", "Dividen Modal Saham", "Pendapatan Dividen Reksa Dana"):
        assert not ex.is_parent_dividend_paid(s), s


def test_label_of_prefers_canonical_english():
    assert ex.label_of("Payment Of Dividend", "Pembayaran Dividen") == "Payment Of Dividend"
    assert ex.label_of("Pembayaran Dividen Tunai ...", "Pembayaran Dividen Tunai ...") == \
        "Pembayaran Dividen Tunai ..."


# ---- period parsing / layout ----

def test_parse_period_variants():
    assert ex.parse_period("Q1 2026") == (1, 2026)
    assert ex.parse_period("H1-2025") == (2, 2025)
    assert ex.parse_period("FY 2024") == (4, 2024)
    assert ex.parse_period("Q4 2024") == (4, 2024)
    assert ex.parse_period("Annual") is None


def test_bbca_shape_is_discrete():
    # FY smaller than its own interim of the same year -> DISCRETE (the BBCA empirical shape)
    p = {"Q2 2026": -37000.0, "FY 2025": -6800.0, "H1 2025": -30800.0}
    assert ex.classify_layout(p) == "DISCRETE"


def test_monotone_ytd_is_cumulative():
    p = {"Q1 2025": -100.0, "H1 2025": -100.0, "Q3 2025": -300.0, "FY 2025": -400.0}
    assert ex.classify_layout(p) == "CUMULATIVE"


def test_single_annual_only_is_unknown():
    assert ex.classify_layout({"FY 2025": -500.0}) == "UNKNOWN"


def test_quarterly_series_differences_cumulative():
    p = {"Q1 2025": -100.0, "H1 2025": -100.0, "Q3 2025": -300.0, "FY 2025": -400.0}
    q = ex.quarterly_series(p, "CUMULATIVE")
    assert q[date(2025, 3, 31)] == 100.0 and q[date(2025, 6, 30)] == 0.0
    assert q[date(2025, 9, 30)] == 200.0 and q[date(2025, 12, 31)] == 100.0


def test_quarterly_series_discrete_passthrough():
    p = {"H1 2025": -300.0, "FY 2025": -100.0}
    q = ex.quarterly_series(p, "DISCRETE")
    assert q[date(2025, 6, 30)] == 300.0 and q[date(2025, 12, 31)] == 100.0


# ---- sum_paid_rows: sign normalization, summation, exclusion ----

def test_sum_paid_rows_positive_payout():
    rows = [("AAAA", 70, "Payment Of Cash Dividends", "Pembayaran Dividen Kas")]
    values = [("AAAA", "cashflow", "statement", 70, "2025-12-31", -1000.0),
              ("AAAA", "cashflow", "statement", 70, "2025-06-30", -3000.0)]
    got = ex.sum_paid_rows(_FakeCon(rows, values), rows)
    assert got[("AAAA", "2025-12-31")] == 1000.0 and got[("AAAA", "2025-06-30")] == 3000.0


def test_excluded_labels_never_sum():
    rows = [("CCCC", 70, "Cash Dividends Received", "Penerimaan"),
            ("CCCC", 71, "Dividends Paid To Minorities", "Minorit")]
    values = [("CCCC", "cashflow", "statement", 70, "2025-12-31", -999.0),
              ("CCCC", "cashflow", "statement", 71, "2025-12-31", -888.0)]
    assert ex.sum_paid_rows(_FakeCon(rows, values), rows) == {}


def test_two_rows_same_period_sum():
    # interim + final as two separate parent-level rows in the same statement: summed
    rows = [("BBBB", 71, "Dividend Payment", "Pembayaran Deviden"),
            ("BBBB", 72, "Dividend Payment", "Pembayaran Deviden")]
    values = [("BBBB", "cashflow", "statement", 71, "2025-12-31", -400.0),
              ("BBBB", "cashflow", "statement", 72, "2025-12-31", -600.0)]
    assert ex.sum_paid_rows(_FakeCon(rows, values), rows)[("BBBB", "2025-12-31")] == 1000.0


# ---- TTM window + PIT gating ----

def _series():
    # H1-2025 deadline 2025-09-30 (D-111 base +3), FY-2025 -> 2026-03-31, H1-2026 -> 2026-09-30
    return [(date(2025, 6, 30), 300.0, date(2025, 9, 30), False),
            (date(2025, 12, 31), 100.0, date(2026, 3, 31), False),
            (date(2026, 6, 30), 370.0, date(2026, 9, 30), False)]


def test_ttm_respects_deadline():
    s = _series()
    assert ex.ttm_at(s, date(2026, 8, 31)) == 400.0      # H1-2025 + FY-2025 (H1-2026 deadline not yet)
    assert ex.ttm_at(s, date(2026, 9, 30)) == 470.0      # H1-2026 deadline day: FY-2025 + H1-2026


def test_ttm_window_anchors_on_newest_disclosed_period():
    s = _series()
    assert ex.ttm_at(s, date(2026, 12, 31)) == 470.0     # newest = H1-2026; H1-2025 left its window
    assert ex.ttm_at(s, date(2027, 6, 30)) == 470.0      # still inside the 15-month staleness cap


def test_ttm_stale_beyond_15_months_is_none():
    s = _series()
    assert ex.ttm_at(s, date(2027, 12, 31)) is None      # newest (2026-06-30) now staler than 456d


def test_withheld_periods_excluded():
    s = [(date(2025, 6, 30), 300.0, date(2025, 9, 30), True),
         (date(2025, 12, 31), 100.0, date(2026, 3, 31), False)]
    assert ex.ttm_at(s, date(2026, 6, 30)) == 100.0


def test_no_deadline_offquarter_fiscal_year_excluded():
    # D-111 R7: off-quarter period_end -> deadline None -> never available
    s = [(date(2025, 5, 31), 300.0, None, False)]
    assert ex.ttm_at(s, date(2026, 6, 30)) is None


# ---- meta: currency conversion ----

def test_usd_reporter_converts_at_period_end_rate():
    payouts = {("UUUU", "2025-12-31"): 10.0}            # USD 10
    ex._CURRENCY_CACHE.clear()
    ex._CURRENCY_CACHE.update({"UUUU": "USD"})
    meta = ex.dividends_with_meta(payouts, yahoo={(2025, 12): 16000.0}, fyx=None)
    assert meta[("UUUU", "2025-12-31")]["payout_idr"] == 160000.0
    assert meta[("UUUU", "2025-12-31")]["deadline"] == date(2026, 3, 31)


def test_idr_reporter_no_conversion():
    payouts = {("IIII", "2025-12-31"): 1000.0}
    ex._CURRENCY_CACHE.clear()
    ex._CURRENCY_CACHE.update({"IIII": "IDR"})
    meta = ex.dividends_with_meta(payouts, yahoo={}, fyx=None)
    assert meta[("IIII", "2025-12-31")]["payout_idr"] == 1000.0
    assert meta[("IIII", "2025-12-31")]["ccy"] == "IDR"


def test_missing_rate_drops_the_period():
    payouts = {("UUUU", "2025-12-31"): 10.0}
    ex._CURRENCY_CACHE.clear()
    ex._CURRENCY_CACHE.update({"UUUU": "USD"})
    meta = ex.dividends_with_meta(payouts, yahoo={}, fyx=None)
    assert ("UUUU", "2025-12-31") not in meta
