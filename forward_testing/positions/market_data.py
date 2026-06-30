"""OHLCV reads + SMA-ATR for the SHADOW engine.

ATR is reimplemented locally (SMA convention, identical to engine.indicators.calc_atr)
so forward_testing stays stdlib-only — no pandas dependency.
"""
from forward_testing.storage.db import ft_get_db


def atr_sma(rows, period=14):
    """SMA-ATR. rows: list of (high, low, close) in ascending date order.

    Returns the mean of the last `period` True Ranges, or None if fewer than
    `period` bars are available (matches calc_atr's min_periods behaviour).
    """
    if len(rows) < period:
        return None
    trs = []
    prev_close = None
    for h, l, c in rows:
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c
    return sum(trs[-period:]) / period


class MarketDataResolver:
    """Reads ohlcv per ticker (cached for the run)."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._cache = {}

    def _rows(self, ticker):
        if ticker not in self._cache:
            with ft_get_db(self.db_path) as c:
                self._cache[ticker] = [
                    dict(r) for r in c.execute(
                        "SELECT date, open, high, low, close FROM ohlcv "
                        "WHERE ticker=? ORDER BY date", (ticker,)
                    ).fetchall()
                ]
        return self._cache[ticker]

    def atr14(self, ticker, as_of):
        rows = [(r["high"], r["low"], r["close"]) for r in self._rows(ticker) if r["date"] <= as_of]
        return atr_sma(rows, 14)

    def next_open(self, ticker, after_date):
        for r in self._rows(ticker):
            if r["date"] > after_date:
                return (r["date"], r["open"])
        return None

    def bar(self, ticker, on_date):
        for r in self._rows(ticker):
            if r["date"] == on_date:
                return (r["date"], r["open"], r["high"], r["low"], r["close"])
        return None
