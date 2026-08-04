"""Parsing tests for stockbit_corporate_actions.py.

Fixtures below are REAL response fragments captured live against
exodus.stockbit.com/corpaction/{ticker} on 2026-08-04 (BBCA/BRPT/BAJA) — see
the module docstring for the full endpoint investigation (confirmed
endpoint, rejected candidates, and why `limit`/pagination isn't needed:
the endpoint always returns a ticker's complete corp-action history
regardless of `limit`, tested down to limit=1 on a 26-row ticker).
"""
from stockbit_corporate_actions import _normalize_event, _extract_event_id, _extract_event_date


def _dividend_event():
    return {
        "action_type": "dividend",
        "action_info": {"dividend": {
            "company_id": "54", "company_symbol": "BBCA", "corp_action_active": False,
            "dividend_created": "2026-06-05", "dividend_cumdate": "2026-06-15",
            "dividend_datahash": "2d563330e11432fc459742ba14bcbc98",
            "dividend_exdate": "2026-06-17", "dividend_id": "117860",
            "dividend_iqp_id": "", "dividend_lastupdate": "2026-06-05",
            "dividend_lock": 0, "dividend_paydate": "2026-06-26",
            "dividend_recdate": "2026-06-18", "dividend_value": "20",
            "dividend_value_formatted": "Rp 20", "dividend_currency": "CURRENCY_IDR",
            "dividend_fiscal_year": 0, "dividend_value_adjusted": 0,
        }},
    }


def _rups_event():
    return {
        "action_type": "rups",
        "action_info": {"rups": {
            "company_id": "54", "company_symbol": "BBCA", "corp_action_active": False,
            "rups_created": "2026-01-29", "rups_datahash": "ef904f297719880d29916ed769f980d9",
            "rups_date": "2026-03-12", "rups_id": "1460182", "rups_time": "14:00",
            "rups_iqp_agenda": "", "rups_venue": "Menara BCA, Jakarta",
            "rups_eligible_date": "2026-02-09", "company_name": "",
        }},
    }


def _bonus_event():
    """Stockbit's own data quirk: 'bonus' action_type carries a
    sahambonus_id (not bonus_id) plus a mix of stocksplit_* fields."""
    return {
        "action_type": "bonus",
        "action_info": {"bonus": {
            "company_id": "93", "company_symbol": "BRPT", "corp_action_active": False,
            "sahambonus_id": "7683", "sahambonus_iqp_id": "",
            "sahambonus_lastupdate": "2024-05-29 17:45:01",
            "stocksplit_created": "2024-05-29", "stocksplit_cumdate": "2024-06-26",
            "stocksplit_exdate": "2024-06-27", "stocksplit_factor": "1.0016",
            "stocksplit_new": "1", "stocksplit_old": "625",
            "stocksplit_paymentdate": "2024-07-19", "stocksplit_recdate": "2024-06-28",
        }},
    }


def _warrant_event():
    """Another naming quirk: 'warrant' carries a wrant_id (typo'd, no 'a'
    after 'w') and has no *_exdate/*_date field at all — event_date falls
    back further down the priority list (see _extract_event_date)."""
    return {
        "action_type": "warrant",
        "action_info": {"warrant": {
            "company_id": "1000000018", "company_symbol": "BRPT-W",
            "corp_action_active": False, "wrant_exc_end": "2021-05-28",
            "wrant_exc_from": "2019-07-01", "wrant_exc_price": "1864",
            "wrant_id": "27", "wrant_iqp_id": "", "wrant_lastupdate": "2025-10-02",
            "wrant_serie": "I", "wrant_trading_end": "2021-05-28",
            "wrant_trading_from": "2018-06-07",
        }},
    }


def _rightissue_event():
    return {
        "action_type": "rightissue",
        "action_info": {"rightissue": {
            "company_id": "1000000019", "company_symbol": "BRPT-R",
            "corp_action_active": False, "rightissue_created": "2018-05-31",
            "rightissue_cumdate": "2018-05-30", "rightissue_exdate": "2018-05-31",
            "rightissue_factor": "1.31746", "rightissue_id": "2493",
            "rightissue_new": "20", "rightissue_old": "63", "rightissue_price": 2330,
            "rightissue_ratio": "63 : 20", "rightissue_recdate": "2018-06-05",
        }},
    }


# ── _extract_event_id ───────────────────────────────────────────────────

def test_event_id_standard_suffix_pattern():
    info = _dividend_event()["action_info"]["dividend"]
    assert _extract_event_id("dividend", info) == "117860"


def test_event_id_handles_sahambonus_naming_quirk():
    info = _bonus_event()["action_info"]["bonus"]
    assert _extract_event_id("bonus", info) == "7683"


def test_event_id_handles_wrant_typo_naming():
    info = _warrant_event()["action_info"]["warrant"]
    assert _extract_event_id("warrant", info) == "27"


def test_event_id_ignores_iqp_and_company_id_fields():
    info = {"widget_iqp_id": "999", "company_id": "1", "widget_real_id": "42"}
    assert _extract_event_id("widget", info) == "42"


def test_event_id_none_when_unresolvable():
    assert _extract_event_id("mystery", {"note": "no id anywhere"}) is None


# ── _extract_event_date ──────────────────────────────────────────────────

def test_event_date_prefers_exdate():
    info = _dividend_event()["action_info"]["dividend"]
    assert _extract_event_date("dividend", info) == "2026-06-17"


def test_event_date_falls_back_to_plain_date_field():
    info = _rups_event()["action_info"]["rups"]
    assert _extract_event_date("rups", info) == "2026-03-12"


def test_event_date_falls_back_further_for_warrant():
    info = _warrant_event()["action_info"]["warrant"]
    # no *_date/*_exdate field exists on warrant — falls back to trading_from
    assert _extract_event_date("warrant", info) == "2018-06-07"


# ── _normalize_event ──────────────────────────────────────────────────────

def test_normalize_dividend_event():
    row = _normalize_event("BBCA", _dividend_event())
    assert row["ticker"] == "BBCA"
    assert row["action_type"] == "dividend"
    assert row["event_id"] == "117860"
    assert row["event_date"] == "2026-06-17"
    assert row["raw"]["dividend_value"] == "20"


def test_normalize_rightissue_event():
    row = _normalize_event("BRPT", _rightissue_event())
    assert row["event_id"] == "2493"
    assert row["event_date"] == "2018-05-31"
    assert row["raw"]["rightissue_ratio"] == "63 : 20"


def test_normalize_bonus_event_uses_sahambonus_id():
    row = _normalize_event("BRPT", _bonus_event())
    assert row["action_type"] == "bonus"
    assert row["event_id"] == "7683"


def test_normalize_returns_none_for_malformed_event():
    """A malformed API row (action_type present but action_info missing/
    empty) must be skipped, not crash the batch."""
    assert _normalize_event("BBCA", {"action_type": "dividend", "action_info": {}}) is None
    assert _normalize_event("BBCA", {"action_type": "dividend"}) is None
    assert _normalize_event("BBCA", {}) is None
