"""Phase 8 Provenance Closure corrections — tests.

Source of truth: docs/audit/PHASE_8_PROVENANCE_CLOSURE_AUDIT_2026-09-03.md.

Each test below pins one correction the audit required. These are provenance
and rule-definition tests: none of them measures performance, and none may be
satisfied by changing a claim without changing the behavior it describes.
"""
import dataclasses

import pytest

from engine.historical.base import (BreakevenPolicy, ExitConvention, ExitKind,
                                    ProtectiveStopMode, ReversalPolicy,
                                    SessionDefinition)
from engine.historical.crabel_open_stretch import CrabelOpenStretchConfig
from engine.historical.crabel_open_stretch import run as run_a2
from engine.historical.crabel_orb import (RECOVERED_OPENING_RANGE_SECONDS,
                                          CrabelOrbConfig)
from engine.historical.crabel_orb import run as run_a
from engine.historical.data import OpeningRangeUnavailable
from engine.historical.id_nr4 import evaluate_id_nr4, is_inside_day
from engine.historical.kernel import AmbiguityPolicy, Bar, GapPolicy
from engine.historical.nr7 import (HISTORICAL_TIE_POLICIES, TiePolicy,
                                   is_historical_tie_policy)
from engine.historical.provenance import (HISTORICAL_SPECS,
                                          UNCONTROLLED_WITNESS,
                                          InvalidConfiguration,
                                          ProvenanceTier)
from engine.historical.raschke_id_nr4 import RaschkeIdNr4Config
from engine.historical.raschke_id_nr4 import run as run_idnr4
from engine.historical.stretch import StretchAnchor, stretch_at_setup
from engine.rule_identity import historical_rule_id


def _bar(date, o, h, l, c):
    return Bar(date=date, open=o, high=h, low=l, close=c)


def _nr7_bars():
    """Day 9 is an NR7 setup; day 10 executes. Stretch at t=9 is exactly 2.0."""
    bars = [_bar(f"2026-01-{i + 1:02d}", 100, 102, 92, 101) for i in range(9)]
    bars.append(_bar("2026-01-10", 100, 102, 97, 101))   # setup (NR7)
    bars.append(_bar("2026-01-11", 100, 110, 96, 105))   # execution
    bars.append(_bar("2026-01-12", 104, 106, 100, 104))
    bars.append(_bar("2026-01-13", 104, 107, 101, 103))
    return bars


def _orb_cfg(**kw):
    d = dict(opening_range_seconds=RECOVERED_OPENING_RANGE_SECONDS,
             session=SessionDefinition("09:00:00"),
             gap_policy=GapPolicy.FILL_AT_OPEN,
             ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
             exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 1),
             breakeven_move=BreakevenPolicy.NONE,
             protective_stop_mode=ProtectiveStopMode.ENABLED)
    d.update(kw)
    return CrabelOrbConfig(**d)


def _a2_cfg(**kw):
    d = dict(session=SessionDefinition("09:00:00"),
             gap_policy=GapPolicy.FILL_AT_OPEN,
             ambiguity_policy=AmbiguityPolicy.PREFER_LONG,
             exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 5),
             breakeven_move=BreakevenPolicy.NONE,
             protective_stop_mode=ProtectiveStopMode.ENABLED)
    d.update(kw)
    return CrabelOpenStretchConfig(**d)


# ── ID/NR4 fixtures (audit R-2: the Raschke rule set is an ID/NR4 rule set) ──

def _idnr4_bars(exec_bar, *tail):
    """Index 4 is an ID/NR4 setup; index 5 is the execution session.

    ranges: 20, 18, 16, 14, 6 → day 4's range is strictly narrower than each of
    the previous three, and day 4 is inside day 3 (104 < 107, 98 > 93).
    tick 1.0 → buy stop 105.0, sell stop 97.0.
    """
    return [
        _bar("2026-02-02", 100, 110, 90, 100),
        _bar("2026-02-03", 100, 109, 91, 100),
        _bar("2026-02-04", 100, 108, 92, 100),
        _bar("2026-02-05", 100, 107, 93, 100),
        _bar("2026-02-06", 100, 104, 98, 100),   # ID/NR4 setup
        exec_bar,
        *tail,
    ]


def _idnr4_cfg(**kw):
    d = dict(tick_size=1.0,
             session=SessionDefinition("09:00:00"),
             gap_policy=GapPolicy.FILL_AT_OPEN,
             ambiguity_policy=AmbiguityPolicy.PREFER_LONG,
             exit_convention=ExitConvention(
                 ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS,
                 profit_check_sessions=2))
    d.update(kw)
    return RaschkeIdNr4Config(**d)


