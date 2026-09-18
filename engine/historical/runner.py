"""engine/historical/runner.py — the shared position-carry loop for the historical systems.

Every system (crabel_orb.v1, crabel_open_stretch.v1, crabel_open_stretch's
sibling raschke_id_nr4.v1 and the declared transfer raschke_nr7.v1) runs through
this ONE loop and the ONE kernel (engine/historical/kernel.py). The systems
differ ONLY in how they plan entry orders and protective stops; entry timing,
OCO, gap handling, ambiguity resolution, costs-in-PnL-only and telemetry are
identical by construction.

Three behaviors were added by the 2026-09-03 provenance closure audit, each
because a recovered primary rule could not previously be expressed:

  ProtectiveStopMode.NONE_TEST_PROTOCOL — Crabel 1990: "no stops were used on
      the tests". A protective stop installed anyway measures a different rule.
  moc_hold_sessions = 0                 — Crabel 1990: "zero indicates an exit
      on the close the same day of entry". This is the book's baseline case.
  ReversalPolicy.ENTRY_DAY_ONLY         — Street Smarts Ch. 19 rule 3: the stop
      does not merely close, it reverses; and the reversal order lives on the
      entry day only, expiring at that day's close.

No pandas, no DB, no legacy strategy imports.
"""
from engine.historical.base import (BreakevenPolicy, ExitKind, HistoricalTrade,
                                    ProtectiveStopMode, ReversalPolicy,
                                    RunResult)
from engine.historical.costs import CostModel
from engine.historical.kernel import (AmbiguityPolicy, Bar, GapPolicy,
                                      KIND_PROTECTIVE, StopOrder,
                                      execute_protective_same_session,
                                      execute_stop_session)
from engine.historical.telemetry import RejectionLog, RejectionReason


class EntryPlan:
    """What an entry planner hands back for execution day bars[t].

    `orders`      — resting stop orders (normally a two-leg OCO entry bracket).
    `meta`        — system-specific provenance of the levels (stretch value,
                    OR high/low, setup extremes, tick size) for the trade record.
    `protective_for(fill)` — the protective StopOrder once a given fill happens.
    """
    __slots__ = ("orders", "meta", "protective_for")

    def __init__(self, orders, meta, protective_for):
        self.orders = orders
        self.meta = meta
        self.protective_for = protective_for


def _direction(side: str) -> float:
    return 1.0 if side == "LONG" else -1.0


