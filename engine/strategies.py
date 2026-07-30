"""
strategies.py — 4 Strategy Definitions untuk BBCA Multi-Strategy Backtest
Terintegrasi dengan idx-walkforward engine (market_structure, indicators, signals)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

from engine.indicators import (
    calc_atr,
    calc_delta,
    calc_relative_strength,
    calc_sma,
    calc_vwap,
    calc_vol_ratio,
    calc_vwma,
    calc_weekly_trend,
)

# ─────────────────────────────────────────────
# CONFIG — cost values live in engine/exits/costs.py (single authority, plan 1C)
# ─────────────────────────────────────────────
from engine.exits.costs import COMMISSION_BUY, COMMISSION_SELL, SLIPPAGE

@dataclass
class Trade:
    entry_date: str
    exit_date:  str
    entry_price: float
    exit_price:  float
    lots: int
    direction: str        # BUY
    exit_reason: str      # TP / SL / EOD / TRAIL
    pnl_rp: float
    pnl_pct: float
    strategy: str


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def lot_size(capital: float, price: float, risk_pct: float, sl_pct: float) -> int:
    """Hitung lot (1 lot = 100 lembar) berdasarkan risk per trade."""
    risk_rp      = capital * risk_pct
    risk_per_lot = price * 100 * sl_pct
    # NaN/inf (e.g. a NaN price or sl_pct from a degenerate bar) defeats the
    # `<= 0` guard — every comparison with NaN is False — and would crash
    # int() below. Treat non-finite as a degenerate input and size minimally.
    if not np.isfinite(risk_per_lot) or risk_per_lot <= 0 or not np.isfinite(risk_rp):
        return 1
    lots = int(risk_rp / risk_per_lot)
    # Cap: maksimum 30% capital per trade
    max_lots = int((capital * 0.30) / (price * 100))
    lots = min(lots, max_lots)
    return max(1, lots)


def atr_tp_sl(entry: float, atr: float, sl_mult: float = 1.0, min_rr: float = 2.0):
    """
    Compute ATR-based TP and SL ensuring minimum R/R ratio.
    Returns (tp_price, sl_price, tp_pct, sl_pct).
    """
    sl_dist = atr * sl_mult
    sl_price = entry - sl_dist
    # TP must satisfy minimum R/R
    tp_price = entry + sl_dist * min_rr
    tp_pct = (tp_price - entry) / entry
    sl_pct = sl_dist / entry
    return tp_price, sl_price, tp_pct, sl_pct

def apply_costs(price: float, side: str) -> float:
    """Thin wrapper over the single cost authority (kept for the many
    strategy call sites and tests that use the 2-arg signature)."""
    from engine.exits.costs import apply_costs as _apply
    return _apply(price, side)


def _watch_signal_block(df: pd.DataFrame) -> pd.Series:
    """
    Approximate daily_screen 'watch' / non-bullish signal block using OHLCV data.
    Matches scheduler.py scan_momentum_signals() logic:
      - daily_screen signal == 'watch' → block
      - signal != 'bullish' AND delta < 50_000 → block
    Returns True for bars that should be BLOCKED (watch / low-conviction).
    """
    vr = calc_vol_ratio(df, 20)
    delta_proxy = calc_delta(df)
    typical_price = (df['high'] + df['low'] + df['close']) / 3

    vr_elevated = vr > 1.5
    # 'bullish' in daily_screen = delta > 0 AND price > vwap
    # Using typical_price as session-VWAP proxy
    is_bullish = (delta_proxy > 0) & (df['close'] > typical_price)

    # Block watch: VR elevated but not clearly bullish
    return vr_elevated & ~is_bullish

# ─────────────────────────────────────────────
# FILTER LIBRARY (on/off kombinasi bebas)
# ─────────────────────────────────────────────

def filter_vwma_above(df: pd.DataFrame) -> pd.Series:
    """Price di atas VWMA 20 — trend bullish filter."""
    vwma = calc_vwma(df, 20)
    return df['close'] > vwma

def filter_above_ma50(df: pd.DataFrame) -> pd.Series:
    """Price di atas MA 50 — medium-term trend filter."""
    return df['close'] > calc_sma(df, 50)

def filter_low_atr(df: pd.DataFrame) -> pd.Series:
    """ATR di bawah 1.2x ATR MA — hindari hari terlalu volatile."""
    atr    = calc_atr(df, 14)
    atr_ma = atr.rolling(10).mean()
    return atr < atr_ma * 1.2

def filter_vr_min(df: pd.DataFrame, threshold: float = 1.3) -> pd.Series:
    """Volume ratio di atas threshold — konfirmasi volume."""
    return calc_vol_ratio(df, 20) >= threshold

def filter_uptrend(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Close lebih tinggi dari N hari lalu — momentum trend."""
    return df['close'] > df['close'].shift(lookback)

def apply_filters(df: pd.DataFrame, filters: list) -> pd.Series:
    """AND semua filter. Jika filters kosong, return semua True."""
    mask = pd.Series(True, index=df.index)
    for f in filters:
        mask = mask & f(df)
    return mask




# ─────────────────────────────────────────────
# BASE BACKTEST ENGINE
# ─────────────────────────────────────────────

def run_strategy(df: pd.DataFrame, signals: pd.Series,
                 tp_pct: float = None, sl_pct: float = None,
                 strategy_name: str = '',
                 initial_capital: float = 50_000_000,
                 risk_per_trade: float = 0.02,
                 trail_sl: bool = False,
                 filters: list = None,
                 atr_sl_mult: float = None,
                 atr_tp_mult: float = None,
                 min_rr: float = 2.0) -> dict:
    """
    Generic backtest engine. signals: Series of True/False per bar.
    When atr_sl_mult is provided, uses ATR-based TP/SL per entry (min_rr enforced).
    Falls back to tp_pct/sl_pct if ATR params not provided.

    Exits are decided by the shared kernel (engine/exits/evaluate_exit) so
    backtest, live monitor, and forward test agree (plan 1B, audit C-3/C-8):
      - trailing stops anchor on the PRIOR bar's high extreme (Chandelier);
        ratcheting from the current bar's own high before testing its low was
        intrabar look-ahead (C-8) and inflated trail exits;
      - the entry bar itself is evaluated (a gap can exit on day one),
        matching the forward-test engine;
      - pct-based params are expressed to the kernel as a synthetic ATR
        (= sl_pct * entry) so one code path serves both parameterizations.
    """
    from engine.exits import ExitPolicy, PositionView, Bar, evaluate_exit

    if filters:
        filter_mask = apply_filters(df, filters)
        signals = signals & filter_mask

    atr_series = calc_atr(df, 14) if atr_sl_mult is not None else None

    capital     = initial_capital
    equity      = [capital]
    trades      = []
    in_trade    = False
    entry_price = 0.0
    entry_date  = ""
    lots        = 0
    policy      = None
    entry_atr   = 0.0
    highest     = 0.0
    lowest      = 0.0

    def _close(row_date, raw_fill, reason):
        nonlocal capital, in_trade
        exit_price = apply_costs(raw_fill, 'SELL')
        gross   = (exit_price - entry_price) * lots * 100
        pnl_pct = (exit_price - entry_price) / entry_price
        capital += gross
        trades.append(Trade(
            entry_date=entry_date, exit_date=row_date,
            entry_price=entry_price, exit_price=exit_price,
            lots=lots, direction='BUY', exit_reason=reason,
            pnl_rp=gross, pnl_pct=pnl_pct * 100,
            strategy=strategy_name
        ))
        in_trade = False

    for i in range(1, len(df)):
        row  = df.iloc[i]
        date = str(row['date'])[:10]
        bar  = Bar(date=date, open=float(row['open']), high=float(row['high']),
                   low=float(row['low']), close=float(row['close']))

        if not in_trade and signals.iloc[i - 1]:
            raw_entry   = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')

            if atr_sl_mult is not None and atr_series is not None:
                atr_val = atr_series.iloc[i - 1]
                if pd.isna(atr_val) or atr_val <= 0:
                    atr_val = entry_price * 0.015  # fallback 1.5%
                entry_atr = float(atr_val)
                _tp_mult = (atr_tp_mult / atr_sl_mult if atr_tp_mult else min_rr) * atr_sl_mult
                policy = ExitPolicy(sl_mult=atr_sl_mult, tp_mult=_tp_mult,
                                    min_rr=min_rr, trail_enable=trail_sl)
                _sl_pct_eff = (atr_sl_mult * entry_atr) / entry_price
            else:
                _tp = tp_pct or 0.04
                _sl = sl_pct or 0.02
                # Express pct levels as a synthetic 1x-ATR policy.
                entry_atr = entry_price * _sl
                policy = ExitPolicy(sl_mult=1.0, tp_mult=_tp / _sl,
                                    min_rr=_tp / _sl, trail_enable=trail_sl)
                _sl_pct_eff = _sl

            lots = lot_size(capital, entry_price, risk_per_trade, _sl_pct_eff)
            cost = entry_price * lots * 100
            if cost <= capital:
                in_trade   = True
                entry_date = date
                highest    = entry_price
                lowest     = entry_price
                # fall through: the entry bar itself is evaluated below
            else:
                equity.append(capital)
                continue

        if in_trade:
            view = PositionView(policy=policy, direction='LONG',
                                entry=entry_price, atr=entry_atr,
                                highest_seen=highest, lowest_seen=lowest,
                                hold_days=0)
            decision = evaluate_exit(view, bar)
            if decision is not None:
                _close(date, decision.fill_price, decision.reason)
            elif i == len(df) - 1:
                _close(date, bar.close, 'EOD')
            else:
                highest = max(highest, bar.high)
                lowest  = min(lowest, bar.low)

        equity.append(capital)

    return {
        'strategy': strategy_name,
        'trades':   trades,
        'equity':   equity,
        'final_capital': capital,
        'initial_capital': initial_capital
    }


# ─────────────────────────────────────────────
# STRATEGY 1 — VOL-WEIGHTED ENTRY
# ─────────────────────────────────────────────

