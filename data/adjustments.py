"""Corporate-action adjustment — the consumer the corporate_actions table was
built for (Phase 2A promised it; research audit R-1 delivered it).

BASIS REALITY (verified 2026-07-11, Phase A validation): the stored corpus is
already SPLIT-adjusted at the source — yfinance adjusts OHLC for splits even
with auto_adjust=False, and the 2026-07-03 raw rebuild inherited that basis
(dividends stay unadjusted = true traded prices). So for splits known at
rebuild time there is NO gap in the series. The residual risk is a FUTURE
split: the scraper appends new-basis bars after stored old-basis history,
printing a real gap until the next full refetch.

Therefore adjustment is GAP-VERIFIED: a split factor is applied only when the
series actually exhibits the gap at the ex-date (observed prev/post close
ratio within tolerance of the declared ratio). Blindly applying factors to an
already-continuous series double-adjusts and fabricates rallies — that
exact incident (CUAN momentum +39%/trade) is pinned as a regression test.

Ratios below MIN_VERIFIABLE_RATIO can't be distinguished from ordinary daily
moves (IDX auto-rejection bands reach ±35%) and are immaterial — skipped.
Storage is never modified; adjustment applies to loaded frames only.
"""
import math

# A gap must be at least this large (or its reciprocal) to be told apart from
# a normal trading move; smaller corporate actions are skipped as immaterial.
MIN_VERIFIABLE_RATIO = 1.5
# Observed prev/post close ratio must fall within [ratio*0.6, ratio*1.6] to
# count as the split's gap — wide enough for a ±35% same-day market move,
# far from the ~1.0 of an already-adjusted series (for ratio >= 1.5).
GAP_TOL_LO, GAP_TOL_HI = 0.6, 1.6


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


def _gap_is_real(dates, closes, ex_date: str, ratio: float) -> bool:
    """True iff the series shows the split's PERSISTENT gap at ex_date.

    Compares the last close strictly before the ex-date against the MEDIAN of
    the first three closes on/after it — a real basis change persists, while
    a single bad tick (TMAS 2023-05-23: 298 -> 43 -> 286) bounces back and
    must not count. Additionally the observed ratio must be closer in log
    space to the declared ratio than to 1.0 — an already-adjusted continuous
    series (~1.0) must never be re-adjusted even when a small declared ratio's
    tolerance band brushes 1.0 (BBRM 2:3 case).
    """
    if max(ratio, 1.0 / ratio) < MIN_VERIFIABLE_RATIO:
        return False
    before = dates < ex_date
    after = ~before
    if not before.any() or not after.any():
        return False
    prev_close = closes[before].iloc[-1]
    post = sorted(closes[after].iloc[:3])
    post_close = post[len(post) // 2]           # median of up to 3 post bars
    if post_close <= 0 or prev_close <= 0:
        return False
    observed = prev_close / post_close
    if not (ratio * GAP_TOL_LO <= observed <= ratio * GAP_TOL_HI):
        return False
    return abs(math.log(observed / ratio)) < abs(math.log(observed))


def adjust_ohlcv(df, splits):
    """Back-adjust one ticker's OHLCV frame through gap-verified `splits`
    [(ex_date, ratio)]: bars strictly before the ex-date get price/ratio and
    volume*ratio, compounding across multiple verified splits.

    Returns the (possibly modified) frame; no-op input is returned unchanged.
    Dates compare as ISO strings — the corpus convention. Verification runs
    against the ORIGINAL series so sequential real splits each see their own
    gap. The input frame is never written back to storage.
    """
    if df is None or len(df) == 0:
        return df
    valid = [(d, r) for d, r in splits
             if isinstance(r, (int, float)) and not math.isnan(r)
             and r > 0 and r != 1.0]
    if not valid:
        return df
    dates = df["date"].astype(str)
    orig_closes = df["close"]
    applicable = [(d, r) for d, r in valid
                  if _gap_is_real(dates, orig_closes, d, r)]
    if not applicable:
        return df
    df = df.copy()
    for ex_date, ratio in applicable:
        before = dates < ex_date
        for col in ("open", "high", "low", "close"):
            df.loc[before, col] = df.loc[before, col] / ratio
        df.loc[before, "volume"] = df.loc[before, "volume"] * ratio
    return df
