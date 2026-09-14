#!/usr/bin/env python3
"""I7 admissibility rules — the E-PIT gate.

Pure, importable, testable. Encodes the four exclusions established by
`I7_PIT_PROVENANCE_AUDIT_2026-09-14.md`. Nothing here reads the outcome
column, computes a return, or knows what I7 predicts: admissibility is a
function of PROVENANCE and SESSION COMPLETENESS only.

Provenance evidence available for the pre-activation cohort
-----------------------------------------------------------
`stockbit_flow_bars` carries no provenance columns. But its sole writer
(`tools/backfill_flow_bars.py::_persist`) writes `stockbit_flow` in the SAME
commit, stamping `updated_at = datetime.now()` (server TZ = Asia/Jakarta, naive
ISO). And the backfill SKIPS already-complete cells rather than overwriting
them, so an `updated_at` still sitting on its own trade date proves the cell was
never rewritten. `stockbit_flow.updated_at` is therefore a genuine write-time
record for the bars committed beside it -- the one provenance fact recoverable
for cells captured before the prospective service is activated.

Once the prospective capture service IS activated, `capture_manifest.captured_at_utc`
supersedes this proxy and `admissible()` is called with `source='capture_manifest'`.
"""
from __future__ import annotations

import datetime as _dt
from typing import NamedTuple

# --- frozen constants -------------------------------------------------------

#: Last session of the v002 historical-backfill interval. Everything at or
#: before this date is class B (median retrieval lag 364 days) and is excluded
#: wholesale by E-PIT-1.
V002_LAST_SESSION = "2026-04-27"

#: First session of the contemporaneous-capture era.
CONTEMPORANEOUS_FIRST_SESSION = "2026-04-28"

#: IDX continuous session ends 15:49 WIB; post-close bars run to 16:14.
#: A capture started before 16:15 WIB cannot hold a complete session.
CUTOFF_WIB = _dt.time(16, 15)

#: Structural minute-bar grid. Friday carries the long (prayer) lunch break.
#: Verified: all 58 Friday sessions in v002 carry 275 bars; all Mon-Thu carry
#: 335; zero sessions deviate from their weekday's grid.
GRID_MON_THU = 335
GRID_FRI = 275

#: Maximum write lag, in days, still counted as contemporaneous.
MAX_CONTEMPORANEOUS_LAG_DAYS = 1

RULES = {
    "E-PIT-1": "historical/backfilled v002 interval excluded wholesale",
    "E-PIT-2": "no contemporaneous provenance (write lag outside 0..1 days)",
    "E-PIT-3": "same-day capture before the 16:15 WIB post-session cutoff",
    "E-PIT-4": "bars absent, or n_bars != the weekday structural grid",
}


def expected_bars(session_date: str) -> int:
    """Structural bar count for a session's weekday. Friday differs."""
    d = _dt.date.fromisoformat(session_date)
    return GRID_FRI if d.weekday() == 4 else GRID_MON_THU


def write_lag_days(session_date: str, captured_at_wib: str) -> int:
    """Whole days between the session and the write. Negative is impossible in
    valid data and is reported as such by admissible()."""
    s = _dt.date.fromisoformat(session_date)
    w = _dt.date.fromisoformat(captured_at_wib[:10])
    return (w - s).days


class Verdict(NamedTuple):
    admissible: bool
    rule: str | None  # the E-PIT rule that excluded it, else None
    detail: str


def admissible(session_date: str,
               captured_at_wib: str | None,
               n_bars: int | None) -> Verdict:
    """Decide one (ticker, session) cell.

    `captured_at_wib` is a naive ISO timestamp in Asia/Jakarta -- either
    `stockbit_flow.updated_at` (pre-activation proxy) or the prospective
    service's captured_at converted to WIB. None means no provenance at all.
    """
    # E-PIT-1 -- the whole historical interval, before anything else is asked.
    if session_date <= V002_LAST_SESSION:
        return Verdict(False, "E-PIT-1",
                       f"session {session_date} <= v002 last session "
                       f"{V002_LAST_SESSION} (historical backfill interval)")

    # E-PIT-2 -- provenance must exist and be contemporaneous.
    if not captured_at_wib:
        return Verdict(False, "E-PIT-2", "no capture timestamp")
    try:
        lag = write_lag_days(session_date, captured_at_wib)
    except ValueError:
        return Verdict(False, "E-PIT-2", f"unparseable timestamp {captured_at_wib!r}")
    if lag < 0:
        return Verdict(False, "E-PIT-2", f"write precedes session (lag {lag}d)")
    if lag > MAX_CONTEMPORANEOUS_LAG_DAYS:
        return Verdict(False, "E-PIT-2", f"write lag {lag}d exceeds "
                                         f"{MAX_CONTEMPORANEOUS_LAG_DAYS}d")

    # E-PIT-3 -- a same-day write must land after the session is complete.
    # A next-day write (lag == 1) is necessarily after the session ended.
    if lag == 0:
        t = _dt.time.fromisoformat(captured_at_wib[11:19])
        if t < CUTOFF_WIB:
            return Verdict(False, "E-PIT-3",
                           f"same-day capture at {t.isoformat()} WIB precedes "
                           f"cutoff {CUTOFF_WIB.isoformat()} -- partial session")

    # E-PIT-4 -- the session must actually be complete.
    exp = expected_bars(session_date)
    if not n_bars:
        return Verdict(False, "E-PIT-4", "no bars")
    if n_bars != exp:
        return Verdict(False, "E-PIT-4", f"n_bars {n_bars} != structural grid {exp}")

    return Verdict(True, None, f"lag {lag}d, {n_bars} bars")


def capture_permitted_now(session_date: str, now_wib: _dt.datetime) -> Verdict:
    """Operational guard (requirement 1e). A capture run targeting `session_date`
    may not produce an I7-admissible cell before the cutoff. Called by the
    capture service BEFORE fetching, so an early run is refused rather than
    silently producing inadmissible cells."""
    if now_wib.date().isoformat() < session_date:
        return Verdict(False, "E-PIT-2", "session has not occurred")
    if now_wib.date().isoformat() == session_date and now_wib.time() < CUTOFF_WIB:
        return Verdict(False, "E-PIT-3",
                       f"now {now_wib.time().isoformat()} WIB precedes cutoff "
                       f"{CUTOFF_WIB.isoformat()}; session incomplete")
    return Verdict(True, None, "after post-session cutoff")
