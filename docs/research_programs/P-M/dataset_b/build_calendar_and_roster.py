#!/usr/bin/env python3
"""Dataset B — session calendar + point-in-time IDX80 roster artifact builder.

READ-ONLY against the production DB. Writes only immutable JSON artifacts under
docs/research_programs/P-M/dataset_b/artifacts/. Never touches broker_flow,
never touches Dataset A, never writes any production table.

WHY THIS EXISTS
---------------
Dataset A's universe came from `idx80_universe()`, a LIVE query on
`idx_tickers WHERE status='active' AND in_idx80=1`. Foundation Audit v2
established that this set matches no IDX80 reconstitution period (best 64/80,
worst 57/80), was written once on 2026-04-27, contains ten names that were
never IDX80 members during the research window, and includes the 692nd most
liquid stock on the exchange. It is also mutable by production, so the
pre-execution gate that hashed it was verifying a moving target against itself.

Dataset B resolves membership per session from the primary-sourced tables
(`idx80_membership_history` x `idx80_reconstitution_periods`) and freezes the
result to a file. Verification reads the FILE, never the database.

WHY TWO ARTIFACTS
-----------------
The session calendar and the roster answer different questions and fail
independently: a session can be defective (partial EOD scrape) while membership
is perfectly known, and vice versa. Keeping them separate means a calendar
rebuild does not invalidate the membership receipt. The roster artifact records
the calendar's SHA-256 so the pairing is still pinned.
"""
import argparse, hashlib, json, sqlite3, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ART = HERE / "artifacts"
DB_PATH = Path("/home/tjiesar/10 Projects/idx-walkforward-5001/data/walkforward.db")

# Window is declared, not discovered. Dataset A's window, so the two are
# directly comparable; Dataset B is a supersession, not an extension.
WINDOW_START = "2025-01-02"
WINDOW_END = "2026-08-27"

# A session enters the calendar only when this share of that session's PIT
# members actually has an ohlcv bar. 0.95 is declared here, not tuned: the
# measured distribution is bimodal (every session is either ~1.00 or 0.00),
# so any threshold in (0.0, 1.0) selects the same set. Recorded so the policy
# is auditable rather than incidental.
COVERAGE_THRESHOLD = 0.95

# Excluded by name, with reasons, independent of the coverage test. These are
# belt-and-braces: the coverage predicate already rejects the two July dates.
NAMED_EXCLUSIONS = {
    "2026-08-25": "no IHSG bar; trading_calendar source is 'scraper_eod', not "
                  "a confirmed IDX session. Excluded from Dataset A for the "
                  "same reason (D-041/D-043) and carried forward.",
}


def ro_connect(path: Path) -> sqlite3.Connection:
    """Read-only connection. Not data.db.connect() on purpose: this is a
    research-side builder and must be provably incapable of writing."""
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(HERE), text=True).strip()
    except Exception:
        return "unknown"


