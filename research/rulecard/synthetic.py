"""Synthetic IDX-like panels with a planted, known effect (D-055).

Used by tests and by rule-script self-tests. Touches no real data.

A latent monthly characteristic `z` is revealed on every row of month m-1 and drives
the drift of month m, so a trailing-only signal (score = z at the month-end formation)
predicts the next holding month exactly as a real characteristic would. Names in the
top `planted_frac` of z get a drift of `effect_pct_per_month` (negative = underperform).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_panel(n_tickers: int = 120, years: int = 6, effect_pct_per_month: float = 0.0,
               planted_frac: float = 0.10, vol: float = 0.02, seed: int = 0,
               start: str = "2015-01-01", shape: str = "step",
               low_adv_boost: float | None = None) -> pd.DataFrame:
    """shape: 'step'   — full effect on the top `planted_frac` of z, nothing elsewhere
                        (what a binary chart trigger looks like);
              'tail'   — effect grows linearly from the median of z to the top
                        (a tail mechanism such as lottery demand);
              'linear' — effect linear in the z rank across the whole cross-section.
    effect_pct_per_month is the drift at the very top of z.
    low_adv_boost: if set, even-numbered names trade 10x less value and carry the effect
    x low_adv_boost — a planted fingerprint (the effect is stronger in low-ADV names)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=252 * years)
    months = dates.to_period("M")
    mcodes, month_idx = np.unique(months.astype(str), return_inverse=True)
    n_m = len(mcodes)
    Z = rng.normal(size=(n_m + 1, n_tickers))       # Z[k] is revealed in month k, acts in k+1
    pct = (Z.argsort(axis=1).argsort(axis=1) + 0.5) / n_tickers
    if shape == "step":
        mult = (pct >= 1 - planted_frac).astype(float)
    elif shape == "tail":
        mult = np.clip((pct - 0.5) / 0.5, 0.0, 1.0)
    elif shape == "linear":
        mult = pct - 0.5
    else:
        raise ValueError("shape must be step, tail or linear")
    frames = []
    for i in range(n_tickers):
        acts = np.r_[0.0, mult[:-2, i]]               # month k drift set by Z[k-1]
        low = low_adv_boost is not None and i % 2 == 0
        boost = low_adv_boost if low else 1.0
        volume = (5e6 if low else 5e7) if low_adv_boost is not None else 1e7
        drift = acts[month_idx] * effect_pct_per_month * boost / 21.0 / 100.0
        r = rng.normal(drift - vol ** 2 / 2, vol, len(dates))
        close = 1000.0 * np.exp(np.cumsum(r))
        gap = np.exp(rng.normal(0, 0.002, len(dates)))
        open_ = np.r_[close[0], close[:-1]] * gap
        rngv = np.abs(rng.normal(0, vol, len(dates))) + vol / 2
        hi = np.maximum(open_, close) * np.exp(rngv / 2)
        lo = np.minimum(open_, close) * np.exp(-rngv / 2)
        frames.append(pd.DataFrame({
            "ticker": f"S{i:03d}", "date": dates, "open": open_, "high": hi, "low": lo,
            "close": close, "volume": volume, "z": Z[month_idx, i]}))
    return pd.concat(frames, ignore_index=True)


def z_signal(panel: pd.DataFrame) -> pd.Series:
    """Trailing-only reference signal: the characteristic revealed on this row."""
    return panel["z"].astype(float)


def make_event_panel(n_tickers: int = 80, years: int = 4, effect_pct_per_event: float = 0.0,
                     hold: int = 20, event_rate: float = 0.005, vol: float = 0.02, seed: int = 0,
                     start: str = "2012-01-02", low_adv_boost: float | None = None) -> pd.DataFrame:
    """Random 0/1 events (column `ev`, known at that row's close); each event adds a drift of
    effect_pct_per_event spread evenly over the name's next `hold` sessions. low_adv_boost as in
    make_panel (even-numbered names trade 10x less value and carry the effect x boost)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=252 * years)
    T = len(dates)
    frames = []
    for i in range(n_tickers):
        ev = rng.random(T) < event_rate
        ev[:30] = False
        low = low_adv_boost is not None and i % 2 == 0
        boost = low_adv_boost if low else 1.0
        volume = (5e6 if low else 5e7) if low_adv_boost is not None else 1e7
        drift = np.zeros(T)
        for t in np.flatnonzero(ev):
            drift[t + 1:t + 1 + hold] += effect_pct_per_event * boost / 100.0 / hold
        r = rng.normal(drift - vol ** 2 / 2, vol, T)
        close = 1000.0 * np.exp(np.cumsum(r))
        gap = np.exp(rng.normal(0, 0.002, T))
        open_ = np.r_[close[0], close[:-1]] * gap
        rngv = np.abs(rng.normal(0, vol, T)) + vol / 2
        hi = np.maximum(open_, close) * np.exp(rngv / 2)
        lo = np.minimum(open_, close) * np.exp(-rngv / 2)
        frames.append(pd.DataFrame({"ticker": f"S{i:03d}", "date": dates, "open": open_, "high": hi,
                                    "low": lo, "close": close, "volume": volume,
                                    "ev": ev.astype(float)}))
    return pd.concat(frames, ignore_index=True)


def ev_signal(panel: pd.DataFrame) -> pd.Series:
    """Trailing-only reference event flag: the event revealed at this row's close."""
    return panel["ev"].astype(float)
