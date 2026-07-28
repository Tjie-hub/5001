"""Phase E knowledge config: typed load of knowledge_config.yaml."""
from research.knowledge import config as cfg


def test_load_config_defaults():
    c = cfg.load_config()
    assert c.version == 1
    assert c.statuses == ["PROPOSED", "UNDER_TEST", "WATCHLIST",
                          "FORWARD_TESTING", "REJECTED", "VALIDATED"]
    assert c.orphan_scope == ["research_runs", "gate_decisions"]
    assert c.source_path.endswith("knowledge_config.yaml")