def run_bracket_system(*, rule_id: str,
                       bars: list[Bar],
                       exit_convention,
                       tie_policy,
                       gap_policy: GapPolicy,
                       ambiguity_policy: AmbiguityPolicy,
                       breakeven_move: str,
                       cost_model: CostModel,
                       quantity: float,
                       capital: float | None,
                       signal_basis: str,
                       identity: str,
                       config_echo: dict,
                       entry_planner,
                       protective_stop_mode: str = ProtectiveStopMode.ENABLED,
                       reversal_policy: str = ReversalPolicy.NONE,
                       ticks_by_date: dict | None = None,
                       log: RejectionLog | None = None) -> RunResult:
    """Generic bracket system loop.

    entry_planner(t: int) -> EntryPlan | None
        Called with the SETUP day index t (execution day is t+1, never traded
        as a setup day). Returns None after recording rejections, or an
        EntryPlan for the execution day.
    """
    ticks_by_date = ticks_by_date or {}
    log = log if log is not None else RejectionLog()
    trades: list[HistoricalTrade] = []
    n = len(bars)

    if protective_stop_mode not in (ProtectiveStopMode.ENABLED,
                                    ProtectiveStopMode.NONE_TEST_PROTOCOL):
        raise ValueError(f"invalid_configuration: protective_stop_mode "
                         f"{protective_stop_mode!r}")
    if reversal_policy not in (ReversalPolicy.NONE, ReversalPolicy.ENTRY_DAY_ONLY):
        raise ValueError(f"invalid_configuration: reversal_policy {reversal_policy!r}")

    stops_enabled = protective_stop_mode == ProtectiveStopMode.ENABLED

    def plan_id(p: EntryPlan, i: int) -> str:
        return p.orders[i].order_id or f"{rule_id}#o{i}"

    def base_conventions(plan: EntryPlan) -> dict:
        return {
            "tie_policy": getattr(tie_policy, "value", str(tie_policy)),
            "gap_policy": gap_policy.value,
            "ambiguity_policy": ambiguity_policy.value,
            "breakeven_move": breakeven_move,
            "protective_stop_mode": protective_stop_mode,
            "reversal_policy": reversal_policy,
            "exit_kind": exit_convention.kind,
            **({"moc_hold_sessions": exit_convention.moc_hold_sessions}
               if exit_convention.kind == ExitKind.MOC_AFTER_N_SESSIONS else {}),
            **({"profit_check_sessions": exit_convention.profit_check_sessions}
               if exit_convention.kind == ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS
               else {}),
            "same_session_protective": stops_enabled,
            **plan.meta,
        }

    t = 0
    while t < n - 1:
        bar = bars[t]

        try:
            plan = entry_planner(t)
        except ValueError as exc:
            if "insufficient_history" in str(exc):
                log.record(bar.date, RejectionReason.INSUFFICIENT_HISTORY,
                           what=str(exc), setup_t=t)
                plan = None
            else:
                raise

        if plan is None or not plan.orders:
            t += 1
            continue

        exec_idx = t + 1
        exec_bar = bars[exec_idx]
        ticks = ticks_by_date.get(exec_bar.date)

        # ── entry ────────────────────────────────────────────────────────────
        orders = [StopOrder(side=o.side, level=o.level, kind=o.kind,
                            oco_group=o.oco_group, order_id=o.order_id or plan_id(plan, i))
                  for i, o in enumerate(plan.orders)]
        outcome = execute_stop_session(orders, exec_bar, gap_policy=gap_policy,
                                       ambiguity_policy=ambiguity_policy,
                                       ticks=ticks, log=log)
        entry_fill = next((f for f in outcome.fills if f.kind == "entry"), None)
        if entry_fill is None:
            t += 1
            continue

        side = "LONG" if entry_fill.side == "BUY" else "SHORT"
        if capital is not None and quantity * entry_fill.price > capital:
            log.record(exec_bar.date, RejectionReason.CAPITAL_UNAVAILABLE,
                       side=side, price=entry_fill.price,
                       required=quantity * entry_fill.price, capital=capital)
            t += 2  # entry consumed; skip to the day after the execution day
            continue

        protective = None
        if stops_enabled:
            planned = plan.protective_for(entry_fill)
            protective = StopOrder(side=planned.side, level=planned.level,
                                   kind=KIND_PROTECTIVE, oco_group=None,
                                   order_id=planned.order_id or f"{rule_id}#prot")

        trade = _open_trade(rule_id=rule_id, side=side, quantity=quantity,
                            signal_basis=signal_basis, entry_date=exec_bar.date,
                            entry_price_raw=entry_fill.price,
                            entry_fill_convention=entry_fill.convention or "stop_touched",
                            stop_level_raw=protective.level if protective else None,
                            cost_model=cost_model,
                            conventions=base_conventions(plan))

        # ── same-session protective stop (and, for Raschke, the reversal) ────
        prot_fill = None
        if protective is not None:
            prot_fill = execute_protective_same_session(
                protective, entry_fill, exec_bar, gap_policy=gap_policy,
                ticks=ticks, log=log)

        if prot_fill is not None and reversal_policy == ReversalPolicy.ENTRY_DAY_ONLY:
            # Street Smarts Ch. 19 rule 3: the stop closes AND reverses. The
            # reversal order exists on the entry day only (Ch. 20 rule 4), so
            # this branch is unreachable from _carry() by construction.
            _close(trade, exec_bar.date, prot_fill.price, "stopped_and_reversed",
                   prot_fill.convention or "stop_touched", cost_model, side, quantity)
            trades.append(trade)

            rev_side = "SHORT" if side == "LONG" else "LONG"
            rev_conventions = dict(base_conventions(plan))
            rev_conventions.update({
                "reversal_of": trade.entry_date,
                "reversal_expiry": "entry_session_close",
                # The reversed leg's own protective stop is not stated anywhere
                # in the recovered text; the engine rests none rather than
                # inventing one. Its exit is the exit convention.
                "reversed_leg_protective_stop": "none: PRIMARY SOURCE NOT RECOVERED.",
            })
            rev_trade = _open_trade(
                rule_id=rule_id, side=rev_side, quantity=quantity,
                signal_basis=signal_basis, entry_date=exec_bar.date,
                entry_price_raw=prot_fill.price,
                entry_fill_convention="stop_and_reverse",
                stop_level_raw=None, cost_model=cost_model,
                conventions=rev_conventions)
            trades.append(rev_trade)

            if _entry_session_exit(rev_trade, exec_bar, exit_convention,
                                   cost_model, rev_side, quantity,
                                   prot_fill.price):
                t = exec_idx + 1
                continue
            exit_idx = _carry(rev_trade, bars, from_idx=exec_idx + 1,
                              entry_session_idx=exec_idx, protective=None,
                              exit_convention=exit_convention,
                              breakeven_move=breakeven_move,
                              entry_fill_raw=prot_fill.price,
                              gap_policy=gap_policy, cost_model=cost_model,
                              ticks_by_date=ticks_by_date, log=log)
            if exit_idx is None:
                break
            t = exit_idx + 1
            continue

        if prot_fill is not None:
            _close(trade, exec_bar.date, prot_fill.price, "protective_stop",
                   prot_fill.convention, cost_model, side, quantity)
            trades.append(trade)
            t = exec_idx + 1
            continue

        trades.append(trade)
        if _entry_session_exit(trade, exec_bar, exit_convention, cost_model,
                               side, quantity, entry_fill.price):
            t = exec_idx + 1
            continue

        # ── carry across sessions ────────────────────────────────────────────
        exit_idx = _carry(trade, bars, from_idx=exec_idx + 1,
                          entry_session_idx=exec_idx, protective=protective,
                          exit_convention=exit_convention,
                          breakeven_move=breakeven_move,
                          entry_fill_raw=entry_fill.price,
                          gap_policy=gap_policy, cost_model=cost_model,
                          ticks_by_date=ticks_by_date, log=log)
        if exit_idx is None:
            break  # end of data with position still open
        t = exit_idx + 1

    return RunResult(rule_id=rule_id, signal_basis=signal_basis, trades=trades,
                     rejections=log, config_echo=config_echo, identity=identity)


