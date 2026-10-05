"""
ATR exit engines for IDX swing strategies (daily bars).

Fill conventions (deliberately conservative):
  * Signal on bar t close -> enter bar t+1 (open, or stop-trigger price for breakout entries).
  * If a bar touches BOTH stop and target: same_bar='stop_first' assumes the STOP (pessimistic,
    penalises tight stops); same_bar='ohlc' uses the O-L-H-C / O-H-L-C path heuristic (neutral).
  * If a bar OPENS beyond the stop (gap), exit at the open, not at the stop (gap-through).
  * Entry bar counts: if the entry bar's low <= stop, it's a stop (we don't know intrabar order).
  * Chandelier/trailing is evaluated on CLOSE and executed at NEXT OPEN.
  * Stops are rounded DOWN to the IDX tick, targets UP; min stop distance = 3 ticks.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- IDX ticks
_TICKS = [(200, 1), (500, 2), (2000, 5), (5000, 10), (float("inf"), 25)]


def tick_size(p: float) -> float:
    for ub, t in _TICKS:
        if p < ub:
            return t
    return 25


def round_down_tick(p: float) -> float:
    t = tick_size(p)
    return np.floor(p / t) * t


def round_up_tick(p: float) -> float:
    t = tick_size(p)
    return np.ceil(p / t) * t


# ---------------------------------------------------------------- indicators
def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()],
                     axis=1).max(axis=1)


def wilder_atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = true_range(df)
    t = tr.to_numpy(dtype=float, copy=True)
    a = np.full(len(t), np.nan)
    if len(t) <= n:
        return pd.Series(a, index=df.index)
    a[n] = t[1:n + 1].mean()                        # Wilder seed = SMA of first n TR
    for i in range(n + 1, len(t)):
        a[i] = (a[i - 1] * (n - 1) + t[i]) / n
    return pd.Series(a, index=df.index)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["atr14"] = wilder_atr(df, 14)
    df["atr22"] = wilder_atr(df, 22)
    df["hh22"] = df["high"].rolling(22, min_periods=22).max()
    df["atr_pct"] = df["atr14"] / df["close"]
    return df


# ---------------------------------------------------------------- specs
@dataclass
class ExitSpec:
    kind: str                      # 'fixed' | 'atr_tpsl' | 'chandelier'
    tp_pct: float | None = None    # fixed
    sl_pct: float | None = None    # fixed
    stop_k: float = 2.0            # ATR14 multiple for initial stop (atr_tpsl / chandelier)
    tp_k: float | None = None      # ATR14 multiple for TP (atr_tpsl); None = no TP
    chand_k: float = 3.0
    time_stop: int | None = None   # bars incl. entry bar; exit at that bar's close
    max_hold: int = 60
    label: str = field(default="")


@dataclass
class Costs:
    buy: float = 0.0025   # 0.15% fee + 0.10% slip
    sell: float = 0.0035  # 0.25% fee + 0.10% slip


# ---------------------------------------------------------------- simulator
def simulate_trade(o, h, l, c, atr14, atr22, hh22, i: int, entry: float,
                   spec: ExitSpec, costs: Costs, same_bar: str = "stop_first",
                   entry_mid: bool = False) -> dict | None:
    """Simulate one long trade entered on bar i at price `entry`.
    Arrays are numpy; atr values are taken from bar i-1 (known at signal time).
    same_bar: 'stop_first' (pessimistic) or 'ohlc' (open nearer low -> O-L-H-C, else O-H-L-C).
    entry_mid: entry filled intrabar via buy-stop (not at the open)."""
    n = len(c)
    a_sig = atr14[i - 1] if i >= 1 else np.nan
    tk = tick_size(entry)

    if spec.kind == "fixed":
        stop = round_down_tick(entry * (1 - spec.sl_pct))
        tp = round_up_tick(entry * (1 + spec.tp_pct)) if spec.tp_pct else None
    else:
        if not np.isfinite(a_sig) or a_sig <= 0:
            return None
        stop = round_down_tick(entry - spec.stop_k * a_sig)
        tp = round_up_tick(entry + spec.tp_k * a_sig) if spec.tp_k else None
    stop = min(stop, entry - 3 * tk)
    if stop <= 0:
        return None
    stop0 = stop

    last = min(i + spec.max_hold - 1, n - 1)
    chand_level = -np.inf
    exit_px, exit_j, reason = None, None, None
    pending_open_exit = False

    for j in range(i, last + 1):
        if pending_open_exit:
            exit_px, exit_j, reason = o[j], j, "trail"
            break
        # ---- gaps (known order: the open comes first)
        if j > i and o[j] <= stop:
            exit_px, exit_j, reason = o[j], j, "gap_stop"
            break
        if tp is not None and j > i and o[j] >= tp:
            exit_px, exit_j, reason = o[j], j, "gap_tp"
            break
        # ---- intrabar: which extreme came first?
        low_first = True if same_bar == "stop_first" else (o[j] - l[j]) <= (h[j] - o[j])
        stop_hit = l[j] <= stop
        if j == i and entry_mid and same_bar == "ohlc" and low_first:
            # buy-stop filled near the high AFTER the low printed -> low can't stop us; use close
            stop_hit = c[j] <= stop
        tp_hit = tp is not None and h[j] >= tp
        if stop_hit and (low_first or not tp_hit):
            exit_px, exit_j, reason = (min(stop, c[j]) if (j == i and entry_mid and same_bar == "ohlc"
                                                           and low_first) else stop), j, "stop"
            break
        if tp_hit:
            exit_px, exit_j, reason = tp, j, "tp"
            break
        # ---- time stop
        if spec.time_stop and (j - i + 1) >= spec.time_stop:
            exit_px, exit_j, reason = c[j], j, "time"
            break
        # ---- chandelier (evaluate on close, act next open)
        if spec.kind == "chandelier" and np.isfinite(hh22[j]) and np.isfinite(atr22[j]):
            chand_level = max(chand_level, hh22[j] - spec.chand_k * atr22[j])
            if c[j] < chand_level and j < n - 1:
                pending_open_exit = True
                if j == last:          # allow the next-open exit beyond max_hold by one bar
                    exit_px, exit_j, reason = o[j + 1], j + 1, "trail"
                    break
    if exit_px is None:
        exit_j = last
        exit_px = c[last]
        reason = "max_hold" if last < n - 1 else "eod"

    gross = exit_px / entry - 1
    net = (exit_px * (1 - costs.sell)) / (entry * (1 + costs.buy)) - 1
    risk = (entry - stop0) / entry
    return {
        "entry_i": i, "exit_i": exit_j, "entry": entry, "exit": float(exit_px),
        "stop0": float(stop0), "tp": None if tp is None else float(tp),
        "reason": reason, "bars": exit_j - i + 1,
        "gross": gross, "net": net, "risk_pct": risk, "R": net / risk if risk > 0 else np.nan,
        "atr_pct_sig": (a_sig / entry) if np.isfinite(a_sig) else np.nan,
    }


# ---------------------------------------------------------------- sizing
def atr_position_size(equity: float, entry: float, stop: float,
                      risk_frac: float = 0.0075, cap_frac: float = 0.30,
                      lot: int = 100) -> int:
    """Shares (multiple of 100). 0 = skip (1 lot exceeds cap or stop invalid)."""
    per_share = entry - stop
    if per_share <= 0:
        return 0
    sh = int((equity * risk_frac / per_share) // lot) * lot
    sh = min(sh, int((equity * cap_frac / entry) // lot) * lot)
    return max(sh, 0)


def cost_filter_ok(atr_pct: float, round_trip: float = 0.006, tp_k: float = 1.5,
                   max_ratio: float = 0.25) -> bool:
    """Skip stocks where round-trip cost is > 25% of a 1.5xATR move (ATR% < ~1.6%)."""
    return np.isfinite(atr_pct) and atr_pct > 0 and round_trip / (tp_k * atr_pct) <= max_ratio
