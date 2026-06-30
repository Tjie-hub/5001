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
    initial_stop: float


@dataclass(frozen=True)
class ExitPolicy:
    sl_mult: float | None = None
    tp_mult: float | None = None
    min_rr: float = 2.0
    trail_enable: bool = False
    trail_atr_mult: float | None = None
    hold_days: int | None = None

    def initial_levels(self, direction, entry, atr):
        sign = 1 if direction == "LONG" else -1
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
    """Maps ft_signal.strategy -> ExitPolicy. Unknown keys fall back to DEFAULT."""

    DEFAULT = ExitPolicy(trail_enable=True, trail_atr_mult=3.0, hold_days=10)

    def __init__(self):
        # Params mirror each strategy's run_strategy(...) call-site in engine/strategies.py.
        self._by_strategy = {
            "vol_weighted":     ExitPolicy(sl_mult=1.0, tp_mult=2.0, min_rr=2.0),
            "momentum":         ExitPolicy(sl_mult=1.2, tp_mult=2.4, min_rr=2.0, trail_enable=True),
            "vwap_reversion":   ExitPolicy(sl_mult=0.8, tp_mult=1.6, min_rr=2.0),
            "conservative":     ExitPolicy(sl_mult=0.7, tp_mult=1.4, min_rr=2.0),
            "Liquidity Sweep":  ExitPolicy(sl_mult=1.0, tp_mult=2.5, min_rr=2.5),
        }

    def get(self, strategy):
        return self._by_strategy.get(strategy, self.DEFAULT)