def strategy_vol_weighted(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> dict:
    """
    Entry: Vol Ratio > 2.0x AND Delta positif (close > open)
    Exit:  SL = ATR×1.0, TP = ATR×2.0 (2:1 R/R minimum)
    """
    vr    = calc_vol_ratio(df, 20)
    delta = calc_delta(df)
    sig   = (vr > 1.8) & (delta > 0) & (df['close'] > df['open'])
    return run_strategy(df, sig, atr_sl_mult=1.0, atr_tp_mult=2.0, min_rr=2.0,
                        strategy_name='Vol-Weighted Entry', initial_capital=capital,
                        filters=filters)


# ─────────────────────────────────────────────
# STRATEGY 2 — MOMENTUM FOLLOWING
# ─────────────────────────────────────────────

def strategy_momentum(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> dict:
    """
    Entry: 2 hari berturut close > close[-1] + Vol Ratio > 1.3x
    Exit:  SL = ATR×1.2 (trailing), TP = ATR×2.4 (2:1 R/R minimum)
    """
    vr        = calc_vol_ratio(df, 20)
    streak2   = (df['close'] > df['close'].shift(1)) & \
                (df['close'].shift(1) > df['close'].shift(2))
    # Watch block + VR cap: match live scheduler.py behavior
    # Live also checks daily_screen signal and caps VR at 5.0x
    watch_block = _watch_signal_block(df)
    sig = streak2 & (vr > 1.3) & (vr <= 5.0) & ~watch_block
    return run_strategy(df, sig, atr_sl_mult=1.2, atr_tp_mult=2.4, min_rr=2.0,
                        strategy_name='Momentum Following',
                        initial_capital=capital, trail_sl=True,
                        filters=filters)


# ─────────────────────────────────────────────
# STRATEGY 3 — VWAP REVERSION
# ─────────────────────────────────────────────

def strategy_vwap_reversion(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> dict:
    """
    Entry: Close > 1.5% di bawah VWAP + Vol spike (ratio > 1.5x)
    Exit:  SL = ATR×0.8 (tight mean-rev), TP = ATR×1.6 (2:1 R/R minimum)
    """
    vwap = calc_vwap(df)
    vr   = calc_vol_ratio(df, 20)
    dist = (df['close'] - vwap) / vwap
    sig  = (dist < -0.010) & (vr > 1.3)
    return run_strategy(df, sig, atr_sl_mult=0.8, atr_tp_mult=1.6, min_rr=2.0,
                        strategy_name='VWAP Reversion', initial_capital=capital,
                        filters=filters)


# ─────────────────────────────────────────────
# STRATEGY 4 — CONSERVATIVE CONFIRMATION
# ─────────────────────────────────────────────

def strategy_conservative(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> dict:
    """
    Entry: Vol Ratio > 1.5x + close > open + close di atas MA20 + ATR normal
    Exit:  TP +1.5% / SL -1.0%  (tightest risk)
    """
    vr    = calc_vol_ratio(df, 20)
    ma20  = calc_sma(df, 20)
    atr   = calc_atr(df, 14)
    atr_ma = atr.rolling(10).mean()
    bullish = df['close'] > df['open']
    above_ma = df['close'] > ma20
    atr_ok   = atr < atr_ma * 1.5   # hindari hari terlalu volatile

    sig = (vr > 1.3) & bullish & above_ma & atr_ok
    return run_strategy(df, sig, atr_sl_mult=0.7, atr_tp_mult=1.4, min_rr=2.0,
                        strategy_name='Conservative Confirm', initial_capital=capital,
                        filters=filters)


# ─────────────────────────────────────────────
# STRATEGY 5 — VWMA BREAKOUT PULLBACK
# ─────────────────────────────────────────────

def strategy_vwma_breakout_pullback(df: pd.DataFrame, capital: float = 50_000_000) -> dict:
    """
    VWMA Breakout Pullback Strategy.

    Setup 2-bar (standard):
      Bar N-1 (breakout): close > VWMA, volume >= 2x avg20
      Bar N   (rejection): low <= VWMA, close > VWMA,
                           volume < volume[N-1],
                           lower_wick >= body
      Entry  : open[N+1] > high[N] -> entry at open[N+1]

    Setup 1-bar (power candle):
      Bar N: open < VWMA, close > VWMA, volume >= 2x avg20,
             lower_wick >= body
      Entry: open[N+1] > high[N] -> entry at open[N+1]

    Invalidasi: jika setelah breakout ada 3 candle naik berturut-turut
                tanpa pullback -> setup dibatalkan.

    TP : swing high tertinggi dalam lookback 20 bar (fixed saat entry)
    SL : VWMA value di bar sinyal (fixed saat entry)
    """
    vwma    = calc_vwma(df, 20)
    avg_vol = df['volume'].rolling(20).mean()
    vr      = df['volume'] / avg_vol

    body       = (df['close'] - df['open']).abs()
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    long_wick  = lower_wick >= body * 0.5

    # -- Setup 2-bar --
    breakout_bar = (df['close'] > vwma) & (vr >= 1.5)

    rejection_bar = (
        (df['low']    <= vwma) &
        (df['close']  >  vwma) &
        (df['volume'] <  df['volume'].shift(1)) &
        long_wick
    )

    setup_2bar = breakout_bar.shift(1).fillna(False) & rejection_bar

    # Invalidasi: 3 candle naik berturut setelah breakout
    three_up = (
        (df['close'] > df['close'].shift(1)) &
        (df['close'].shift(1) > df['close'].shift(2)) &
        (df['close'].shift(2) > df['close'].shift(3))
    )
    setup_2bar = setup_2bar & ~three_up

    # -- Setup 1-bar (power candle) --
    setup_1bar = (
        (df['open']  < vwma) &
        (df['close'] > vwma) &
        (vr >= 1.5)          &
        long_wick
    )

    raw_signal = setup_2bar | setup_1bar

    # -- Entry filter: open[N+1] > high[N] --
    entry_signal = pd.Series(False, index=df.index)
    for i in range(1, len(df)):
        if raw_signal.iloc[i - 1]:
            if df['open'].iloc[i] >= df['high'].iloc[i - 1]:
                entry_signal.iloc[i - 1] = True

    return _run_vwma_bp(df, entry_signal, vwma,
                        strategy_name='VWMA Breakout Pullback',
                        initial_capital=capital)


def _run_vwma_bp(df: pd.DataFrame, signals: pd.Series,
                 vwma: pd.Series,
                 strategy_name: str,
                 initial_capital: float = 50_000_000,
                 risk_per_trade: float  = 0.02) -> dict:
    """
    Custom runner untuk VWMA BP:
    - TP = swing high max 20 bar lookback dari bar sinyal (fixed)
    - SL = VWMA value di bar sinyal (fixed)
    """
    capital     = initial_capital
    equity      = [capital]
    trades      = []
    in_trade    = False
    entry_price = tp_level = sl_level = 0.0
    entry_date  = ""
    lots        = 0

    for i in range(1, len(df)):
        row  = df.iloc[i]
        date = str(row['date'])[:10]

        if in_trade:
            hi  = row['high']
            lo  = row['low']
            cur = row['close']

            exit_reason = None
            if lo <= sl_level:
                exit_price  = apply_costs(sl_level, 'SELL')
                exit_reason = 'SL'
            elif hi >= tp_level:
                exit_price  = apply_costs(tp_level, 'SELL')
                exit_reason = 'TP'
            elif i == len(df) - 1:
                exit_price  = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'

            if exit_reason:
                gross   = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy=strategy_name
                ))
                in_trade = False

        elif signals.iloc[i - 1]:
            raw_entry   = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')

            # SL = VWMA di bar sinyal, fixed
            sl_raw   = vwma.iloc[i - 1]
            sl_level = apply_costs(sl_raw, 'SELL')

            sl_pct_eff = (entry_price - sl_level) / entry_price
            if sl_pct_eff <= 0:
                equity.append(capital)
                continue

            # TP = swing high max 20 bar lookback
            lookback_start = max(0, i - 20)
            swing_high = df['high'].iloc[lookback_start:i].max()
            tp_level   = swing_high

            if tp_level <= entry_price:
                equity.append(capital)
                continue
            # Min TP distance 1.5% untuk layak risk/reward
            if (tp_level - entry_price) / entry_price < 0.015:
                equity.append(capital)
                continue

            lots = lot_size(capital, entry_price, risk_per_trade, sl_pct_eff)
            cost = entry_price * lots * 100
            if cost <= capital:
                in_trade   = True
                entry_date = date

        equity.append(capital)

    return {
        'strategy':        strategy_name,
        'trades':          trades,
        'equity':          equity,
        'final_capital':   capital,
        'initial_capital': initial_capital
    }


# ─────────────────────────────────────────────
# STRATEGY 6 — VOLUME PROFILE POC BOUNCE
# ─────────────────────────────────────────────

def calc_volume_profile(df: pd.DataFrame, lookback: int = 20,
                        resolution: float = 0.005) -> pd.DataFrame:
    """
    Approximasi volume profile dari OHLCV daily.
    Distribusi volume merata antara high-low per bar.
    resolution: 0.5% per price bucket.
    Returns DataFrame dengan columns: price_level, volume (per lookback window).
    Dipanggil per bar, bukan pre-compute seluruh df.
    """
    pass  # logic ada di strategy function langsung


def _get_poc_hvn(df_window: pd.DataFrame, resolution: float = 0.005):
    """
    Hitung POC dan HVN dari window df.
    Returns: (poc_price, hvn_levels_list)
    """
    if len(df_window) == 0:
        return None, []

    price_min = df_window['low'].min()
    price_max = df_window['high'].max()
    # A fully-NaN window yields NaN min/max, which slips past `<=` (NaN
    # comparisons are False) and crashes int() below — reject explicitly.
    if not np.isfinite(price_min) or not np.isfinite(price_max) or price_max <= price_min:
        return None, []

    # Buat price buckets
    bucket_size = price_min * resolution
    if not np.isfinite(bucket_size) or bucket_size <= 0:
        return None, []

    n_buckets = max(1, int((price_max - price_min) / bucket_size) + 1)
    buckets   = np.zeros(n_buckets)
    prices    = np.array([price_min + i * bucket_size for i in range(n_buckets)])

    for _, row in df_window.iterrows():
        # Skip degenerate bars (e.g. a mid-session partial or suspended day
        # with NaN OHLCV); a single NaN cell here would crash int() below.
        try:
            _lo, _hi, _cl, _vo = float(row['low']), float(row['high']), float(row['close']), float(row['volume'])
            if not (np.isfinite(_lo) and np.isfinite(_hi) and np.isfinite(_cl) and np.isfinite(_vo)):
                continue
        except (TypeError, ValueError):
            continue
        rng = row['high'] - row['low']
        if rng <= 0:
            # Semua volume di satu level
            idx = min(int((row['close'] - price_min) / bucket_size), n_buckets - 1)
            buckets[idx] += row['volume']
            continue
        # Distribusi merata antara low-high
        i_low  = max(0, int((row['low']  - price_min) / bucket_size))
        i_high = min(n_buckets - 1, int((row['high'] - price_min) / bucket_size))
        n_in   = max(1, i_high - i_low + 1)
        vol_per_bucket = row['volume'] / n_in
        buckets[i_low:i_high+1] += vol_per_bucket

    poc_idx = int(np.argmax(buckets))
    poc     = prices[poc_idx]

    # HVN: top 3 volume nodes (exclude POC)
    sorted_idx = np.argsort(buckets)[::-1]
    hvn = []
    for idx in sorted_idx[1:6]:
        if abs(prices[idx] - poc) > bucket_size * 2:  # minimal 2 bucket dari POC
            hvn.append(prices[idx])
        if len(hvn) >= 3:
            break

    return poc, hvn


def strategy_volume_profile_poc(df: pd.DataFrame, capital: float = 50_000_000,
                                filters: list = None) -> dict:
    """
    Volume Profile POC Bounce Strategy.

    Setup:
      Bar N: low menyentuh area POC (dalam ±1.5%), close di atas POC,
             volume < avg_vol_20, lower_wick >= 50% body
      Entry: open[N+1] > high[N]

    TP : HVN terdekat di atas entry price
    SL : low bar N (fixed)
    """
    avg_vol    = df['volume'].rolling(20).mean()
    body       = (df['close'] - df['open']).abs()
    lower_wick = df[['open', 'close']].min(axis=1) - df['low']
    long_wick  = lower_wick >= body * 0.5

    # Apply filters
    if filters:
        from engine.strategies import apply_filters
        filter_mask = apply_filters(df, filters)
    else:
        filter_mask = pd.Series(True, index=df.index)

    capital_cur  = capital
    equity       = [capital_cur]
    trades       = []
    in_trade     = False
    entry_price  = tp_level = sl_level = 0.0
    entry_date   = ""
    lots         = 0

    for i in range(20, len(df)):
        row  = df.iloc[i]
        date = str(row['date'])[:10]

        if in_trade:
            hi  = row['high']
            lo  = row['low']
            cur = row['close']

            exit_reason = None
            if lo <= sl_level:
                exit_price  = apply_costs(sl_level, 'SELL')
                exit_reason = 'SL'
            elif hi >= tp_level:
                exit_price  = apply_costs(tp_level, 'SELL')
                exit_reason = 'TP'
            elif i == len(df) - 1:
                exit_price  = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'

            if exit_reason:
                gross   = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital_cur += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy='Volume Profile POC'
                ))
                in_trade = False

        else:
            # Cek signal di bar i-1, entry di bar i
            prev_i = i - 1
            prev   = df.iloc[prev_i]

            if not filter_mask.iloc[prev_i]:
                equity.append(capital_cur)
                continue

            # Hitung POC + HVN dari lookback 20 bar sebelum prev
            window = df.iloc[max(0, prev_i - 20):prev_i]
            poc, hvn = _get_poc_hvn(window)

            if poc is None:
                equity.append(capital_cur)
                continue

            # Signal: low menyentuh POC area (±1.5%), close di atas POC
            poc_low  = poc * 0.985
            poc_high = poc * 1.015
            touch_poc = (prev['low'] <= poc_high) and (prev['low'] >= poc_low)
            close_above = prev['close'] > poc
            low_vol  = prev['volume'] < (avg_vol.iloc[prev_i] if not pd.isna(avg_vol.iloc[prev_i]) else float('inf'))
            wick_ok  = long_wick.iloc[prev_i]

            if not (touch_poc and close_above and low_vol and wick_ok):
                equity.append(capital_cur)
                continue

            # Entry filter: open[i] > high[i-1]
            if row['open'] < prev['high']:
                equity.append(capital_cur)
                continue

            raw_entry   = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')

            # SL = low bar N (prev), fixed
            sl_raw   = prev['low']
            sl_level = apply_costs(sl_raw, 'SELL')

            sl_pct_eff = (entry_price - sl_level) / entry_price
            if sl_pct_eff <= 0.001:  # minimal SL 0.1%
                equity.append(capital_cur)
                continue

            # TP = HVN terdekat di atas entry
            hvn_above = [h for h in hvn if h > entry_price]
            if hvn_above:
                tp_level = min(hvn_above)
            else:
                # Fallback: swing high 20 bar
                tp_level = df['high'].iloc[max(0, prev_i-20):prev_i].max()

            if tp_level <= entry_price:
                equity.append(capital_cur)
                continue
            # Min TP distance 1.5% untuk layak risk/reward
            if (tp_level - entry_price) / entry_price < 0.015:
                equity.append(capital_cur)
                continue

            lots = lot_size(capital_cur, entry_price, 0.02, sl_pct_eff)
            cost = entry_price * lots * 100
            if cost <= capital_cur:
                in_trade   = True
                entry_date = date

        equity.append(capital_cur)

    return {
        'strategy':        'Volume Profile POC',
        'trades':          trades,
        'equity':          equity,
        'final_capital':   capital_cur,
        'initial_capital': capital
    }


