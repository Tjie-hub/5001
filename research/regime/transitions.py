"""Market-wide (IHSG) regime-transition detector (spec §7, Flow B).

Descriptive/context overlay only — it does NOT re-key edge cells. Input is a
per-date regime label series (from engine.regime_filter.detect_regime rolled over
the IHSG history); output tags each date STEADY / TRANSITION + a direction.
"""
from __future__ import annotations

import pandas as pd


def detect_transitions(regime_series: pd.DataFrame, k_bars: int) -> pd.DataFrame:
    """regime_series: DataFrame with 'date' (sorted asc) and 'regime'. Returns the
    same rows with added 'state' (STEADY/TRANSITION) and 'direction' (str|None).

    A bar is TRANSITION if the regime changed on any of the last k_bars (inclusive
    of the change bar itself)."""
    df = regime_series.sort_values("date").reset_index(drop=True)
    prev = df["regime"].shift(1)
    changed = (df["regime"] != prev) & prev.notna()

    states, directions = [], []
    last_change_idx = None
    last_direction = None
    for i in range(len(df)):
        if changed.iloc[i]:
            last_change_idx = i
            last_direction = f"{prev.iloc[i]}->{df['regime'].iloc[i]}"
        within = last_change_idx is not None and (i - last_change_idx) < k_bars
        states.append("TRANSITION" if within else "STEADY")
        directions.append(last_direction if within else None)

    out = df.copy()
    out["state"] = states
    out["direction"] = directions
    return out
