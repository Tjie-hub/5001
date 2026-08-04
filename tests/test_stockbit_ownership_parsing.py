"""Parsing tests for stockbit_ownership.py.

Fixture below is a REAL response fragment captured live against
exodus.stockbit.com/insider/shareholding/composition/companies/BBCA on
2026-08-05 — see the module docstring for the full endpoint investigation.
"""
from stockbit_ownership import _normalize_composition


def _bbca_period():
    """Trimmed real period payload (first 6 of 37 real rows — same shape,
    fewer rows for test readability). Note: the API gives no explicit field
    distinguishing a named holder ("DWIMURIA INVESTAMA ANDALAN") from an
    aggregate investor-type bucket ("Mutual Funds") — both are plain
    `label` strings. See module docstring for why holder_category is not
    fabricated here."""
    return {
        "report_date": "2026-07-31",
        "total_shares": {"raw": "123275050000", "formatted": "123.28B"},
        "compositions": [
            {"label": "DWIMURIA INVESTAMA ANDALAN",
             "shares": {"raw": "67729950000", "formatted": "67.73B"},
             "percentage": {"raw": 54.94213954891927, "formatted": "54.94%"},
             "colors": {"light": "#0BA16B", "dark": "#0BA16B"}},
            {"label": "Mutual Funds",
             "shares": {"raw": "19723748161", "formatted": "19.72B"},
             "percentage": {"raw": 15.999789220122, "formatted": "16.00%"},
             "colors": {"light": "#1FD795", "dark": "#1FD795"}},
            {"label": "Individual",
             "shares": {"raw": "11417972693", "formatted": "11.42B"},
             "percentage": {"raw": 9.26219270890582, "formatted": "9.26%"},
             "colors": {"light": "#35CBB1", "dark": "#35CBB1"}},
        ],
    }


def test_normalize_produces_one_row_per_composition_entry():
    rows = _normalize_composition("BBCA", _bbca_period())
    assert len(rows) == 3


def test_normalize_preserves_order_as_rank_starting_at_one():
    rows = _normalize_composition("BBCA", _bbca_period())
    assert [r["rank"] for r in rows] == [1, 2, 3]
    assert rows[0]["holder_label"] == "DWIMURIA INVESTAMA ANDALAN"
    assert rows[2]["holder_label"] == "Individual"


def test_normalize_parses_numeric_shares_and_percentage():
    rows = _normalize_composition("BBCA", _bbca_period())
    top = rows[0]
    assert top["shares"] == 67729950000
    assert top["percentage"] == 54.94213954891927


def test_normalize_carries_ticker_report_date_and_total_shares():
    rows = _normalize_composition("BBCA", _bbca_period())
    for r in rows:
        assert r["ticker"] == "BBCA"
        assert r["report_date"] == "2026-07-31"
        assert r["total_shares"] == 123275050000


def test_normalize_preserves_raw_fields_for_forward_compatibility():
    rows = _normalize_composition("BBCA", _bbca_period())
    assert rows[0]["raw"]["colors"]["light"] == "#0BA16B"


def test_normalize_handles_missing_shares_or_percentage_gracefully():
    period = {
        "report_date": "2026-07-31",
        "total_shares": {"raw": "1000"},
        "compositions": [{"label": "Unknown Bucket", "shares": {}, "percentage": {}}],
    }
    rows = _normalize_composition("BBCA", period)
    assert rows[0]["shares"] is None
    assert rows[0]["percentage"] is None
    assert rows[0]["holder_label"] == "Unknown Bucket"


def test_normalize_skips_entries_with_no_label():
    period = {
        "report_date": "2026-07-31",
        "total_shares": {"raw": "1000"},
        "compositions": [
            {"label": "", "shares": {"raw": "1"}, "percentage": {"raw": 0.1}},
            {"shares": {"raw": "1"}, "percentage": {"raw": 0.1}},
            {"label": "Real Holder", "shares": {"raw": "5"}, "percentage": {"raw": 0.5}},
        ],
    }
    rows = _normalize_composition("BBCA", period)
    assert len(rows) == 1
    assert rows[0]["holder_label"] == "Real Holder"
    assert rows[0]["rank"] == 1  # rank counts only kept rows, not skipped ones


def test_normalize_empty_compositions_returns_empty_list():
    period = {"report_date": "2026-07-31", "total_shares": {"raw": "0"}, "compositions": []}
    assert _normalize_composition("BBCA", period) == []