# STRATEGY - INSIDE BAR BREAKOUT
def strategy_inside_bar_breakout(df: pd.DataFrame, capital: float = 50_000_000,
                                  filters: list = None) -> dict:
    # Current spec: 1 inside bar (i-1 inside i-2), entry bar i opens above prev high.
    # TP = max(swing_hi_20, entry + 2*ATR14), SL = prev low. WR baseline ~60%.
    # Design-intent (per STRATEGY_AUDIT.md A.1) was "2 inside + 3rd break + vol";
    # implementing that requires re-running walk-forward to revalidate WR.
    atr = calc_atr(df, 14)  # FIXED: was simplified (high-low) only, now uses full True Range
    if filters:
        from engine.strategies import apply_filters
        filter_mask = apply_filters(df, filters)
    else:
        filter_mask = pd.Series(True, index=df.index)
    capital_cur = capital
    equity = [capital_cur]
    trades = []
    in_trade = False
    entry_price = tp_level = sl_level = 0.0
    entry_date = ''
    lots = 0
    for i in range(21, len(df)):
        row = df.iloc[i]
        date = str(row['date'])[:10]
        if in_trade:
            hi, lo, cur = row['high'], row['low'], row['close']
            exit_reason = None
            if lo <= sl_level:
                exit_price = apply_costs(sl_level, 'SELL')
                exit_reason = 'SL'
            elif hi >= tp_level:
                exit_price = apply_costs(tp_level, 'SELL')
                exit_reason = 'TP'
            elif i == len(df) - 1:
                exit_price = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'
            if exit_reason:
                gross = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital_cur += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy='Inside Bar Breakout'
                ))
                in_trade = False
        else:
            prev = df.iloc[i - 1]
            prev2 = df.iloc[i - 2]
            if not filter_mask.iloc[i - 1]:
                equity.append(capital_cur)
                continue
            inside = (prev['high'] < prev2['high']) and (prev['low'] > prev2['low'])
            if not inside:
                equity.append(capital_cur)
                continue
            if row['open'] <= prev['high']:
                equity.append(capital_cur)
                continue
            raw_entry = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')
            sl_level = apply_costs(prev['low'], 'SELL')
            sl_pct = (entry_price - sl_level) / entry_price
            if sl_pct <= 0.002:
                equity.append(capital_cur)
                continue
            swing_hi = df['high'].iloc[max(0, i - 20):i].max()
            atr_tp = entry_price + atr.iloc[i - 1] * 2 if not pd.isna(atr.iloc[i - 1]) else swing_hi
            tp_level = max(swing_hi, atr_tp)
            if tp_level <= entry_price * 1.01:
                equity.append(capital_cur)
                continue
            lots = lot_size(capital_cur, entry_price, 0.02, sl_pct)
            cost = entry_price * lots * 100
            if cost <= capital_cur and lots > 0:
                in_trade = True
                entry_date = date
        equity.append(capital_cur)
    return {
        'strategy': 'Inside Bar Breakout',
        'trades': trades, 'equity': equity,
        'final_capital': capital_cur, 'initial_capital': capital
    }


# STRATEGY - NR7 BREAKOUT
def strategy_nr7_breakout(df: pd.DataFrame, capital: float = 50_000_000,
                           filters: list = None) -> dict:
    ranges = df['high'] - df['low']  # kept for NR7 detection
    atr = calc_atr(df, 14)  # FIXED: was simplified (high-low), now full True Range
    avg_vol5 = df['volume'].rolling(5).mean()
    if filters:
        from engine.strategies import apply_filters
        filter_mask = apply_filters(df, filters)
    else:
        filter_mask = pd.Series(True, index=df.index)
    capital_cur = capital
    equity = [capital_cur]
    trades = []
    in_trade = False
    entry_price = tp_level = sl_level = 0.0
    entry_date = ''
    lots = 0
    for i in range(21, len(df)):
        row = df.iloc[i]
        date = str(row['date'])[:10]
        if in_trade:
            hi, lo, cur = row['high'], row['low'], row['close']
            exit_reason = None
            if lo <= sl_level:
                exit_price = apply_costs(sl_level, 'SELL')
                exit_reason = 'SL'
            elif hi >= tp_level:
                exit_price = apply_costs(tp_level, 'SELL')
                exit_reason = 'TP'
            elif i == len(df) - 1:
                exit_price = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'
            if exit_reason:
                gross = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital_cur += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy='NR7 Breakout'
                ))
                in_trade = False
        else:
            prev = df.iloc[i - 1]
            if not filter_mask.iloc[i - 1]:
                equity.append(capital_cur)
                continue
            if i < 8:
                equity.append(capital_cur)
                continue
            window_ranges = ranges.iloc[i - 7:i]
            if ranges.iloc[i - 1] != window_ranges.min():
                equity.append(capital_cur)
                continue
            if not pd.isna(avg_vol5.iloc[i - 1]):
                if prev['volume'] < avg_vol5.iloc[i - 1] * 0.8:
                    equity.append(capital_cur)
                    continue
            if row['open'] <= prev['high']:
                equity.append(capital_cur)
                continue
            raw_entry = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')
            sl_level = apply_costs(prev['low'], 'SELL')
            sl_pct = (entry_price - sl_level) / entry_price
            if sl_pct <= 0.002:
                equity.append(capital_cur)
                continue
            cur_atr = atr.iloc[i - 1] if not pd.isna(atr.iloc[i - 1]) else ranges.iloc[i - 1] * 2
            tp_level = entry_price + cur_atr * 2
            if (tp_level - entry_price) / entry_price < 0.015:
                equity.append(capital_cur)
                continue
            lots = lot_size(capital_cur, entry_price, 0.02, sl_pct)
            cost = entry_price * lots * 100
            if cost <= capital_cur and lots > 0:
                in_trade = True
                entry_date = date
        equity.append(capital_cur)
    return {
        'strategy': 'NR7 Breakout',
        'trades': trades, 'equity': equity,
        'final_capital': capital_cur, 'initial_capital': capital
    }


def check_nr7_signal(df: pd.DataFrame) -> dict:
    """Live NR7 Breakout checker — mirrors strategy_nr7_breakout's per-bar entry
    applied to the last bar (the one positive-edge strategy from the 2026-07-04
    re-baseline; audit item 2.5 follow-up).

    Setup: bar[-2] is the narrowest-range bar of the trailing 7 (NR7), with
    volume >= 0.8x its 5-bar average. Trigger: the last bar opened above bar[-2]'s
    high (breakout). Entry = last open; SL = NR7-bar low; TP = entry + 2xATR14
    (min 1.5%). Pure: no df mutation.
    """
    if df is None or len(df) < 22:
        return {'has_signal': False, 'reason': 'Data tidak cukup (minimum 22 bars)',
                'details': {}}

    ranges   = df['high'] - df['low']
    atr      = calc_atr(df, 14)
    avg_vol5 = df['volume'].rolling(5).mean()

    nr7_bar = df.iloc[-2]
    last    = df.iloc[-1]

    nr7_window = ranges.iloc[-8:-1]          # the 7 bars ending at bar[-2]
    is_nr7  = bool(ranges.iloc[-2] == nr7_window.min())
    v5      = avg_vol5.iloc[-2]
    vol_ok  = bool(pd.isna(v5) or nr7_bar['volume'] >= v5 * 0.8)

    entry   = float(last['open'])
    sl      = float(nr7_bar['low'])
    cur_atr = atr.iloc[-2]
    tp      = entry + (float(cur_atr) * 2 if not pd.isna(cur_atr)
                       else float(ranges.iloc[-2]) * 2)

    breakout = bool(entry > float(nr7_bar['high']))
    sl_ok    = bool(sl < entry)
    tp_ok    = bool(entry > 0 and (tp - entry) / entry >= 0.015)

    has_signal = bool(is_nr7 and vol_ok and breakout and tp_ok and sl_ok)

    details = {
        'price':           entry,
        'sl':              round(sl),
        'tp':              round(tp),
        'nr7_range':       float(round(ranges.iloc[-2], 2)),
        'breakout_level':  float(nr7_bar['high']),
        'is_nr7':          is_nr7,
        'vol_ok':          vol_ok,
        'breakout':        breakout,
    }
    if has_signal:
        reason = (f"NR7 breakout: open {entry:.0f} > NR7 high "
                  f"{float(nr7_bar['high']):.0f}, SL {sl:.0f} TP {tp:.0f}")
    else:
        miss = []
        if not is_nr7:    miss.append('not 7-bar narrowest')
        if not vol_ok:    miss.append('low NR7 volume')
        if not breakout:  miss.append(f"no breakout (open {entry:.0f} <= "
                                      f"{float(nr7_bar['high']):.0f})")
        if not tp_ok:     miss.append('TP < 1.5%')
        if not sl_ok:     miss.append('SL >= entry')
        reason = f"NR7: {', '.join(miss)}"
    return {'has_signal': has_signal, 'reason': str(reason), 'details': details}


# STRATEGY - OPENING RANGE BREAKOUT (Daily Approximation)
#
# NOTE: Despite the "Opening Range Breakout" name and registry key 'ORB', this is
# NOT genuine intraday ORB (Crabel/Fisher). It's a daily-bar volatility breakout
# using ATR×0.5 around the daily open as a proxy for the morning range.
#
# True intraday ORB (first 30/60 min high-low from minute bars) is available via
# `check_orb_intraday_signal()` below, backed by the `ticks` table. That helper is
# live-screener ready; for backtest integration see STRATEGY_AUDIT.md item A.2.
#
# Kept under this name to preserve walk-forward scores, UI dropdown, and DB
# strategy column values that already reference 'ORB'.
def strategy_orb(df: pd.DataFrame, capital: float = 50_000_000,
                 filters: list = None) -> dict:
    """
    Daily-bar ATR-around-open breakout (a.k.a. "ORB daily approximation").
    Opening Range proxy = open ± (ATR14 × 0.5)
    Breakout signal: close > open + (ATR × 0.5) AND volume > avg_vol × 1.5
    Entry: next bar open
    TP: swing high 20 bars atau ATR × 2 (whichever larger, min entry+2%)
    SL: open of signal bar - ATR × 0.5

    For true intraday ORB use `check_orb_intraday_signal()` (ticks-backed).
    """
    atr = calc_atr(df, 14)  # FIXED: was simplified (high-low), now full True Range
    avg_vol = df['volume'].rolling(20).mean()

    if filters:
        filter_mask = apply_filters(df, filters)
    else:
        filter_mask = pd.Series(True, index=df.index)

    capital_cur = capital
    equity = [capital_cur]
    trades = []
    in_trade = False
    entry_price = tp_level = sl_level = 0.0
    entry_date = ''
    lots = 0

    for i in range(21, len(df)):
        row = df.iloc[i]
        date = str(row['date'])[:10]

        if in_trade:
            hi, lo, cur = row['high'], row['low'], row['close']
            exit_reason = None
            if lo <= sl_level:
                exit_price = apply_costs(sl_level, 'SELL')
                exit_reason = 'SL'
            elif hi >= tp_level:
                exit_price = apply_costs(tp_level, 'SELL')
                exit_reason = 'TP'
            elif i == len(df) - 1:
                exit_price = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'
            if exit_reason:
                gross = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital_cur += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy='ORB'
                ))
                in_trade = False
        else:
            sig = df.iloc[i - 1]
            sig_atr = atr.iloc[i - 1]
            sig_vol = avg_vol.iloc[i - 1]

            if not filter_mask.iloc[i - 1]:
                equity.append(capital_cur)
                continue
            if pd.isna(sig_atr) or pd.isna(sig_vol) or sig_vol == 0:
                equity.append(capital_cur)
                continue

            # Breakout condition: close > open + ATR*0.5, volume spike
            or_high = sig['open'] + sig_atr * 0.5
            breakout = (sig['close'] > or_high) and (sig['volume'] > sig_vol * 1.5)
            if not breakout:
                equity.append(capital_cur)
                continue

            # Entry next bar open
            raw_entry = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')

            # SL = signal bar open - ATR*0.5
            sl_raw = sig['open'] - sig_atr * 0.5
            sl_level = apply_costs(sl_raw, 'SELL')
            sl_pct = (entry_price - sl_level) / entry_price
            if sl_pct <= 0.005 or sl_pct > 0.08:
                equity.append(capital_cur)
                continue

            # TP = swing high 20 bars atau ATR*2, min entry+2%
            swing_hi = df['high'].iloc[max(0, i - 20):i].max()
            atr_tp = entry_price + sig_atr * 2
            tp_level = max(swing_hi * 0.995, atr_tp)
            tp_level = max(tp_level, entry_price * 1.02)

            lots = lot_size(capital_cur, entry_price, 0.02, sl_pct)
            cost = entry_price * lots * 100
            if cost <= capital_cur and lots > 0:
                in_trade = True
                entry_date = date

        equity.append(capital_cur)

    return {
        'strategy': 'ORB',
        'trades': trades, 'equity': equity,
        'final_capital': capital_cur, 'initial_capital': capital
    }


