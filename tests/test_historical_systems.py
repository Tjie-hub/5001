"""Phase 9 tests — the three historical systems: A/A2 separation, Crabel vs
Raschke isolation, Opening-Range duration configurability, zero-trade
telemetry, e2e bracket execution on synthetic RAW-basis bars.
"""
import dataclasses
import pytest

from engine.historical.base import (BreakevenPolicy, ExitConvention, ExitKind,
                                    ProtectiveStopMode, SessionDefinition)
from engine.historical.crabel_open_stretch import CrabelOpenStretchConfig
from engine.historical.crabel_open_stretch import run as run_a2
from engine.historical.crabel_orb import CrabelOrbConfig
from engine.historical.crabel_orb import run as run_a
from engine.historical.kernel import AmbiguityPolicy, GapPolicy, Tick
from engine.historical.nr7 import TiePolicy
from engine.historical.raschke_nr7 import RaschkeNr7Config
from engine.historical.raschke_nr7 import run as run_b


def _bars():
    """13 RAW-basis daily bars.

    Days 0..8: range 10 (H−L), min(|O−H|,|O−L|) = 2 → contributes 2 to Stretch.
    Day 9 (setup): range 5 < 10 → NR7 under STRICT_LESS; min distance 2.
    Day 10 (execution): O=100 H=110 L=96 C=105.
    Day 11: O=104 H=106 L=100 C=104.  Day 12: O=104 H=107 L=101 C=103.
    Stretch at t=9 = (2*9 + 2)/10 = 2.0 exactly.
    """
    bars = []
    for i in range(9):
        bars.append(_bar(f"2026-01-{i+1:02d}", 100, 102, 92, 101))
    bars.append(_bar("2026-01-10", 100, 102, 97, 101))   # setup day (NR7)
    bars.append(_bar("2026-01-11", 100, 110, 96, 105))   # execution day
    bars.append(_bar("2026-01-12", 104, 106, 100, 104))
    bars.append(_bar("2026-01-13", 104, 107, 101, 103))
    return bars


def _bar(date, o, h, l, c):
    from engine.historical.kernel import Bar
    return Bar(date=date, open=o, high=h, low=l, close=c)


def _orb_cfg(**kw):
    d = dict(nr7_tie_policy=TiePolicy.STRICT_LESS,
             opening_range_seconds=30,
             session=SessionDefinition("09:00:00"),
             gap_policy=GapPolicy.FILL_AT_OPEN,
             ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
             # N = 0 is "exit on the close the same day of entry" (Crabel 1990
             # test protocol). Under the pre-audit semantics this was N = 1.
             exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
             breakeven_move=BreakevenPolicy.NONE,
             protective_stop_mode=ProtectiveStopMode.ENABLED)
    d.update(kw)
    return CrabelOrbConfig(**d)


def _a2_cfg(**kw):
    d = dict(nr7_tie_policy=TiePolicy.STRICT_LESS,
             session=SessionDefinition("09:00:00"),
             gap_policy=GapPolicy.FILL_AT_OPEN,
             ambiguity_policy=AmbiguityPolicy.PREFER_LONG,
             exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 5),
             breakeven_move=BreakevenPolicy.NONE,
             protective_stop_mode=ProtectiveStopMode.ENABLED)
    d.update(kw)
    return CrabelOpenStretchConfig(**d)


def _b_cfg(**kw):
    d = dict(nr7_tie_policy=TiePolicy.STRICT_LESS, tick_size=0.25,
             session=SessionDefinition("09:00:00"),
             gap_policy=GapPolicy.FILL_AT_OPEN,
             ambiguity_policy=AmbiguityPolicy.PREFER_LONG,
             exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 5))
    d.update(kw)
    return RaschkeNr7Config(**d)


def _or(high, low):
    def provider(date):
        return {"or_high": high, "or_low": low, "n_ticks": 5, "basis": "raw_ticks"}
    return provider


# ── System A (crabel_orb.v1) ─────────────────────────────────────────────────

def test_system_a_entry_levels_are_or_plus_stretch():
    bars = _bars()
    res = run_a(bars, _orb_cfg(), _or(105.0, 95.0))
    assert res.n_trades == 1
    t = res.trades[0]
    # Buy stop = OR High + Stretch = 105 + 2 = 107; touched by H=110 → fill 107.
    assert t.side == "LONG" and t.entry_price_raw == 107.0
    assert t.entry_date == "2026-01-11"
    assert t.conventions["stretch"] == 2.0
    assert t.conventions["or_high"] == 105.0 and t.conventions["or_low"] == 95.0
    assert t.stop_level_raw == 93.0                       # OR Low − Stretch
    assert t.signal_basis == "stored_raw"


