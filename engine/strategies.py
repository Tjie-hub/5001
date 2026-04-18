"""
strategies.py — 4 Strategy Definitions untuk BBCA Multi-Strategy Backtest
Terintegrasi dengan idx-walkforward engine (market_structure, indicators, signals)
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
COMMISSION_BUY  = 0.0015   # 0.15%
COMMISSION_SELL = 0.0025   # 0.25%
SLIPPAGE        = 0.001    # 0.10%

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

def calc_vwap(df: pd.DataFrame, window: int = 60) -> pd.Series:
    """Rolling VWAP 60 hari — lebih relevan untuk sinyal entry."""
    tp = (df['high'] + df['low'] + df['close']) / 3
    cum_tp_vol = (tp * df['volume']).rolling(window).sum()
    cum_vol    = df['volume'].rolling(window).sum()
    return cum_tp_vol / cum_vol

def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l,
                    (h - c.shift()).abs(),
                    (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calc_vol_ratio(df: pd.DataFrame, period: int = 20) -> pd.Series:
    avg = df['volume'].rolling(period).mean()
    return df['volume'] / avg

def calc_delta(df: pd.DataFrame) -> pd.Series:
    """Proxy delta: (close - open) / (high - low) * volume, normalized."""
    rng = (df['high'] - df['low']).replace(0, np.nan)
    return ((df['close'] - df['open']) / rng * df['volume']).fillna(0)

def lot_size(capital: float, price: float, risk_pct: float, sl_pct: float) -> int:
    """Hitung lot (1 lot = 100 lembar) berdasarkan risk per trade."""
    risk_rp      = capital * risk_pct
    risk_per_lot = price * 100 * sl_pct
    if risk_per_lot <= 0:
        return 1
    lots = int(risk_rp / risk_per_lot)
    # Cap: maksimum 30% capital per trade
    max_lots = int((capital * 0.30) / (price * 100))
    lots = min(lots, max_lots)
    return max(1, lots)

def apply_costs(price: float, side: str) -> float:
    if side == 'BUY':
        return price * (1 + COMMISSION_BUY + SLIPPAGE)
    else:
        return price * (1 - COMMISSION_SELL - SLIPPAGE)

# ─────────────────────────────────────────────
# FILTER LIBRARY (on/off kombinasi bebas)
# ─────────────────────────────────────────────

def filter_vwma_above(df: pd.DataFrame) -> pd.Series:
    """Price di atas VWMA 20 — trend bullish filter."""
    vwma = calc_vwma(df, 20)
    return df['close'] > vwma

def filter_above_ma50(df: pd.DataFrame) -> pd.Series:
    """Price di atas MA 50 — medium-term trend filter."""
    return df['close'] > df['close'].rolling(50).mean()

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
                 tp_pct: float, sl_pct: float,
                 strategy_name: str,
                 initial_capital: float = 50_000_000,
                 risk_per_trade: float = 0.02,
                 trail_sl: bool = False,
                 filters: list = None) -> dict:
    """
    Generic backtest engine. signals: Series of True/False per bar.
    Returns dict dengan trades list + equity curve.
    """
    # Apply filters ke signal
    if filters:
        filter_mask = apply_filters(df, filters)
        signals = signals & filter_mask

    capital   = initial_capital
    equity    = [capital]
    trades    = []
    in_trade  = False
    entry_price = exit_price = 0.0
    entry_date  = ""
    lots        = 0
    peak_price  = 0.0

    for i in range(1, len(df)):
        row   = df.iloc[i]
        prev  = df.iloc[i - 1]
        date  = str(row['date'])[:10]

        if in_trade:
            hi   = row['high']
            lo   = row['low']
            cur  = row['close']

            # Update trailing stop
            if trail_sl and row['high'] > peak_price:
                peak_price = row['high']

            sl_level = (peak_price * (1 - sl_pct)) if trail_sl else (entry_price * (1 - sl_pct))
            tp_level = entry_price * (1 + tp_pct)

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
                gross    = (exit_price - entry_price) * lots * 100
                pnl_pct  = (exit_price - entry_price) / entry_price
                capital += gross
                trades.append(Trade(
                    entry_date=entry_date, exit_date=date,
                    entry_price=entry_price, exit_price=exit_price,
                    lots=lots, direction='BUY', exit_reason=exit_reason,
                    pnl_rp=gross, pnl_pct=pnl_pct * 100,
                    strategy=strategy_name
                ))
                in_trade = False

        elif signals.iloc[i - 1]:   # signal dari bar sebelumnya, entry open hari ini
            raw_entry  = row['open']
            entry_price = apply_costs(raw_entry, 'BUY')
            lots        = lot_size(capital, entry_price, risk_per_trade, sl_pct)
            cost        = entry_price * lots * 100
            if cost <= capital:
                in_trade   = True
                entry_date = date
                peak_price = entry_price

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
    Exit:  TP +2.0% / SL -1.5%
    """
    vr    = calc_vol_ratio(df, 20)
    delta = calc_delta(df)
    sig   = (vr > 1.8) & (delta > 0) & (df['close'] > df['open'])
    return run_strategy(df, sig, tp_pct=0.02, sl_pct=0.015,
                        strategy_name='Vol-Weighted Entry', initial_capital=capital,
                        filters=filters)


