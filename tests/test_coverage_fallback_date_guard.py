"""P0.E2.S1.T1 — EOD coverage-fallback date guard.

`screener_jobs.run_eod`'s coverage-fallback path used to take a ticker's
*last available* OHLCV bar and report it as trade_date's coverage without
checking the bar's own date — a stale bar (e.g. a ticker that stopped
trading days ago) would be silently written into daily_screen under today's
date. Tests the extracted `_coverage_fallback_row` helper directly, the same
idiom used for `_eod_calendar_cleanup` in test_eod_purge.py.
"""
import pandas as pd
import pytest

from screener.screener_jobs import _coverage_fallback_row

TRADE_DATE = "2026-07-30"


def _df(dates):
    """Build a minimal 20+ row OHLCV frame; the last row's date is `dates[-1]`."""
    n = len(dates)
    return pd.DataFrame({
        "date": dates,
        "open": [100.0] * n,
        "high": [105.0] * n,
        "low": [95.0] * n,
        "close": [102.0] * n,
        "volume": [1000.0] * n,
    })


def test_stale_last_bar_is_skipped_not_reported_as_trade_date():
    """Last bar dated before trade_date -> skipped with reason 'stale', no row."""
    dates = [f"2026-07-{d:02d}" for d in range(1, 21)]  # last real bar: 2026-07-20
    row, reason = _coverage_fallback_row("AAAA", _df(dates), TRADE_DATE)
    assert row is None
    assert reason == "stale"


def test_fresh_last_bar_still_computes_a_row():
    """Last bar dated == trade_date -> unchanged behavior, a row is computed."""
    dates = [f"2026-07-{d:02d}" for d in range(1, 20)] + [TRADE_DATE]  # 20 rows, last == trade_date
    row, reason = _coverage_fallback_row("AAAA", _df(dates), TRADE_DATE)
    assert reason is None
    assert row is not None
    assert row["signal"] in {"neutral", "bullish", "bearish", "watch"}
    assert row["close"] == 102


def test_insufficient_history_skipped_unchanged_from_prior_behavior():
    """Fewer than 20 bars -> skipped with reason 'insufficient_history' (pre-existing guard, untouched)."""
    dates = [f"2026-07-{d:02d}" for d in range(1, 10)]  # only 9 rows
    row, reason = _coverage_fallback_row("AAAA", _df(dates), TRADE_DATE)
    assert row is None
    assert reason == "insufficient_history"


def test_missing_ticker_dataframe_skipped():
    """No OHLCV history at all for the ticker (df=None) -> insufficient_history."""
    row, reason = _coverage_fallback_row("ZZZZ", None, TRADE_DATE)
    assert row is None
    assert reason == "insufficient_history"