# ═════ 1. System B provenance: no NR7 rule set exists in Street Smarts ══════

def test_raschke_nr7_is_not_tier_a():
    """Audit R-3: Street Smarts states no NR7 rule set; Tier A is unsupported."""
    p = HISTORICAL_SPECS["raschke_nr7.v1"].provenance
    assert p.tier is ProvenanceTier.TIER_T_TRANSFER
    assert p.tier is not ProvenanceTier.TIER_A_DIRECT


def test_raschke_nr7_declares_the_transfer_explicitly():
    p = HISTORICAL_SPECS["raschke_nr7.v1"].provenance
    joined = " ".join(p.adaptations).lower()
    assert p.adaptations, "a transfer must name what was transferred"
    assert "id/nr4" in joined and "nr7" in joined


def test_genuine_raschke_id_nr4_system_is_registered_tier_a():
    p = HISTORICAL_SPECS["raschke_id_nr4.v1"].provenance
    assert p.tier is ProvenanceTier.TIER_A_DIRECT


def test_transfer_tier_requires_declared_adaptations():
    from engine.historical.provenance import HistoricalProvenance
    with pytest.raises(InvalidConfiguration):
        HistoricalProvenance(
            tier=ProvenanceTier.TIER_T_TRANSFER, citations=("c",),
            historical_rules=("r",), engine_conventions=("e",), data_basis="b",
            entry_mechanism="m", exit_mechanism="x", session_definition="s",
            tick_size="t", tie_policy="tp", gap_policy="gp",
            unrecovered_items=("PRIMARY SOURCE NOT RECOVERED.",),
            witness=UNCONTROLLED_WITNESS, adaptations=())


# ═════ 2. Raschke stop-and-reverse ═════════════════════════════════════════

def test_id_nr4_setup_requires_both_inside_day_and_nr4():
    highs = [110, 109, 108, 107, 104]
    lows = [90, 91, 92, 93, 98]
    ranges = [h - l for h, l in zip(highs, lows)]
    assert is_inside_day(highs, lows, 4) is True
    assert evaluate_id_nr4(highs, lows, ranges, 4, TiePolicy.STRICT_LESS) == "ok"
    # Same narrow range, but not inside the previous day → not a setup.
    highs2, lows2 = list(highs), list(lows)
    highs2[4], lows2[4] = 112, 106
    ranges2 = [h - l for h, l in zip(highs2, lows2)]
    assert evaluate_id_nr4(highs2, lows2, ranges2, 4,
                           TiePolicy.STRICT_LESS) == "not_inside_day"


def test_stopped_long_reverses_to_short_on_the_entry_day():
    bars = _idnr4_bars(_bar("2026-02-09", 104, 106, 96, 96.5),
                       _bar("2026-02-10", 96, 98, 94, 95))
    res = run_idnr4(bars, _idnr4_cfg(reversal_policy=ReversalPolicy.ENTRY_DAY_ONLY))
    assert len(res.trades) == 2
    long_leg, short_leg = res.trades
    assert long_leg.side == "LONG" and long_leg.exit_reason == "stopped_and_reversed"
    assert short_leg.side == "SHORT"
    assert short_leg.entry_date == "2026-02-09"
    assert short_leg.entry_price_raw == pytest.approx(97.0)


def test_no_reversal_when_the_stop_fires_after_the_entry_day():
    """The reversal order exists on the entry day only and expires at its close."""
    bars = _idnr4_bars(_bar("2026-02-09", 104, 106, 100, 105),   # entry, no stop
                       _bar("2026-02-10", 104, 105, 95, 96),     # stop fires here
                       _bar("2026-02-11", 96, 97, 94, 95))
    res = run_idnr4(bars, _idnr4_cfg(reversal_policy=ReversalPolicy.ENTRY_DAY_ONLY))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "protective_stop"
    assert res.trades[0].exit_date == "2026-02-10"


def test_one_tick_short_entry_is_the_mirror_of_the_long():
    """Ch. 19 rule 2 is symmetric: a sell-stop one tick BELOW the setup bar."""
    bars = _idnr4_bars(_bar("2026-02-09", 100, 104.5, 96, 96.5),
                       _bar("2026-02-10", 96, 98, 94, 95))
    res = run_idnr4(bars, _idnr4_cfg())
    trade = res.trades[0]
    assert trade.side == "SHORT"
    assert trade.entry_price_raw == pytest.approx(97.0)    # setup low 98 - 1 tick
    assert trade.stop_level_raw == pytest.approx(105.0)    # setup high 104 + 1 tick


