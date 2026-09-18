"""Phase 9 tests — historical rule identity (rule_identity v2).

Every material convention must move the hash (Phase 9 §4/§E): the legacy
identity hashed only (name, gates) and could not see entry timing, tie
policy, gap policy, data basis, session, tick size, exit or OR duration.
"""
import pytest

from engine.historical.base import (BreakevenPolicy, ExitConvention, ExitKind,
                                    ProtectiveStopMode, SessionDefinition)
from engine.historical.crabel_open_stretch import CrabelOpenStretchConfig
from engine.historical.crabel_orb import CrabelOrbConfig
from engine.historical.kernel import AmbiguityPolicy, GapPolicy
from engine.historical.nr7 import TiePolicy
from engine.historical.raschke_id_nr4 import RaschkeIdNr4Config
from engine.historical.raschke_nr7 import RaschkeNr7Config
from engine.rule_identity import (HISTORICAL_IDENTITY_VERSION,
                                  historical_rule_id)


def _cfg(**kw):
    d = dict(nr7_tie_policy=TiePolicy.STRICT_LESS,
             opening_range_seconds=30,
             session=SessionDefinition("09:00:00"),
             gap_policy=GapPolicy.FILL_AT_OPEN,
             ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
             exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
             breakeven_move=BreakevenPolicy.NONE,
             protective_stop_mode=ProtectiveStopMode.ENABLED)
    d.update(kw)
    return CrabelOrbConfig(**d)


def test_identity_is_stable_and_versioned():
    m = _cfg().identity_material()
    assert historical_rule_id(m) == historical_rule_id(dict(m))
    assert historical_rule_id(m).startswith("hid:")


def test_setup_tie_policy_changes_identity():
    m = _cfg().identity_material()
    m2 = dict(m, setup_tie_policy=TiePolicy.MIN_INCLUSIVE.value)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_opening_range_duration_changes_identity():
    m = _cfg().identity_material()
    m2 = dict(m, opening_range_seconds=900)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_session_definition_changes_identity():
    m = _cfg().identity_material()
    m2 = dict(m, session_definition=("09:30:00", None))
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_gap_policy_changes_identity():
    m = _cfg().identity_material()
    m2 = dict(m, gap_policy=GapPolicy.CANCEL.value)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_ambiguity_policy_changes_identity():
    m = _cfg().identity_material()
    m2 = dict(m, ambiguity_policy=AmbiguityPolicy.CANCEL_BOTH.value)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_exit_mechanism_changes_identity():
    m = _cfg().identity_material()
    m2 = dict(m, exit_mechanism=("moc_after_n_sessions", 3, None))
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_breakeven_policy_changes_identity():
    m = _cfg().identity_material()
    m2 = dict(m, breakeven_move=BreakevenPolicy.AFTER_ENTRY_SESSION)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_stretch_lookback_changes_identity():
    m = _cfg().identity_material()
    m2 = dict(m, stretch_lookback=5)
    assert historical_rule_id(m2) != historical_rule_id(m)


def test_entry_mechanism_and_timing_change_identity():
    m = _cfg().identity_material()
    assert historical_rule_id(dict(m, entry_mechanism="x")) != historical_rule_id(m)
    assert historical_rule_id(dict(m, entry_timing="same_session")) != historical_rule_id(m)


def test_data_basis_and_tick_size_change_identity():
    m = _cfg().identity_material()
    assert historical_rule_id(dict(m, data_basis="adjusted")) != historical_rule_id(m)
    assert historical_rule_id(dict(m, tick_size=0.25)) != historical_rule_id(m)


def test_incomplete_material_is_rejected():
    m = _cfg().identity_material()
    del m["setup_tie_policy"]
    with pytest.raises(ValueError, match="incomplete"):
        historical_rule_id(m)


def test_the_four_systems_have_mutually_distinct_identities():
    a = _cfg().identity_material()
    a2 = CrabelOpenStretchConfig(
        nr7_tie_policy=TiePolicy.STRICT_LESS,
        session=SessionDefinition("09:00:00"),
        gap_policy=GapPolicy.FILL_AT_OPEN,
        ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
        breakeven_move=BreakevenPolicy.NONE,
        protective_stop_mode=ProtectiveStopMode.ENABLED).identity_material()
    b = RaschkeNr7Config(
        nr7_tie_policy=TiePolicy.STRICT_LESS, tick_size=0.25,
        session=SessionDefinition("09:00:00"),
        gap_policy=GapPolicy.FILL_AT_OPEN,
        ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 0),
    ).identity_material()
    b2 = RaschkeIdNr4Config(
        tick_size=0.25,
        session=SessionDefinition("09:00:00"),
        gap_policy=GapPolicy.FILL_AT_OPEN,
        ambiguity_policy=AmbiguityPolicy.RESOLVE_INTRADAY,
        exit_convention=ExitConvention(
            ExitKind.MOC_IF_UNPROFITABLE_AFTER_N_SESSIONS,
            profit_check_sessions=2)).identity_material()
    ids = {historical_rule_id(x) for x in (a, a2, b, b2)}
    assert len(ids) == 4


def test_reversal_policy_changes_identity():
    """A stop that reverses is a different rule from a stop that only closes."""
    m = _cfg().identity_material()
    assert historical_rule_id(dict(m, reversal_policy="entry_day_only")) \
        != historical_rule_id(m)


def test_protective_stop_mode_changes_identity():
    """Crabel's Ch. 1 trading rule and his no-stop test protocol are different
    rules at identical levels."""
    m = _cfg().identity_material()
    assert historical_rule_id(
        dict(m, protective_stop_mode=ProtectiveStopMode.NONE_TEST_PROTOCOL)) \
        != historical_rule_id(m)


def test_identity_version_is_part_of_the_hash():
    m = _cfg().identity_material()
    assert HISTORICAL_IDENTITY_VERSION == "hist-identity-v2"
    assert historical_rule_id(m) != historical_rule_id(
        dict(m, identity_version="hist-identity-v1"))