def canonical_json(obj) -> str:
    """Order-independent-safe serialisation: sorted keys, fixed separators.
    Hashing this rather than the file bytes means whitespace/ordering changes
    in the writer cannot silently change a receipt."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(obj) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- periods ---
def load_periods(conn):
    rows = conn.execute(
        "SELECT period_label, effective_from, effective_to, left_censored, "
        "constituent_count, confidence, source FROM idx80_reconstitution_periods "
        "ORDER BY effective_from").fetchall()
    periods = []
    for lbl, frm, to, lc, cnt, conf, src in rows:
        members = sorted(r[0] for r in conn.execute(
            "SELECT ticker FROM idx80_membership_history "
            "WHERE period_label=? AND membership_status='MEMBER'", (lbl,)))
        periods.append({
            "period_label": lbl, "effective_from": frm,
            "effective_to": to,  # None == open-ended (current period)
            "left_censored": bool(lc), "confidence": conf,
            "declared_constituent_count": cnt,
            "observed_member_count": len(members),
            "source": src, "members": members,
        })
    return periods


# Mirrors foundation.BAND_REGIMES. Duplicated deliberately: the builder must not
# import the consumer, so the artifact stays buildable in isolation. The two are
# asserted equal by validate.py.
_BAND_REGIMES = (("R3", "2023-09-04", "2025-04-07"), ("R4", "2025-04-08", None))


def _band_regime(session: str):
    for label, frm, to in _BAND_REGIMES:
        if frm <= session and (to is None or session <= to):
            return label
    return None


def period_for(periods, session: str):
    for p in periods:
        if p["effective_from"] <= session and (
                p["effective_to"] is None or session <= p["effective_to"]):
            return p
    return None


# --------------------------------------------------------------- calendar ---
def build_calendar(conn, periods):
    """Candidate sessions = trading_calendar rows with an IHSG bar (the legacy
    canonical test), then filtered by PER-TICKER completeness against that
    session's PIT membership. The legacy test admitted 2026-07-09 and
    2026-07-24, on which ZERO roster tickers had a price bar."""
    cal = [r[0] for r in conn.execute(
        "SELECT date FROM trading_calendar WHERE date >= ? AND date <= ? ORDER BY date",
        (WINDOW_START, WINDOW_END))]
    ihsg = {r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM ohlcv WHERE ticker='IHSG' AND date >= ? AND date <= ?",
        (WINDOW_START, WINDOW_END))}

    sessions, excluded = [], []
    for d in cal:
        members = (period_for(periods, d) or {}).get("members", [])
        if not members:
            excluded.append({"date": d, "reason": "no IDX80 period covers this session",
                             "coverage": None, "members": 0}); continue
        if d in NAMED_EXCLUSIONS:
            excluded.append({"date": d, "reason": NAMED_EXCLUSIONS[d],
                             "coverage": None, "members": len(members)}); continue
        if d not in ihsg:
            excluded.append({"date": d, "reason": "no IHSG bar (not a confirmed IDX session)",
                             "coverage": None, "members": len(members)}); continue
        ph = ",".join("?" * len(members))
        have = conn.execute(
            f"SELECT COUNT(*) FROM ohlcv WHERE date=? AND ticker IN ({ph}) "
            f"AND close IS NOT NULL", [d] + members).fetchone()[0]
        cov = have / len(members)
        if cov < COVERAGE_THRESHOLD:
            excluded.append({"date": d, "reason": "member price coverage below threshold",
                             "coverage": round(cov, 4), "members": len(members)})
        else:
            sessions.append({"date": d, "members": len(members), "with_price": have,
                             "coverage": round(cov, 4), "band_regime": _band_regime(d)})
    return sessions, excluded


# ------------------------------------------------------------------- main ---
def main(argv=None):
    ap = argparse.ArgumentParser(description="Build Dataset B calendar + PIT roster artifacts")
    ap.add_argument("--version", default="v1")
    ap.add_argument("--write", action="store_true",
                    help="write the artifacts; without it the build is a dry run")
    a = ap.parse_args(argv)

    conn = ro_connect(DB_PATH)
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit = _git_commit()
    periods = load_periods(conn)
    sessions, excluded = build_calendar(conn, periods)

    cal_body = {
        "artifact": "DATASET_B_SESSION_CALENDAR", "version": a.version,
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "coverage_threshold": COVERAGE_THRESHOLD,
        "named_exclusions": NAMED_EXCLUSIONS,
        "source_tables": ["trading_calendar", "ohlcv",
                          "idx80_reconstitution_periods", "idx80_membership_history"],
        "band_regimes": [{"label": l, "from": f, "to": t} for l, f, t in _BAND_REGIMES],
        "band_regime_note": "LC-PM-0009: R3 symmetric bands to 2025-04-07, R4 ARB -15% "
                            "from 2025-04-08. This window STRADDLES the boundary; pooling "
                            "across it without conditioning is void under B8.",
        "sessions_by_regime": {l: sum(1 for s in sessions if s["band_regime"] == l)
                               for l, _, _ in _BAND_REGIMES},
        "session_count": len(sessions),
        "excluded_count": len(excluded),
        "sessions": [s["date"] for s in sessions],
        "session_detail": sessions,
        "excluded": excluded,
    }
    cal_hash = sha256_of(cal_body)
    calendar = {"sha256": cal_hash, "built_at_utc": built_at, "git_commit": commit,
                "builder": "docs/research_programs/P-M/dataset_b/build_calendar_and_roster.py",
                "source_db": str(DB_PATH), **cal_body}

    session_members = {s["date"]: period_for(periods, s["date"])["members"] for s in sessions}
    universe = sorted({t for m in session_members.values() for t in m})
    ros_body = {
        "artifact": "DATASET_B_PIT_ROSTER", "version": a.version,
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "session_calendar_sha256": cal_hash,
        "source_tables": ["idx80_reconstitution_periods", "idx80_membership_history"],
        "membership_rule": "a ticker is a member of session d iff d falls within "
                           "the [effective_from, effective_to] interval of a period "
                           "in which it holds a MEMBER row; effective_to NULL == open",
        "period_count": len(periods),
        "distinct_tickers": len(universe),
        "universe": universe,
        "periods": [{k: v for k, v in p.items() if k != "members"} for p in periods],
        "period_members": {p["period_label"]: p["members"] for p in periods},
        "session_members": session_members,
    }
    ros_hash = sha256_of(ros_body)
    roster = {"sha256": ros_hash, "built_at_utc": built_at, "git_commit": commit,
              "builder": "docs/research_programs/P-M/dataset_b/build_calendar_and_roster.py",
              "source_db": str(DB_PATH), **ros_body}
    conn.close()

    print(f"session calendar : {len(sessions)} sessions, {len(excluded)} excluded")
    print(f"                   sha256 {cal_hash}")
    print(f"PIT roster       : {len(periods)} periods, {len(universe)} distinct tickers")
    print(f"                   sha256 {ros_hash}")
    if not a.write:
        print("\n(dry run — pass --write to materialise)"); return calendar, roster

    ART.mkdir(parents=True, exist_ok=True)
    for name, obj, h in (("SESSION_CALENDAR", calendar, cal_hash),
                         ("PIT_ROSTER", roster, ros_hash)):
        p = ART / f"DATASET_B_{name}_{a.version}.json"
        if p.exists():
            # Immutable by policy: a new build is a new version, never an edit.
            raise SystemExit(f"REFUSING to overwrite existing artifact {p.name} — "
                             f"bump --version instead (artifacts are append-only)")
        p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
        (ART / f"{p.name}.sha256").write_text(f"{h}  {p.name}\n")
        print(f"wrote {p.name}  ({p.stat().st_size:,} bytes)")
    return calendar, roster


if __name__ == "__main__":
    main()
