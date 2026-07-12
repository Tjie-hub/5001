from research.regime.config import load_config, config_hash


def test_defaults_match_pre_registered_constants():
    c = load_config()
    assert c.taxonomy_version == 1
    assert c.cell["min_n"] == 100          # = gatekeeper min_n_cell
    assert c.conditioning_bar["min_gap_pct"] == 0.50
    assert c.transitions["k_bars"] == 5
    assert c.seed == 20260711


def test_config_hash_is_deterministic_and_path_independent():
    c1 = load_config()
    c2 = load_config()
    assert config_hash(c1) == config_hash(c2)
    c2.source_path = "/somewhere/else.yaml"
    assert config_hash(c1) == config_hash(c2)   # provenance excluded
