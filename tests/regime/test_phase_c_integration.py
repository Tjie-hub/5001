from research.gatekeeper.config import load_config as load_gate_config
from research.gatekeeper.candidate import Candidate, build_ctx


def test_gate_config_v2_family_is_three_regimes_only():
    cfg = load_gate_config()
    assert cfg.version == 2
    assert cfg.multiplicity["family"]["regimes"] == ["BULL", "BEAR", "SIDEWAYS"]


def test_gate_config_family_is_the_taxonomy_primary_regimes():
    """Spec §9.1: taxonomy.PRIMARY_REGIMES is the canonical source for Phase C's
    pre-registered family. The frozen gate_config literal must equal it, so adding a
    primary regime to the taxonomy without updating the (hashed) config fails CI."""
    from research.regime.taxonomy import PRIMARY_REGIMES
    fam = load_gate_config().multiplicity["family"]["regimes"]
    assert fam == list(PRIMARY_REGIMES)


def _candidate(regime_cells, declared_labels):
    trades = [t for cell in regime_cells.values() for t in cell]
    meta = {"target_regime": "BULL", "declared_labels": declared_labels,
            "wf": {}, "oos": {}}
    return Candidate(strategy_fn="demo", trades=trades, regime_cells=regime_cells,
                     scan_family=[], meta=meta)


def test_no_declared_labels_family_is_config_only():
    cells = {"BULL": [{"raw_entry": 100, "raw_exit": 102}] * 5,
             "BEAR": [{"raw_entry": 100, "raw_exit": 99}] * 5}
    ctx = build_ctx(_candidate(cells, declared_labels=[]), load_gate_config())
    assert ctx["family_labels"] == ["BULL", "BEAR", "SIDEWAYS"]


def test_declared_label_widens_the_family():
    cells = {
        "BULL": [{"raw_entry": 100, "raw_exit": 102}] * 5,
        "BULL::HIGH_VOL": [{"raw_entry": 100, "raw_exit": 103}] * 3,
    }
    ctx = build_ctx(_candidate(cells, declared_labels=["BULL::HIGH_VOL"]),
                    load_gate_config())
    assert "BULL::HIGH_VOL" in ctx["family_labels"]
    # one p-value per label, aligned
    assert len(ctx["family_pvalues"]) == len(ctx["family_labels"])


def test_nr7_multiplicity_family_shrank_to_three_and_still_passes():
    """v1→v2: the empty vol/liq placeholders leave the family. NR7 already PASSED
    multiplicity at 7 labels; at 3 it must still PASS (fewer tests = not stricter).
    DSR n_trials is derived from non-empty scan cells, so it is unaffected."""
    from research.gatekeeper.stages import stage_multiplicity

    cfg = load_gate_config()
    assert cfg.multiplicity["family"]["regimes"] == ["BULL", "BEAR", "SIDEWAYS"]

    # NR7 BULL is the strongly-significant governing cell (p ~ 0); BEAR/SIDEWAYS weak.
    ctx = {
        "family_labels": ["BULL", "BEAR", "SIDEWAYS"],
        "family_pvalues": [0.0005, 0.40, 0.30],
        "governing_index": 0,
    }
    res = stage_multiplicity(ctx, cfg)
    assert res.verdict == "PASS"
