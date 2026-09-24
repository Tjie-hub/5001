"""RC-0001-MAX — lottery avoidance on the IDX liquid universe (D-055 Rule Card).

Signal (Julianto & Ekaputra 2020; Bali, Cakici & Whitelaw 2011 MAX(1)): the highest
close-to-close daily return inside the formation's calendar month. At a month-end row
this is the month's maximum; at any other row it is the maximum so far — both use only
rows dated on or before that row (the LA-1 prefix check verifies it on every run).

Why these choices, so nobody "fixes" them later:
- MAX(1), not MAX(5): the IDX paper this card replicates sorts on the single highest day.
  MAX(5) and the limit-hit count are declared variants — each would be its own card.
- close-to-close returns: the first return of a month uses the prior month's last close,
  exactly as a daily return series does.
- ties at the auto-rejection cap (many names print exactly +25% / +35%) are broken by the
  engine's deterministic ticker order; the price-limit-modified MAX is a declared variant.
"""
import pandas as pd

from research.rulecard.data import load_extended_ohlcv


def load_panel(ctx):
    return load_extended_ohlcv()


def signal(panel: pd.DataFrame) -> pd.Series:
    ret = panel.groupby("ticker", sort=False)["close"].pct_change()
    month = panel["date"].dt.to_period("M")
    return ret.groupby([panel["ticker"], month], sort=False).cummax()
