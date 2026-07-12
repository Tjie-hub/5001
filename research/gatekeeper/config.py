"""Gate configuration (spec §8): typed load of gate_config.yaml + a deterministic,
order-independent config_hash so every decision pins the exact thresholds it used.

The config is pre-registration: the thresholds AND the multiplicity family are fixed
before a candidate is evaluated. Changing any value yields a new config_hash and a
new decision lineage — it is never a silent in-place edit.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field

import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "gate_config.yaml")


@dataclass
class GateConfig:
    version: int
    promotion_bar_pct: float
    min_n_overall: int
    min_n_cell: int
    ci: dict
    multiplicity: dict
    psr: dict
    deflated_sharpe: dict
    walk_forward: dict
    out_of_sample: dict
    forward_test_rule: dict
    seed: int
    source_path: str = field(default="", compare=False)


def load_config(path: str = None) -> GateConfig:
    """Load gate_config.yaml into a GateConfig. Defaults to the shipped config."""
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
    return GateConfig(
        version=raw["version"],
        promotion_bar_pct=raw["promotion_bar_pct"],
        min_n_overall=raw["min_n_overall"],
        min_n_cell=raw["min_n_cell"],
        ci=raw["ci"],
        multiplicity=raw["multiplicity"],
        psr=raw["psr"],
        deflated_sharpe=raw["deflated_sharpe"],
        walk_forward=raw["walk_forward"],
        out_of_sample=raw["out_of_sample"],
        forward_test_rule=raw["forward_test_rule"],
        seed=raw["seed"],
        source_path=path,
    )


def config_hash(config: GateConfig) -> str:
    """sha256 over the canonicalised config (sort_keys → order-independent).

    Excludes source_path (provenance, not a threshold)."""
    payload = asdict(config)
    payload.pop("source_path", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