# ─────────────────────────────────────────────
# TRUE INTRADAY ORB — uses minute-resolution `ticks` table
# Ready for live screener; backtest integration is a follow-up (see A.2)
# ─────────────────────────────────────────────

def calc_opening_range_from_ticks(ticker: str, trade_date: str,
                                  opening_minutes: int = 30,
                                  db_path: str = None) -> dict | None:
    """
    Compute true intraday Opening Range from the `ticks` table (1-min Stockbit).
    trade_date: 'YYYY-MM-DD'. Window: 09:00:00 (inclusive) to 09:00 + opening_minutes (exclusive).
    Returns {or_high, or_low, or_range, or_vol, or_open, n_ticks} or None if no data.
    """
    import sqlite3
    from datetime import datetime, timedelta
    if db_path is None:
        from config import DB_PATH
        db_path = DB_PATH
    end_time = (datetime.strptime('09:00:00', '%H:%M:%S')
                + timedelta(minutes=opening_minutes)).strftime('%H:%M:%S')
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute("""
            SELECT price, volume FROM ticks
            WHERE ticker=? AND date=?
              AND time >= '09:00:00' AND time < ?
            ORDER BY time ASC
        """, (ticker, trade_date, end_time)).fetchall()
        conn.close()
    except Exception as e:
        print(f"[orb] ticks query error {ticker} {trade_date}: {e}")
        return None
    if not rows:
        return None
    prices = [r[0] for r in rows if r[0]]
    vols   = [r[1] for r in rows if r[1]]
    if not prices:
        return None
    return {
        'or_high':  max(prices),
        'or_low':   min(prices),
        'or_range': max(prices) - min(prices),
        'or_vol':   sum(vols),
        'or_open':  prices[0],
        'n_ticks':  len(rows),
    }


def check_orb_intraday_signal(ticker: str, opening_minutes: int = 30,
                              lookback_days: int = 20, vol_mult: float = 1.5,
                              db_path: str = None,
                              as_of_date: str = None,
                              as_of_time: str = None) -> dict:
    """
    True intraday ORB signal — only fires after the opening window is complete.

    Setup:
      - Compute today's opening range (high/low/vol) from first `opening_minutes`.
      - Compare today's OR vol to avg OR vol from last `lookback_days` sessions.
      - Signal: current price > OR_high AND today's OR_vol > avg_OR_vol × vol_mult.

    Args:
        as_of_date, as_of_time: override "now" for testing/backtest replay.
            Both must be set to override; else uses datetime.now().

    Returns {'has_signal', 'reason', 'details'} matching other check_*_signal().
    Suggested SL = OR_low; suggested TP = OR_high + (OR_range × 2).
    """
    import sqlite3
    from datetime import datetime, timedelta

    if db_path is None:
        from config import DB_PATH
        db_path = DB_PATH

    if as_of_date and as_of_time:
        today, now_time = as_of_date, as_of_time
    else:
        _now = datetime.now()
        today    = _now.strftime('%Y-%m-%d')
        now_time = _now.strftime('%H:%M:%S')
    end_time = (datetime.strptime('09:00:00', '%H:%M:%S')
                + timedelta(minutes=opening_minutes)).strftime('%H:%M:%S')
    if now_time < end_time:
        return {'has_signal': False,
                'reason': f'Opening range belum lengkap (now {now_time} < {end_time})',
                'details': {}}

    or_today = calc_opening_range_from_ticks(ticker, today, opening_minutes, db_path)
    if or_today is None or or_today['n_ticks'] < 5:
        return {'has_signal': False,
                'reason': f'Tidak cukup ticks pagi ini untuk {ticker}',
                'details': {'or_today': or_today}}

    try:
        conn = sqlite3.connect(db_path)
        past_dates = [r[0] for r in conn.execute("""
            SELECT DISTINCT date FROM ticks
            WHERE ticker=? AND date < ?
            ORDER BY date DESC LIMIT ?
        """, (ticker, today, lookback_days)).fetchall()]
        latest_row = conn.execute("""
            SELECT price FROM ticks WHERE ticker=? AND date=?
            ORDER BY time DESC LIMIT 1
        """, (ticker, today)).fetchone()
        conn.close()
    except Exception as e:
        return {'has_signal': False, 'reason': f'DB error: {e}', 'details': {}}

    or_vols = []
    for d in past_dates:
        or_past = calc_opening_range_from_ticks(ticker, d, opening_minutes, db_path)
        if or_past and or_past['or_vol'] > 0:
            or_vols.append(or_past['or_vol'])
    if len(or_vols) < 5:
        return {'has_signal': False,
                'reason': f'Insufficient OR history ({len(or_vols)} sessions, need ≥5)',
                'details': {'or_today': or_today}}

    avg_or_vol = sum(or_vols) / len(or_vols)
    current_price = latest_row[0] if latest_row else None
    if current_price is None:
        return {'has_signal': False, 'reason': 'No current price tick',
                'details': {'or_today': or_today}}

    breakout = current_price > or_today['or_high']
    vol_ok   = or_today['or_vol'] > avg_or_vol * vol_mult
    details = {
        'or_high':         or_today['or_high'],
        'or_low':          or_today['or_low'],
        'or_range':        or_today['or_range'],
        'or_vol':          or_today['or_vol'],
        'avg_or_vol_20d':  round(avg_or_vol, 0),
        'or_vol_ratio':    round(or_today['or_vol'] / avg_or_vol, 2),
        'current_price':   current_price,
        'breakout':        breakout,
        'vol_ok':          vol_ok,
        'suggested_sl':    or_today['or_low'],
        'suggested_tp':    round(or_today['or_high'] + or_today['or_range'] * 2),
    }
    if breakout and vol_ok:
        return {'has_signal': True,
                'reason': (f"ORB breakout: {current_price} > OR_hi {or_today['or_high']}, "
                           f"vol {details['or_vol_ratio']}× avg"),
                'details': details}
    elif breakout:
        return {'has_signal': False,
                'reason': f"Breakout tanpa volume (ratio {details['or_vol_ratio']}× < {vol_mult}×)",
                'details': details}
    else:
        return {'has_signal': False,
                'reason': (f"Price {current_price} masih dalam OR "
                           f"({or_today['or_low']}-{or_today['or_high']})"),
                'details': details}


