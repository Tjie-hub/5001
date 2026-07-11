"""Corporate-action adjustment — the consumer the corporate_actions table was
built for (Phase 2A promised it; research audit R-1 delivered it).

Basis contract (C-4): ohlcv storage is RAW exchange prices, always. This module
back-adjusts a loaded frame through stock splits so research sees a continuous
current-basis series: for a split of ratio k (yfinance new/old shares) on
ex-date d, every bar strictly BEFORE d gets price/k and volume*k, compounding
across multiple splits. The ex-date bar itself already trades on the new basis.

Dividends are deliberately NOT price-adjusted: signals run on a price-return
basis (what the tape actually printed); total-return adjustment would move
every historical level away from real traded prices.
"""
import math


def load_split_factors(conn):
    """{ticker: [(ex_date, ratio), ...]} from corporate_actions, date-sorted.

    Ratios <= 0, NaN, or exactly 1.0 (no-op) are dropped. Fail-soft: a DB
    without the table (pre-migration, test fixtures) yields {} — raw data.
    """
    try:
        rows = conn.execute(
            "SELECT ticker, date, value FROM corporate_actions "
            "WHERE action='split' ORDER BY ticker, date").fetchall()
    except Exception:
        return {}
    factors = {}
    for ticker, date, value in rows:
        try:
            ratio = float(value)
        except (TypeError, ValueError):
            continue
        if math.isnan(ratio) or ratio <= 0 or ratio == 1.0:
            continue
        factors.setdefault(ticker, []).append((str(date), ratio))
    return factors


def adjust_ohlcv(df, splits):
    """Back-adjust one ticker's OHLCV frame through `splits` [(ex_date, ratio)].

    Returns the (possibly modified) frame; no-op input is returned unchanged.
    Dates compare as ISO strings — the corpus convention. The input frame is
    never written back to storage; raw prices stay raw.
    """
    valid = [(d, r) for d, r in splits
             if isinstance(r, (int, float)) and not math.isnan(r) and r > 0 and r != 1.0]
    if not valid or df is None or len(df) == 0:
        return df
    df = df.copy()
    dates = df["date"].astype(str)
    for ex_date, ratio in valid:
        before = dates < ex_date
        if not before.any():
            continue
        for col in ("open", "high", "low", "close"):
            df.loc[before, col] = df.loc[before, col] / ratio
        df.loc[before, "volume"] = df.loc[before, "volume"] * ratio
    return df
