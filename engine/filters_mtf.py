"""engine/filters_mtf.py — the weekly multi-timeframe trend gate, as a causal
per-bar mask.

WHY THIS EXISTS (audit 2026-09-02, finding L-1)
------------------------------------------------
`engine.indicators.calc_weekly_trend(df)` answers "does the LAST bar of this
frame pass the weekly trend gate?". The live scanner applies it to every signal
(`check_current_entry_signal`, all strategies outside `_WEEKLY_GATE_BYPASS`);
the walk-forward backtest applies nothing. So `wf_edge` measured a rule that
production does not execute, and the OOS claim did not describe the deployed
system.

The remedy chosen (documented in engine/rule_identity.py) is to RESEARCH the
production variant rather than remove the gate. That needs the same gate
expressed as a per-bar boolean mask so `run_walk_forward(..., filters=[...])`
can apply it at every candidate entry bar exactly as live applies it at the
signal bar.

CAUSALITY
---------
`mask[i]` uses only bars 0..i. The current (partial) week's weekly close is the
close of bar i itself — which is precisely what the live gate sees intraday, since
`calc_weekly_trend` resamples the frame it is handed and the last weekly bucket
is the in-progress week. No future bar enters any value.

EQUIVALENCE
-----------
This is not "a weekly filter"; it must be THE gate. Equivalence with
`calc_weekly_trend(df.iloc[:i+1])[0]` is asserted bar-by-bar over real corpus
data in tests/test_filters_mtf.py. If the two ever diverge, the parity claim
that admits a strategy to live trading is void.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Mirrors engine.indicators.calc_weekly_trend exactly.
MIN_BARS = 100          # below this the live gate soft-passes
MIN_WEEKS = 22          # below this the live gate soft-passes
MA_WEEKS = 20           # weekly MA length
SLOPE_LOOKBACK = 5      # weeks back for the MA slope
SLOPE_FLOOR = -1.0      # slope >= this passes

# Bars of prior history needed before the gate is fully warm: MA_WEEKS +
# SLOPE_LOOKBACK weeks of weekly data ≈ 25 weeks ≈ 125 trading bars, and the
# gate additionally soft-passes under MIN_BARS. 160 gives comfortable margin and
# is what the parity walk-forward run uses as its warm-up tail.
WARMUP_BARS = 160


def weekly_mtf_mask(df: pd.DataFrame) -> pd.Series:
    """Per-bar boolean: would the live weekly gate pass if this bar were last?

    Vectorised. Returns a Series aligned to `df.index`.
    """
    n = len(df)
    if n == 0:
        return pd.Series([], dtype=bool, index=df.index)

    dates = pd.to_datetime(df["date"])
    close = df["close"].astype(float).to_numpy()

    # Week bucket per bar. pandas 'W' resample closes on Sunday; to_period('W')
    # uses the same Mon-Sun convention, so bucket boundaries agree.
    week = dates.dt.to_period("W")
    # K[i] = 0-based position of bar i's week within the weekly series formed by
    # bars 0..i (i.e. how many completed weeks precede it).
    new_week = np.empty(n, dtype=bool)
    new_week[0] = True
    new_week[1:] = week.to_numpy()[1:] != week.to_numpy()[:-1]
    K = np.cumsum(new_week) - 1

    # complete_last[k] = closing price of the last bar of week k.
    last_idx_of_week = np.where(np.append(new_week[1:], True))[0]
    complete_last = close[last_idx_of_week]          # length = number of weeks
    csum = np.concatenate([[0.0], np.cumsum(complete_last)])

    def _win(a, b):
        """sum(complete_last[a:b]) with clamping; NaN when out of range."""
        return csum[b] - csum[a]

    out = np.ones(n, dtype=bool)

    for i in range(n):
        if i + 1 < MIN_BARS:
            continue                     # soft-pass: insufficient data
        k = K[i]
        n_weeks = k + 1
        if n_weeks < MIN_WEEKS:
            continue                     # soft-pass: insufficient weeks
        if k < MA_WEEKS - 1:
            continue                     # cur_ma20 would be NaN -> soft-pass
        # cur_ma20 over the as-of-i weekly array: last 19 COMPLETED weeks plus
        # this bar's close standing in for the in-progress week.
        cur_ma20 = (_win(k - (MA_WEEKS - 1), k) + close[i]) / MA_WEEKS
        if not np.isfinite(cur_ma20) or cur_ma20 <= 0:
            continue                     # soft-pass: ma20 unusable
        # ma20_5w = wma20 at position k-5 of the same array; every entry there is
        # a completed week, so it reads straight off complete_last.
        j = k - SLOPE_LOOKBACK
        if n_weeks >= 6 and j >= MA_WEEKS - 1:
            ma20_5w = _win(j - (MA_WEEKS - 1), j + 1) / MA_WEEKS
        else:
            ma20_5w = np.nan             # matches wma20.iloc[0] / NaN -> slope 0
        slope = (float((cur_ma20 - ma20_5w) / ma20_5w * 100)
                 if (np.isfinite(ma20_5w) and ma20_5w > 0) else 0.0)
        out[i] = bool(close[i] >= cur_ma20 and slope >= SLOPE_FLOOR)

    return pd.Series(out, index=df.index)


# ── memoised wrapper ─────────────────────────────────────────────────────────
# apply_filters() calls the filter once per STRATEGY per window on the SAME
# frame. Recomputing the mask 11x per window would dominate the parity run, so
# cache on a cheap content fingerprint (length + first/last date + last close).
# Bounded: one entry per window, cleared between tickers by the job.
_MASK_CACHE: dict = {}
_MASK_CACHE_MAX = 64


def _fingerprint(df: pd.DataFrame):
    return (len(df), str(df["date"].iloc[0]), str(df["date"].iloc[-1]),
            float(df["close"].iloc[-1]), float(df["close"].iloc[0]))


def weekly_mtf_filter(df: pd.DataFrame) -> pd.Series:
    """Memoised `weekly_mtf_mask` for use in `filters=[...]`."""
    if len(df) == 0:
        return weekly_mtf_mask(df)
    key = _fingerprint(df)
    hit = _MASK_CACHE.get(key)
    if hit is not None and len(hit) == len(df):
        return pd.Series(hit.to_numpy(), index=df.index)
    mask = weekly_mtf_mask(df)
    if len(_MASK_CACHE) >= _MASK_CACHE_MAX:
        _MASK_CACHE.clear()
    _MASK_CACHE[key] = mask
    return mask


def clear_mask_cache() -> int:
    n = len(_MASK_CACHE)
    _MASK_CACHE.clear()
    return n


# The callable `run_strategy(filters=[...])` / `apply_filters` expect.
WEEKLY_MTF_FILTER = weekly_mtf_filter
