"""Parsing tests for stockbit_broker_period.py — the period-aggregated broker
summary collector (complementary to broker_flow, single-day only).

Fixtures below mirror the REAL exodus.stockbit.com/marketdetectors/{ticker}
response shape (verified live 2026-08-04 against BBCA with a wide from/to
range — the same endpoint/params fetch_broker_flow() already uses for
single-day historical replay, confirmed here to genuinely aggregate over a
period when from != to, not just replay one historical day). Field names
(blot/blotv/bval/bvalv/netbs_broker_code/type/freq for buys; slot/slotv/
sval/svalv for sells) match exactly what stockbit_fetcher.fetch_broker_flow()
already parses for the single-day case — reused here, not reinvented. Raw
sell fields (slot/sval/slotv/svalv) come back NEGATIVE from the API; the
merge normalizes sell_volume/sell_value to positive magnitudes so
net_value = buy_value - sell_value reads as an intuitive accumulation signal.
"""
from stockbit_broker_period import _merge_broker_rows, period_date_range


def _sample_broker_summary():
    return {
        "brokers_buy": [
            {"blot": "4.612375e+06", "blotv": "4.800001e+08", "bval": "2.90233487e+12",
             "bvalv": "3.0196141625e+12", "netbs_broker_code": "DX",
             "netbs_buy_avg_price": "6290.86", "netbs_date": "20260701",
             "netbs_stock_code": "BBCA", "type": "Pemerintah", "freq": "40246"},
            {"blot": "1.0e+06", "blotv": "1.0e+08", "bval": "5.0e+11",
             "bvalv": "5.2e+11", "netbs_broker_code": "AK",
             "netbs_buy_avg_price": "6300.0", "netbs_date": "20260701",
             "netbs_stock_code": "BBCA", "type": "Asing", "freq": "5000"},
        ],
        "brokers_sell": [
            {"netbs_broker_code": "BK", "netbs_date": "20260701",
             "netbs_sell_avg_price": "6276.50", "netbs_stock_code": "BBCA",
             "slot": "-3.229048e+06", "slotv": "6.438924e+08",
             "sval": "-2.011046725e+12", "svalv": "4.04139241e+12",
             "type": "Asing", "freq": "69467"},
            {"netbs_broker_code": "DX", "netbs_date": "20260701",
             "netbs_sell_avg_price": "6280.0", "netbs_stock_code": "BBCA",
             "slot": "-2.0e+05", "slotv": "2.0e+07",
             "sval": "-1.0e+09", "svalv": "1.05e+09",
             "type": "Pemerintah", "freq": "1200"},
        ],
    }


def test_merge_produces_one_row_per_distinct_broker_code():
    rows = _merge_broker_rows(_sample_broker_summary())
    codes = {r["broker_code"] for r in rows}
    assert codes == {"DX", "AK", "BK"}  # DX appears in both buy and sell — one row, not two
    assert len(rows) == 3


def test_broker_appearing_only_in_buy_side_has_zero_sell_fields():
    rows = _merge_broker_rows(_sample_broker_summary())
    ak = next(r for r in rows if r["broker_code"] == "AK")
    assert ak["buy_volume"] == 1_000_000
    assert ak["buy_value"] == 500_000_000_000
    assert ak["sell_volume"] == 0
    assert ak["sell_value"] == 0
    assert ak["net_value"] == 500_000_000_000


def test_broker_appearing_only_in_sell_side_has_zero_buy_fields_and_positive_sell_magnitude():
    rows = _merge_broker_rows(_sample_broker_summary())
    bk = next(r for r in rows if r["broker_code"] == "BK")
    assert bk["buy_volume"] == 0
    assert bk["buy_value"] == 0
    # raw sval was negative (-2.011046725e+12) — normalized to a positive magnitude
    assert bk["sell_volume"] == 3229048
    assert bk["sell_value"] == 2011046725000
    assert bk["net_value"] == -2011046725000  # net seller


def test_broker_appearing_in_both_sides_nets_correctly():
    rows = _merge_broker_rows(_sample_broker_summary())
    dx = next(r for r in rows if r["broker_code"] == "DX")
    assert dx["buy_value"] == 2902334870000
    assert dx["sell_value"] == 1000000000  # abs(-1.0e9)
    assert dx["net_value"] == 2902334870000 - 1000000000


def test_rank_assigned_by_absolute_net_value_descending():
    rows = _merge_broker_rows(_sample_broker_summary())
    by_code = {r["broker_code"]: r for r in rows}
    # |net|: DX ~2.9T, BK ~2.0T, AK 0.5T -> rank 1,2,3 respectively
    assert by_code["DX"]["rank"] == 1
    assert by_code["BK"]["rank"] == 2
    assert by_code["AK"]["rank"] == 3


def test_merge_preserves_raw_fields_for_forward_compatibility():
    rows = _merge_broker_rows(_sample_broker_summary())
    dx = next(r for r in rows if r["broker_code"] == "DX")
    assert dx["raw"]["buy"]["netbs_buy_avg_price"] == "6290.86"
    assert dx["raw"]["sell"]["netbs_sell_avg_price"] == "6280.0"


def test_merge_handles_empty_broker_summary():
    rows = _merge_broker_rows({"brokers_buy": [], "brokers_sell": []})
    assert rows == []


def test_merge_handles_missing_keys_gracefully():
    rows = _merge_broker_rows({})
    assert rows == []


# ── period_date_range ────────────────────────────────────────────────────

def test_last_7_days_is_six_days_back_inclusive():
    from datetime import date
    frm, to = period_date_range("LAST_7_DAYS", today=date(2026, 8, 4))
    assert (frm, to) == ("2026-07-29", "2026-08-04")


def test_last_1_month_is_one_calendar_month_back():
    from datetime import date
    frm, to = period_date_range("LAST_1_MONTH", today=date(2026, 8, 4))
    assert (frm, to) == ("2026-07-04", "2026-08-04")


def test_last_3_months_is_three_calendar_months_back():
    from datetime import date
    frm, to = period_date_range("LAST_3_MONTHS", today=date(2026, 8, 4))
    assert (frm, to) == ("2026-05-04", "2026-08-04")


def test_unknown_period_name_raises():
    try:
        period_date_range("NOT_A_REAL_PERIOD")
        assert False, "expected ValueError"
    except ValueError:
        pass