# ─────────────────────────────────────────────
# STRATEGY 2 — MOMENTUM FOLLOWING
# ─────────────────────────────────────────────

def strategy_momentum(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> dict:
    """
    Entry: 2 hari berturut close > close[-1] + Vol Ratio > 1.3x
    Exit:  Trailing SL 2% dari peak / SL -2.5% dari entry
    """
    vr      = calc_vol_ratio(df, 20)
    streak2 = (df['close'] > df['close'].shift(1)) & \
              (df['close'].shift(1) > df['close'].shift(2))
    sig     = streak2 & (vr > 1.3)
    return run_strategy(df, sig, tp_pct=0.035, sl_pct=0.025,
                        strategy_name='Momentum Following',
                        initial_capital=capital, trail_sl=True,
                        filters=filters)


# ─────────────────────────────────────────────
# STRATEGY 3 — VWAP REVERSION
# ─────────────────────────────────────────────

def strategy_vwap_reversion(df: pd.DataFrame, capital: float = 50_000_000, filters: list = None) -> dict:
    """
    Entry: Close > 1.5% di bawah VWAP + Vol spike (ratio > 1.5x)
    Exit:  TP = kembali ke VWAP (proxy: +1.5%) / SL -1.0%
    """
    vwap = calc_vwap(df)
    vr   = calc_vol_ratio(df, 20)
    dist = (df['close'] - vwap) / vwap      # negatif = di bawah VWAP
    sig  = (dist < -0.010) & (vr > 1.3)
    return run_strategy(df, sig, tp_pct=0.015, sl_pct=0.01,
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
    ma20  = df['close'].rolling(20).mean()
    atr   = calc_atr(df, 14)
    atr_ma = atr.rolling(10).mean()
    bullish = df['close'] > df['open']
    above_ma = df['close'] > ma20
    atr_ok   = atr < atr_ma * 1.5   # hindari hari terlalu volatile

    sig = (vr > 1.3) & bullish & above_ma & atr_ok
    return run_strategy(df, sig, tp_pct=0.015, sl_pct=0.01,
                        strategy_name='Conservative Confirm', initial_capital=capital,
                        filters=filters)


# ─────────────────────────────────────────────
# STRATEGY 5 — VWMA BREAKOUT PULLBACK
# ─────────────────────────────────────────────

def calc_vwma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Volume Weighted Moving Average."""
    return (df['close'] * df['volume']).rolling(period).sum() / \
            df['volume'].rolling(period).sum()


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
                equity.append(capital_cur)
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
    if price_max <= price_min:
        return None, []

    # Buat price buckets
    bucket_size = price_min * resolution
    if bucket_size <= 0:
        return None, []

    n_buckets = max(1, int((price_max - price_min) / bucket_size) + 1)
    buckets   = np.zeros(n_buckets)
    prices    = np.array([price_min + i * bucket_size for i in range(n_buckets)])

    for _, row in df_window.iterrows():
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
    atr = (df['high'] - df['low']).rolling(14).mean()
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
    ranges = df['high'] - df['low']
    atr = ranges.rolling(14).mean()
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


# STRATEGY - OPENING RANGE BREAKOUT (Daily Approximation)
def strategy_orb(df: pd.DataFrame, capital: float = 50_000_000,
                 filters: list = None) -> dict:
    """
    Opening Range Breakout — Daily approximation.
    Opening Range = open ± (ATR14 × 0.5)
    Breakout signal: close > open + (ATR × 0.5) AND volume > avg_vol × 1.5
    Entry: next bar open
    TP: swing high 20 bars atau ATR × 2 (whichever larger, min entry+2%)
    SL: open of signal bar - ATR × 0.5
    """
    atr = (df['high'] - df['low']).rolling(14).mean()
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


"""
Signal Checker untuk Multi-Strategy Backtest
Tambahkan kode ini ke engine/strategies.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def check_current_entry_signal(ticker: str, strategy: str, df: pd.DataFrame = None) -> dict:
    """
    Cek apakah ticker memenuhi entry criteria dari strategy yang dipilih
    pada data terbaru (last bar)
    
    Args:
        ticker: Kode ticker (e.g., 'BBCA')
        strategy: Nama strategy ('vol_weighted', 'momentum', dll)
        df: DataFrame OHLCV ticker (optional, akan di-fetch jika None)
    
    Returns:
        dict: {
            'has_signal': bool,
            'reason': str (penjelasan kenapa pass/tidak pass),
            'details': dict (nilai-nilai metric untuk display)
        }
    """
    # Jika df tidak diberikan, fetch dari database
    if df is None:
        df = get_ticker_data(ticker)
    
    if df.empty or len(df) < 20:
        return {
            'has_signal': False,
            'reason': 'Data tidak cukup (minimum 20 bars)',
            'details': {}
        }
    
    # Route ke fungsi checker sesuai strategy
    if strategy == 'vol_weighted':
        return check_vol_weighted_signal(df)
    elif strategy == 'momentum':
        return check_momentum_signal(df)
    elif strategy == 'vwap_reversion':
        return check_vwap_reversion_signal(df)
    elif strategy == 'conservative':
        return check_conservative_signal(df)
    else:
        return {
            'has_signal': False,
            'reason': f'Strategy {strategy} belum didukung',
            'details': {}
        }


def check_vol_weighted_signal(df: pd.DataFrame) -> dict:
    """
    Vol-Weighted Entry Signal Checker
    
    Entry Criteria:
    - Volume Ratio (VR) > 1.8x
    - Price > VWAP (optional tapi recommended)
    
    Returns:
        dict dengan has_signal, reason, details
    """
    latest = df.iloc[-1]
    
    # Hitung Volume Ratio
    # VR = current_volume / avg_volume_20d
    if 'avg_volume_20d' not in df.columns:
        # Calculate avg volume 20 days
        df['avg_volume_20d'] = df['volume'].rolling(window=20).mean()
        latest = df.iloc[-1]
    
    current_volume = latest['volume']
    avg_volume = latest['avg_volume_20d']
    
    if pd.isna(avg_volume) or avg_volume == 0:
        return {
            'has_signal': False,
            'reason': 'Avg volume tidak tersedia',
            'details': {}
        }
    
    vr = current_volume / avg_volume
    
    # Hitung VWAP
    if 'vwap' not in df.columns:
        # Calculate VWAP: (typical_price * volume).cumsum() / volume.cumsum()
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        latest = df.iloc[-1]
    
    current_price = latest['close']
    vwap = latest['vwap']
    price_vs_vwap = ((current_price - vwap) / vwap * 100) if vwap > 0 else 0
    
    # Check entry criteria
    vr_pass = vr > 1.8
    price_above_vwap = current_price > vwap
    
    # Entry signal = VR > 1.8 (VWAP check optional)
    has_signal = vr_pass
    
    # Build reason string
    if has_signal:
        vwap_status = "above VWAP ✓" if price_above_vwap else "below VWAP ⚠"
        reason = f"VR {vr:.2f}x > 1.8 ✓, Price {vwap_status}"
    else:
        reason = f"VR {vr:.2f}x ≤ 1.8 (butuh > 1.8)"
    
    return {
        'has_signal': bool(has_signal),
        'reason': str(reason),
        'details': {
            'vr': float(round(vr, 2)),
            'current_volume': int(current_volume),
            'avg_volume': int(avg_volume),
            'price': float(round(current_price, 2)),
            'vwap': float(round(vwap, 2)),
            'price_vs_vwap_pct': float(round(price_vs_vwap, 2)),
            'price_above_vwap': bool(price_above_vwap)
        }
    }


def check_momentum_signal(df: pd.DataFrame) -> dict:
    """
    Momentum Following Signal Checker
    
    Entry Criteria:
    - 2-day consecutive up streak
    - Volume Ratio (VR) > 1.3x
    """
    latest = df.iloc[-1]
    
    # Calculate streak
    df['daily_return'] = df['close'].pct_change()
    streak = 0
    for i in range(len(df) - 1, max(len(df) - 10, -1), -1):
        if df.iloc[i]['daily_return'] > 0:
            streak += 1
        else:
            break
    
    # Calculate VR
    if 'avg_volume_20d' not in df.columns:
        df['avg_volume_20d'] = df['volume'].rolling(window=20).mean()
        latest = df.iloc[-1]
    
    vr = latest['volume'] / latest['avg_volume_20d'] if latest['avg_volume_20d'] > 0 else 0
    
    # Check criteria
    streak_pass = streak >= 2
    vr_pass = vr > 1.3
    has_signal = streak_pass and vr_pass
    
    if has_signal:
        reason = f"{streak}-day streak ✓, VR {vr:.2f}x ✓"
    elif not streak_pass:
        reason = f"Streak {streak} < 2 days"
    else:
        reason = f"VR {vr:.2f}x ≤ 1.3"
    
    return {
        'has_signal': bool(has_signal),
        'reason': str(reason),
        'details': {
            'streak': int(streak),
            'vr': float(round(vr, 2)),
            'daily_return': float(round(latest['daily_return'] * 100, 2))
        }
    }


def check_vwap_reversion_signal(df: pd.DataFrame) -> dict:
    """
    VWAP Mean Reversion Signal Checker
    
    Entry Criteria:
    - Distance from VWAP < -1% (oversold)
    - Volume Ratio > 1.3x
    """
    latest = df.iloc[-1]
    
    # Calculate VWAP
    if 'vwap' not in df.columns:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        latest = df.iloc[-1]
    
    distance = ((latest['close'] - latest['vwap']) / latest['vwap'] * 100) if latest['vwap'] > 0 else 0
    
    # Calculate VR
    if 'avg_volume_20d' not in df.columns:
        df['avg_volume_20d'] = df['volume'].rolling(window=20).mean()
        latest = df.iloc[-1]
    
    vr = latest['volume'] / latest['avg_volume_20d'] if latest['avg_volume_20d'] > 0 else 0
    
    # Check criteria
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
            'vwap': float(round(latest['vwap'], 2))
        }
    }