"""
Signal Checker untuk Multi-Strategy Backtest
Tambahkan kode ini ke engine/strategies.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Live checker dispatch — one entry per live-capable strategy. Consistency with
# engine/strategy_specs.SPECS and scanner._REGIME_STRATEGY_MAP is pinned by
# tests/test_strategy_specs.py (audit C-1: a strategy must not be
# live-selectable without a working checker).
_CHECKER_DISPATCH = {
    'vol_weighted':             lambda ticker, df: check_vol_weighted_signal(df),
    'momentum':                 lambda ticker, df: check_momentum_signal(df),
    'vwap_reversion':           lambda ticker, df: check_vwap_reversion_signal(df),
    'conservative':             lambda ticker, df: check_conservative_signal(df),
    'Trend Following Breakout': lambda ticker, df: check_trend_following_breakout_signal(df),
    'NR7 Breakout':             lambda ticker, df: check_nr7_signal(df),
    # True intraday ORB — bypasses daily df; uses ticks DB directly.
    'orb_intraday':             lambda ticker, df: check_orb_intraday_signal(ticker),
    'ORB_intraday':             lambda ticker, df: check_orb_intraday_signal(ticker),
    'Crash Recovery':           lambda ticker, df: check_crash_recovery_signal(ticker, df),
    'Panic Rebound':            lambda ticker, df: check_panic_rebound_signal(df),
    'Liquidity Sweep':          lambda ticker, df: check_sweep_flow_signal(df, ticker),
}

# Counter-trend/reversal setups skip the weekly-trend gate by design:
# Crash Recovery (crash bounce), Panic Rebound (the signal IS a downtrend),
# Liquidity Sweep (the setup IS a dip). Matches the pre-refactor early returns.
_WEEKLY_GATE_BYPASS = {'Crash Recovery', 'Panic Rebound', 'Liquidity Sweep'}


def check_current_entry_signal(ticker: str, strategy: str, df: pd.DataFrame = None) -> dict:
    """
    Cek apakah ticker memenuhi entry criteria dari strategy yang dipilih
    pada data terbaru (last bar).
    Includes multi-timeframe weekly trend confirmation as final gate
    (bypassed for the counter-trend book).

    Output contract (audit C-1): any has_signal=True result carries
    details['price'] — enforced via engine.strategy_specs.ensure_entry_price.

    Returns:
        dict: {'has_signal': bool, 'reason': str, 'details': dict}
    """
    from engine.strategy_specs import ensure_entry_price

    if df is None:
        df = get_ticker_data(ticker)

    if df.empty or len(df) < 20:
        return {
            'has_signal': False,
            'reason': 'Data tidak cukup (minimum 20 bars)',
            'details': {}
        }

    checker = _CHECKER_DISPATCH.get(strategy)
    if checker is None:
        return {
            'has_signal': False,
            'reason': f'Strategy {strategy} belum didukung',
            'details': {}
        }

    result = checker(ticker, df)

    # Multi-timeframe gate: only when the daily signal passes and the
    # strategy is not in the counter-trend bypass set.
    if strategy not in _WEEKLY_GATE_BYPASS and result.get('has_signal'):
        w_pass, w_reason = calc_weekly_trend(df)
        result['details']['weekly_trend'] = w_reason
        if not w_pass:
            result['has_signal'] = False
            result['reason'] = f"W-BLOCK: {w_reason} | daily: {result['reason']}"

    return ensure_entry_price(result, df)


def check_vol_weighted_signal(df: pd.DataFrame) -> dict:
    """
    Vol-Weighted Entry Signal Checker — mirrors strategy_vol_weighted exactly
    (plan 1C item 1.6): VR > 1.8x AND delta > 0 AND close > open.
    Pure: no df mutation (audit H-4). VWAP shown is the rolling-60 calc_vwap
    (info only, not a gate).
    """
    from engine.indicators import calc_delta, calc_vwap

    latest = df.iloc[-1]
    avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
    if pd.isna(avg_volume) or avg_volume == 0:
        return {
            'has_signal': False,
            'reason': 'Avg volume tidak tersedia',
            'details': {}
        }

    current_volume = latest['volume']
    vr = current_volume / avg_volume

    delta_val = float(calc_delta(df).iloc[-1])
    bullish = bool(latest['close'] > latest['open'])

    vwap = calc_vwap(df).iloc[-1]
    current_price = latest['close']
    if pd.isna(vwap) or vwap <= 0:
        vwap, price_vs_vwap = None, 0.0
    else:
        price_vs_vwap = (current_price - vwap) / vwap * 100

    vr_pass = vr > 1.8
    has_signal = vr_pass and delta_val > 0 and bullish

    if has_signal:
        reason = f"VR {vr:.2f}x > 1.8 ✓, delta {delta_val:,.0f} > 0 ✓, bullish ✓"
    elif not vr_pass:
        reason = f"VR {vr:.2f}x ≤ 1.8 (butuh > 1.8)"
    else:
        reason = f"VR {vr:.2f}x ✓ tapi delta/candle tidak bullish (delta={delta_val:,.0f})"

    return {
        'has_signal': bool(has_signal),
        'reason': str(reason),
        'details': {
            'vr': float(round(vr, 2)),
            'current_volume': int(current_volume),
            'avg_volume': int(avg_volume),
            'price': float(round(current_price, 2)),
            'delta': float(round(delta_val, 0)),
            'bullish': bullish,
            'vwap': float(round(vwap, 2)) if vwap else None,
            'price_vs_vwap_pct': float(round(price_vs_vwap, 2)),
            'price_above_vwap': bool(vwap and current_price > vwap),
        }
    }


def check_momentum_signal(df: pd.DataFrame) -> dict:
    """
    Momentum Following Signal Checker — mirrors strategy_momentum exactly
    (plan 1C item 1.6): 2-day up streak AND 1.3 < VR ≤ 5.0 AND not
    watch-blocked. Pure: no df mutation.
    """
    daily_return = df['close'].pct_change()
    streak = 0
    for i in range(len(df) - 1, max(len(df) - 10, -1), -1):
        r = daily_return.iloc[i]
        if not pd.isna(r) and r > 0:
            streak += 1
        else:
            break

    avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
    latest = df.iloc[-1]
    vr = latest['volume'] / avg_volume if (not pd.isna(avg_volume) and avg_volume > 0) else 0

    watch_blocked = bool(_watch_signal_block(df).iloc[-1])

    streak_pass = streak >= 2
    vr_pass = 1.3 < vr <= 5.0
    has_signal = streak_pass and vr_pass and not watch_blocked

    if has_signal:
        reason = f"{streak}-day streak ✓, VR {vr:.2f}x ✓"
    elif not streak_pass:
        reason = f"Streak {streak} < 2 days"
    elif watch_blocked:
        reason = "Watch-blocked (VR elevated, non-bullish session)"
    elif vr > 5.0:
        reason = f"VR {vr:.2f}x > 5.0 (climax cap)"
    else:
        reason = f"VR {vr:.2f}x ≤ 1.3"

    last_ret = daily_return.iloc[-1]
    return {
        'has_signal': bool(has_signal),
        'reason': str(reason),
        'details': {
            'streak': int(streak),
            'vr': float(round(vr, 2)),
            'daily_return': float(round((last_ret if not pd.isna(last_ret) else 0) * 100, 2)),
            'watch_blocked': watch_blocked,
        }
    }


def check_vwap_reversion_signal(df: pd.DataFrame) -> dict:
    """
    VWAP Mean Reversion Signal Checker — mirrors strategy_vwap_reversion
    exactly (plan 1C item 1.6): rolling-60 calc_vwap (the old anchored-cumsum
    VWAP changed value with however much history was loaded — audit H-5),
    distance < -1%, VR > 1.3.  Pure: no df mutation.
    """
    from engine.indicators import calc_vwap

    latest = df.iloc[-1]
    vwap = calc_vwap(df).iloc[-1]
    if pd.isna(vwap) or vwap <= 0:
        return {
            'has_signal': False,
            'reason': 'VWAP-60 belum siap (butuh 60 bars)',
            'details': {}
        }

    distance = (latest['close'] - vwap) / vwap * 100

    avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
    vr = latest['volume'] / avg_volume if (not pd.isna(avg_volume) and avg_volume > 0) else 0

    distance_pass = distance < -1
    vr_pass = vr > 1.3
    has_signal = distance_pass and vr_pass

    if has_signal:
        reason = f"Distance {distance:.2f}% < -1% ✓, VR {vr:.2f}x ✓"
    elif not distance_pass:
        reason = f"Distance {distance:.2f}% ≥ -1% (not oversold)"
    else:
        reason = f"VR {vr:.2f}x ≤ 1.3"

    return {
        'has_signal': bool(has_signal),
        'reason': str(reason),
        'details': {
            'distance_pct': float(round(distance, 2)),
            'vr': float(round(vr, 2)),
            'price': float(round(latest['close'], 2)),
            'vwap': float(round(vwap, 2))
        }
    }


def check_conservative_signal(df: pd.DataFrame) -> dict:
    """
    Conservative Confirm Signal Checker — mirrors strategy_conservative
    exactly (plan 1C item 1.6): VR > 1.3, bullish candle, close > MA20,
    AND ATR calm (ATR < 1.5x its 10-bar mean — was missing live).
    Pure: no df mutation.
    """
    from engine.indicators import calc_atr

    latest = df.iloc[-1]
    avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
    vr = latest['volume'] / avg_volume if (not pd.isna(avg_volume) and avg_volume > 0) else 0
    ma20 = df['close'].rolling(window=20).mean().iloc[-1]

    atr = calc_atr(df, 14)
    atr_ma = atr.rolling(10).mean()
    atr_now, atr_ma_now = atr.iloc[-1], atr_ma.iloc[-1]
    atr_ok = (not pd.isna(atr_now) and not pd.isna(atr_ma_now)
              and atr_now < atr_ma_now * 1.5)

    vr_pass = vr > 1.3
    bullish = bool(latest['close'] > latest['open'])
    above_ma = bool(not pd.isna(ma20) and latest['close'] > ma20)

    has_signal = vr_pass and bullish and above_ma and atr_ok

    checks = [
        f"VR {vr:.2f}x {'✓' if vr_pass else '✗'}",
        f"Bullish {'✓' if bullish else '✗'}",
        f"Above MA20 {'✓' if above_ma else '✗'}",
        f"ATR calm {'✓' if atr_ok else '✗'}",
    ]
    reason = ", ".join(checks)

    return {
        'has_signal': bool(has_signal),
        'reason': str(reason),
        'details': {
            'vr': float(round(vr, 2)),
            'bullish': bullish,
            'above_ma20': above_ma,
            'atr_ok': bool(atr_ok),
            'price': float(round(latest['close'], 2)),
            'ma20': float(round(ma20, 2)) if not pd.isna(ma20) else None,
        }
    }


# Helper function untuk fetch data ticker dari database
def get_ticker_data(ticker: str) -> pd.DataFrame:
    """
    Fetch OHLCV data untuk ticker dari database
    
    Args:
        ticker: Kode ticker
    
    Returns:
        DataFrame dengan kolom: date, open, high, low, close, volume
    """
    import sqlite3
    from config import DB_PATH as db_path

    try:
        conn = sqlite3.connect(db_path)
        query = f"""
            SELECT date, open, high, low, close, volume
            FROM ohlcv
            WHERE ticker = '{ticker}'
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert date column
        df['date'] = pd.to_datetime(df['date'])
        
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


# Example usage
if __name__ == '__main__':
    # Test signal checker
    test_ticker = 'BBCA'
    test_strategy = 'vol_weighted'
    
    result = check_current_entry_signal(test_ticker, test_strategy)
    
    print(f"\nSignal Check untuk {test_ticker} - Strategy: {test_strategy}")
    print(f"Has Signal: {result['has_signal']}")
    print(f"Reason: {result['reason']}")


# ─────────────────────────────────────────────
# STRATEGY: SWING TREND (big TP, reverse-trend SL)
# ─────────────────────────────────────────────

def _confirmed_pivots(pivot_indices, i: int, n: int = 2) -> list:
    """Pivots usable at decision bar i.

    A 2n+1 centered swing pivot at index p is only confirmable once bar p+n
    exists, so at bar i only pivots with p + n <= i are known. Using later
    pivots leaks future bars into the decision (look-ahead bias).
    """
    return [p for p in pivot_indices if p + n <= i]


def _bearish_engulfing(df: pd.DataFrame, i: int) -> bool:
    if i < 1:
        return False
    prev_bull = df['close'].iloc[i - 1] > df['open'].iloc[i - 1]
    cur_bear  = df['close'].iloc[i]     < df['open'].iloc[i]
    engulf = (df['open'].iloc[i] >= df['close'].iloc[i - 1] and
              df['close'].iloc[i] <= df['open'].iloc[i - 1])
    return bool(prev_bull and cur_bear and engulf)


