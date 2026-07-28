from research.regime.config import load_config, config_hash


def test_defaults_match_pre_registered_constants():
    c = load_config()
    assert c.taxonomy_version == 1
    assert c.cell["min_n"] == 100          # = gatekeeper min_n_cell
    assert c.conditioning_bar["min_gap_pct"] == 0.50
    assert c.transitions["k_bars"] == 5
    assert c.seed == 20260711


def test_taxonomy_version_matches_the_taxonomy_module():
    # taxonomy.py is the source of truth for the taxonomy lineage; the frozen
    # regime_config literal must track it (bumping one without the other = CI fail).
    from research.regime import taxonomy
    assert load_config().taxonomy_version == taxonomy.TAXONOMY_VERSION


def test_config_hash_is_deterministic_and_path_independent():
    c1 = load_config()
    c2 = load_config()
    assert config_hash(c1) == config_hash(c2)
    c2.source_path = "/somewhere/else.yaml"
    assert config_hash(c1) == config_hash(c2)   # provenance excluded
