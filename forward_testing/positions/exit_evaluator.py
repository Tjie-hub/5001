"""ExitEvaluator — pure exit decision for one open SHADOW position over one daily bar.

No I/O. Direction-aware (LONG/SHORT). Deterministic ordering on a conflict bar:
STOP (SL if fixed, TRAIL if trailing) -> TP -> TIME. Gap-aware fills.
Metrics are raw (pre-cost); the manager layers Costs on entry/exit for stored pnl_pct.
"""
from dataclasses import dataclass
from forward_testing.positions.exit_policy import ExitPolicy


@dataclass(frozen=True)
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class PositionView:
    policy: ExitPolicy
    direction: str            # "LONG" / "SHORT"
    entry: float              # raw fill price (costs applied by manager at persist)
    atr: float                # atr14 at entry (fixed for the position's life)
    highest_seen: float
    lowest_seen: float
    hold_days: int


@dataclass(frozen=True)
class ExitDecision:
    reason: str               # SL / TP / TRAIL / TIME
    fill_price: float         # raw, gap-aware
    pnl_pct: float            # raw, direction-signed
    r_multiple: float         # realised / one_r
    mae_pct: float            # most adverse excursion (signed, <=0 typically)
    mfe_pct: float            # most favourable excursion (signed, >=0 typically)


def _stop_for(view):
    """Stop level active DURING this bar + whether it is trailing.

    The trailing stop is anchored to the extreme established BEFORE this bar
    (view.highest_seen / view.lowest_seen), never to the current bar's own
    high/low. Trailing to this bar's high and then triggering on this bar's low
    is intrabar look-ahead (no guarantee the high preceded the low) and inflates
    trailing-stop exits. The extreme advances only after a no-exit bar (the
    manager updates highest_seen/lowest_seen), so the ratchet applies next bar.
    """
    lv = view.policy.initial_levels(view.direction, view.entry, view.atr)
    if lv.trailing:
        mult = lv.trail_mult
        if view.direction == "LONG":
            return view.highest_seen - mult * view.atr, True
        return view.lowest_seen + mult * view.atr, True
    return lv.initial_stop, False


def evaluate_exit(view, bar):
    """Return an ExitDecision if the bar triggers an exit, else None."""
    long = view.direction == "LONG"
    sign = 1 if long else -1
    lv = view.policy.initial_levels(view.direction, view.entry, view.atr)

    new_high = max(view.highest_seen, bar.high)
    new_low = min(view.lowest_seen, bar.low)
    mae = ((new_low - view.entry) / view.entry) if long else ((new_high - view.entry) / view.entry)
    mfe = ((new_high - view.entry) / view.entry) if long else ((new_low - view.entry) / view.entry)

    stop, trailing = _stop_for(view)

    def realised(fill):
        return sign * (fill - view.entry)

    # 1) STOP (SL/TRAIL)
    stop_hit = (bar.low <= stop) if long else (bar.high >= stop)
    if stop_hit:
        gap = (bar.open <= stop) if long else (bar.open >= stop)
        fill = bar.open if gap else stop
        reason = "TRAIL" if trailing else "SL"
        return ExitDecision(reason, fill, realised(fill) / view.entry,
                            realised(fill) / lv.one_r, mae, mfe)

    # 2) TP (fixed policies only)
    if lv.tp_price is not None:
        tp_hit = (bar.high >= lv.tp_price) if long else (bar.low <= lv.tp_price)
        if tp_hit:
            gap = (bar.open >= lv.tp_price) if long else (bar.open <= lv.tp_price)
            fill = bar.open if gap else lv.tp_price
            return ExitDecision("TP", fill, realised(fill) / view.entry,
                                realised(fill) / lv.one_r, mae, mfe)

    # 3) TIME
    if view.policy.hold_days is not None and view.hold_days >= view.policy.hold_days:
        fill = bar.close
        return ExitDecision("TIME", fill, realised(fill) / view.entry,
                            realised(fill) / lv.one_r, mae, mfe)

    return None