def strategy_swing_trend(df: pd.DataFrame,
                         capital: float = 50_000_000,
                         filters: list = None,
                         risk_per_trade: float = 0.01,
                         flow_data: dict = None) -> dict:
    """
    Swing-Trend Strategy — ride early-stage uptrends; exit on trend reversal.

    Entry: trend-onset (ADX rising ROC>15%, 20<adx<30, MA20 slope up,
           reclaimed MA50, HH/HL pivots, 1.5<=vol_ratio<=5.0,
           close>open, not overextended, score>=60).
    Initial SL: max(last swing-low, MA50, entry - 1.5*ATR14).
    Partial TP: close 50% position at 1.5x RR.
    Exit on any reverse-trend trigger:
      R1 close<MA20 & slope neg 2d & VR>=1.3
      R3 ADX drop >20% from peak
      R4 3-of-4 lower closes, vol_ratio >= 1.8
      R5 flow composite_score <= -2 for 2d (jika flow_data tersedia)
      R6 bearish engulfing, volume > 1.8x avg20
      R7 trailed SL hit (raised to each new HL pivot after 1 ATR; BE at +8%)

    flow_data: optional dict {date_str: composite_score} untuk R5 exit.
               Jika None, R5 tidak diaktifkan.
    """
    from engine.regime_filter import calc_adx, calc_ma_slope
    from engine.swing_screener import find_swing_points

    strategy_name = 'Swing Trend'
    initial_capital = capital

    if len(df) < 55:
        return {'strategy': strategy_name, 'trades': [],
                'equity': [capital] * len(df),
                'final_capital': capital,
                'initial_capital': capital}

    adx       = calc_adx(df, 14)
    slope     = calc_ma_slope(df, 20, 5)
    ma20      = df['close'].rolling(20).mean()
    ma50      = df['close'].rolling(50).mean()
    atr       = calc_atr(df, 14)
    avg_vol   = df['volume'].rolling(20).mean()
    vr        = df['volume'] / avg_vol

    highs_idx_all, lows_idx_all = find_swing_points(df, n=2)

    equity      = [capital]
    trades      = []
    in_trade    = False
    entry_price = 0.0
    entry_date  = ''
    sl_level    = 0.0
    lots        = 0
    adx_peak    = 0.0
    highest_seen = 0.0
    entry_sl_price = 0.0
    partial_done = False

    for i in range(1, len(df)):
        row  = df.iloc[i]
        date = str(row['date'])[:10]

        if in_trade:
            high_i = row['high']
            low_i  = row['low']
            cur    = row['close']

            highest_seen = max(highest_seen, high_i)
            if not pd.isna(adx.iloc[i]):
                adx_peak = max(adx_peak, float(adx.iloc[i]))

            # Partial TP at 1.5x RR — close 50% position
            if not partial_done and entry_sl_price > 0:
                rr_dist = entry_price - entry_sl_price
                rr_target = entry_price + 1.5 * rr_dist
                if highest_seen >= rr_target:
                    partial_lots = lots // 2
                    if partial_lots > 0:
                        partial_pnl = round((rr_target - entry_price) * partial_lots * 100)
                        capital += partial_pnl
                        trades.append(Trade(
                            entry_date=entry_date, exit_date=date,
                            entry_price=entry_price, exit_price=rr_target,
                            lots=partial_lots, direction='BUY',
                            exit_reason='PARTIAL_TP',
                            pnl_rp=partial_pnl,
                            pnl_pct=(rr_target - entry_price) / entry_price * 100,
                            strategy=f"{strategy_name}[PARTIAL_TP]"
                        ))
                        lots -= partial_lots
                        partial_done = True

            # Raise SL to latest HL pivot (only after 1 ATR from entry)
            lows_seen = _confirmed_pivots(lows_idx_all, i, n=2)
            if lows_seen:
                new_hl = float(df['low'].iloc[lows_seen[-1]])
                atr_ok = not pd.isna(atr.iloc[i]) and (highest_seen - entry_price) > atr.iloc[i]
                if new_hl > sl_level and atr_ok:
                    sl_level = new_hl

            # Break-even lock after +8%
            if highest_seen >= entry_price * 1.08 and sl_level < entry_price:
                sl_level = entry_price

            exit_reason = None
            exit_price  = None

            # R7 — trailed SL hit
            if low_i <= sl_level:
                exit_price  = apply_costs(sl_level, 'SELL')
                exit_reason = 'R7_TRAIL_SL'

            # R1 — close < MA20, slope negative 2 days, volume confirmation
            if exit_reason is None and not pd.isna(ma20.iloc[i]) and not pd.isna(slope.iloc[i]):
                slope_neg_2d = slope.iloc[i] < 0 and (pd.isna(slope.iloc[i-1]) or slope.iloc[i-1] < 0)
                vr_ok = not pd.isna(vr.iloc[i]) and vr.iloc[i] >= 1.3
                if cur < ma20.iloc[i] and slope_neg_2d and vr_ok:
                    exit_price  = apply_costs(cur, 'SELL')
                    exit_reason = 'R1_MA_BREAK'

            # R3 — ADX collapse (percentage drop from peak)
            if exit_reason is None and adx_peak > 25 and not pd.isna(adx.iloc[i]):
                adx_drop_pct = (adx_peak - adx.iloc[i]) / adx_peak
                if adx_drop_pct > 0.20:
                    exit_price  = apply_costs(cur, 'SELL')
                    exit_reason = 'R3_ADX_FADE'

            # R4 — 3-of-4 lower closes on >=1.8 vol
            if exit_reason is None and i >= 4:
                c0, c1, c2, c3, c4 = df['close'].iloc[i], df['close'].iloc[i-1], df['close'].iloc[i-2], df['close'].iloc[i-3], df['close'].iloc[i-4]
                three_of_four = sum([c0 < c1, c1 < c2, c2 < c3, c3 < c4]) >= 3
                vr_hot = (not pd.isna(vr.iloc[i])) and vr.iloc[i] >= 1.8
                if three_of_four and vr_hot:
                    exit_price  = apply_costs(cur, 'SELL')
                    exit_reason = 'R4_DISTRIBUTION'

            # R5 — flow flip (jika data tersedia)
            if exit_reason is None and flow_data is not None:
                date_i = str(df['date'].iloc[i])[:10]
                date_i_minus_1 = str(df['date'].iloc[i-1])[:10] if i > 0 else date_i
                scores = []
                for d in [date_i, date_i_minus_1]:
                    cs = flow_data.get(d)
                    if cs is not None:
                        scores.append(cs)
                if len(scores) == 2 and all(s <= -2 for s in scores):
                    exit_price  = apply_costs(cur, 'SELL')
                    exit_reason = 'R5_FLOW_FLIP'

            # R6 — bearish engulfing on high volume
            if exit_reason is None and _bearish_engulfing(df, i):
                if not pd.isna(vr.iloc[i]) and vr.iloc[i] > 1.8:
                    exit_price  = apply_costs(cur, 'SELL')
                    exit_reason = 'R6_BEAR_ENGULF'

            # EOD force close on last bar
            if exit_reason is None and i == len(df) - 1:
                exit_price  = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'

            if exit_reason:
                gross   = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital += gross
                # 1.9: record the REAL trigger (R1_MA_BREAK, R7_TRAIL_SL, ...)
                # — the old TP/SL/TRAIL remap made exit-reason stats meaningless.
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy=f"{strategy_name}[{exit_reason}]"
                ))
                in_trade = False

        else:
            if i < 55 or i >= len(df) - 1:
                equity.append(capital)
                continue

            # Onset gates (mirrors swing_screener, simplified for per-bar loop)
            adx_i, adx_prev = adx.iloc[i], adx.iloc[i - 1]
            if pd.isna(adx_i) or pd.isna(adx_prev):
                equity.append(capital); continue
            slope_i = slope.iloc[i]
            slope_5 = slope.iloc[i - 5] if i >= 5 else np.nan
            if pd.isna(slope_i) or pd.isna(slope_5):
                equity.append(capital); continue

            adx_roc = (adx_i - adx_prev) / adx_prev if adx_prev > 0 else 0
            gate_adx   = (20 < adx_i < 30) and adx_roc > 0.15
            gate_slope = (slope_i > 0) and (slope_i > slope_5)

            if pd.isna(ma50.iloc[i]):
                equity.append(capital); continue
            above_ma50_now = df['close'].iloc[i] > ma50.iloc[i]
            was_below = (df['close'].iloc[max(0, i-5):i] <= ma50.iloc[max(0, i-5):i]).any()
            gate_reclaim = bool(above_ma50_now and was_below)

            lows_so_far  = _confirmed_pivots(lows_idx_all,  i, n=2)
            highs_so_far = _confirmed_pivots(highs_idx_all, i, n=2)
            gate_hhhl = (
                len(highs_so_far) >= 2 and len(lows_so_far) >= 2 and
                df['high'].iloc[highs_so_far[-1]] > df['high'].iloc[highs_so_far[-2]] and
                df['low'].iloc[lows_so_far[-1]]  > df['low'].iloc[lows_so_far[-2]]
            )

            gate_vol = (not pd.isna(vr.iloc[i])) and 1.5 <= vr.iloc[i] <= 5.0
            bullish_close = df['close'].iloc[i] > df['open'].iloc[i]

            ma20_i = ma20.iloc[i]
            distance = (df['close'].iloc[i] - ma20_i) / ma20_i * 100 if ma20_i else 100
            gate_extend = distance < 8.0

            # Pullback-reclaim of MA20 (any of last 3 bars was <= MA20)
            ma20_win = ma20.iloc[max(0, i-3):i+1]
            c_win    = df['close'].iloc[max(0, i-3):i+1]
            pullback_reclaim = (c_win <= ma20_win).any() and (df['close'].iloc[i] > ma20_i)

            score = 0
            score += 25 if gate_adx     else 0
            score += 20 if gate_slope   else 0
            score += 15 if gate_reclaim else 0
            score += 15 if gate_hhhl    else 0
            score += 10 if gate_vol     else 0
            score +=  5 if gate_extend  else 0
            # flow_confirms not evaluable in offline backtest -> max achievable = 90

            if score >= 60 and bullish_close and pullback_reclaim and not _watch_signal_block(df).iloc[i]:
                # Enter next bar open
                next_i = i + 1
                if next_i >= len(df):
                    equity.append(capital); continue
                raw_entry   = df['open'].iloc[next_i]
                entry_price = apply_costs(raw_entry, 'BUY')

                atr_val = atr.iloc[i] if not pd.isna(atr.iloc[i]) else entry_price * 0.02
                last_sl = df['low'].iloc[lows_so_far[-1]] if lows_so_far else entry_price * 0.95
                sl_candidates = [last_sl, ma50.iloc[i], entry_price - 1.5 * atr_val]
                sl_candidates = [x for x in sl_candidates if x > 0]
                initial_sl = max(sl_candidates) if sl_candidates else entry_price * 0.95
                if initial_sl >= entry_price:
                    initial_sl = entry_price * 0.97

                sl_pct_eff = (entry_price - initial_sl) / entry_price
                if sl_pct_eff <= 0:
                    equity.append(capital); continue

                lots = lot_size(capital, entry_price, risk_per_trade, sl_pct_eff)
                cost = entry_price * lots * 100
                if cost > capital:
                    equity.append(capital); continue

                sl_level       = initial_sl
                entry_sl_price = initial_sl
                entry_date     = str(df.iloc[next_i]['date'])[:10]
                adx_peak     = float(adx_i)
                highest_seen = entry_price
                in_trade     = True

        equity.append(capital)

    return {
        'strategy':        strategy_name,
        'trades':          trades,
        'equity':          equity,
        'final_capital':   capital,
        'initial_capital': initial_capital,
    }


# ── Strategi 9: Trend-Following Breakout ─────────────────────────────────────

def strategy_trend_following_breakout(df: pd.DataFrame,
                                      capital: float = 50_000_000,
                                      filters: list = None,
                                      atr_mult: float = 3.0) -> dict:
    """
    Trend-Following Breakout — catch high-momentum breakouts, let runners run.

    Entry (all required):
      1. close > prior 20-bar Donchian high (breakout)
      2. volume > 1.8× MA20(volume)
      3. ATR(14) > 0.5× 60-bar median ATR  (volatility expanding)
      4. close > MA50                        (level regime filter)
      5. MA20 slope > 0.5%                    (trend actually rising — market context)
      6. volume < 4.0× MA20(volume)           (reject climax blow-off)
    Exit (shared kernel, engine/exits — plan 1B):
      - Chandelier trail: stop = highest_seen(prior bars) − atr_mult×ATR(entry)
      - OR close < MA20 (ma_break_period=20 policy metadata)
    NOTE 2026-07-02: trail anchor unified close→high to match the forward-test
    engine; the old label 'TRAIL_SL' is now the kernel's 'TRAIL'. The entry
    bar itself is evaluated (a gap can exit day one), matching the ft engine.
    Sizing: risk 0.5% of capital; SL = atr_mult×ATR; max 30% capital per trade.
    atr_mult defaults to 3.0 (full-history WF validated 2026-06-27: pooled PF
    1.82->1.98, avg P&L/trade +4.63->+6.03% vs the prior 2.5; see scripts/tfb_trail_wf.py).
    Was 2.5 through 2026-06-26. Tunable for walk-forward exit validation.

    Conditions 5–6 (market-context gate) were validated out-of-sample: rolling
    12mo/3mo walk-forward across 852 tickers lifted consistency 31.7%→40.7%,
    win-rate 31.6%→39.6%, avg P&L/trade +0.95%→+4.63% (cost: ~46% fewer trades).
    ADX was tested and rejected — winners/losers both ~27 (no separation).
    """
    from engine.regime_filter import calc_ma_slope

    strategy_name  = 'Trend Following Breakout'
    initial_capital = capital

    if len(df) < 65:
        return {'strategy': strategy_name, 'trades': [],
                'equity': [capital] * len(df),
                'final_capital': capital, 'initial_capital': capital}

    ma20        = df['close'].rolling(20).mean()
    ma50        = df['close'].rolling(50).mean()
    atr         = calc_atr(df, 14)
    avg_vol     = df['volume'].rolling(20).mean()
    donchian20  = df['high'].rolling(20).max().shift(1)   # prior 20-bar high
    atr60_med   = atr.rolling(60).median()
    ma20_slope  = calc_ma_slope(df, 20, 5)                # % rise of MA20 over 5 bars

    # Breakout signal per bar (NaN operands compare False, so unready bars
    # are naturally excluded). Evaluated on the signal bar; entry fills at the
    # NEXT bar's open — never at the signal bar's own close.
    signal = (
        (df['close']  > donchian20) &
        (df['volume'] > 1.8 * avg_vol) &
        (atr          > 0.5 * atr60_med) &
        (df['close']  > ma50) &
        (ma20_slope   > 0.5) &                # rising trend (not sideways/down)
        (df['volume'] < 4.0 * avg_vol)        # not a climax blow-off
    )

    from engine.exits import ExitPolicy, PositionView, Bar, evaluate_exit
    # atr_mult is a backtest parameter (trail-sweep validation); build the
    # policy from it so non-default sweeps stay honest. At the default 3.0
    # this equals get_policy('Trend Following Breakout') minus ma_break
    # metadata (the MA20 break is evaluated inline below).
    _policy = ExitPolicy(trail_enable=True, trail_atr_mult=atr_mult,
                         ma_break_period=20)

    equity      = [capital]
    trades      = []
    in_trade    = False
    entry_price = 0.0
    entry_atr   = 0.0
    highest     = 0.0
    lowest      = 0.0
    lots        = 0
    entry_date  = ''

    for i in range(65, len(df)):
        row     = df.iloc[i]
        date    = str(row['date'])[:10]
        cur_ma20 = ma20.iloc[i]
        bar = Bar(date=date, open=float(row['open']), high=float(row['high']),
                  low=float(row['low']), close=float(row['close']))

        if not in_trade and signal.iloc[i - 1]:
            sig_atr = atr.iloc[i - 1]
            if pd.isna(sig_atr) or sig_atr <= 0:
                equity.append(capital)
                continue
            entry_price = apply_costs(row['open'], 'BUY')   # next-bar open
            sl_dist     = atr_mult * sig_atr
            sl_pct      = sl_dist / entry_price
            if sl_pct <= 0.001:
                equity.append(capital)
                continue
            lots = lot_size(capital, entry_price, 0.005, sl_pct)
            cost = entry_price * lots * 100
            if cost <= capital and lots > 0:
                in_trade    = True
                entry_date  = date
                entry_atr   = float(sig_atr)
                highest     = entry_price
                lowest      = entry_price
                # fall through: evaluate the entry bar too (gap day-one exit)
            else:
                equity.append(capital)
                continue

        if in_trade:
            # Kernel decides SL/TRAIL/TP/TIME from PRIOR-bar extremes —
            # the C3 (2026-06-30) test-first/ratchet-after discipline, now
            # high-anchored (Chandelier) to match the forward-test engine.
            view = PositionView(policy=_policy, direction='LONG',
                                entry=entry_price, atr=entry_atr,
                                highest_seen=highest, lowest_seen=lowest,
                                hold_days=0)
            decision = evaluate_exit(view, bar)
            exit_reason = exit_price = None
            if decision is not None:
                exit_reason = decision.reason              # 'TRAIL'
                exit_price  = apply_costs(decision.fill_price, 'SELL')
            elif not pd.isna(cur_ma20) and bar.close < cur_ma20:
                exit_reason = 'MA20_BREAK'
                exit_price  = apply_costs(bar.close, 'SELL')
            elif i == len(df) - 1:
                exit_reason = 'EOD'
                exit_price  = apply_costs(bar.close, 'SELL')

            if exit_reason:
                gross   = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy=strategy_name
                ))
                in_trade = False
            else:
                highest = max(highest, bar.high)
                lowest  = min(lowest, bar.low)

        equity.append(capital)

    return {
        'strategy':        strategy_name,
        'trades':          trades,
        'equity':          equity,
        'final_capital':   capital,
        'initial_capital': initial_capital,
    }