def test_stopped_short_reverses_to_long_on_the_entry_day():
    """(The rule is reversed if initially filled on the short side.)"""
    bars = _idnr4_bars(_bar("2026-02-09", 100, 106, 96, 105.5),
                       _bar("2026-02-10", 105, 107, 104, 106))
    res = run_idnr4(bars, _idnr4_cfg(
        ambiguity_policy=AmbiguityPolicy.PREFER_SHORT,
        reversal_policy=ReversalPolicy.ENTRY_DAY_ONLY))
    assert len(res.trades) == 2
    short_leg, long_leg = res.trades
    assert short_leg.side == "SHORT" and short_leg.exit_reason == "stopped_and_reversed"
    assert long_leg.side == "LONG"
    assert long_leg.entry_date == "2026-02-09"
    assert long_leg.entry_price_raw == pytest.approx(105.0)


def test_reversal_records_its_entry_day_only_expiry_convention():
    bars = _idnr4_bars(_bar("2026-02-09", 104, 106, 96, 96.5),
                       _bar("2026-02-10", 96, 98, 94, 95))
    res = run_idnr4(bars, _idnr4_cfg(reversal_policy=ReversalPolicy.ENTRY_DAY_ONLY))
    conv = res.trades[1].conventions
    assert conv["reversal_policy"] == ReversalPolicy.ENTRY_DAY_ONLY
    assert conv["reversal_expiry"] == "entry_session_close"


def test_reversal_is_absent_when_policy_is_none():
    bars = _idnr4_bars(_bar("2026-02-09", 104, 106, 96, 96.5),
                       _bar("2026-02-10", 96, 98, 94, 95))
    res = run_idnr4(bars, _idnr4_cfg(reversal_policy=ReversalPolicy.NONE))
    assert len(res.trades) == 1
    assert res.trades[0].exit_reason == "protective_stop"


def test_crabel_systems_carry_no_reversal_mechanism():
    """Audit: the reversal is Raschke's; it must not leak into Crabel."""
    for cfg_cls in (CrabelOrbConfig, CrabelOpenStretchConfig):
        names = {f.name for f in dataclasses.fields(cfg_cls)}
        assert "reversal_policy" not in names


# ═════ 3. Raschke two-day MOC exit ═════════════════════════════════════════

def test_two_day_moc_exit_closes_an_unprofitable_position():
    bars = _idnr4_bars(_bar("2026-02-09", 104, 106, 100, 105),   # long @ 105
                       _bar("2026-02-10", 104, 106, 101, 102),   # session 2: unprofitable
                       _bar("2026-02-11", 102, 103, 99, 100))
    res = run_idnr4(bars, _idnr4_cfg())
    trade = res.trades[0]
    assert trade.exit_reason == "moc_unprofitable_time_stop"
    assert trade.exit_date == "2026-02-10"
    assert trade.exit_price_raw == pytest.approx(102.0)


def test_two_day_moc_exit_leaves_a_profitable_position_open():
    bars = _idnr4_bars(_bar("2026-02-09", 104, 106, 100, 105),   # long @ 105
                       _bar("2026-02-10", 106, 112, 105.5, 111),  # session 2: profitable
                       _bar("2026-02-11", 111, 112, 110, 111))
    res = run_idnr4(bars, _idnr4_cfg())
    assert res.trades[0].exit_date != "2026-02-10"


def test_two_day_moc_exit_is_a_recovered_historical_rule():
    p = HISTORICAL_SPECS["raschke_id_nr4.v1"].provenance
    joined = " ".join(p.historical_rules).lower()
    assert "not profitable within two days" in joined
    assert not any("deterministic mechanical exit" in u.lower()
                   for u in p.unrecovered_items)


# ═════ 4. Crabel opening range = first thirty seconds ══════════════════════

def test_recovered_opening_range_is_thirty_seconds():
    assert RECOVERED_OPENING_RANGE_SECONDS == 30


def test_orb_config_expresses_the_opening_range_in_seconds():
    names = {f.name for f in dataclasses.fields(CrabelOrbConfig)}
    assert "opening_range_seconds" in names
    assert "opening_range_minutes" not in names


def test_orb_provenance_states_the_thirty_second_opening_range():
    p = HISTORICAL_SPECS["crabel_orb.v1"].provenance
    joined = " ".join(p.historical_rules).lower()
    assert "thirty seconds" in joined or "30 seconds" in joined
    assert not any("opening-range duration" in u.lower()
                   for u in p.unrecovered_items)