def check_conservative_signal(df: pd.DataFrame) -> dict:
    """
    Conservative Confirm Signal Checker
    
    Entry Criteria:
    - Volume Ratio > 1.3x
    - Bullish candle (close > open)
    - Price above MA20
    - ATR check (optional)
    """
    latest = df.iloc[-1]
    
    # Calculate VR
    if 'avg_volume_20d' not in df.columns:
        df['avg_volume_20d'] = df['volume'].rolling(window=20).mean()
        latest = df.iloc[-1]
    
    vr = latest['volume'] / latest['avg_volume_20d'] if latest['avg_volume_20d'] > 0 else 0
    
    # Calculate MA20
    if 'ma20' not in df.columns:
        df['ma20'] = df['close'].rolling(window=20).mean()
        latest = df.iloc[-1]
    
    # Check criteria
    vr_pass = vr > 1.3
    bullish = latest['close'] > latest['open']
    above_ma = latest['close'] > latest['ma20']
    
    has_signal = vr_pass and bullish and above_ma
    
    checks = []
    checks.append(f"VR {vr:.2f}x {'✓' if vr_pass else '✗'}")
    checks.append(f"Bullish {'✓' if bullish else '✗'}")
    checks.append(f"Above MA20 {'✓' if above_ma else '✗'}")
    
    reason = ", ".join(checks)
    
    return {
        'has_signal': bool(has_signal),
        'reason': str(reason),
        'details': {
            'vr': float(round(vr, 2)),
            'bullish': bool(bullish),
            'above_ma20': bool(above_ma),
            'price': float(round(latest['close'], 2)),
            'ma20': float(round(latest['ma20'], 2))
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
    
    # Path ke database (adjust sesuai struktur project)
    db_path = 'data/walkforward.db'
    
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
    print(f"Details: {result['details']}")
