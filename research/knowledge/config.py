"""Knowledge-base configuration (Phase E, spec §7): typed load of
knowledge_config.yaml. Pre-registered — the status vocabulary and orphan scope
are fixed before use; changing them bumps `version`."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "knowledge_config.yaml")


@dataclass
class KnowledgeConfig:
    version: int
    statuses: list
    orphan_scope: list
    source_path: str = field(default="", compare=False)


def load_config(path: str = None) -> KnowledgeConfig:
    """Load knowledge_config.yaml into a KnowledgeConfig. Defaults to the shipped file."""
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return KnowledgeConfig(
        version=int(raw["version"]),
        statuses=list(raw["statuses"]),
        orphan_scope=list(raw["orphan_scope"]),
        source_path=path)