def test_orb_source_carries_no_unsourced_minute_claim():
    import engine.historical.crabel_orb as mod
    assert "5/10/15" not in (mod.__doc__ or "")


def test_opening_range_seconds_changes_identity():
    m = _orb_cfg().identity_material()
    assert historical_rule_id(dict(m, opening_range_seconds=300)) \
        != historical_rule_id(m)


def test_insufficient_intraday_resolution_is_rejected_not_approximated():
    def provider(date):
        return OpeningRangeUnavailable(
            reason="insufficient_intraday_resolution",
            details={"opening_range_seconds": 30, "source_resolution_seconds": 60})

    res = run_a(_nr7_bars(), _orb_cfg(), provider)
    assert res.n_trades == 0
    assert res.histogram().get("insufficient_intraday_resolution") == 1


def test_tick_opening_range_provider_reports_resolution_shortfall():
    from engine.historical.data import tick_opening_range_provider
    provider = tick_opening_range_provider(
        db_path=":memory:", ticker="AAAA", session_start="09:00:00",
        opening_range_seconds=30, source_resolution_seconds=60)
    out = provider("2026-01-11")
    assert isinstance(out, OpeningRangeUnavailable)
    assert out.reason == "insufficient_intraday_resolution"


# ═════ 5. Crabel exit model: N=0 and the no-stop test protocol ═════════════

def test_moc_hold_sessions_zero_exits_on_the_entry_session_close():
    res = run_a2(_nr7_bars(), _a2_cfg(
        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
        protective_stop_mode=ProtectiveStopMode.NONE_TEST_PROTOCOL))
    trade = res.trades[0]
    assert trade.entry_date == "2026-01-11"
    assert trade.exit_date == "2026-01-11"
    assert trade.exit_price_raw == pytest.approx(105.0)   # entry-session close
    assert trade.exit_reason == "moc_convention"


def test_no_stop_protocol_installs_no_protective_stop():
    res = run_a2(_nr7_bars(), _a2_cfg(
        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
        protective_stop_mode=ProtectiveStopMode.NONE_TEST_PROTOCOL))
    assert res.trades[0].conventions["protective_stop_mode"] == \
        ProtectiveStopMode.NONE_TEST_PROTOCOL
    assert res.trades[0].stop_level_raw is None


def test_enabled_stop_mode_still_stops_the_same_position_out():
    res = run_a2(_nr7_bars(), _a2_cfg(
        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
        protective_stop_mode=ProtectiveStopMode.ENABLED))
    assert res.trades[0].exit_reason == "protective_stop"


def test_protective_stop_mode_changes_identity():
    m = _a2_cfg().identity_material()
    m2 = dict(m, protective_stop_mode=ProtectiveStopMode.NONE_TEST_PROTOCOL)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_discretionary_guidance_is_kept_out_of_historical_rules():
    p = HISTORICAL_SPECS["crabel_orb.v1"].provenance
    rules = " ".join(p.historical_rules).lower()
    assert "two to three day run" not in rules
    assert any("two to three day run" in g.lower()
               for g in p.discretionary_guidance)


# ═════ 6. Stretch anchor is an engine convention ═══════════════════════════

def test_stretch_anchor_is_an_explicit_convention_in_identity():
    m = _orb_cfg().identity_material()
    assert m["stretch_anchor"] == StretchAnchor.INCLUDE_SETUP_DAY.value
    m2 = dict(m, stretch_anchor=StretchAnchor.EXCLUDE_SETUP_DAY.value)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_stretch_anchor_is_not_claimed_as_recovered():
    p = HISTORICAL_SPECS["crabel_orb.v1"].provenance
    assert not any("t-9" in r for r in p.historical_rules)
    assert any("anchor" in c.lower() for c in p.engine_conventions)


def test_stretch_formula_is_unchanged_and_both_anchors_shift_the_window():
    opens = [100.0] * 12
    highs = [102.0] * 11 + [110.0]
    lows = [98.0] * 11 + [90.0]
    inc = stretch_at_setup(opens, highs, lows, 11, 10,
                           StretchAnchor.INCLUDE_SETUP_DAY)
    exc = stretch_at_setup(opens, highs, lows, 11, 10,
                           StretchAnchor.EXCLUDE_SETUP_DAY)
    assert exc == pytest.approx(2.0)
    # day 11 contributes min(|100-110|, |100-90|) = 10.0
    assert inc == pytest.approx((2.0 * 9 + 10.0) / 10)


# ═════ 7. A2 is a labelled Tier-B synthesis ════════════════════════════════

