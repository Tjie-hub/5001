"""Phase 9 tests — the one stop-order execution kernel.

Covers: long/short entries, gap-through-stop (both policies), OCO,
same-session protective stop, simultaneous-trigger ambiguity, intraday
tick ordering, long/short symmetry. All prices raw basis.
"""
from engine.historical.kernel import (AmbiguityPolicy, Bar, GapPolicy, SELL,
                                      StopOrder, Tick,
                                      execute_protective_same_session,
                                      execute_stop_session)
from engine.historical.telemetry import RejectionLog, RejectionReason


def _bar(o, h, l, c, date="2026-01-15"):
    return Bar(date=date, open=o, high=h, low=l, close=c)


def _buy(level, group="g", oid="b"):
    return StopOrder(side="BUY", level=level, kind="entry", oco_group=group, order_id=oid)


def _sell(level, group="g", oid="s"):
    return StopOrder(side="SELL", level=level, kind="entry", oco_group=group, order_id=oid)


def _prot(side, level, oid="p"):
    return StopOrder(side=side, level=level, kind="protective", order_id=oid)


# ── plain stop entries ───────────────────────────────────────────────────────

def test_long_stop_fills_at_level_when_touched():
    log = RejectionLog()
    out = execute_stop_session([_buy(110)], _bar(100, 120, 95, 115),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert len(out.fills) == 1
    assert out.fills[0].price == 110.0 and out.fills[0].side == "BUY"


def test_short_stop_fills_at_level_when_touched():
    log = RejectionLog()
    out = execute_stop_session([_sell(90)], _bar(100, 105, 80, 85),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert len(out.fills) == 1
    assert out.fills[0].price == 90.0 and out.fills[0].side == "SELL"


def test_long_short_symmetry_distances_from_open():
    """Mirror scenarios must fill at equal distances from the open."""
    long_out = execute_stop_session([_buy(110)], _bar(100, 120, 95, 115),
                                    gap_policy=GapPolicy.FILL_AT_OPEN,
                                    ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH)
    short_out = execute_stop_session([_sell(90)], _bar(100, 105, 80, 85),
                                     gap_policy=GapPolicy.FILL_AT_OPEN,
                                     ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH)
    assert long_out.fills[0].price - 100 == 100 - short_out.fills[0].price == 10


def test_untriggered_entry_records_trigger_not_reached():
    log = RejectionLog()
    out = execute_stop_session([_buy(110)], _bar(100, 105, 99, 102),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert not out.fills
    assert log.histogram()[RejectionReason.TRIGGER_NOT_REACHED.value] == 1


# ── gap-through-stop (PRIMARY SOURCE NOT RECOVERED — both are conventions) ──

def test_gap_fill_at_open_convention():
    log = RejectionLog()
    out = execute_stop_session([_buy(110)], _bar(115, 120, 95, 118),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert out.fills[0].price == 115.0        # the OPEN, never the stop level


def test_gap_cancel_convention():
    log = RejectionLog()
    out = execute_stop_session([_buy(110)], _bar(115, 120, 95, 118),
                               gap_policy=GapPolicy.CANCEL,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert not out.fills
    assert "b" in out.cancelled
    assert log.histogram()[RejectionReason.GAP_CANCELLED.value] == 1


def test_gap_down_through_short_stop_fills_at_open():
    out = execute_stop_session([_sell(90)], _bar(85, 100, 80, 88),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH)
    assert out.fills[0].price == 85.0


# ── OCO ──────────────────────────────────────────────────────────────────────

def test_oco_sibling_cancelled_after_single_fill():
    log = RejectionLog()
    out = execute_stop_session([_buy(110), _sell(90)], _bar(100, 115, 95, 112),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert [f.side for f in out.fills] == ["BUY"]
    assert "s" in out.cancelled
    assert log.histogram()[RejectionReason.OCO_CANCELLED.value] == 1


def test_oco_double_trigger_ambiguity_cancel_both():
    log = RejectionLog()
    out = execute_stop_session([_buy(110), _sell(90)], _bar(100, 125, 75, 100),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert not out.fills
    assert log.histogram()[RejectionReason.AMBIGUITY.value] == 1


def test_oco_double_trigger_resolve_intraday_without_ticks():
    log = RejectionLog()
    out = execute_stop_session([_buy(110), _sell(90)], _bar(100, 125, 75, 100),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY, log=log)
    assert not out.fills
    assert log.histogram()[RejectionReason.INSUFFICIENT_INTRADAY_DATA.value] == 1


def test_oco_double_trigger_prefer_long_convention():
    log = RejectionLog()
    out = execute_stop_session([_buy(110), _sell(90)], _bar(100, 125, 75, 100),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.PREFER_LONG, log=log)
    assert [f.side for f in out.fills] == ["BUY"]


# ── same-session protective stop ─────────────────────────────────────────────

def test_same_session_protective_stop_fills():
    log = RejectionLog()
    fill = execute_protective_same_session(
        _prot(SELL, 90), entry_fill=None, bar=_bar(100, 120, 80, 95),
        gap_policy=GapPolicy.FILL_AT_OPEN, ticks=None, log=log)
    assert fill is not None and fill.price == 90.0
    assert "same_session_protective_daily_convention" in fill.convention


def test_same_session_protective_gap_cancel():
    log = RejectionLog()
    fill = execute_protective_same_session(
        _prot(SELL, 90), entry_fill=None, bar=_bar(85, 100, 80, 88),
        gap_policy=GapPolicy.CANCEL, ticks=None, log=log)
    assert fill is None
    assert log.histogram()[RejectionReason.GAP_CANCELLED.value] == 1


def test_protective_never_touches_is_silent():
    """A protective stop that simply never triggers is normal life, not a
    rejection — no trigger_not_reached noise for protective orders."""
    log = RejectionLog()
    execute_stop_session([_prot(SELL, 50)], _bar(100, 120, 80, 95),
                         gap_policy=GapPolicy.FILL_AT_OPEN,
                         ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert log.histogram() == {}


# ── intraday tick ordering (Phase 9 §11) ─────────────────────────────────────

def test_intraday_ticks_resolve_order_exactly():
    ticks = [Tick("09:00:01", 100.0), Tick("10:00:00", 103.0), Tick("10:30:00", 97.0)]
    log = RejectionLog()
    out = execute_stop_session([_buy(102), _sell(98)], _bar(100, 110, 96, 105),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
                               ticks=ticks, log=log)
    assert [f.side for f in out.fills] == ["BUY"]       # OCO sibling gone
    assert out.fills[0].price == 103.0                  # filled at the 10:00 tick
    assert out.fills[0].tick_index == 1


def test_intraday_protective_only_after_entry_tick():
    ticks = [Tick("09:00:01", 100.0), Tick("10:00:00", 103.0), Tick("10:30:00", 97.0)]
    entry = None
    log = RejectionLog()
    out = execute_stop_session([_buy(102)], _bar(100, 110, 96, 105),
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
                               ticks=ticks, log=log)
    entry = out.fills[0]
    prot = execute_protective_same_session(
        _prot(SELL, 98), entry, _bar(100, 110, 96, 105),
        gap_policy=GapPolicy.FILL_AT_OPEN, ticks=ticks, log=log)
    assert prot is not None and prot.tick_index == 2    # strictly AFTER entry tick


def test_invalid_session_rejected():
    log = RejectionLog()
    bad = Bar(date="2026-01-15", open=0.0, high=-5, low=1, close=1)
    out = execute_stop_session([_buy(110)], bad,
                               gap_policy=GapPolicy.FILL_AT_OPEN,
                               ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH, log=log)
    assert out.rejected and not out.fills
    assert log.histogram()[RejectionReason.INVALID_SESSION.value] == 1
