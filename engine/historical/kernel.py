"""engine/historical/kernel.py — the one stop-order execution kernel.

Phase 9 §11: all four historical systems (crabel_orb.v1, crabel_open_stretch.v1,
raschke_id_nr4.v1, raschke_nr7.v1) execute through THIS kernel. It supports long and short, stop
orders, gap-through-stop behavior, OCO groups, same-bar (same-session) execution
and explicit resolution of simultaneous-trigger ambiguity.

ENGINE CONVENTIONS — NOT HISTORICAL RULES
-----------------------------------------
Gap behavior (PRIMARY SOURCE NOT RECOVERED):
    GapPolicy.FILL_AT_OPEN — an order whose level is breached by the session
    open fills at the open print.
    GapPolicy.CANCEL       — the order is cancelled for that session
    (rejection reason gap_cancelled).

Simultaneous trigger ambiguity (PRIMARY SOURCE NOT RECOVERED):
    When both legs of an OCO group trigger within one session and no intraday
    ticks are supplied, the first-touch order is unknowable from daily bars.
    AmbiguityPolicy prescribes the convention: CANCEL_BOTH, PREFER_LONG,
    PREFER_SHORT, or RESOLVE_INTRADAY (which, without ticks, degrades to
    rejection reason insufficient_intraday_data rather than guessing).

Same-session protective stop:
    After an entry fill, a protective stop may fire within the same session.
    With daily bars, whether the protective extreme occurred AFTER the entry
    is unknowable; the kernel conservatively allows the stop to fire
    (details.convention='same_session_protective'). With ticks, ordering is
    resolved exactly.

Where intraday data exists it is used for trigger ordering (Phase 9 §11).
All prices are RAW BASIS; this kernel never sees cost-adjusted numbers.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from engine.historical.telemetry import RejectionLog, RejectionReason

KERNEL_VERSION = "hist-kernel-1.0.0"

LONG = "LONG"
SHORT = "SHORT"
BUY = "BUY"
SELL = "SELL"
KIND_ENTRY = "entry"
KIND_PROTECTIVE = "protective"


class GapPolicy(str, Enum):
    """ENGINE CONVENTION — gap-through-stop behavior: PRIMARY SOURCE NOT RECOVERED."""
    FILL_AT_OPEN = "fill_at_open"
    CANCEL = "cancel"


class AmbiguityPolicy(str, Enum):
    """ENGINE CONVENTION — same-session OCO double trigger: PRIMARY SOURCE NOT RECOVERED."""
    CANCEL_BOTH = "cancel_both"
    PREFER_LONG = "prefer_long"
    PREFER_SHORT = "prefer_short"
    RESOLVE_INTRADAY = "resolve_intraday"


@dataclass(frozen=True)
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Tick:
    time: str          # 'HH:MM:SS', zero-padded, sortable
    price: float
    volume: float = 0.0


@dataclass(frozen=True)
class StopOrder:
    side: str                     # BUY (long entry / short cover) or SELL
    level: float                  # raw-basis trigger
    kind: str = KIND_ENTRY        # entry | protective
    oco_group: Optional[str] = None
    order_id: str = ""


@dataclass(frozen=True)
class Fill:
    side: str
    level: float
    price: float                  # raw-basis fill price
    kind: str
    date: str
    tick_index: Optional[int] = None
    convention: str = ""          # non-empty when a declared engine convention decided the fill


@dataclass
class SessionOutcome:
    fills: list = field(default_factory=list)
    cancelled: list = field(default_factory=list)     # order_ids cancelled (OCO / gap / ambiguity)
    rejected: bool = False
    convention_notes: list = field(default_factory=list)


def _bad_bar(bar: Bar) -> bool:
    vals = (bar.open, bar.high, bar.low, bar.close)
    return any(v is None or v <= 0 for v in vals) or any(v != v for v in vals)


# ── daily-bar (no ticks) resolution ──────────────────────────────────────────

def _triggered(order: StopOrder, bar: Bar) -> tuple[bool, bool]:
    """(triggered, gapped). Gapped means the session OPEN already breached the level."""
    if order.side == BUY:
        gapped = bar.open >= order.level
        touched = gapped or bar.high >= order.level
    else:
        gapped = bar.open <= order.level
        touched = gapped or bar.low <= order.level
    return touched, gapped


def _fill_price_daily(order: StopOrder, bar: Bar, gap_policy: GapPolicy,
                      outcome: SessionOutcome, log: RejectionLog) -> Optional[float]:
    touched, gapped = _triggered(order, bar)
    if not touched:
        return None
    if gapped:
        if gap_policy is GapPolicy.FILL_AT_OPEN:
            return bar.open
        log.record(bar.date, RejectionReason.GAP_CANCELLED,
                   order_id=order.order_id, side=order.side, level=order.level,
                   open=bar.open, note="gap policy cancel")
        outcome.cancelled.append(order.order_id)
        return None
    return order.level


# ── intraday resolution ──────────────────────────────────────────────────────

def _touched_at_tick(order: StopOrder, price: float) -> bool:
    return price >= order.level if order.side == BUY else price <= order.level


# ── session execution ────────────────────────────────────────────────────────

def execute_stop_session(orders: list[StopOrder], bar: Bar, *,
                         gap_policy: GapPolicy,
                         ambiguity_policy: AmbiguityPolicy,
                         ticks: Optional[list[Tick]] = None,
                         log: Optional[RejectionLog] = None) -> SessionOutcome:
    """Execute resting stop orders against one session.

    Returns every fill/cancellation. Orders resting that never touch produce
    rejection reason trigger_not_reached (per order, entry orders only —
    protective orders that simply never trigger are normal life, not noise).
    """
    log = log if log is not None else RejectionLog()
    outcome = SessionOutcome()

    if _bad_bar(bar):
        log.record(bar.date, RejectionReason.INVALID_SESSION,
                   what="non-finite or non-positive OHLC")
        outcome.rejected = True
        return outcome

    orders = list(orders)

    # ── intraday path: exact first-touch ordering ────────────────────────────
    if ticks:
        remaining = list(orders)
        cancelled_ids: set[str] = set()
        for idx, tick in enumerate(sorted(ticks, key=lambda t: t.time)):
            for order in list(remaining):
                if order.order_id in cancelled_ids:
                    continue
                if not _touched_at_tick(order, tick.price):
                    continue
                outcome.fills.append(Fill(side=order.side, level=order.level,
                                          price=tick.price, kind=order.kind,
                                          date=bar.date, tick_index=idx))
                remaining.remove(order)
                # OCO: first fill cancels the rest of its group.
                if order.oco_group is not None:
                    for other in list(remaining):
                        if other.oco_group == order.oco_group:
                            cancelled_ids.add(other.order_id)
                            outcome.cancelled.append(other.order_id)
                            log.record(bar.date, RejectionReason.OCO_CANCELLED,
                                       order_id=other.order_id,
                                       filled_order_id=order.order_id)
                            remaining.remove(other)
        for order in remaining:
            if order.kind == KIND_ENTRY:
                log.record(bar.date, RejectionReason.TRIGGER_NOT_REACHED,
                           order_id=order.order_id, side=order.side, level=order.level)
        return outcome

    # ── daily-bar path ───────────────────────────────────────────────────────
    states = {o.order_id: _fill_price_daily(o, bar, gap_policy, outcome, log)
              for o in orders}

    # OCO conflict resolution for entry groups where BOTH legs triggered.
    groups: dict[str, list[StopOrder]] = {}
    for o in orders:
        if o.kind == KIND_ENTRY and o.oco_group is not None:
            groups.setdefault(o.oco_group, []).append(o)

    for group_id, group_orders in groups.items():
        triggered = [o for o in group_orders if states.get(o.order_id) is not None]
        if len(triggered) <= 1:
            continue
        if ambiguity_policy is AmbiguityPolicy.RESOLVE_INTRADAY:
            # Intraday resolution was promised but no ticks were supplied.
            log.record(bar.date, RejectionReason.INSUFFICIENT_INTRADAY_DATA,
                       what="oco double trigger without ticks",
                       oco_group=group_id)
            for o in triggered:
                states[o.order_id] = None
                outcome.cancelled.append(o.order_id)
            continue
        if ambiguity_policy is AmbiguityPolicy.CANCEL_BOTH:
            log.record(bar.date, RejectionReason.AMBIGUITY,
                       oco_group=group_id,
                       convention="cancel_both")
            outcome.convention_notes.append(f"{bar.date}: oco {group_id} cancel_both")
            for o in triggered:
                states[o.order_id] = None
                outcome.cancelled.append(o.order_id)
            continue
        keep = BUY if ambiguity_policy is AmbiguityPolicy.PREFER_LONG else SELL
        for o in triggered:
            if o.side != keep:
                states[o.order_id] = None
                outcome.cancelled.append(o.order_id)
                log.record(bar.date, RejectionReason.AMBIGUITY,
                           oco_group=group_id, cancelled_order_id=o.order_id,
                           convention=f"prefer_{keep.lower()}")
        outcome.convention_notes.append(
            f"{bar.date}: oco {group_id} resolved by convention prefer_{keep.lower()}")

    # Emit fills; a filled entry cancels its OCO siblings that never triggered.
    filled_ids = [oid for oid, price in states.items() if price is not None]
    for order in orders:
        price = states.get(order.order_id)
        if price is None:
            continue
        outcome.fills.append(Fill(side=order.side, level=order.level, price=price,
                                  kind=order.kind, date=bar.date))
        if order.oco_group is not None:
            for other in orders:
                if (other.oco_group == order.oco_group
                        and other.order_id != order.order_id
                        and other.order_id not in filled_ids
                        and other.order_id not in outcome.cancelled):
                    outcome.cancelled.append(other.order_id)
                    log.record(bar.date, RejectionReason.OCO_CANCELLED,
                               order_id=other.order_id, filled_order_id=order.order_id)

    for order in orders:
        if (order.order_id not in states or states[order.order_id] is None) \
                and order.kind == KIND_ENTRY \
                and order.order_id not in outcome.cancelled \
                and not _triggered(order, bar)[0]:
            log.record(bar.date, RejectionReason.TRIGGER_NOT_REACHED,
                       order_id=order.order_id, side=order.side, level=order.level)

    return outcome


def execute_protective_same_session(protective: StopOrder, entry_fill: Fill, bar: Bar, *,
                                    gap_policy: GapPolicy,
                                    ticks: Optional[list[Tick]] = None,
                                    log: Optional[RejectionLog] = None) -> Optional[Fill]:
    """Evaluate a protective stop within the entry session, after an entry fill.

    Intraday ticks: exact — only ticks STRICTLY AFTER the entry fill's tick can
    trigger the protective stop, and ordering is resolved by time.

    Daily bars (ENGINE CONVENTION — PRIMARY SOURCE NOT RECOVERED for whether the
    protective extreme can follow the entry within one daily bar): the stop is
    conservatively allowed to fire. Fill price follows the gap policy exactly
    like any other stop.
    """
    log = log if log is not None else RejectionLog()
    if _bad_bar(bar):
        return None

    if ticks:
        start_idx = (entry_fill.tick_index + 1) if entry_fill.tick_index is not None else 0
        for idx, tick in enumerate(sorted(ticks, key=lambda t: t.time)):
            if idx <= start_idx - 1:
                continue
            if _touched_at_tick(protective, tick.price):
                return Fill(side=protective.side, level=protective.level,
                            price=tick.price, kind=KIND_PROTECTIVE,
                            date=bar.date, tick_index=idx)
        return None

    touched, gapped = _triggered(protective, bar)
    if not touched:
        return None
    if gapped and gap_policy is GapPolicy.CANCEL:
        log.record(bar.date, RejectionReason.GAP_CANCELLED,
                   order_id=protective.order_id, kind=KIND_PROTECTIVE,
                   level=protective.level, note="same-session gap policy cancel")
        return None
    price = bar.open if gapped else protective.level
    note = "same_session_protective_daily_convention" + ("" if not gapped else "+fill_at_open")
    return Fill(side=protective.side, level=protective.level, price=price,
                kind=KIND_PROTECTIVE, date=bar.date, convention=note)