def test_a2_cannot_claim_tier_a():
    p = HISTORICAL_SPECS["crabel_open_stretch.v1"].provenance
    assert p.tier is ProvenanceTier.TIER_B_CONTEMPORARY_SECONDARY


def test_a2_open_plus_stretch_is_an_adaptation_not_a_historical_rule():
    p = HISTORICAL_SPECS["crabel_open_stretch.v1"].provenance
    assert not any("open + stretch" in r.lower() for r in p.historical_rules)
    assert any("open + stretch" in a.lower() for a in p.adaptations)


def test_a2_citation_no_longer_claims_the_text_was_unavailable():
    p = HISTORICAL_SPECS["crabel_open_stretch.v1"].provenance
    joined = " ".join(p.citations).lower()
    assert "full text not recovered" not in joined
    assert not any("full primary text of the 1990 book" in u.lower()
                   for u in p.unrecovered_items)


# ═════ 8. Tick size: rule vs instrument parameter ══════════════════════════

def test_one_tick_offset_is_a_historical_rule_not_an_unrecovered_item():
    p = HISTORICAL_SPECS["raschke_id_nr4.v1"].provenance
    assert any("one tick" in r.lower() for r in p.historical_rules)
    assert not any("tick-size definition" in u.lower()
                   for u in p.unrecovered_items)


def test_tick_size_is_declared_an_instrument_parameter():
    p = HISTORICAL_SPECS["raschke_id_nr4.v1"].provenance
    assert "instrument" in p.tick_size.lower()
    assert "PRIMARY SOURCE NOT RECOVERED." not in p.tick_size


def test_tick_size_changes_identity():
    m = _idnr4_cfg().identity_material()
    assert historical_rule_id(dict(m, tick_size=0.25)) != historical_rule_id(m)


# ═════ 9. Tie policy: strict inequality is the historical reading ══════════

def test_strict_less_is_the_only_historical_tie_policy():
    assert HISTORICAL_TIE_POLICIES == frozenset({TiePolicy.STRICT_LESS})
    assert is_historical_tie_policy(TiePolicy.STRICT_LESS) is True
    assert is_historical_tie_policy(TiePolicy.MIN_INCLUSIVE) is False


def test_historical_systems_default_to_strict_inequality():
    assert _orb_cfg().nr7_tie_policy is TiePolicy.STRICT_LESS
    assert _a2_cfg().nr7_tie_policy is TiePolicy.STRICT_LESS
    assert _idnr4_cfg().setup_tie_policy is TiePolicy.STRICT_LESS


def test_tie_policy_modes_are_distinguished_in_identity():
    m = _orb_cfg().identity_material()
    m2 = dict(m, setup_tie_policy=TiePolicy.MIN_INCLUSIVE.value)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_min_inclusive_is_labelled_ahistorical():
    doc = (TiePolicy.MIN_INCLUSIVE.__doc__ or "").lower()
    assert "ahistorical" in doc or "legacy" in doc


# ═════ 10. Provenance witness caveat ═══════════════════════════════════════

def test_every_historical_spec_records_the_witness_caveat():
    assert HISTORICAL_SPECS
    for name, spec in HISTORICAL_SPECS.items():
        assert spec.provenance.witness, name
        assert "uncontrolled" in spec.provenance.witness.lower(), name


def test_witness_is_mandatory():
    from engine.historical.provenance import HistoricalProvenance
    with pytest.raises(InvalidConfiguration):
        HistoricalProvenance(
            tier=ProvenanceTier.TIER_A_DIRECT, citations=("c",),
            historical_rules=("r",), engine_conventions=("e",), data_basis="b",
            entry_mechanism="m", exit_mechanism="x", session_definition="s",
            tick_size="t", tie_policy="tp", gap_policy="gp",
            unrecovered_items=("PRIMARY SOURCE NOT RECOVERED.",), witness="")


# ═════ 11. Source references ═══════════════════════════════════════════════

def test_street_smarts_chapters_are_corrected():
    for name in ("raschke_id_nr4.v1", "raschke_nr7.v1"):
        joined = " ".join(HISTORICAL_SPECS[name].provenance.citations)
        assert "Chapter 19" in joined and "Chapter 20" in joined, name
        assert "Chapter 16" not in joined, name
        assert "Chapters 16" not in joined, name


def test_crabel_systems_cite_the_recovered_1990_book():
    for name in ("crabel_orb.v1", "crabel_open_stretch.v1"):
        joined = " ".join(HISTORICAL_SPECS[name].provenance.citations)
        assert "1990" in joined, name