def _open_trade(*, rule_id, side, quantity, signal_basis, entry_date,
                entry_price_raw, entry_fill_convention, stop_level_raw,
                cost_model, conventions) -> HistoricalTrade:
    return HistoricalTrade(
        rule_id=rule_id, side=side, quantity=quantity,
        signal_basis=signal_basis, pnl_basis=signal_basis,
        entry_date=entry_date, entry_price_raw=entry_price_raw,
        entry_price_accounting=(cost_model.buy_fill(entry_price_raw)
                                if side == "LONG"
                                else cost_model.sell_fill(entry_price_raw)),
        entry_fill_convention=entry_fill_convention,
        stop_level_raw=stop_level_raw,
        conventions=dict(conventions))


def _entry_session_exit(trade: HistoricalTrade, exec_bar: Bar, exit_convention,
                        cost_model: CostModel, side: str, quantity: float,
                        entry_fill_raw: float) -> bool:
    """Exits that can fire at the close of the ENTRY session itself.

    Crabel 1990's N = 0 ("an exit on the close the same day of entry") lives
    here — the old loop counted the entry session as session 1 and so could
    only express N >= 1.
    """
    if (exit_convention.kind == ExitKind.MOC_AFTER_N_SESSIONS
            and exit_convention.moc_hold_sessions == 0):
        _close(trade, exec_bar.date, exec_bar.close, "moc_convention",
               "moc_after_n_sessions", cost_model, side, quantity)
        return True
    if (exit_convention.kind == ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS
            and exit_convention.profit_check_sessions == 1):
        if (exec_bar.close - entry_fill_raw) * _direction(side) <= 0:
            _close(trade, exec_bar.date, exec_bar.close,
                   "moc_unprofitable_time_stop", "street_smarts_ch19_rule5",
                   cost_model, side, quantity)
            return True
    return False