def check_trend_following_breakout_signal(df: pd.DataFrame) -> dict:
    """Live signal checker for Trend Following Breakout (last bar only)."""
    if len(df) < 65:
        return {'has_signal': False, 'reason': 'Data tidak cukup (65 bars)', 'details': {}}

    from engine.regime_filter import calc_ma_slope

    ma20       = df['close'].rolling(20).mean()
    ma50       = df['close'].rolling(50).mean()
    atr        = calc_atr(df, 14)
    avg_vol    = df['volume'].rolling(20).mean()
    donchian20 = df['high'].rolling(20).max().shift(1)
    atr60_med  = atr.rolling(60).median()
    ma20_slope = calc_ma_slope(df, 20, 5)

    latest     = df.iloc[-1]
    cur_atr    = atr.iloc[-1]
    cur_ma20   = ma20.iloc[-1]
    cur_ma50   = ma50.iloc[-1]
    cur_don    = donchian20.iloc[-1]
    cur_atr60  = atr60_med.iloc[-1]
    cur_avvol  = avg_vol.iloc[-1]
    cur_slope  = ma20_slope.iloc[-1]

    if any(pd.isna(v) for v in [cur_atr, cur_ma20, cur_ma50, cur_don, cur_atr60, cur_avvol, cur_slope]):
        return {'has_signal': False, 'reason': 'Indikator belum siap (NaN)', 'details': {}}

    cond_breakout = latest['close'] > cur_don
    cond_volume   = latest['volume'] > 1.8 * cur_avvol
    cond_atr_exp  = cur_atr > 0.5 * cur_atr60
    cond_regime   = latest['close'] > cur_ma50

    vol_ratio = latest['volume'] / cur_avvol if cur_avvol > 0 else 0

    cond_slope    = cur_slope > 0.5            # MA20 rising (market context)
    cond_no_climax = vol_ratio < 4.0           # not a climax blow-off

    details = {
        'close':         latest['close'],
        'donchian20':    round(cur_don, 0),
        'vol_ratio':     round(vol_ratio, 2),
        'atr':           round(cur_atr, 2),
        'atr60_median':  round(cur_atr60, 2),
        'ma20':          round(cur_ma20, 0),
        'ma50':          round(cur_ma50, 0),
        'ma20_slope':    round(cur_slope, 2),
        'cond_breakout': cond_breakout,
        'cond_volume':   cond_volume,
        'cond_atr_exp':  cond_atr_exp,
        'cond_regime':   cond_regime,
        'cond_slope':    cond_slope,
        'cond_no_climax': cond_no_climax,
    }

    if cond_breakout and cond_volume and cond_atr_exp and cond_regime and cond_slope and cond_no_climax:
        return {
            'has_signal': True,
            'reason': f"TFB: breakout D20={cur_don:.0f}, VR={vol_ratio:.1f}x, slope={cur_slope:.1f}%, ATR expanding",
            'details': details,
        }

    missing = [k for k, v in {
        'breakout': cond_breakout, 'volume': cond_volume,
        'atr_exp': cond_atr_exp, 'regime': cond_regime,
        'slope': cond_slope, 'no_climax': cond_no_climax
    }.items() if not v]
    return {
        'has_signal': False,
        'reason': f"TFB: kondisi belum terpenuhi ({', '.join(missing)})",
        'details': details,
    }
    print(f"Details: {result['details']}")


# ─────────────────────────────────────────────
# CRASH RECOVERY CONSTANTS
# ─────────────────────────────────────────────
CRASH_MIN_GAP_DAYS   = 5      # calendar days — suspension proxy (weekend = 2-3 days)
CRASH_GAP_DOWN_PCT   = -0.20  # ≥20% gap-down on resume open vs prior close
CRASH_VR_MIN         = 2.0    # volume ratio threshold for confirmation
CRASH_ENTRY_WINDOW   = 3      # max bars after crash resume to find confirmation
CRASH_TP_RETRACEMENT = 0.50   # TP at 50% gap retracement from resume open


# ─────────────────────────────────────────────
# STRATEGY 11 — CRASH RECOVERY
# ─────────────────────────────────────────────

def strategy_crash_recovery(df: pd.DataFrame, capital: float = 50_000_000,
                             filters: list = None) -> dict:
    """
    Entry: gap-down >=20% after >=5 calendar day gap (suspension proxy),
           confirmed by VR>2x + bullish close within 3 bars post-resume.
    SL: low of crash resume bar (NOT ATR — ATR is inflated by the gap bar).
    TP: resume_open + 50% x gap_amount (50% gap retracement).
    """
    if len(df) < 5:
        return {'strategy': 'Crash Recovery', 'trades': [], 'equity': [capital],
                'final_capital': capital, 'initial_capital': capital}

    df = df.copy().reset_index(drop=True)
    df['_dt'] = pd.to_datetime(df['date'])
    day_diff = df['_dt'].diff().dt.days.fillna(1)
    open_gap_pct = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
    vr = calc_vol_ratio(df, 20)

    capital_cur = capital
    equity = [capital_cur]
    trades = []
    in_trade = False
    entry_price = tp_level = sl_level = 0.0
    entry_date = ''
    lots = 0

    entry_window_active = False
    window_bars_remaining = 0
    resume_low = 0.0
    resume_open_price = 0.0
    gap_amount = 0.0
    enter_next_bar = False

    for i in range(1, len(df)):
        row = df.iloc[i]
        date = str(row['date'])[:10]

        if enter_next_bar and not in_trade:
            raw_entry = row['open']
            ep = apply_costs(raw_entry, 'BUY')
            sl_price = apply_costs(resume_low, 'SELL')
            sl_pct = (ep - sl_price) / ep if ep > sl_price else 0.02
            if sl_pct < 0.005:
                sl_pct = 0.02
                sl_price = ep * (1.0 - sl_pct)
            tp_price = resume_open_price + CRASH_TP_RETRACEMENT * gap_amount
            if tp_price > ep * 1.02:
                lots_n = lot_size(capital_cur, ep, 0.02, sl_pct)
                cost = ep * lots_n * 100
                if cost <= capital_cur and lots_n > 0:
                    entry_price = ep
                    sl_level = sl_price
                    tp_level = tp_price
                    lots = lots_n
                    in_trade = True
                    entry_date = date
            enter_next_bar = False

        if in_trade:
            hi, lo, cur = row['high'], row['low'], row['close']
            exit_reason = None
            if lo <= sl_level:
                exit_price = apply_costs(sl_level, 'SELL')
                exit_reason = 'SL'
            elif hi >= tp_level:
                exit_price = apply_costs(tp_level, 'SELL')
                exit_reason = 'TP'
            elif i == len(df) - 1:
                exit_price = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'
            if exit_reason:
                gross = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital_cur += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy='Crash Recovery'
                ))
                in_trade = False
        else:
            is_crash_resume = (
                not pd.isna(open_gap_pct.iloc[i])
                and day_diff.iloc[i] >= CRASH_MIN_GAP_DAYS
                and open_gap_pct.iloc[i] <= CRASH_GAP_DOWN_PCT
            )

            if is_crash_resume:
                entry_window_active = True
                window_bars_remaining = CRASH_ENTRY_WINDOW
                resume_low = row['low']
                resume_open_price = row['open']
                gap_amount = df['close'].iloc[i - 1] - resume_open_price
                enter_next_bar = False
            elif entry_window_active and window_bars_remaining > 0:
                vr_val = vr.iloc[i]
                if (not pd.isna(vr_val) and vr_val >= CRASH_VR_MIN
                        and row['close'] > row['open']):
                    enter_next_bar = True
                    entry_window_active = False
                else:
                    window_bars_remaining -= 1
                    if window_bars_remaining == 0:
                        entry_window_active = False

        equity.append(capital_cur)

    return {
        'strategy':        'Crash Recovery',
        'trades':          trades,
        'equity':          equity,
        'final_capital':   capital_cur,
        'initial_capital': capital,
    }


def check_crash_recovery_signal(ticker: str, df: pd.DataFrame,
                                 db_path: str = None) -> dict:
    """
    Live signal check for crash recovery. Queries suspension_events for a
    recent suspension (within last 5 trading bars). If found, checks VR>2x
    + bullish close on the last bar.
    Returns: {'has_signal': bool, 'reason': str, 'details': dict}
    """
    import sqlite3 as _sqlite3
    if db_path is None:
        from config import DB_PATH
        db_path = DB_PATH

    if df is None or len(df) < 5:
        return {'has_signal': False, 'reason': 'Insufficient data', 'details': {}}

    last_5_dates = [str(df['date'].iloc[i])[:10] for i in range(-5, 0)]
    earliest = min(last_5_dates)

    try:
        conn = _sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT resume_date, gap_pct, last_normal_date, missing_td "
            "FROM suspension_events "
            "WHERE ticker=? AND resume_date >= ? AND classification='suspension' "
            "ORDER BY resume_date DESC LIMIT 1",
            (ticker, earliest)
        ).fetchone()
        conn.close()
    except Exception:
        row = None

    if not row:
        return {
            'has_signal': False,
            'reason': f'No recent suspension event for {ticker}',
            'details': {}
        }

    resume_date, gap_pct, last_normal_date, missing_td = row

    date_strs = df['date'].astype(str).str[:10]
    resume_mask = date_strs == resume_date
    if not resume_mask.any():
        return {
            'has_signal': False,
            'reason': f'Resume date {resume_date} not in OHLCV data',
            'details': {}
        }

    resume_idx = int(df[resume_mask].index[-1])
    resume_low = float(df.loc[resume_idx, 'low'])
    resume_open = float(df.loc[resume_idx, 'open'])

    if resume_idx == 0:
        return {'has_signal': False, 'reason': 'Resume bar at start of data', 'details': {}}
    last_pre_close = float(df.loc[resume_idx - 1, 'close'])
    gap_amount = last_pre_close - resume_open

    last = df.iloc[-1]
    vr_series = calc_vol_ratio(df, 20)
    vr_val = vr_series.iloc[-1]

    is_bullish = float(last['close']) > float(last['open'])
    has_volume = (not pd.isna(vr_val)) and float(vr_val) >= CRASH_VR_MIN

    entry_approx = float(last['close'])
    sl_approx = float(apply_costs(resume_low, 'SELL'))
    tp_approx = resume_open + CRASH_TP_RETRACEMENT * gap_amount
    sl_pct = (entry_approx - sl_approx) / entry_approx if entry_approx > sl_approx else 0.02

    details = {
        'price':       float(round(entry_approx, 2)),
        'vr':          round(float(vr_val), 2) if not pd.isna(vr_val) else None,
        'bullish':     is_bullish,
        'resume_date': resume_date,
        'gap_pct':     round(float(gap_pct) * 100, 1),
        'missing_td':  missing_td,
        'sl':          round(sl_approx, 0),
        'tp':          round(tp_approx, 0),
        'sl_pct':      round(sl_pct * 100, 2),
    }

    if is_bullish and has_volume and tp_approx > entry_approx * 1.02:
        return {
            'has_signal': True,
            'reason': (f"Crash Recovery: VR={float(vr_val):.1f}x, "
                       f"gap {float(gap_pct)*100:.1f}% on {resume_date}"),
            'details': details,
        }

    missing = []
    if not is_bullish:
        missing.append('bearish close')
    if not has_volume:
        missing.append(f'VR={float(vr_val):.1f}x<{CRASH_VR_MIN}x')
    if tp_approx <= entry_approx * 1.02:
        missing.append('insufficient TP headroom')
    return {
        'has_signal': False,
        'reason': f"Crash Recovery: conditions not met ({', '.join(missing)})",
        'details': details,
    }


