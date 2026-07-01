"""ExitEvaluator — pure exit decision for one open SHADOW position over one daily bar.

No I/O. Direction-aware (LONG/SHORT). Deterministic ordering on a conflict bar:
STOP (SL if fixed, TRAIL if trailing) -> TP -> TIME. Gap-aware fills.

Returns only WHICH exit fires and the raw fill price. Cost-basis-dependent metrics
(pnl_pct, r_multiple, MAE/MFE) are NOT computed here — they belong to the manager,
which is the single authority on the cost convention: net P&L uses the cost-adjusted
entry/exit, while MAE/MFE are gross excursions from the raw entry. Keeping them out of
this pure layer prevents the two-bases-in-two-places drift this module used to have
(its `entry` is the cost-adjusted fill, so any metric computed here was a hybrid).
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
    entry: float              # cost-adjusted fill; drives the stop/TP/one_r levels
    atr: float                # atr14 at entry (fixed for the position's life)
    highest_seen: float
    lowest_seen: float
    hold_days: int


@dataclass(frozen=True)
class ExitDecision:
    reason: str               # SL / TP / TRAIL / TIME
    fill_price: float         # raw, gap-aware


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
    """Return an ExitDecision (reason + raw fill) if the bar triggers an exit, else None."""
    long = view.direction == "LONG"
    lv = view.policy.initial_levels(view.direction, view.entry, view.atr)

    stop, trailing = _stop_for(view)

    # 1) STOP (SL/TRAIL)
    stop_hit = (bar.low <= stop) if long else (bar.high >= stop)
    if stop_hit:
        gap = (bar.open <= stop) if long else (bar.open >= stop)
        fill = bar.open if gap else stop
        return ExitDecision("TRAIL" if trailing else "SL", fill)

    # 2) TP (fixed policies only)
    if lv.tp_price is not None:
        tp_hit = (bar.high >= lv.tp_price) if long else (bar.low <= lv.tp_price)
        if tp_hit:
            gap = (bar.open >= lv.tp_price) if long else (bar.open <= lv.tp_price)
            fill = bar.open if gap else lv.tp_price
            return ExitDecision("TP", fill)

    # 3) TIME
    if view.policy.hold_days is not None and view.hold_days >= view.policy.hold_days:
        return ExitDecision("TIME", bar.close)

    return None