def _close(trade: HistoricalTrade, exit_date: str, exit_price_raw: float,
           reason: str, convention: str, cost_model: CostModel,
           side: str, quantity: float) -> None:
    direction = _direction(side)
    trade.exit_date = exit_date
    trade.exit_price_raw = exit_price_raw
    trade.exit_reason = reason
    trade.exit_price_accounting = (cost_model.sell_fill(exit_price_raw)
                                   if side == "LONG"
                                   else cost_model.buy_fill(exit_price_raw))
    trade.pnl_raw = (trade.exit_price_raw - trade.entry_price_raw) * direction * quantity
    trade.pnl_net = (trade.exit_price_accounting - trade.entry_price_accounting) \
        * direction * quantity
    if convention:
        trade.conventions["exit_fill_convention"] = convention


def _carry(trade: HistoricalTrade, bars: list[Bar], *, from_idx: int,
           entry_session_idx: int, protective: StopOrder | None, exit_convention,
           breakeven_move: str, entry_fill_raw: float, gap_policy: GapPolicy,
           cost_model: CostModel, ticks_by_date: dict, log: RejectionLog) -> int | None:
    """Walk sessions until protective stop, an exit convention fires, or the
    sample ends.

    Returns the INDEX OF THE EXIT SESSION, or None when the position reaches
    the end of the sample — closed at the last bar's close with reason
    end_of_data under ExitKind.HOLD_TO_END_OF_DATA, otherwise left open.

    `protective` is None under ProtectiveStopMode.NONE_TEST_PROTOCOL and for a
    reversed leg: no stop rests, so no stop can fire.
    """
    n = len(bars)
    if breakeven_move not in (BreakevenPolicy.NONE, BreakevenPolicy.AFTER_ENTRY_SESSION):
        raise ValueError(f"unknown breakeven policy: {breakeven_move!r}")

    for k in range(from_idx, n):
        bar = bars[k]
        ticks = ticks_by_date.get(bar.date)

        if protective is not None:
            level = protective.level
            if (breakeven_move == BreakevenPolicy.AFTER_ENTRY_SESSION
                    and k > entry_session_idx):
                level = entry_fill_raw  # break-even (raw); ENGINE CONVENTION
                trade.conventions["breakeven_applied_date"] = bar.date

            prot = StopOrder(side=protective.side, level=level, kind=KIND_PROTECTIVE,
                             oco_group=None, order_id=protective.order_id)
            outcome = execute_stop_session([prot], bar, gap_policy=gap_policy,
                                           ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH,
                                           ticks=ticks, log=log)
            if outcome.fills:
                fill = outcome.fills[0]
                _close(trade, bar.date, fill.price, "protective_stop",
                       fill.convention or "stop_touched", cost_model,
                       trade.side, trade.quantity)
                return k

        sessions_held = k - entry_session_idx + 1   # entry session counts as 1

        if exit_convention.kind == ExitKind.MOC_AFTER_N_SESSIONS:
            # N counts sessions AFTER the entry session (N = 0 handled at entry).
            if sessions_held - 1 >= exit_convention.moc_hold_sessions:
                _close(trade, bar.date, bar.close, "moc_convention",
                       "moc_after_n_sessions", cost_model,
                       trade.side, trade.quantity)
                return k

        elif exit_convention.kind == ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS:
            # Street Smarts Ch. 19 rule 5 is a SINGLE check at the two-day mark,
            # not a standing condition: a position that IS profitable there is
            # left to the (unrecovered) trailing stop, not re-tested daily.
            if sessions_held == exit_convention.profit_check_sessions:
                unrealized = (bar.close - entry_fill_raw) * _direction(trade.side)
                if unrealized <= 0:
                    _close(trade, bar.date, bar.close, "moc_unprofitable_time_stop",
                           "street_smarts_ch19_rule5", cost_model,
                           trade.side, trade.quantity)
                    return k

    if exit_convention.kind == ExitKind.HOLD_TO_END_OF_DATA:
        last = bars[-1]
        _close(trade, last.date, last.close, "end_of_data",
               "hold_to_end_of_data", cost_model, trade.side, trade.quantity)
    return None
