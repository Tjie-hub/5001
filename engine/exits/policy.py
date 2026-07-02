"""Exit policy per strategy + registry. Pure module (no I/O).

Two flavors:
  * Fixed ATR SL/TP (sl_mult/tp_mult set): stop and target fixed at entry;
    trail_enable ratchets the SL using sl_mult as the trail distance.
  * Pure trail (trail_atr_mult set, sl_mult=None): no fixed target; trail + time-stop.

Direction-aware: SHORT mirrors all signs (SL above entry, TP below).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class InitialLevels:
    sl_price: float | None
    tp_price: float | None
    trail_anchor: float
    one_r: float
    trailing: bool
    trail_mult: float | None   # ATR distance used to recompute the trailing stop
    initial_stop: float | None


@dataclass(frozen=True)
class ExitPolicy:
    sl_mult: float | None = None
    tp_mult: float | None = None
    min_rr: float = 2.0
    trail_enable: bool = False
    trail_atr_mult: float | None = None
    hold_days: int | None = None
    # plan 1B metadata:
    no_sl: bool = False              # never price-stop (Panic Rebound); TIME bounds risk
    fixed_levels: bool = False       # absolute SL/TP computed at entry; ATR mults are fallbacks
    ma_break_period: int | None = None  # exit at close when close < SMA(period); caller-evaluated
    rule_based: bool = False         # Swing Trend R1-R7: kernel not used; monitor has own path

    def initial_levels(self, direction, entry, atr):
        sign = 1 if direction == "LONG" else -1
        if self.no_sl:
            # Pure TP + time-stop. one_r = tp_mult*atr keeps r_multiple defined.
            mult = self.tp_mult if self.tp_mult is not None else 1.5
            tp = entry + sign * mult * atr
            return InitialLevels(None, tp, entry, mult * atr, False, None, None)
        if self.sl_mult is not None:
            sl = entry - sign * self.sl_mult * atr
            # TP honours min_rr: at least min_rr*R beyond entry (R = sl_mult*atr).
            tp = entry + sign * max(self.tp_mult, self.min_rr * self.sl_mult) * atr
            trailing = self.trail_enable
            trail_mult = self.sl_mult if trailing else None
            one_r = self.sl_mult * atr
            return InitialLevels(sl, tp, entry, one_r, trailing, trail_mult, sl)
        # Pure trail.
        mult = self.trail_atr_mult
        stop = entry - sign * mult * atr
        return InitialLevels(None, None, entry, mult * atr, True, mult, stop)


class ExitPolicyRegistry:
    """Maps strategy name -> ExitPolicy. Unknown keys fall back to DEFAULT.

    Params mirror each strategy's backtest exit in engine/strategies.py.
    fixed_levels strategies compute absolute SL/TP at entry (stored on the
    position and passed to the kernel as overrides); their sl_mult/tp_mult
    here are ATR FALLBACKS for contexts without levels (ft signal ingest).
    """

    DEFAULT = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)

    def __init__(self):
        self._by_strategy = {
            "vol_weighted":     ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0),
            "momentum":         ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True),
            "vwap_reversion":   ExitPolicy(sl_mult=0.8, tp_mult=1.6, min_rr=2.0),
            "conservative":     ExitPolicy(sl_mult=0.7, tp_mult=1.4, min_rr=2.0),
            "Liquidity Sweep":  ExitPolicy(sl_mult=1.0, tp_mult=2.5, min_rr=2.5),
            # 3xATR high-anchored trail + MA20-break; no TP, no time cap.
            "Trend Following Breakout": ExitPolicy(trail_enable=True, trail_atr_mult=3.0,
                                                   ma_break_period=20),
            # v3 design: NO hard SL (stops + mean reversion realize entry noise
            # as losses); TP = retracement level (absolute, at entry) with
            # tp_mult as ATR fallback; 5-bar time stop.
            "Panic Rebound":    ExitPolicy(no_sl=True, tp_mult=1.5, hold_days=5),
            # Fixed levels at entry (SL = resume low / signal structure; TP =
            # gap retracement / swing target). ATR mults are fallbacks only.
            "Crash Recovery":          ExitPolicy(sl_mult=1.0, tp_mult=2.0, fixed_levels=True),
            "VWMA Breakout Pullback":  ExitPolicy(sl_mult=1.0, tp_mult=2.0, fixed_levels=True),
            "Volume Profile POC":      ExitPolicy(sl_mult=1.0, tp_mult=2.0, fixed_levels=True),
            "Inside Bar Breakout":     ExitPolicy(sl_mult=1.0, tp_mult=2.0, fixed_levels=True),
            "NR7 Breakout":            ExitPolicy(sl_mult=1.0, tp_mult=2.0, fixed_levels=True),
            "ORB":                     ExitPolicy(sl_mult=0.5, tp_mult=2.0, fixed_levels=True),
            # R1-R7 reverse-trend rules — monitor._evaluate_swing_trend owns it;
            # ATR mults approximate the initial bracket for level-less contexts.
            "Swing Trend":      ExitPolicy(sl_mult=1.5, tp_mult=3.0, rule_based=True),
            # ft SHORT book from the bearish distribution screener — explicit
            # so the dominant shadow cohort no longer rides an implicit DEFAULT.
            "distribution":     ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10),
        }

    def get(self, strategy):
        return self._by_strategy.get(strategy, self.DEFAULT)
