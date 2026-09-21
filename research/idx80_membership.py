"""Point-in-time IDX80 membership accessor.

Reads the frozen reconstitution ledger built by WP-D
(docs/research_programs/P-A/WP-D/) -- idx80_reconstitution_periods (one row
per reconstitution window) and idx80_membership_history (one row per
ticker x window) -- to answer "who was in the IDX80 on date X", by evidence
tier. This is the PIT replacement for idx_tickers.in_idx80, which only ever
holds *today's* membership and must never be used for historical research
(look-ahead / survivorship bias).

Evidence tiers (idx80_reconstitution_periods.confidence /
idx80_membership_history.confidence; see WP-D DATA_DICTIONARY.md):

    PRIMARY_VERIFIED         confirmed against the official IDX announcement
    BRACKETED_RECONSTRUCTED  derived from a verified delta bracketing the window
    CROSS_VALIDATED          derived + independently cross-checked, zero discrepancy
    UNRESOLVED               a known data conflict/gap; not corroborated

STRICT (the default) is PRIMARY_VERIFIED-only. RECONSTRUCTED opts into the
two reconstructed-but-corroborated tiers as well. UNRESOLVED evidence is
never reachable through members_as_of() at all -- not even by passing a
string -- precisely so a typo can't silently let it through; the only door
is the separately-named members_as_of_all_evidence().

effective_to is the last INCLUSIVE day a period is valid (not an exclusive
cutoff): consecutive periods in the source ledger are one calendar day
apart (period[i].effective_to + 1 day == period[i+1].effective_from), never
equal -- confirmed against the live P0-P7 ledger, including a real window
boundary that lands on an ordinary trading Wednesday. A NULL effective_to
(currently only P7) means "still open as of the last refresh".

Dates before the earliest period's effective_from, or falling in a genuine
gap between two periods (e.g. a market holiday with no reconstitution row),
resolve to no membership at all -- this accessor never imputes.
"""
from __future__ import annotations

from typing import FrozenSet, Optional, Tuple

STRICT = "strict"
RECONSTRUCTED = "reconstructed"
ALL_EVIDENCE = "all_evidence"

_TIER_CONFIDENCE = {
    STRICT: frozenset({"PRIMARY_VERIFIED"}),
    RECONSTRUCTED: frozenset({
        "PRIMARY_VERIFIED", "BRACKETED_RECONSTRUCTED", "CROSS_VALIDATED",
    }),
}

_ALL_EVIDENCE_CONFIDENCE = frozenset({
    "PRIMARY_VERIFIED", "BRACKETED_RECONSTRUCTED", "CROSS_VALIDATED", "UNRESOLVED",
})


def _period_for(conn, as_of_date: str) -> Optional[str]:
    rows = conn.execute(
        "SELECT period_label FROM idx80_reconstitution_periods "
        "WHERE effective_from <= ? AND (effective_to IS NULL OR ? <= effective_to)",
        (as_of_date, as_of_date),
    ).fetchall()
    if len(rows) > 1:
        raise ValueError(
            f"data integrity error: {len(rows)} idx80_reconstitution_periods "
            f"rows overlap as_of_date={as_of_date!r}: {[r[0] for r in rows]}"
        )
    return rows[0][0] if rows else None


def _members(conn, period_label: Optional[str], allowed_confidence: FrozenSet[str]) -> FrozenSet[str]:
    if period_label is None or not allowed_confidence:
        return frozenset()
    placeholders = ",".join("?" for _ in allowed_confidence)
    rows = conn.execute(
        "SELECT DISTINCT ticker FROM idx80_membership_history "
        f"WHERE period_label = ? AND membership_status = 'MEMBER' "
        f"AND confidence IN ({placeholders})",
        (period_label, *allowed_confidence),
    ).fetchall()
    return frozenset(r[0] for r in rows)


def members_as_of(conn, as_of_date: str, confidence_tier: str = STRICT) -> FrozenSet[str]:
    """IDX80 constituents as of `as_of_date` (ISO 'YYYY-MM-DD'), by evidence tier.

    confidence_tier is "strict" (default, PRIMARY_VERIFIED only) or
    "reconstructed" (also accepts BRACKETED_RECONSTRUCTED / CROSS_VALIDATED).
    UNRESOLVED evidence is never returned here -- use
    members_as_of_all_evidence() for that, explicitly.

    Returns an empty frozenset when no reconstitution period covers the date
    (before the left-censored start, or in a genuine gap between periods) or
    when the covering period's confidence doesn't meet the requested tier.
    """
    if confidence_tier not in _TIER_CONFIDENCE:
        raise ValueError(
            f"confidence_tier must be one of {sorted(_TIER_CONFIDENCE)!r}; "
            f"got {confidence_tier!r}. To include UNRESOLVED evidence, call "
            f"members_as_of_all_evidence() explicitly."
        )
    period_label = _period_for(conn, as_of_date)
    return _members(conn, period_label, _TIER_CONFIDENCE[confidence_tier])


def members_as_of_all_evidence(conn, as_of_date: str) -> FrozenSet[str]:
    """IDX80 constituents as of `as_of_date`, including UNRESOLVED evidence.

    Deliberately separate from members_as_of(): this is the only way to see
    an UNRESOLVED period's membership, so it can't be triggered by a typo'd
    confidence_tier string on the default API.
    """
    period_label = _period_for(conn, as_of_date)
    return _members(conn, period_label, _ALL_EVIDENCE_CONFIDENCE)


def idx80_universe_as_of(conn, as_of_date: str, confidence_tier: str = STRICT) -> Tuple[str, ...]:
    """Research-universe-selection entry point for IDX80-scoped studies.

    A deterministic, sorted-tuple wrapper around members_as_of() -- matching
    the return convention of this repo's other universe providers
    (research.studies.nr7_generalization_study.liquid_universe,
    research.gatekeeper.cli._default_universe) so it drops into the same
    call sites those use.

    `as_of_date` has no default: every call site must state, explicitly,
    which date's universe it means. This function (like members_as_of) never
    reads idx_tickers.in_idx80 or any other "current membership" source, and
    never returns UNRESOLVED evidence -- pass confidence_tier="reconstructed"
    to opt into BRACKETED_RECONSTRUCTED/CROSS_VALIDATED periods; use
    members_as_of_all_evidence() directly (not through this function) for
    UNRESOLVED evidence.
    """
    return tuple(sorted(members_as_of(conn, as_of_date, confidence_tier)))
