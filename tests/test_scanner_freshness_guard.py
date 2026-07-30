"""P0.E2.S1.T2 — minimal last-bar freshness guard wired into scan loops
(audit H-3: `scheduler/scanner.py`'s `scan_momentum_signals` and
`scheduled_multi_strategy_scan`).

Follows the same wiring idiom as tests/test_scanner_vpin_gate.py: drive the
real scan function with every other filter switched off, and prove whether
downstream code was reached by spying on the first call made after the
freshness check.
"""
from datetime import date, timedelta

import pandas as pd
import pytest

import scheduler.scanner as scanner
from engine.calendar_filter import is_trading_day


def _previous_trading_day(from_date: date) -> date:
    d = from_date
    while True:
        d -= timedelta(days=1)
        is_open, _ = is_trading_day(d)
        if is_open:
            return d


TODAY = date.today()
ONE_SESSION_AGO = _previous_trading_day(TODAY)          # boundary: still fresh (<=1)
TWO_SESSIONS_AGO = _previous_trading_day(ONE_SESSION_AGO)  # boundary: stale (>1)


def _ohlcv_df(last_bar_date: date, n: int = 25):
    """n-row df ending on `last_bar_date`; enough rows to clear the
    pre-existing len(df)<25/20 history guards in both scan loops."""
    dates = [(last_bar_date - timedelta(days=n - 1 - i)).isoformat() for i in range(n)]
    return pd.DataFrame({
        "date": dates,
        "open": [100.0] * n, "high": [105.0] * n, "low": [95.0] * n,
        "close": list(range(100, 100 + n)), "volume": [1000.0] * n,
    })


@pytest.fixture
def wire_momentum_scan(monkeypatch):
    """Every scan_momentum_signals() dependency wired to a no-op except the
    ohlcv map, VPIN/fundamental/sector/flow/liquidity all switched off, so
    control reaches the freshness check (right after the len(df)<25 guard)
    directly."""
    monkeypatch.setattr("engine.calendar_filter.is_trading_day", lambda *a, **k: (True, ""))
    monkeypatch.setattr("engine.calendar_filter.is_blackout_day", lambda *a, **k: (False, ""))
    monkeypatch.setattr(scanner, "get_all_tickers", lambda: ["TESTFRESH"])
    monkeypatch.setattr(scanner, "_get_sector_scores_cached", lambda: [])
    monkeypatch.setattr("engine.regime_filter.get_macro_overlay",
                         lambda *a, **k: {"idr_weakening": 0.0, "bi_rate": 6.25, "source": "test"})
    monkeypatch.setattr("paper_trade.get_config", lambda: {
        "filter_fundamental": 0, "filter_sector": 0, "filter_flow": 0,
        "filter_rs": 0, "filter_regime": 0, "filter_vpin": 0, "filter_liquidity": 0,
        "disabled_strategies": "",
    })

    class _FakeConn:
        def execute(self, *_a, **_k):
            return self

        def fetchall(self):
            return []

        def close(self):
            pass

    monkeypatch.setattr(scanner, "db_connect", lambda *_a, **_k: _FakeConn())

    def _set(df: pd.DataFrame):
        monkeypatch.setattr(scanner, "_load_ohlcv_bulk", lambda: {"TESTFRESH": df})

    return _set


def test_fresh_last_bar_reaches_downstream_processing(wire_momentum_scan, monkeypatch):
    """Last bar dated today -> freshness guard passes, scan proceeds to
    compute the signal (proven via a spy on calc_vol_ratio, the first call
    made right after the freshness check)."""
    downstream_reached = []
    monkeypatch.setattr("engine.indicators.calc_vol_ratio",
                         lambda *a, **k: downstream_reached.append(1) or pd.Series([1.0] * 25))
    wire_momentum_scan(_ohlcv_df(TODAY))

    scanner.scan_momentum_signals()

    assert downstream_reached == [1]


def test_stale_last_bar_is_skipped_before_downstream_processing(wire_momentum_scan, monkeypatch, caplog):
    """Last bar 30 calendar days old -> freshness guard blocks the ticker;
    calc_vol_ratio (first call after the guard) is never reached, and the
    aggregate stale-skip warning is logged (skip + count + one alert)."""
    downstream_reached = []
    monkeypatch.setattr("engine.indicators.calc_vol_ratio",
                         lambda *a, **k: downstream_reached.append(1))
    wire_momentum_scan(_ohlcv_df(TODAY - timedelta(days=30)))

    import logging
    with caplog.at_level(logging.WARNING):
        result = scanner.scan_momentum_signals()

    assert result == []
    assert downstream_reached == []
    assert any("stale last bar" in r.message for r in caplog.records)


