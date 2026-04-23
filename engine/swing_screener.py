"""
swing_screener.py — Trend-Onset Scorer for Swing-Trend Strategy.

Goal: detect stocks *just entering* a new uptrend (early-stage), not ones
already extended. Produces a 0-100 score from 7 weighted components.

Verdicts:
  score >= 60  -> SWING_ONSET  (actionable)
  40..60       -> WATCH        (pre-setup; monitor)
  < 40         -> SKIP

Public API:
  find_swing_points(df, n=2)      -> (highs_idx, lows_idx)
  score_swing_onset(df, flow_row) -> dict
"""

import numpy as np
import pandas as pd

from engine.regime_filter import calc_adx, calc_ma_slope
from engine.strategies import calc_atr, calc_vol_ratio


# ── Pivot detection ──────────────────────────────────────────────────

def find_swing_points(df: pd.DataFrame, n: int = 2):
    """
    2n+1 bar pivot: a bar is a swing-high if its high exceeds the N bars
    on each side, swing-low if its low is below the N bars on each side.
    Returns (highs_idx, lows_idx) — lists of df row indices.
    """
    highs, lows = [], []
    h, l = df['high'].values, df['low'].values
    for i in range(n, len(df) - n):
        window_h = h[i - n:i + n + 1]
        window_l = l[i - n:i + n + 1]
        if h[i] == window_h.max() and (window_h == h[i]).sum() == 1:
            highs.append(i)
        if l[i] == window_l.min() and (window_l == l[i]).sum() == 1:
            lows.append(i)
    return highs, lows


# ── Component checks ─────────────────────────────────────────────────

def _adx_rising(df: pd.DataFrame) -> tuple[bool, dict]:
    adx = calc_adx(df, 14)
    if len(adx) < 2 or pd.isna(adx.iloc[-1]) or pd.isna(adx.iloc[-2]):
        return False, {'adx': None, 'adx_prev': None}
    today = float(adx.iloc[-1])
    prev = float(adx.iloc[-2])
    ok = (today > prev) and (20 < today < 35)
    return ok, {'adx': round(today, 2), 'adx_prev': round(prev, 2)}


def _ma_slope_up(df: pd.DataFrame) -> tuple[bool, dict]:
    slope = calc_ma_slope(df, 20, 5)
    if len(slope) < 6 or pd.isna(slope.iloc[-1]) or pd.isna(slope.iloc[-6]):
        return False, {'slope': None, 'slope_5ago': None}
    s0 = float(slope.iloc[-1])
    s5 = float(slope.iloc[-6])
    ok = s0 > 0 and s0 > s5
    return ok, {'slope': round(s0, 3), 'slope_5ago': round(s5, 3)}


def _reclaimed_ma50(df: pd.DataFrame) -> tuple[bool, dict]:
    if len(df) < 51:
        return False, {'reclaimed': False}
    ma50 = df['close'].rolling(50).mean()
    close = df['close']
    if pd.isna(ma50.iloc[-1]):
        return False, {'reclaimed': False}
    above_now = close.iloc[-1] > ma50.iloc[-1]
    # at least one of the last 5 bars was at-or-below MA50
    window = slice(-6, -1)
    was_below = (close.iloc[window] <= ma50.iloc[window]).any()
    ok = bool(above_now and was_below)
    return ok, {'close': float(close.iloc[-1]), 'ma50': float(ma50.iloc[-1])}


def _higher_highs(df: pd.DataFrame) -> tuple[bool, dict]:
    highs_idx, lows_idx = find_swing_points(df, n=2)
    if len(highs_idx) < 2 or len(lows_idx) < 2:
        return False, {'pivots_h': len(highs_idx), 'pivots_l': len(lows_idx)}
    last_h = df['high'].iloc[highs_idx[-1]]
    prev_h = df['high'].iloc[highs_idx[-2]]
    last_l = df['low'].iloc[lows_idx[-1]]
    prev_l = df['low'].iloc[lows_idx[-2]]
    ok = bool((last_h > prev_h) and (last_l > prev_l))
    return ok, {'last_hh': float(last_h), 'prev_hh': float(prev_h),
                'last_hl': float(last_l), 'prev_hl': float(prev_l)}