# ─────────────────────────────────────────────
# PANIC REBOUND CONSTANTS
# ─────────────────────────────────────────────
# v3 params (2026-06-13, walkforward-selected over 4 variants):
#   v1 -15%/VR1.5/green close, SL at signal low      → -0.25%/window
#   v2 -20%/VR2.0/washout+close_pos, SL at low        → -0.73%/window
#   v3 = v2 entries, NO hard SL, fixed horizon        → +0.05%/window,
#        with +0.87%/+0.42% in normal-regime quarters
#   v4 = v1 entries, v3 exits                          → -0.20%/window
# Two lessons encoded here: (1) stops + mean reversion realize entry noise
# as losses — exits are TP (38.2% retrace) or the 5-bar time-stop, and the
# signal-low distance survives only as a synthetic sizing input; (2) the
# edge exists for SINGLE-STOCK panics in a calm market and inverts during
# market-wide panic (2025-04 tariff, 2026 MSCI crash buckets all negative)
# — so the scanner only routes this strategy when macro panic state is OFF.
PANIC_DROP_PCT       = -0.20   # 5-day return threshold — oversold panic
PANIC_DROP_BARS      = 5       # lookback bars for the drop measurement
PANIC_VR_MIN         = 2.0     # volume ratio confirmation (capitulation volume)
PANIC_CLOSE_POS_MIN  = 0.60    # close in upper 40% of signal-bar range
PANIC_WASHOUT_BARS   = 10      # signal-bar low must be the N-bar lowest low
PANIC_TP_RETRACEMENT = 0.382   # TP at 38.2% retracement of the 5-day drop
PANIC_SL_BUFFER      = 0.995   # SL slightly below signal low (retest noise)
PANIC_TIME_STOP_BARS = 5       # reversal alpha decays in days — force exit
PANIC_MIN_PRICE      = 100     # skip gocap tickers (ARB-trap risk)


# ─────────────────────────────────────────────
# STRATEGY 12 — PANIC REBOUND (short-term reversal)
# ─────────────────────────────────────────────

def strategy_panic_rebound(df: pd.DataFrame, capital: float = 50_000_000,
                            filters: list = None) -> dict:
    """
    Short-term reversal / liquidity provision after panic selling.
    Entry: 5-day return <= -15%, signal bar closes green (selling exhaustion),
           VR > 1.5x, price >= 100. Enter next bar open.
    SL: signal-bar low.
    TP: signal close + 50% x 5-day drop amount.
    Time-stop: 5 bars — reversal alpha decays fast (RFS 2025).
    """
    if len(df) < PANIC_DROP_BARS + 2:
        return {'strategy': 'Panic Rebound', 'trades': [], 'equity': [capital],
                'final_capital': capital, 'initial_capital': capital}

    df = df.copy().reset_index(drop=True)
    ret5 = df['close'] / df['close'].shift(PANIC_DROP_BARS) - 1.0
    vr = calc_vol_ratio(df, 20)

    capital_cur = capital
    equity = [capital_cur]
    trades = []
    in_trade = False
    entry_price = tp_level = sl_level = 0.0
    entry_date = ''
    entry_idx = -1
    lots = 0

    enter_next_bar = False
    pend_sl = pend_tp = 0.0

    for i in range(PANIC_DROP_BARS + 1, len(df)):
        row = df.iloc[i]
        date = str(row['date'])[:10]

        if enter_next_bar and not in_trade:
            raw_entry = row['open']
            ep = apply_costs(raw_entry, 'BUY')
            sl_price = apply_costs(pend_sl, 'SELL')
            sl_pct = (ep - sl_price) / ep if ep > sl_price else 0.02
            if sl_pct < 0.005:
                sl_pct = 0.02
                sl_price = ep * (1.0 - sl_pct)
            if pend_tp > ep * 1.02:
                lots_n = lot_size(capital_cur, ep, 0.02, sl_pct)
                cost = ep * lots_n * 100
                if cost <= capital_cur and lots_n > 0:
                    entry_price = ep
                    sl_level = sl_price
                    tp_level = pend_tp
                    lots = lots_n
                    in_trade = True
                    entry_date = date
                    entry_idx = i
            enter_next_bar = False

        if in_trade:
            hi, lo, cur = row['high'], row['low'], row['close']
            exit_reason = None
            # No hard SL: stops + mean reversion realize entry noise as
            # losses (v1/v2 walkforward). Risk is bounded by the time-stop.
            if hi >= tp_level:
                exit_price = apply_costs(tp_level, 'SELL')
                exit_reason = 'TP'
            elif i - entry_idx >= PANIC_TIME_STOP_BARS:
                exit_price = apply_costs(cur, 'SELL')
                exit_reason = 'TIME'
            elif i == len(df) - 1:
                exit_price = apply_costs(cur, 'SELL')
                exit_reason = 'EOD'
            if exit_reason:
                gross = (exit_price - entry_price) * lots * 100
                pnl_pct = (exit_price - entry_price) / entry_price
                capital_cur += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy='Panic Rebound'
                ))
                equity.append(capital_cur)
                in_trade = False
            continue

        # Signal evaluation on bar i (all data through bar i only)
        r5 = ret5.iloc[i]
        vr_val = vr.iloc[i]
        bar_range = float(row['high']) - float(row['low'])
        close_pos = ((float(row['close']) - float(row['low'])) / bar_range
                     if bar_range > 0 else 0.0)
        lo_start = max(0, i - PANIC_WASHOUT_BARS + 1)
        is_washout_low = float(row['low']) <= float(df['low'].iloc[lo_start:i + 1].min())
        if (not pd.isna(r5) and r5 <= PANIC_DROP_PCT
                and close_pos >= PANIC_CLOSE_POS_MIN
                and is_washout_low
                and row['close'] >= PANIC_MIN_PRICE
                and not pd.isna(vr_val) and vr_val >= PANIC_VR_MIN):
            drop_amount = float(df['close'].iloc[i - PANIC_DROP_BARS]) - float(row['close'])
            pend_tp = float(row['close']) + PANIC_TP_RETRACEMENT * drop_amount
            pend_sl = float(row['low']) * PANIC_SL_BUFFER
            enter_next_bar = True

    return {
        'strategy':        'Panic Rebound',
        'trades':          trades,
        'equity':          equity,
        'final_capital':   capital_cur,
        'initial_capital': capital,
    }


def check_panic_rebound_signal(df: pd.DataFrame) -> dict:
    """
    Live signal check for Panic Rebound on the last bar.
    Same conditions as the backtest signal bar; suggested entry is next open
    (approximated by last close), SL = last bar low, TP = 50% drop retracement.
    """
    if df is None or len(df) < PANIC_DROP_BARS + 1:
        return {'has_signal': False, 'reason': 'Insufficient data', 'details': {}}

    last = df.iloc[-1]
    close_now = float(last['close'])
    ref_close = float(df['close'].iloc[-1 - PANIC_DROP_BARS])
    r5 = close_now / ref_close - 1.0 if ref_close > 0 else 0.0

    vr_series = calc_vol_ratio(df, 20)
    vr_val = vr_series.iloc[-1]
    has_volume = (not pd.isna(vr_val)) and float(vr_val) >= PANIC_VR_MIN
    bar_range = float(last['high']) - float(last['low'])
    close_pos = ((close_now - float(last['low'])) / bar_range
                 if bar_range > 0 else 0.0)
    is_bullish = close_pos >= PANIC_CLOSE_POS_MIN
    is_washout_low = float(last['low']) <= float(
        df['low'].iloc[-PANIC_WASHOUT_BARS:].min())
    price_ok = close_now >= PANIC_MIN_PRICE

    drop_amount = ref_close - close_now
    tp_approx = close_now + PANIC_TP_RETRACEMENT * drop_amount
    sl_approx = float(apply_costs(float(last['low']) * PANIC_SL_BUFFER, 'SELL'))

    details = {
        'price':     float(round(close_now, 2)),
        'ret5_pct':  round(r5 * 100, 1),
        'vr':        round(float(vr_val), 2) if not pd.isna(vr_val) else None,
        'bullish':   is_bullish,
        'sl':        round(sl_approx, 0),
        'tp':        round(tp_approx, 0),
        'time_stop': PANIC_TIME_STOP_BARS,
    }

    if (r5 <= PANIC_DROP_PCT and is_bullish and is_washout_low
            and has_volume and price_ok and tp_approx > close_now * 1.02):
        return {
            'has_signal': True,
            'reason': (f"Panic Rebound: {r5*100:.1f}% in {PANIC_DROP_BARS}d, "
                       f"green close, VR={float(vr_val):.1f}x"),
            'details': details,
        }

    missing = []
    if r5 > PANIC_DROP_PCT:
        missing.append(f'drop {r5*100:.1f}%>{PANIC_DROP_PCT*100:.0f}%')
    if not is_bullish:
        missing.append(f'close_pos {close_pos:.2f}<{PANIC_CLOSE_POS_MIN}')
    if not is_washout_low:
        missing.append(f'not {PANIC_WASHOUT_BARS}-bar washout low')
    if not has_volume:
        vtxt = f'{float(vr_val):.1f}x' if not pd.isna(vr_val) else 'n/a'
        missing.append(f'VR={vtxt}<{PANIC_VR_MIN}x')
    if not price_ok:
        missing.append(f'price<{PANIC_MIN_PRICE}')
    if tp_approx <= close_now * 1.02:
        missing.append('insufficient TP headroom')
    return {
        'has_signal': False,
        'reason': f"Panic Rebound: conditions not met ({', '.join(missing)})",
        'details': details,
    }


def strategy_liquidity_sweep_flow(df: pd.DataFrame, ticker: str = None,
                                  capital: float = 50_000_000,
                                  filters: list = None) -> dict:
    """SMC liquidity-sweep entry (bullish PDL/PWL trap) confirmed by order flow.

    Long-only. ATR SL×1.0 / TP×2.5 (RR 2.5). When ticker is None the flow gate
    is skipped (price-only) so this can be walk-forward backtested on full OHLCV
    history. When a ticker is given, each candidate sweep day must pass
    confirm_sweep_flow (fail-open on missing data, fail-closed on negative flow).
    """
    from engine.smc import calc_sweep_signal
    sig = calc_sweep_signal(df)

    if ticker is not None and sig.any():
        from engine.smc_flow import confirm_sweep_flow
        dates = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d').values
        vals = sig.values.copy()
        for pos in range(len(vals)):
            if vals[pos] and not confirm_sweep_flow(ticker, dates[pos])['confirmed']:
                vals[pos] = False
        sig = pd.Series(vals, index=df.index)

    return run_strategy(df, sig, atr_sl_mult=1.0, atr_tp_mult=2.5, min_rr=2.5,
                        strategy_name='Liquidity Sweep', initial_capital=capital,
                        filters=filters)


def check_sweep_flow_signal(df: pd.DataFrame, ticker: str) -> dict:
    """Live last-bar check: bullish sweep on the current bar, confirmed by flow.

    Returns {'has_signal': bool, 'reason': str, 'details': dict}.
    """
    from engine.smc import detect_liquidity_sweep
    from engine.smc_flow import confirm_sweep_flow

    sweeps = detect_liquidity_sweep(df)
    if sweeps.empty:
        return {'has_signal': False, 'reason': 'No sweeps detected', 'details': {}}

    bullish = sweeps[sweeps['signal'] == 1]
    if bullish.empty:
        return {'has_signal': False, 'reason': 'No bullish sweep', 'details': {}}

    last = bullish.iloc[-1]
    last_bar_date = str(df.iloc[-1]['date'])[:10]
    if str(last['date'])[:10] != last_bar_date:
        return {'has_signal': False,
                'reason': f"Last bullish sweep {last['date']} not on current bar",
                'details': {}}

    flow = confirm_sweep_flow(ticker, last_bar_date)
    if not flow['confirmed']:
        return {'has_signal': False,
                'reason': f"{last['sweep_type'].upper()} sweep but flow rejected: {flow['reason']}",
                'details': {'flow': flow}}

    return {'has_signal': True,
            'reason': (f"{last['sweep_type'].upper()} sweep @ {last['level_price']} "
                       f"(wick {last['wick_pct']:.0%}), flow {flow['source']}: {flow['reason']}"),
            'details': {'sweep_type': last['sweep_type'],
                        'level_price': float(last['level_price']),
                        'wick_pct': float(last['wick_pct']),
                        'flow': flow}}


# ── Strategy registry dict (moved from walkforward_multi in M2) ──────────────
# Shared floor: research backtests and the production dashboard both import
# this; the definitions live in this module so there is no boundary crossing.
STRATEGY_FUNCS = {
    'vol_weighted':              strategy_vol_weighted,
    'momentum':                  strategy_momentum,
    'vwap_reversion':            strategy_vwap_reversion,
    'conservative':              strategy_conservative,
    'Volume Profile POC':        strategy_volume_profile_poc,
    'Inside Bar Breakout':       strategy_inside_bar_breakout,
    'NR7 Breakout':              strategy_nr7_breakout,
    'ORB':                       strategy_orb,
    'VWMA Breakout Pullback':    strategy_vwma_breakout_pullback,
    'Swing Trend':               strategy_swing_trend,
    'Trend Following Breakout':  strategy_trend_following_breakout,
    'Crash Recovery':            strategy_crash_recovery,
    'Panic Rebound':             strategy_panic_rebound,
    'Liquidity Sweep':           strategy_liquidity_sweep_flow,
    # 'Regime Adaptive' deregistered 2026-07-02 (audit C-7): whole-window
    # look-ahead. Re-register only after a per-bar reimplementation.
}