def test_boundary_one_session_old_is_still_fresh(wire_momentum_scan, monkeypatch):
    """Exactly 1 trading session old (the default max_age_sessions) -> still
    fresh, still reaches downstream."""
    downstream_reached = []
    monkeypatch.setattr("engine.indicators.calc_vol_ratio",
                         lambda *a, **k: downstream_reached.append(1) or pd.Series([1.0] * 25))
    wire_momentum_scan(_ohlcv_df(ONE_SESSION_AGO))

    scanner.scan_momentum_signals()

    assert downstream_reached == [1]


def test_boundary_two_sessions_old_is_stale(wire_momentum_scan, monkeypatch):
    """2 trading sessions old (one more than the default threshold) -> stale,
    blocked before downstream processing."""
    downstream_reached = []
    monkeypatch.setattr("engine.indicators.calc_vol_ratio",
                         lambda *a, **k: downstream_reached.append(1))
    wire_momentum_scan(_ohlcv_df(TWO_SESSIONS_AGO))

    result = scanner.scan_momentum_signals()

    assert result == []
    assert downstream_reached == []


class _FakeDistConn:
    """Cold-review fix: scan_distribution_signals() reads ohlcv_map
    independently of scan_momentum_signals/scheduled_multi_strategy_scan's
    adaptive-selection loop (its own DB query drives its own ticker set), so
    it needs its own freshness-guard coverage — it was missed by the
    original P0.E2.S1.T2 diff."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_a, **_k):
        return self

    def fetchall(self):
        return self._rows

    def close(self):
        pass


def _decline_df(last_bar_date: date, n: int = 10) -> pd.DataFrame:
    """Same shape as _ohlcv_df but close[-1] < close[-5], satisfying
    scan_distribution_signals' decline check independent of the freshness
    guard under test."""
    df = _ohlcv_df(last_bar_date, n=n)
    df.loc[df.index[-1], "close"] = 90.0
    return df


def test_distribution_scan_fresh_last_bar_reaches_downstream_processing(monkeypatch):
    monkeypatch.setattr(scanner, "db_connect",
                         lambda *_a, **_k: _FakeDistConn([("TESTFRESH", -4, "")]))
    monkeypatch.setattr(scanner, "_safe_regime", lambda df: "BEAR")

    results = scanner.scan_distribution_signals(
        {"TESTFRESH": _decline_df(TODAY)}, TODAY.isoformat(), "16:00")

    assert [r["ticker"] for r in results] == ["TESTFRESH"]


def test_distribution_scan_stale_last_bar_is_skipped_before_downstream_processing(monkeypatch, caplog):
    monkeypatch.setattr(scanner, "db_connect",
                         lambda *_a, **_k: _FakeDistConn([("TESTSTALE", -4, "")]))
    monkeypatch.setattr(scanner, "_safe_regime", lambda df: "BEAR")

    import logging
    with caplog.at_level(logging.WARNING):
        results = scanner.scan_distribution_signals(
            {"TESTSTALE": _decline_df(TODAY - timedelta(days=30))}, TODAY.isoformat(), "16:00")

    assert results == []
    assert any("stale last bar" in r.message for r in caplog.records)


def test_distribution_scan_boundary_one_session_old_is_still_fresh(monkeypatch):
    monkeypatch.setattr(scanner, "db_connect",
                         lambda *_a, **_k: _FakeDistConn([("TESTFRESH", -4, "")]))
    monkeypatch.setattr(scanner, "_safe_regime", lambda df: "BEAR")

    results = scanner.scan_distribution_signals(
        {"TESTFRESH": _decline_df(ONE_SESSION_AGO)}, TODAY.isoformat(), "16:00")

    assert [r["ticker"] for r in results] == ["TESTFRESH"]


def test_distribution_scan_boundary_two_sessions_old_is_stale(monkeypatch):
    monkeypatch.setattr(scanner, "db_connect",
                         lambda *_a, **_k: _FakeDistConn([("TESTSTALE", -4, "")]))
    monkeypatch.setattr(scanner, "_safe_regime", lambda df: "BEAR")

    results = scanner.scan_distribution_signals(
        {"TESTSTALE": _decline_df(TWO_SESSIONS_AGO)}, TODAY.isoformat(), "16:00")

    assert results == []
