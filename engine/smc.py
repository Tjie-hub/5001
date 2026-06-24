"""
engine/smc.py — ICT Institutional SMC Detection Library for IDX
=================================================================
Adapted from "Advanced ICT Institutional SMC Trading Book" (David Woods, 2022)
for the Indonesian Stock Exchange (IDX) market structure.

Three core concepts implemented:
  1. DAILY OPEN (D.O.) — Premium/Discount zones
  2. FAIR VALUE GAP (FVG) — Imbalance detection & fill tracking
  3. LIQUIDITY SWEEP — PDH/PDL & Weekly high/low trap detection

All functions accept a DataFrame with OHLCV columns (date-ascending) and
return pd.Series aligned to the input index, following the same contract
as engine/indicators.py.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, List, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DAILY OPEN (D.O.) — Premium / Discount
# ═══════════════════════════════════════════════════════════════════════════════
#
# The Daily Open acts as a fair-value reference line (like VWAP but simpler).
#   - Price ABOVE D.O. = PREMIUM (favor shorts / tighten TP on longs)
#   - Price BELOW D.O. = DISCOUNT (favor longs / tighten TP on shorts)
#
# On IDX, the daily open is the first traded price of the session (09:00 WIB).
# We use the `open` column of each daily bar.

def calc_do_zone(df: pd.DataFrame) -> pd.Series:
    """
    Returns the Daily Open price for each row (same value across the day).
    For daily bars, this is simply the `open` column carried forward until
    the next day. For intraday use, this would need timestamp-aware grouping;
    here we assume daily OHLCV input.

    Returns
    -------
    pd.Series : daily open price, aligned to df index.
    """
    return df['open'].copy()

calc_do_zone.warmup_bars = lambda: 0  # no warmup needed — open is always known


def calc_premium_discount(df: pd.DataFrame) -> pd.Series:
    """
    Binary signal: 1 = price in DISCOUNT (below D.O.), 0 = PREMIUM (above D.O.).

    Uses the most recent bar's close vs its own open as a daily approximation.
    For true intraday, use current price vs D.O.

    Returns
    -------
    pd.Series : 1 (discount) or 0 (premium), aligned to df index.
    """
    do_price = df['open']
    return (df['close'] < do_price).astype(int)

calc_premium_discount.warmup_bars = lambda: 0


def premium_discount_signal(df: pd.DataFrame) -> pd.Series:
    """
    Entry signal based on SMC premium/discount logic:
      - In DISCOUNT (close < D.O.): bullish bias  → return True (buy signal)
      - In PREMIUM  (close > D.O.): bearish bias   → return False (no buy)

    This is a DIRECTIONAL BIAS, not a standalone entry. Combine with
    other confirmations (FVG fill, liquidity sweep, volume).

    Returns
    -------
    pd.Series : True when price is in discount zone.
    """
    return df['close'] < df['open']


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FAIR VALUE GAP (FVG) — Imbalance Detection
# ═══════════════════════════════════════════════════════════════════════════════
#
# An FVG forms when a candle's range does NOT overlap with the prior candle,
# creating a "gap" or "void" in price. The algo must fill this void.
#
#   BULLISH FVG: candle[i].low > candle[i-2].high  (3-candle pattern)
#                 → gap between candle[i-2].high and candle[i].low
#   BEARISH FVG: candle[i].high < candle[i-2].low
#                 → gap between candle[i].low and candle[i-2].high
#
# Once price retraces INTO the FVG zone, we get a fill → reversal opportunity.
#
# Also detect HVI (High Volume Imbalance) — an FVG formed by a vector candle
# (engulfing) with elevated volume.

@dataclass
class FVG:
    """A detected Fair Value Gap."""
    index: int             # bar index where FVG was first detected
    date: str              # date string
    fvg_high: float        # upper boundary of the gap
    fvg_low: float         # lower boundary of the gap
    direction: str         # 'bullish' (gap above = sell into fill) or 'bearish' (gap below = buy into fill)
    size_pct: float        # gap size as % of price
    is_hvi: bool           # True if this is a High Volume Imbalance
    filled: bool = False   # has price since entered this zone?
    fill_date: str = None  # date when filled
    fill_index: int = None # bar index when filled


def detect_fvg(df: pd.DataFrame, hvi_vol_threshold: float = 1.5) -> pd.DataFrame:
    """
    Detect all FVGs in a price series using the 3-candle ICT pattern.

    Parameters
    ----------
    df : pd.DataFrame with OHLCV columns (date-ascending)
    hvi_vol_threshold : float — VR threshold for HVI classification (default 1.5x)

    Returns
    -------
    pd.DataFrame with columns: [date, fvg_high, fvg_low, direction, size_pct, is_hvi, filled, fill_date]
        One row per detected FVG.
    """
    if len(df) < 3:
        return pd.DataFrame(columns=['date', 'fvg_high', 'fvg_low', 'direction',
                                      'size_pct', 'is_hvi', 'filled', 'fill_date'])

    closes = df['close'].values
    highs  = df['high'].values
    lows   = df['low'].values
    volumes = df['volume'].values if 'volume' in df.columns else np.ones(len(df))
    dates  = df['date'].values if 'date' in df.columns else np.arange(len(df))

    # Volume ratio (simple: current vol / 20-bar average)
    vol_ma = pd.Series(volumes).rolling(20, min_periods=5).mean().values

    fvgs = []
    for i in range(2, len(df)):
        prev2_high = highs[i - 2]
        prev2_low  = lows[i - 2]
        curr_low   = lows[i]
        curr_high  = highs[i]
        curr_vol   = volumes[i]
        vol_ratio  = curr_vol / vol_ma[i] if vol_ma[i] > 0 else 1.0

        # BULLISH FVG: price gaps UP (gap between prev2 high and curr low)
        if curr_low > prev2_high:
            gap_size = curr_low - prev2_high
            size_pct = (gap_size / prev2_high) * 100
            fvgs.append({
                'index': i,
                'date': str(dates[i])[:10],
                'fvg_high': curr_low,
                'fvg_low': prev2_high,
                'direction': 'bullish',
                'size_pct': round(size_pct, 3),
                'is_hvi': vol_ratio >= hvi_vol_threshold,
                'filled': False,
                'fill_date': None,
                'fill_index': None,
            })

        # BEARISH FVG: price gaps DOWN (gap between prev2 low and curr high)
        elif curr_high < prev2_low:
            gap_size = prev2_low - curr_high
            size_pct = (gap_size / prev2_low) * 100
            fvgs.append({
                'index': i,
                'date': str(dates[i])[:10],
                'fvg_high': prev2_low,
                'fvg_low': curr_high,
                'direction': 'bearish',
                'size_pct': round(size_pct, 3),
                'is_hvi': vol_ratio >= hvi_vol_threshold,
                'filled': False,
                'fill_date': None,
                'fill_index': None,
            })

    if not fvgs:
        return pd.DataFrame(columns=['date', 'fvg_high', 'fvg_low', 'direction',
                                      'size_pct', 'is_hvi', 'filled', 'fill_date'])

    fvg_df = pd.DataFrame(fvgs)

    # Check which FVGs have been filled by subsequent price action
    for idx, fvg in fvg_df.iterrows():
        fvg_high = fvg['fvg_high']
        fvg_low  = fvg['fvg_low']
        start_i  = int(fvg['index']) + 1  # look forward from formation bar
        for j in range(start_i, len(df)):
            bar_high = highs[j]
            bar_low  = lows[j]
            # Price enters the FVG zone → fill
            if bar_low <= fvg_high and bar_high >= fvg_low:
                fvg_df.at[idx, 'filled'] = True
                fvg_df.at[idx, 'fill_date'] = str(dates[j])[:10]
                fvg_df.at[idx, 'fill_index'] = j
                break

    return fvg_df


def calc_fvg_signal(df: pd.DataFrame, lookback_days: int = 5,
                    require_hvi: bool = False) -> pd.Series:
    """
    Generate a daily signal: True when price is INSIDE an unfilled FVG zone.
    This indicates a likely fill → reversal opportunity.

    .. deprecated::
        DIRECTION-AGNOSTIC DEFECT — do NOT wire this into a long-only strategy.
        It fires True for ANY unfilled FVG, bullish OR bearish, so a long-only
        consumer would buy into bearish-FVG fills (overhead supply). No FVG
        strategy is built on top of this (see
        docs/superpowers/specs/2026-06-24-flow-confirmed-sweep-design.md, debug
        finding #1). Use the flow-confirmed liquidity sweep instead. If a real
        FVG strategy is ever needed, split this into bullish/bearish variants
        first.

    Parameters
    ----------
    df : pd.DataFrame with OHLCV
    lookback_days : int — how many recent bars to check for unfilled FVGs
    require_hvi : bool — if True, only consider High Volume Imbalance FVGs

    Returns
    -------
    pd.Series : True on bars where price is inside an unfilled FVG.
    """
    fvg_df = detect_fvg(df)
    signal = pd.Series(False, index=df.index)

    if fvg_df.empty:
        return signal

    # Consider only recent, unfilled FVGs
    active = fvg_df[(~fvg_df['filled']) & (fvg_df['index'] >= len(df) - lookback_days - 1)]
    if require_hvi:
        active = active[active['is_hvi']]

    for _, fvg in active.iterrows():
        fvg_high = fvg['fvg_high']
        fvg_low  = fvg['fvg_low']
        start_i  = int(fvg['index']) + 1
        end_i    = min(start_i + lookback_days, len(df))
        for j in range(start_i, end_i):
            if df['close'].iloc[j] >= fvg_low and df['close'].iloc[j] <= fvg_high:
                signal.iloc[j] = True

    return signal


def detect_vector_candle(df: pd.DataFrame) -> pd.Series:
    """
    Detect Vector Candles (VC) — engulfing candles that create imbalance.
    In ICT/SMC: a VC is a candle whose body completely engulfs the prior
    candle's body, creating a liquidity void.

    Returns
    -------
    pd.Series : 1 for bullish VC, -1 for bearish VC, 0 otherwise.
    """
    if len(df) < 2:
        return pd.Series(0, index=df.index)

    curr_body_high = np.maximum(df['open'], df['close'])
    curr_body_low  = np.minimum(df['open'], df['close'])
    prev_body_high = np.maximum(df['open'].shift(1), df['close'].shift(1))
    prev_body_low  = np.minimum(df['open'].shift(1), df['close'].shift(1))

    bullish_vc = (curr_body_high > prev_body_high) & (curr_body_low < prev_body_low) & \
                 (df['close'] > df['open'])
    bearish_vc = (curr_body_high > prev_body_high) & (curr_body_low < prev_body_low) & \
                 (df['close'] < df['open'])

    result = pd.Series(0, index=df.index)
    result[bullish_vc] = 1
    result[bearish_vc] = -1
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LIQUIDITY SWEEP — PDH / PDL & Weekly Trap Detection
# ═══════════════════════════════════════════════════════════════════════════════
#
# The core ICT concept: price hunts liquidity (stop losses) above previous
# highs and below previous lows, then REVERSES. This is called a "liquidity
# sweep" or "trap."
#
#   PDH = Previous Day High
#   PDL = Previous Day Low
#   PWH = Previous Week High
#   PWL = Previous Week Low
#
# When price breaks PDH/PDL but fails to hold → reversal entry (the trap).
# Combine with D.O. (premium/discount) for higher-probability setups.

def calc_previous_day_levels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate PDH, PDL, and mid-point for each bar.

    Returns
    -------
    pd.DataFrame with columns: [pdh, pdl, pd_mid]
    """
    result = pd.DataFrame(index=df.index)
    result['pdh'] = df['high'].shift(1)
    result['pdl'] = df['low'].shift(1)
    result['pd_mid'] = (result['pdh'] + result['pdl']) / 2
    return result


def calc_previous_week_levels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate PWH, PWL using a 5-bar rolling window (Mon-Fri assumption).
    For daily bars, 5 bars ≈ 1 trading week.

    Returns
    -------
    pd.DataFrame with columns: [pwh, pwl, pw_mid]
    """
    result = pd.DataFrame(index=df.index)
    result['pwh'] = df['high'].shift(1).rolling(5, min_periods=1).max()
    result['pwl'] = df['low'].shift(1).rolling(5, min_periods=1).min()
    result['pw_mid'] = (result['pwh'] + result['pwl']) / 2
    return result


def detect_liquidity_sweep(df: pd.DataFrame,
                           use_weekly: bool = True,
                           wick_pct_threshold: float = 0.3) -> pd.DataFrame:
    """
    Detect liquidity sweeps (traps) at PDH/PDL and optionally PWH/PWL.

    A sweep is detected when:
      1. Price briefly breaks a key level (PDH or PDL)
      2. Price closes BACK inside the range (reversal)
      3. The wick beyond the level is significant (>30% of the bar range)

    Parameters
    ----------
    df : pd.DataFrame with OHLCV columns
    use_weekly : bool — also check PWH/PWL (default True)
    wick_pct_threshold : float — minimum wick % for a valid sweep (default 0.3)

    Returns
    -------
    pd.DataFrame with columns:
        [date, sweep_type, level, level_price, wick_pct, direction, signal]
      - sweep_type: 'pdh', 'pdl', 'pwh', 'pwl'
      - direction: 'bullish' (sweep below → buy) or 'bearish' (sweep above → sell)
      - signal: +1 (bullish entry), -1 (bearish entry), 0 (no signal)
    """
    if len(df) < 3:
        return pd.DataFrame(columns=['date', 'sweep_type', 'level', 'level_price',
                                      'wick_pct', 'direction', 'signal'])

    pd_levels = calc_previous_day_levels(df)
    if use_weekly and len(df) >= 6:
        pw_levels = calc_previous_week_levels(df)

    sweeps = []

    for i in range(2, len(df)):
        row = df.iloc[i]
        bar_range = row['high'] - row['low']
        if bar_range <= 0:
            continue
        date_str = str(row['date'])[:10] if 'date' in df.columns else str(i)

        # ── PDH sweep (bearish trap: price breaks above PDH then closes below) ──
        pdh = pd_levels['pdh'].iloc[i]
        if pd.notna(pdh) and row['high'] > pdh:
            wick_above = row['high'] - pdh
            wick_pct = wick_above / bar_range
            # Sweep confirmed if wick is significant and close is below the level
            if wick_pct >= wick_pct_threshold and row['close'] < pdh:
                sweeps.append({
                    'date': date_str,
                    'sweep_type': 'pdh',
                    'level': 'PDH',
                    'level_price': round(pdh, 2),
                    'wick_pct': round(wick_pct, 3),
                    'direction': 'bearish',
                    'signal': -1,
                })

        # ── PDL sweep (bullish trap: price breaks below PDL then closes above) ──
        pdl = pd_levels['pdl'].iloc[i]
        if pd.notna(pdl) and row['low'] < pdl:
            wick_below = pdl - row['low']
            wick_pct = wick_below / bar_range
            if wick_pct >= wick_pct_threshold and row['close'] > pdl:
                sweeps.append({
                    'date': date_str,
                    'sweep_type': 'pdl',
                    'level': 'PDL',
                    'level_price': round(pdl, 2),
                    'wick_pct': round(wick_pct, 3),
                    'direction': 'bullish',
                    'signal': 1,
                })

        # ── PWH sweep ──
        if use_weekly and len(df) >= 6:
            pwh = pw_levels['pwh'].iloc[i]
            if pd.notna(pwh) and row['high'] > pwh:
                wick_above = row['high'] - pwh
                wick_pct = wick_above / bar_range
                if wick_pct >= wick_pct_threshold and row['close'] < pwh:
                    sweeps.append({
                        'date': date_str,
                        'sweep_type': 'pwh',
                        'level': 'PWH',
                        'level_price': round(pwh, 2),
                        'wick_pct': round(wick_pct, 3),
                        'direction': 'bearish',
                        'signal': -1,
                    })

            pwl = pw_levels['pwl'].iloc[i]
            if pd.notna(pwl) and row['low'] < pwl:
                wick_below = pwl - row['low']
                wick_pct = wick_below / bar_range
                if wick_pct >= wick_pct_threshold and row['close'] > pwl:
                    sweeps.append({
                        'date': date_str,
                        'sweep_type': 'pwl',
                        'level': 'PWL',
                        'level_price': round(pwl, 2),
                        'wick_pct': round(wick_pct, 3),
                        'direction': 'bullish',
                        'signal': 1,
                    })

    if not sweeps:
        return pd.DataFrame(columns=['date', 'sweep_type', 'level', 'level_price',
                                      'wick_pct', 'direction', 'signal'])

    return pd.DataFrame(sweeps)


def calc_sweep_signal(df: pd.DataFrame) -> pd.Series:
    """
    Generate a daily signal series: True on bars where a bullish liquidity
    sweep is detected (buy signal). For bearish sweeps, this returns False.

    Use this as an ENTRY CONFIRMATION (not standalone).

    Returns
    -------
    pd.Series : True on bars with bullish sweep (PDL or PWL trap).
    """
    sweeps = detect_liquidity_sweep(df)
    signal = pd.Series(False, index=df.index)

    if sweeps.empty:
        return signal

    bullish_sweeps = sweeps[sweeps['signal'] == 1]
    for _, sweep in bullish_sweeps.iterrows():
        date_str = sweep['date']
        # Find matching row in df
        mask = pd.Series(df['date'].astype(str).str[:10] == date_str, index=df.index)
        signal = signal | mask

    return signal


# ═══════════════════════════════════════════════════════════════════════════════
# 4. COMPOSITE SMC SIGNAL — Combines all three concepts
# ═══════════════════════════════════════════════════════════════════════════════

def calc_smc_composite(df: pd.DataFrame,
                       require_discount: bool = True,
                       require_fvg: bool = False,
                       require_sweep: bool = True) -> pd.Series:
    """
    Composite ICT/SMC entry signal combining premium/discount, FVG, and
    liquidity sweeps.

    Default config (conservative):
      - Price must be in DISCOUNT (below D.O.)
      - A liquidity sweep (PDL trap) must have occurred
      - FVG check is optional (adds selectivity)

    Parameters
    ----------
    df : pd.DataFrame with OHLCV
    require_discount : bool — require price below daily open
    require_fvg : bool — require price inside unfilled FVG
    require_sweep : bool — require bullish liquidity sweep

    Returns
    -------
    pd.Series : True where all required conditions are met.
    """
    signal = pd.Series(True, index=df.index)

    if require_discount:
        in_discount = df['close'] < df['open']
        signal = signal & in_discount

    if require_fvg:
        fvg_sig = calc_fvg_signal(df)
        signal = signal & fvg_sig

    if require_sweep:
        sweep_sig = calc_sweep_signal(df)
        signal = signal & sweep_sig

    return signal


# ═══════════════════════════════════════════════════════════════════════════════
# 5. UTILITY — SMC Dashboard Summary
# ═══════════════════════════════════════════════════════════════════════════════

def smc_summary(df: pd.DataFrame) -> dict:
    """
    Generate a one-shot SMC summary for a ticker — useful for scanner
    integration and Telegram reports.

    Returns
    -------
    dict with keys:
        do_price, zone, fvg_active, fvg_count, hvi_count,
        last_sweep_type, last_sweep_date, composite_signal
    """
    if len(df) < 3:
        return {'error': 'insufficient data', 'bars': len(df)}

    last = df.iloc[-1]
    do_price = last['open']
    zone = 'DISCOUNT' if last['close'] < do_price else 'PREMIUM'

    fvg_df = detect_fvg(df)
    unfilled = fvg_df[~fvg_df['filled']] if not fvg_df.empty else pd.DataFrame()

    sweeps = detect_liquidity_sweep(df)
    last_sweep = None
    if not sweeps.empty:
        last_sweep = sweeps.iloc[-1].to_dict()

    composite = calc_smc_composite(df)

    return {
        'ticker': str(df['ticker'].iloc[0]) if 'ticker' in df.columns else '???',
        'date': str(last['date'])[:10] if 'date' in df.columns else '???',
        'close': round(float(last['close']), 2),
        'do_price': round(float(do_price), 2),
        'zone': zone,
        'fvg_active': len(unfilled) > 0,
        'fvg_count': len(unfilled),
        'hvi_count': int(unfilled['is_hvi'].sum()) if not unfilled.empty else 0,
        'last_sweep_type': last_sweep['sweep_type'] if last_sweep else None,
        'last_sweep_date': last_sweep['date'] if last_sweep else None,
        'last_sweep_direction': last_sweep['direction'] if last_sweep else None,
        'composite_signal': bool(composite.iloc[-1]) if len(composite) > 0 else False,
    }
