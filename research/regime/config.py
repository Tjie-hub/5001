"""Regime config: typed load of regime_config.yaml + a deterministic, order-
independent config_hash so every profile pins the exact thresholds it used."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field

import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "regime_config.yaml")


@dataclass
class RegimeConfig:
    version: int
    taxonomy_version: int
    conditioning: dict
    cell: dict
    conditioning_bar: dict
    transitions: dict
    seed: int
    source_path: str = field(default="", compare=False)


def load_config(path: str = None) -> RegimeConfig:
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
    return RegimeConfig(
        version=raw["version"],
        taxonomy_version=raw["taxonomy_version"],
        conditioning=raw["conditioning"],
        cell=raw["cell"],
        conditioning_bar=raw["conditioning_bar"],
        transitions=raw["transitions"],
        seed=raw["seed"],
        source_path=path,
    )


def config_hash(config: RegimeConfig) -> str:
    payload = asdict(config)
    payload.pop("source_path", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
