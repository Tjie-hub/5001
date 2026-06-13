"""Scanner result hygiene: dedupe by (ticker, strategy) and suppress rows
that carry no usable data (no close AND no WF score).

Reviewer (2026-06-13) saw FORU listed twice (one with close 3,600, one with
close —) and BULLISH rows at 0% strength / WF — / close — (BAIK, GRPH).
"""
from routes.backtest import dedupe_and_filter_scan_rows


def test_dedupe_keeps_richer_duplicate():
    rows = [
        {"ticker": "FORU", "strategy": "conservative_confirm", "close": None,   "wf_score": None},
        {"ticker": "FORU", "strategy": "conservative_confirm", "close": 3600.0, "wf_score": 72.0},
    ]
    out = dedupe_and_filter_scan_rows(rows)
    assert len(out) == 1
    assert out[0]["close"] == 3600.0
    assert out[0]["wf_score"] == 72.0


def test_suppresses_rows_with_no_close_and_no_wf():
    rows = [
        {"ticker": "BAIK", "strategy": "vol_weighted", "close": None, "wf_score": None},
        {"ticker": "GRPH", "strategy": "vol_weighted", "close": None, "wf_score": None},
        {"ticker": "BBRI", "strategy": "vol_weighted", "close": 4500.0, "wf_score": 80.0},
    ]
    out = dedupe_and_filter_scan_rows(rows)
    tickers = {r["ticker"] for r in out}
    assert tickers == {"BBRI"}


def test_keeps_row_with_close_but_no_wf():
    rows = [
        {"ticker": "NEWL", "strategy": "vol_weighted", "close": 1200.0, "wf_score": None},
    ]
    out = dedupe_and_filter_scan_rows(rows)
    assert len(out) == 1


def test_keeps_row_with_wf_but_no_close():
    rows = [
        {"ticker": "ILIQ", "strategy": "vol_weighted", "close": None, "wf_score": 65.0},
    ]
    out = dedupe_and_filter_scan_rows(rows)
    assert len(out) == 1


def test_distinct_strategies_not_merged():
    rows = [
        {"ticker": "BBRI", "strategy": "vol_weighted",        "close": 4500.0, "wf_score": 80.0},
        {"ticker": "BBRI", "strategy": "conservative_confirm", "close": 4500.0, "wf_score": 80.0},
    ]
    out = dedupe_and_filter_scan_rows(rows)
    assert len(out) == 2
