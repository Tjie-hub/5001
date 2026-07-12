"""Canonical regime taxonomy (spec §5).

Primary partition = the 3-class per-ticker entry regime (mutually exclusive,
always in the multiplicity family). vol/liq are ORTHOGONAL declarable axes that
sub-partition a regime cell and only enter a strategy's family when declared.
"""
from __future__ import annotations

TAXONOMY_VERSION = 1

PRIMARY_REGIMES = ("BULL", "BEAR", "SIDEWAYS")
DECLARABLE_AXES = ("vol", "liq")
AXIS_TIERS = {
    "vol": ("HIGH_VOL", "LOW_VOL"),
    "liq": ("HIGH_LIQ", "LOW_LIQ"),
}


def subcell_label(regime: str, tier: str) -> str:
    """Compose a hierarchical sub-cell key, e.g. ('BULL','HIGH_VOL') -> 'BULL::HIGH_VOL'."""
    return f"{regime}::{tier}"


def is_primary(label: str) -> bool:
    return label in PRIMARY_REGIMES


def is_declarable_axis(axis: str) -> bool:
    return axis in DECLARABLE_AXES
