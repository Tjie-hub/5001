"""RC-0002-FB-PRE2021 — failed-breakdown anti-edge, out-of-sample on the pre-2021 backfill.

Signal = FADE-001's frozen definition (P-M/forward_fade/scripts/fade_failed_breakdown.py):
on day t the low breaks the lowest low of the prior 20 sessions (today excluded) and the close
ends back above it. The engine adds eligibility (liquid_idx_v1), next-open entry, a 20-session
hold and the day-weighted calendar-time estimand.

Why these choices, so nobody "fixes" them later:
- LOOKBACK 20 and the strict inequalities are FADE-001's, copied, not re-chosen (R2).
- load_panel cuts at 2021-07-05. Everything on or after that date is the corpus the pattern was
  discovered on (pattern scan 2026-09-17); reading it would turn a replication into a re-cut.
- No holding-window contamination guard. FADE-001 had one and it read the future (audit R-3);
  bad data fails SPL-1 here instead.
"""
import pandas as pd

from research.rulecard.data import load_extended_ohlcv

CUT = pd.Timestamp("2021-07-05")
LOOKBACK = 20


def load_panel(ctx):
    P = load_extended_ohlcv()
    P = P[pd.to_datetime(P["date"]) < CUT].reset_index(drop=True)
    if len(P) and pd.to_datetime(P["date"]).max() >= CUT:
        raise RuntimeError("discovery-period rows present")
    return P


def signal(panel: pd.DataFrame) -> pd.Series:
    lo20 = panel.groupby("ticker", sort=False)["low"].transform(
        lambda s: s.rolling(LOOKBACK, min_periods=LOOKBACK).min().shift(1))
    return ((panel["low"] < lo20) & (panel["close"] > lo20)).astype(float)