def _vol_expansion(df: pd.DataFrame) -> tuple[bool, dict]:
    vr = calc_vol_ratio(df, 20)
    if pd.isna(vr.iloc[-1]):
        return False, {'vr': None}
    v = float(vr.iloc[-1])
    return v >= 1.5, {'vr': round(v, 2)}


def _flow_confirms(flow_row) -> tuple[bool, dict]:
    if not flow_row:
        return False, {'score': None}
    score = flow_row.get('composite_score') if isinstance(flow_row, dict) else getattr(flow_row, 'composite_score', None)
    if score is None:
        return False, {'score': None}
    return float(score) >= 2.0, {'score': float(score)}


def _not_overextended(df: pd.DataFrame) -> tuple[bool, dict]:
    if len(df) < 20:
        return False, {'distance_pct': None}
    ma20 = df['close'].rolling(20).mean().iloc[-1]
    close = df['close'].iloc[-1]
    if pd.isna(ma20) or ma20 <= 0:
        return False, {'distance_pct': None}
    dist = (close - ma20) / ma20 * 100
    return dist < 8.0, {'distance_pct': round(float(dist), 2)}


# ── Main scorer ──────────────────────────────────────────────────────

COMPONENT_WEIGHTS = {
    'adx_rising':       25,
    'ma_slope_up':      20,
    'reclaimed_ma50':   15,
    'higher_highs':     15,
    'vol_expansion':    10,
    'flow_confirms':    10,
    'not_overextended':  5,
}


def score_swing_onset(df: pd.DataFrame, flow_row=None) -> dict:
    """
    Compute 0-100 trend-onset score for the latest bar.

    Returns:
      {
        'score': int,
        'verdict': 'SWING_ONSET' | 'WATCH' | 'SKIP',
        'components': {name: {'passed': bool, 'weight': int, 'detail': {...}}},
        'close': float,
        'atr14': float,
        'initial_sl_hint': float,   # suggested initial stop
        'tp_projection': float,     # 3R aim (informational)
      }
    """
    if len(df) < 55:
        return {
            'score': 0, 'verdict': 'SKIP',
            'components': {}, 'reason': 'insufficient_data',
        }

    checks = {
        'adx_rising':       _adx_rising(df),
        'ma_slope_up':      _ma_slope_up(df),
        'reclaimed_ma50':   _reclaimed_ma50(df),
        'higher_highs':     _higher_highs(df),
        'vol_expansion':    _vol_expansion(df),
        'flow_confirms':    _flow_confirms(flow_row),
        'not_overextended': _not_overextended(df),
    }

    score = 0
    components = {}
    for name, (passed, detail) in checks.items():
        w = COMPONENT_WEIGHTS[name]
        if passed:
            score += w
        components[name] = {'passed': bool(passed), 'weight': w, 'detail': detail}

    verdict = 'SWING_ONSET' if score >= 60 else ('WATCH' if score >= 40 else 'SKIP')

    # Initial-SL hint = max(last swing low, MA50, entry - 1.5*ATR)
    atr = calc_atr(df, 14).iloc[-1]
    atr_val = float(atr) if not pd.isna(atr) else 0.0
    close = float(df['close'].iloc[-1])
    ma50 = float(df['close'].rolling(50).mean().iloc[-1]) if len(df) >= 50 else 0.0
    _, lows_idx = find_swing_points(df, n=2)
    last_swing_low = float(df['low'].iloc[lows_idx[-1]]) if lows_idx else 0.0

    candidates = [x for x in (last_swing_low, ma50, close - 1.5 * atr_val) if x > 0]
    initial_sl = max(candidates) if candidates else close * 0.95
    # SL must be below entry — cap at 97% of close if math produced ≥ close
    if initial_sl >= close:
        initial_sl = close * 0.97
    risk = close - initial_sl
    tp_projection = close + 3 * risk if risk > 0 else close * 1.06

    return {
        'score': score,
        'verdict': verdict,
        'components': components,
        'close': close,
        'atr14': round(atr_val, 4),
        'initial_sl_hint': round(initial_sl, 2),
        'tp_projection': round(tp_projection, 2),
    }
