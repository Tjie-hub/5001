"""Phase C gatekeeper config (spec §8). Frozen defaults sourced from existing
constants; config_hash must be deterministic and order-independent so a decision's
config lineage is pinned."""
from research.gatekeeper import config as cfg


def test_load_default_config_has_frozen_values():
    c = cfg.load_config()
    assert c.version == 2                        # v2: hierarchical family (Phase D)
    # primary partition only; vol/liq are declarable sub-cells added per-strategy
    assert c.multiplicity["family"]["regimes"] == ["BULL", "BEAR", "SIDEWAYS"]
    assert c.promotion_bar_pct == 0.50          # = nr7_study THRESHOLDS.min_net_exp
    assert c.min_n_overall == 300               # = THRESHOLDS.t1_min_n
    assert c.min_n_cell == 100                  # = THRESHOLDS.t3_min_n
    assert c.seed == 20260711                   # = statistics.SEED
    assert c.forward_test_rule["min_n"] == 15   # = phase5_tracker.RULE
    assert c.forward_test_rule["go_exp"] == 0.50
    # pre-registered WF consistency bar = the engine scanner's strict 50% gate
    assert c.walk_forward["min_consistency_pct"] == 50


def test_config_hash_is_deterministic():
    c = cfg.load_config()
    assert cfg.config_hash(c) == cfg.config_hash(c)
    assert len(cfg.config_hash(c)) == 64        # sha256 hex


def test_config_hash_changes_when_a_threshold_changes():
    c1 = cfg.load_config()
    c2 = cfg.load_config()
    c2.psr = dict(c2.psr, min=0.99)
    assert cfg.config_hash(c1) != cfg.config_hash(c2)


def test_config_hash_independent_of_dict_key_order():
    c1 = cfg.load_config()
    c2 = cfg.load_config()
    # reversing the multiplicity dict's key order must not change the hash
    c2.multiplicity = dict(reversed(list(c2.multiplicity.items())))
    assert cfg.config_hash(c1) == cfg.config_hash(c2)
