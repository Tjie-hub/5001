"""MarketDataResolver: ATR14 (SMA), next_open, bar — read from ohlcv."""
import sqlite3
from forward_testing.positions.market_data import atr_sma, MarketDataResolver
from tests.forward_testing.conftest import seed_ohlcv


def test_atr_sma_matches_simple_average_of_true_range():
    # 14 flat bars (h=11,l=9,c=10): TR=2 each -> ATR14=2.0
    rows = [(11, 9, 10)] * 14
    assert atr_sma(rows, 14) == 2.0


def test_atr_sma_none_when_insufficient_history():
    assert atr_sma([(11, 9, 10)] * 13, 14) is None


def test_atr_sma_uses_gap_vs_prev_close():
    rows = [(11, 9, 10), (12, 11, 11.5)]   # bar1 TR = max(1, |12-10|, |11-10|) = 2
    assert atr_sma(rows, 2) == 2.0          # mean(2, 2)


def _resolver(ft_db):
    conn = sqlite3.connect(ft_db)
    seed_ohlcv(conn, "BBCA", [
        ("2026-06-20", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-21", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-22", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-23", 100, 100.5, 99.5, 100, 1000),
        ("2026-06-27", 105, 105.5, 104.5, 105, 1000),   # D+1 open after a 06-26 signal
    ])
    conn.commit(); conn.close()
    return MarketDataResolver(ft_db)


def test_resolver_next_open_returns_first_bar_after(ft_db):
    r = _resolver(ft_db)
    assert r.next_open("BBCA", "2026-06-26") == ("2026-06-27", 105)


def test_resolver_next_open_none_when_no_future_bar(ft_db):
    r = _resolver(ft_db)
    assert r.next_open("BBCA", "2026-06-29") is None


def test_resolver_bar_returns_ohlc(ft_db):
    r = _resolver(ft_db)
    assert r.bar("BBCA", "2026-06-27") == ("2026-06-27", 105, 105.5, 104.5, 105)
    assert r.bar("BBCA", "2026-06-30") is None


def test_resolver_atr14_none_with_too_few_bars(ft_db):
    r = _resolver(ft_db)   # only 5 bars seeded
    assert r.atr14("BBCA", "2026-06-27") is None


def test_resolver_skips_null_ohlc_bars(ft_db):
    # Prod ohlcv carries all-NULL rows for non-trading/suspended days; they must not
    # crash ATR math and must read as 'no bar' (missing -> manager holds).
    conn = sqlite3.connect(ft_db)
    bars = [("2026-05-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 15)]  # 14 valid
    bars.append(("2026-05-20", None, None, None, None, 0))                            # non-trading day
    seed_ohlcv(conn, "NULLY", bars)
    conn.commit(); conn.close()
    r = MarketDataResolver(ft_db)
    assert r.atr14("NULLY", "2026-05-20") == 1.0     # computed from the 14 valid bars only
    assert r.bar("NULLY", "2026-05-20") is None      # NULL-OHLC date treated as missing
    assert r.next_open("NULLY", "2026-05-14") is None  # no valid bar after the last good day
