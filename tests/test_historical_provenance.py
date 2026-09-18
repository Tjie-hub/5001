"""Phase 9 tests — provenance-required registration and legacy quarantine.

Phase 8 §1/§3 + Phase 9 §3: legacy strategies are frozen with an explicit
marker; historical systems cannot register without complete provenance
metadata; Tier-E material can never back a historical system.
"""
import pytest

from engine.historical.provenance import (HISTORICAL_SPECS,
                                          InvalidConfiguration,
                                          ProvenanceTier,
                                          register_historical_spec)


LEGACY_NAMES = {"NR7 Breakout", "ORB"}

HISTORICAL_NAMES = {"crabel_orb.v1", "crabel_open_stretch.v1",
                    "raschke_id_nr4.v1", "raschke_nr7.v1"}


def test_import_registers_exactly_the_historical_systems():
    import engine.historical  # noqa: F401
    assert HISTORICAL_NAMES == set(HISTORICAL_SPECS)


def test_every_historical_spec_carries_complete_provenance():
    import engine.historical  # noqa: F401
    for name, spec in HISTORICAL_SPECS.items():
        p = spec.provenance
        assert p is not None, name
        assert p.tier in (ProvenanceTier.TIER_A_DIRECT,
                          ProvenanceTier.TIER_B_CONTEMPORARY_SECONDARY,
                          ProvenanceTier.TIER_T_TRANSFER)
        assert p.citations and p.historical_rules and p.engine_conventions
        assert p.data_basis and p.entry_mechanism and p.exit_mechanism
        assert p.session_definition and p.tick_size
        assert p.tie_policy and p.gap_policy
        assert p.witness
        assert not spec.legacy


def test_every_provenance_records_unrecovered_items_with_exact_phrase():
    import engine.historical  # noqa: F401
    for name, spec in HISTORICAL_SPECS.items():
        assert any("PRIMARY SOURCE NOT RECOVERED." in u
                   for u in spec.provenance.unrecovered_items), name


def test_transfer_exit_is_declared_source_insufficient():
    """The two-day MOC rule is an ID/NR4 rule; the NR7 transfer cannot claim it,
    so its deterministic exit stays source-insufficient."""
    spec = HISTORICAL_SPECS["raschke_nr7.v1"]
    joined = " ".join(spec.provenance.unrecovered_items)
    assert "Deterministic exit for this transfer: PRIMARY SOURCE NOT RECOVERED." in joined


def test_genuine_raschke_exit_is_a_recovered_rule():
    """...while the genuine Ch. 19 system states one (rule 5)."""
    spec = HISTORICAL_SPECS["raschke_id_nr4.v1"]
    joined = " ".join(spec.provenance.historical_rules).lower()
    assert "not profitable within two days" in joined


def test_tier_e_can_never_back_a_historical_system():
    from engine.historical.provenance import HistoricalProvenance
    with pytest.raises(InvalidConfiguration):
        HistoricalProvenance(
            tier=ProvenanceTier.TIER_E_UNSUPPORTED,
            citations=("some forex blog",), historical_rules=("x",),
            engine_conventions=("y",), data_basis="stored_raw",
            entry_mechanism="e", exit_mechanism="x",
            session_definition="s", tick_size="t", tie_policy="tp",
            gap_policy="gp", unrecovered_items=("PRIMARY SOURCE NOT RECOVERED.",),
            witness="uncontrolled scan")


def test_registration_without_provenance_is_refused():
    from engine.strategy_specs import StrategySpec
    with pytest.raises(InvalidConfiguration):
        register_historical_spec(StrategySpec("bogus.v1", "historical", False))


def test_registration_with_incomplete_provenance_is_refused():
    """Incomplete provenance cannot even be CONSTRUCTED — the frozen dataclass
    validates field completeness at __post_init__ (Phase 9 §3)."""
    from engine.historical.provenance import HistoricalProvenance
    with pytest.raises(InvalidConfiguration):
        HistoricalProvenance(
            tier=ProvenanceTier.TIER_A_DIRECT, citations=(),   # empty: incomplete
            historical_rules=("r",), engine_conventions=("e",),
            data_basis="stored_raw", entry_mechanism="em", exit_mechanism="xm",
            session_definition="s", tick_size="t", tie_policy="tp",
            gap_policy="gp", unrecovered_items=("PRIMARY SOURCE NOT RECOVERED.",),
            witness="uncontrolled scan")
    # ...and a spec whose provenance is None is refused at registration:
    from engine.strategy_specs import StrategySpec
    with pytest.raises(InvalidConfiguration):
        register_historical_spec(StrategySpec("bogus.v2", "historical", False,
                                              provenance=None))


def test_legacy_specs_are_marked_and_frozen():
    from engine.strategy_specs import SPECS
    assert LEGACY_NAMES <= set(SPECS)
    assert SPECS["NR7 Breakout"].legacy is True
    assert SPECS["ORB"].legacy is True
    for name, spec in SPECS.items():
        if name not in LEGACY_NAMES:
            assert spec.legacy is False, name


def test_legacy_spec_cannot_register_as_historical():
    from engine.strategy_specs import SPECS
    with pytest.raises(ValueError, match="legacy"):
        register_historical_spec(SPECS["NR7 Breakout"])
    with pytest.raises(ValueError, match="legacy"):
        register_historical_spec(SPECS["ORB"])


def test_legacy_spec_names_are_frozen():
    """Quarantine guard: the legacy keys must keep their exact DB-facing names
    (walk-forward scores, UI dropdown and paper_trades rows reference them)."""
    from engine.strategy_specs import SPECS
    assert LEGACY_NAMES <= set(SPECS)
    assert SPECS["NR7 Breakout"].family == "breakout"
    assert SPECS["ORB"].family == "breakout"
