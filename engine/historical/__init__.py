"""engine/historical — Phase 8 clean-room historical systems.

Quarantine boundary: NOTHING in this package imports engine.strategies
(strategy_nr7_breakout / strategy_orb) or any modern ATR/volume logic. The
legacy live strategies remain frozen in engine/strategies.py under legacy
provenance markers in engine/strategy_specs.SPECS.

Systems (source-of-truth: docs/audit/PHASE_8_PROVENANCE_CLOSURE_AUDIT_2026-09-03.md):
    crabel_orb.v1          — Crabel 1990 ORB, OR High/Low ± Stretch      [Tier A]
    crabel_open_stretch.v1 — Open ± Stretch; a declared SYNTHESIS of two
                             separate primary constructions               [Tier B]
    raschke_id_nr4.v1      — Street Smarts Ch. 19/20 ID/NR4, one-tick
                             entry, stop-and-reverse, two-day MOC         [Tier A]
    raschke_nr7.v1         — Crabel's NR7 setup carrying Raschke's ID/NR4
                             mechanics; a declared TRANSFER                [Tier T]

Importing this package registers all four in
engine.historical.provenance.HISTORICAL_SPECS.
"""
from engine.historical import (crabel_open_stretch, crabel_orb,
                               raschke_id_nr4, raschke_nr7)
from engine.historical.provenance import (HISTORICAL_SPECS,
                                          InvalidConfiguration,
                                          ProvenanceTier,
                                          register_historical_spec)

__all__ = [
    "crabel_orb", "crabel_open_stretch", "raschke_id_nr4", "raschke_nr7",
    "HISTORICAL_SPECS", "InvalidConfiguration", "ProvenanceTier",
    "register_historical_spec",
]
