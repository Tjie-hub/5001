"""PIT dynamic-universe planning layer for the IDX80 broker-flow backfill.

"IDX80" is the index name, not a promise that every historical date has the
same 80 tickers. This module is the data-collection authority for roster
resolution: for a trading date T it resolves the point-in-time IDX80
membership from the frozen WP-D ledger (idx80_reconstitution_periods /
idx80_membership_history) via research.idx80_membership, and NEVER

  * truncates the roster to the nominal 80,
  * pads a short roster with invented names,
  * substitutes today's idx_tickers.in_idx80 for a historical date.

DATA COLLECTION vs RESEARCH ELIGIBILITY (deliberately separate concepts):

  * Collection completeness (this module, `--universe pit`): "did we fetch
    broker flow for every ticker that was actually in the PIT universe on
    date T?" The roster authority here is members_as_of_all_evidence() --
    UNRESOLVED periods (e.g. P2, 81 members) are fetched like any other,
    because a collection gap is a fact about the vendor, not about evidence.
  * Research eligibility (research.idx80_membership strict/reconstructed
    tiers, gatekeeper): "is this PIT period trustworthy enough to trade on?"
    UNRESOLVED periods stay excluded there by design. A period can therefore
    be fully fetched AND excluded from research -- that is correct behavior.

A member count != 80 is an ADVISORY (anomaly/anotation), never a filter: the
nominal index size is metadata, not a constraint on the fetch predicate.

Dates with no covering reconstitution period resolve to no membership at all
(the accessor never imputes); the planner reports them and plans zero cells
for them rather than falling back to the live roster.
"""
from __future__ import annotations

from research.idx80_membership import members_as_of_all_evidence

NOMINAL_IDX80_SIZE = 80


def expected_nominal_count() -> int:
    """The nominal IDX80 size -- metadata for advisories ONLY. Never used to
    filter, truncate, or pad a roster."""
    return NOMINAL_IDX80_SIZE


def period_info(conn, trade_date: str) -> tuple:
    """(period_label, confidence) of the reconstitution period covering
    `trade_date`, or (None, None). effective_to is INCLUSIVE (the accessor's
    documented, frozen semantics)."""
    row = conn.execute(
        "SELECT period_label, confidence FROM idx80_reconstitution_periods "
        "WHERE effective_from <= ? AND (effective_to IS NULL OR ? <= effective_to)",
        (trade_date, trade_date),
    ).fetchall()
    if len(row) > 1:
        raise ValueError(
            f"data integrity error: {len(row)} idx80_reconstitution_periods "
            f"rows overlap trade_date={trade_date!r}: {[r[0] for r in row]}")
    return (row[0][0], row[0][1]) if row else (None, None)


def required_members(conn, trade_date: str) -> tuple:
    """The PIT roster for `trade_date` -- the data-collection authority.

    Returns (members, advisory): a deterministically sorted list of tickers
    (every resolved PIT member -- never truncated, never padded, never taken
    from idx_tickers), plus an advisory dict when the roster is empty or its
    size != the nominal 80. The advisory annotates; it does not filter.
    """
    members = sorted(members_as_of_all_evidence(conn, trade_date))
    period_label, confidence = period_info(conn, trade_date)
    advisory = None
    if not members:
        advisory = {
            "date": trade_date,
            "period_label": period_label,
            "confidence": confidence,
            "member_count": 0,
            "expected_nominal_count": NOMINAL_IDX80_SIZE,
            "message": (f"no PIT reconstitution period covers {trade_date}; "
                        f"no members resolved, no imputation performed"),
        }
    elif len(members) != NOMINAL_IDX80_SIZE:
        if len(members) > NOMINAL_IDX80_SIZE:
            message = (f"PIT universe has {len(members)} members; expected "
                       f"nominal IDX80 size is {NOMINAL_IDX80_SIZE}. "
                       f"No members dropped.")
        else:
            message = (f"PIT universe has {len(members)} members; "
                       f"no members invented.")
        advisory = {
            "date": trade_date,
            "period_label": period_label,
            "confidence": confidence,
            "member_count": len(members),
            "expected_nominal_count": NOMINAL_IDX80_SIZE,
            "message": message,
        }
    return members, advisory


def pit_gap_plan(conn, dates: list, missing_cells_fn) -> dict:
    """Per-date PIT gap plan over `dates` (canonical trading dates).

    `missing_cells_fn(conn, trade_date, tickers)` is the existing completion
    predicate (tools.broker_flow_idx80_gap.missing_cells) -- reused verbatim
    so PIT planning and live planning can never disagree about what
    "already fetched" means. Read-only: no vendor calls, no writes.
    """
    rows = []
    advisories = []
    required = covered = 0
    for d in dates:
        members, advisory = required_members(conn, d)
        if advisory is not None:
            advisories.append(advisory)
        need = missing_cells_fn(conn, d, members) if members else []
        required += len(members)
        covered += len(members) - len(need)
        rows.append({
            "date": d,
            "period_label": advisory["period_label"] if advisory else
            period_info(conn, d)[0],
            "confidence": advisory["confidence"] if advisory else
            period_info(conn, d)[1],
            "member_count": len(members),
            "missing_count": len(need),
            "missing_cells": list(need),
            "advisory": advisory,
        })
    return {
        "universe_mode": "pit",
        "dates": rows,
        "required_ticker_days": required,
        "covered_ticker_days": covered,
        "missing_ticker_days": required - covered,
        "coverage_pct": round(100.0 * covered / required, 4) if required else 0.0,
        "advisories": advisories,
        "nominal_idx80_size": NOMINAL_IDX80_SIZE,
    }