def test_system_a_moc_n_zero_exits_at_entry_session_close():
    res = run_a(_bars(), _orb_cfg(), _or(105.0, 95.0))
    t = res.trades[0]
    assert t.exit_reason == "moc_convention"
    assert t.exit_date == "2026-01-11" and t.exit_price_raw == 105.0


def test_system_a_moc_n_one_exits_the_session_after_entry():
    res = run_a(_bars(), _orb_cfg(
        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 1)),
        _or(105.0, 95.0))
    t = res.trades[0]
    assert t.exit_date == "2026-01-12" and t.exit_price_raw == 104.0


def test_system_a_short_leg_fires_when_or_low_breaks():
    # OR entirely above the day's range → only the sell stop can trigger.
    bars = _bars()
    bars[10] = _bar("2026-01-11", 104, 105, 85, 90)      # execution day crashes
    res = run_a(bars, _orb_cfg(), _or(105.0, 95.0))
    t = res.trades[0]
    assert t.side == "SHORT" and t.entry_price_raw == 93.0   # 95 − 2
    assert t.stop_level_raw == 107.0                         # opposite OR side


def test_system_a_missing_opening_range_is_rejected_not_fabricated():
    res = run_a(_bars(), _orb_cfg(), lambda date: None)
    assert res.zero_trade
    assert res.histogram()["insufficient_intraday_data"] >= 1


def test_opening_range_duration_is_required_never_defaulted():
    """The recovered OR is thirty seconds (1990 Glossary p. 285). The field has
    NO default anyway: a run must STATE the window it used, so that a
    non-historical choice is visible in the config echo and the identity hash
    rather than inherited silently."""
    with pytest.raises(TypeError):
        CrabelOrbConfig(nr7_tie_policy=TiePolicy.STRICT_LESS,
                        session=SessionDefinition("09:00:00"),
                        gap_policy=GapPolicy.FILL_AT_OPEN,
                        ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
                        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
                        breakeven_move=BreakevenPolicy.NONE,
                        protective_stop_mode=ProtectiveStopMode.ENABLED)
    with pytest.raises(ValueError, match="invalid_configuration"):
        _orb_cfg(opening_range_seconds=0)


def test_opening_range_duration_changes_outcome_and_identity():
    """A configurable OR duration must move both the traded levels and the
    rule identity (Phase 9 §14 item 14). OR choices keep exactly one OCO leg
    inside the execution day's range so the comparison isolates the level."""
    short_or = run_a(_bars(), _orb_cfg(opening_range_seconds=30), _or(101.0, 97.0))
    long_or = run_a(_bars(), _orb_cfg(opening_range_seconds=300), _or(105.0, 95.0))
    assert short_or.trades[0].entry_price_raw == 103.0    # 101 + 2
    assert long_or.trades[0].entry_price_raw == 107.0     # 105 + 2
    assert short_or.identity != long_or.identity


# ── System A2 (crabel_open_stretch.v1) — completely separate from A ─────────

def test_a2_entry_anchors_to_open_not_opening_range():
    bars = _bars()
    ticks = {"2026-01-11": [Tick("09:00:01", 100.0), Tick("10:00:00", 103.0),
                            Tick("10:30:00", 97.0)]}
    res = run_a2(bars, _a2_cfg(), ticks_by_date=ticks)
    assert res.n_trades == 1
    t = res.trades[0]
    # Buy stop = Open + Stretch = 100 + 2 = 102; first tick ≥ 102 is 103 → fill 103.
    assert t.entry_price_raw == 103.0
    assert t.conventions["open_anchor"] == 100.0
    assert t.conventions["stretch"] == 2.0
    assert t.stop_level_raw == 98.0                       # Open − Stretch


def test_a2_never_reads_opening_range_data():
    """A2 runs with NO or-provider argument at all and its config has no OR
    field — configuration cannot transform A2 into A (Phase 9 §9)."""
    import inspect
    sig = inspect.signature(run_a2)
    assert "or_provider" not in sig.parameters
    assert all(f.name != "opening_range_seconds"
               for f in dataclasses.fields(CrabelOpenStretchConfig))


def test_a_and_a2_have_distinct_rule_ids_and_identities():
    import engine.historical as h
    ids = {name: spec for name, spec in h.HISTORICAL_SPECS.items()}
    assert {"crabel_orb.v1", "crabel_open_stretch.v1",
            "raschke_id_nr4.v1", "raschke_nr7.v1"} <= set(ids)
    a = run_a(_bars(), _orb_cfg(), _or(105.0, 95.0))
    a2 = run_a2(_bars(), _a2_cfg())
    assert a.identity != a2.identity
    assert a.rule_id != a2.rule_id


