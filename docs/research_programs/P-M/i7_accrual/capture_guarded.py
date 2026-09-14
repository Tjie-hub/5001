#!/usr/bin/env python3
"""Guarded entrypoint for I7-admissible prospective capture.

Requirement 1(d)/1(e): capture must not be able to produce an I7-admissible
cell before the 16:15 WIB post-session cutoff.

Enforcement is deliberately in TWO places, because one is not enough:

  1. PRE-FETCH REFUSAL (here). `capture_permitted_now()` refuses to launch a
     run against a session that has not yet completed. This stops partial
     sessions entering the store at all.

  2. COHORT GATE (`build_v003_freeze.py` via `i7_admissibility.admissible()`).
     Even if a cell reaches the store by some other path -- a manual run, a
     future scheduler, a clock skew -- it is classified E-PIT-3 and never
     enters the frozen cohort.

Layer 1 is operational hygiene. **Layer 2 is the guarantee**, because it is
evaluated at cohort-construction time from each cell's own recorded timestamp
rather than from the honesty of whoever launched the run.

This wraps `flow_capture_prospective.prospective_capture` WITHOUT modifying it.

    python3 capture_guarded.py --session 2026-09-15 --dry-run

NOT ACTIVATED. This module is not wired to cron, systemd, or any scheduler.
Activation is an Owner action.
"""
from __future__ import annotations

import argparse, datetime as _dt, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVICE = os.path.abspath(os.path.join(HERE, "..", "flow_capture_prospective"))
sys.path.insert(0, HERE)
sys.path.insert(0, SERVICE)

import i7_admissibility as ADM  # noqa: E402

WIB = _dt.timezone(_dt.timedelta(hours=7))


def now_wib() -> _dt.datetime:
    return _dt.datetime.now(WIB).replace(tzinfo=None)


def guard(session_date: str, now: _dt.datetime | None = None) -> ADM.Verdict:
    """Refuse a run that cannot yield an admissible cell."""
    return ADM.capture_permitted_now(session_date, now or now_wib())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, help="session date, YYYY-MM-DD (WIB)")
    ap.add_argument("--now", help="override wall clock (testing), ISO local WIB")
    ap.add_argument("--dry-run", action="store_true",
                    help="evaluate the guard and exit without capturing")
    a = ap.parse_args()

    now = _dt.datetime.fromisoformat(a.now) if a.now else now_wib()
    v = guard(a.session, now)

    print(f"session      : {a.session}")
    print(f"now (WIB)    : {now.isoformat(timespec='seconds')}")
    print(f"cutoff (WIB) : {ADM.CUTOFF_WIB.isoformat()}")
    print(f"verdict      : {'PERMITTED' if v.admissible else 'REFUSED'}  {v.detail}")

    if not v.admissible:
        print(f"\nREFUSED [{v.rule}] — a capture now cannot hold a complete session, "
              f"so it cannot produce an I7-admissible cell.")
        return 3

    if a.dry_run:
        print("\nDRY RUN — guard passed; capture not invoked.")
        return 0

    print("\nGuard passed. Capture is NOT auto-invoked by this build: activation "
          "is an Owner action (see flow_capture_prospective/DESIGN.md §7).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
