"""engine/historical/provenance.py — provenance model for Phase 8 historical systems.

Phase 9 mandate: a historical strategy must not be registerable without complete
provenance metadata. Every field below is mandatory; a spec that cannot state its
source tier, citations, recovered rules, and engine conventions is rejected at
registration, not at research time.

DISCIPLINE (Phase 8 handover §13, §16):
  - Where the primary material does not settle a point, the exact phrase
    "PRIMARY SOURCE NOT RECOVERED." is recorded in `unrecovered_items` and the
    corresponding engine behavior is declared in `engine_conventions` — never
    presented as a historical rule.
  - No claim may be upgraded beyond the recovered evidence.

PROVENANCE CLOSURE AUDIT 2026-09-03 (docs/audit/PHASE_8_PROVENANCE_CLOSURE_AUDIT_2026-09-03.md)
added three separations that the original model could not express, and each one
existed because a real defect had already slipped through:

  `adaptations`             — a rule the engine runs that NO primary source
                              states, built by combining or transferring
                              primary material. `crabel_open_stretch.v1`
                              (Open ± Stretch) and `raschke_nr7.v1` (Raschke's
                              ID/NR4 mechanics moved onto Crabel's NR7 setup)
                              were both filed as recovered historical rules.
                              A Tier B or Tier T spec MUST declare them.
  `discretionary_guidance`  — recovered author language that is advice, not a
                              mechanical rule ("a two to three day run"). It is
                              primary text, so it does not belong in
                              `unrecovered_items`; it is not executable, so it
                              does not belong in `historical_rules`.
  `witness`                 — HOW the primary text was read. Both books were
                              recovered from uncontrolled third-party scans.
                              The rule is not downgraded for that, but the
                              record must not imply publisher-controlled access.

Pure module: no pandas, no DB, no imports from engine.* (strategy_specs imports
the HistoricalProvenance type under TYPE_CHECKING only, so this module must stay
dependency-free to avoid an import cycle).
"""
from dataclasses import dataclass, fields
from enum import Enum
from typing import Optional


class ProvenanceTier(str, Enum):
    """Phase 8 handover §11 hierarchy, extended by the 2026-09-03 audit."""
    TIER_A_DIRECT = "tier_a_direct"                      # rule stated in recovered primary text
    TIER_B_CONTEMPORARY_SECONDARY = "tier_b_secondary"   # synthesis over primary material
    TIER_T_TRANSFER = "tier_t_transfer"                  # primary mechanics moved onto a setup
                                                         # the source does not pair them with
    SOURCE_INSUFFICIENT = "source_insufficient"
    TIER_E_UNSUPPORTED = "tier_e_unsupported"            # must never back a historical system


#: Standing caveat for every rule recovered during the 2026-09-03 closure audit.
#: Crabel (1990) and Raschke & Connors (1995) were both read from third-party
#: scans — the Crabel copy through an OCR layer with visible character noise in
#: the glossary headwords. The rule text itself was clean and cross-corroborated
#: (the S&C publisher records independently restate the Stretch and the opening
#: range), so the rules are NOT downgraded. What cannot be asserted is edition
#: identity and page-level fidelity.
UNCONTROLLED_WITNESS = (
    "Primary rule recovered from an uncontrolled third-party scan/OCR witness; "
    "edition/page fidelity not independently verified.")

#: Tiers whose whole point is that the engine runs something no source states.
#: They cannot be registered without naming it.
_TIERS_REQUIRING_ADAPTATIONS = (
    ProvenanceTier.TIER_B_CONTEMPORARY_SECONDARY,
    ProvenanceTier.TIER_T_TRANSFER,
)

#: Fields that are legitimately empty (a Tier A system adapts nothing and may
#: quote no discretionary guidance). Every OTHER field must be non-empty.
_OPTIONAL_FIELDS = frozenset({"adaptations", "discretionary_guidance"})


class InvalidConfiguration(ValueError):
    """Raised when a historical system is constructed or registered without the
    parameters/provenance the Phase 8 discipline requires (rejection reason:
    invalid_configuration)."""


@dataclass(frozen=True)
class HistoricalProvenance:
    """Complete provenance record. Every field is required and non-empty except
    `adaptations` and `discretionary_guidance`.

    `unrecovered_items` entries must use the exact phrase
    "PRIMARY SOURCE NOT RECOVERED." where evidence is insufficient.
    """
    tier: ProvenanceTier
    citations: tuple[str, ...]
    historical_rules: tuple[str, ...]       # statements directly recovered from primary sources
    engine_conventions: tuple[str, ...]     # engine choices that are NOT historical rules
    data_basis: str                         # which basis signal geometry is computed on
    entry_mechanism: str
    exit_mechanism: str
    session_definition: str
    tick_size: str                          # 'not_applicable: <reason>' allowed for tick-free systems
    tie_policy: str
    gap_policy: str
    unrecovered_items: tuple[str, ...]
    witness: str                            # how the primary text was read
    adaptations: tuple[str, ...] = ()       # rules NO source states (synthesis/transfer)
    discretionary_guidance: tuple[str, ...] = ()   # recovered advice, not mechanical rules

    def __post_init__(self):
        missing = [f.name for f in fields(self)
                   if f.name not in _OPTIONAL_FIELDS
                   and (getattr(self, f.name) is None
                        or (isinstance(getattr(self, f.name), (str, tuple))
                            and len(getattr(self, f.name)) == 0))]
        if missing:
            raise InvalidConfiguration(
                f"historical provenance incomplete; missing/empty: {sorted(missing)}")
        if isinstance(self.tier, str):
            object.__setattr__(self, "tier", ProvenanceTier(self.tier))
        if self.tier is ProvenanceTier.TIER_E_UNSUPPORTED:
            raise InvalidConfiguration(
                "tier_e_unsupported material can never back a historical system")
        if self.tier in _TIERS_REQUIRING_ADAPTATIONS and not self.adaptations:
            raise InvalidConfiguration(
                f"{self.tier.value} exists precisely because the engine runs a rule no "
                "primary source states; it must declare `adaptations`")


def validate_provenance(provenance: Optional[HistoricalProvenance], rule_id: str) -> HistoricalProvenance:
    if provenance is None:
        raise InvalidConfiguration(
            f"{rule_id}: a historical strategy cannot be registered without "
            "provenance metadata (Phase 8/9 discipline)")
    return provenance


# ── Registry ─────────────────────────────────────────────────────────────────
# Populated by the system modules at import time via register_historical_spec().
# Kept separate from strategy_specs.SPECS: legacy live strategies and Phase 8
# historical systems must never share one namespace (Phase 8 review H-3).

HISTORICAL_SPECS: dict = {}


def register_historical_spec(spec) -> None:
    """Register a Phase 8 historical system spec. Refuses incomplete provenance."""
    if getattr(spec, "legacy", False):
        raise InvalidConfiguration(f"{spec.name}: a legacy spec cannot be registered as historical")
    provenance = validate_provenance(getattr(spec, "provenance", None), spec.name)
    HISTORICAL_SPECS[spec.name] = spec


def get_historical_spec(rule_id: str):
    return HISTORICAL_SPECS[rule_id]