def test_a_and_a2_trade_differently_on_identical_bars():
    """Same setup, same Stretch — different entry mechanisms must produce
    different trades (separation is behavioral, not just nominal)."""
    ticks = {"2026-01-11": [Tick("09:00:01", 100.0), Tick("10:00:00", 103.0),
                            Tick("10:30:00", 97.0)]}
    a = run_a(_bars(), _orb_cfg(), _or(105.0, 95.0))
    a2 = run_a2(_bars(), _a2_cfg(), ticks_by_date=ticks)
    assert a.trades[0].entry_price_raw != a2.trades[0].entry_price_raw


# ── raschke_nr7.v1 (declared TRANSFER) — Crabel isolation ───────────────────

def test_raschke_entry_is_setup_extreme_plus_one_tick():
    bars = _bars()
    res = run_b(bars, _b_cfg())
    assert res.n_trades == 1
    t = res.trades[0]
    # Setup day 9: H=102 L=97; buy = 102.25; day-10 low 96 ≤ protective 96.75
    # → same-session stop (declared daily-bar convention).
    assert t.entry_price_raw == 102.25
    assert t.stop_level_raw == 96.75
    assert t.conventions["tick_size"] == 0.25
    assert "stretch" not in t.conventions                 # NO Crabel Stretch anywhere
    assert "or_high" not in t.conventions                 # NO Opening Range anywhere


def test_raschke_tick_size_moves_levels_and_identity():
    res25 = run_b(_bars(), _b_cfg(tick_size=0.25))
    res50 = run_b(_bars(), _b_cfg(tick_size=0.50))
    assert res25.trades[0].entry_price_raw == 102.25
    assert res50.trades[0].entry_price_raw == 102.50
    assert res25.identity != res50.identity


def test_raschke_config_has_no_crabel_channels():
    """Structural isolation: no field through which Stretch, the Opening Range,
    ATR or volume could enter System B (Phase 9 §10)."""
    names = {f.name for f in dataclasses.fields(RaschkeNr7Config)}
    assert not any("stretch" in n for n in names)
    assert not any("opening" in n for n in names)
    assert not any("atr" in n.lower() for n in names)
    assert not any("volume" in n for n in names)
    assert "tick_size" in names


def test_crabel_configs_have_no_tick_offset_channel():
    """Structural isolation: no 1-tick mechanics can leak into Crabel systems."""
    for cfg in (CrabelOrbConfig, CrabelOpenStretchConfig):
        names = {f.name for f in dataclasses.fields(cfg)}
        assert not any("tick" in n for n in names)
    names = {f.name for f in dataclasses.fields(CrabelOrbConfig)}
    assert not any("atr" in n.lower() for n in names)
    assert not any("volume" in n for n in names)
    assert not any("sma" in n.lower() or "ema" in n.lower() for n in names)


# ── telemetry / zero-trade diagnostics ───────────────────────────────────────

def test_zero_trade_run_exposes_full_rejection_histogram():
    """Flat ranges under STRICT_LESS are pure tie cases → every day is
    tie_rejected (or insufficient_history in the warmup); the run must end
    with zero trades AND the complete machine-readable histogram."""
    bars = [_bar(f"2026-02-{i+1:02d}", 100, 102, 92, 101) for i in range(13)]
    res = run_a2(bars, _a2_cfg(nr7_tie_policy=TiePolicy.STRICT_LESS))
    assert res.zero_trade
    summary = res.to_summary()
    assert summary["zero_trade"] is True
    assert summary["rejection_histogram"]["tie_rejected"] == 6   # days t=6..11
    assert summary["rejection_histogram"]["insufficient_history"] == 6  # t=0..5


def test_tie_policy_min_inclusive_produces_setups_where_strict_rejects():
    bars = [_bar(f"2026-02-{i+1:02d}", 100, 102, 92, 101) for i in range(13)]
    strict = run_a2(bars, _a2_cfg(nr7_tie_policy=TiePolicy.STRICT_LESS))
    inclusive = run_a2(bars, _a2_cfg(nr7_tie_policy=TiePolicy.MIN_INCLUSIVE))
    assert strict.zero_trade
    assert not inclusive.zero_trade          # same data, opposite tie convention


def test_insufficient_history_is_a_recorded_rejection():
    bars = _bars()[:9]                        # shorter than any NR7/Stretch window
    res = run_a2(bars, _a2_cfg())
    assert res.zero_trade
    assert res.histogram()["insufficient_history"] >= 1


def test_capital_unavailable_is_a_recorded_rejection():
    res = run_a2(_bars(), _a2_cfg(capital=50.0, quantity=1.0))
    assert res.zero_trade
    assert res.histogram()["capital_unavailable"] == 1
