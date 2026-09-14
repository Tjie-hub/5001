#!/usr/bin/env python3
"""Build the I7 v004 admissible-cohort freeze — the v003 mechanical correction.

Implements readiness-review §2.4 remediation (a): the spec's exclusion set
X1–X6 (BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md §8) is now enforced at the
cohort layer exactly as far as accrual-layer data allows, WITHOUT changing the
substantive I7 hypothesis, estimator, state definition, threshold, inference,
or decision rule, and WITHOUT any minimum-cell/session rule.

What v004 changes relative to v003 (mechanical only):
  * X3 is enforced: a candidate cell whose session is not admitted by the
    session calendar (base DATASET_B_SESSION_CALENDAR_v2 + frozen extension
    I7_SESSION_CALENDAR_EXTENSION_v1, which extends coverage through
    2026-09-11) is excluded with rule label "X3". Precedence: X3 (session
    level) is evaluated before the E-PIT cell rules; E-PIT-1 (wholesale
    historical interval) still bounds the candidate set. This removes
    2026-07-09 from the cohort and makes X3 evaluable for every session
    through 2026-09-11.
  * X1 (2025-04-14 fixture) and X2 (2025-08-04..2025-09-17 zone) are
    subsumed: both lie entirely inside the E-PIT-1 interval
    (session <= 2026-04-27); the builder asserts this.
  * X4 is the same predicate as E-PIT-4 (bars present, exact weekday grid).
  * X5 (corporate action / RAJA / price floor / liquidity floor) and X6
    (t, t+1, t+2 consecutivity) are ESTIMATION-TIME filters over ohlcv
    (readiness review §2.5). They are NOT applied here — applying them at
    accrual would require reading prices/outcomes, which accrual forbids.
    The estimator must apply and count them.

Outcome-blind by construction, unchanged from v003: the only production
columns read are the bar fields, `stockbit_flow.updated_at` (provenance), and
calendar membership. No close, return, or outcome column is read.

READ-ONLY against production. Writes only to this package's own store/.
Never touches data/walkforward.db, Dataset B, the v002 freeze, or v003.

  python3 build_v004_freeze.py            # dry run: full exclusion accounting
  python3 build_v004_freeze.py --write    # materialise the immutable freeze
"""
from __future__ import annotations

import argparse, datetime as _dt, hashlib, json, os, sqlite3, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i7_admissibility as ADM  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PROD = os.path.join(REPO, "data", "walkforward.db")
DSB = os.path.join(REPO, "docs", "research_programs", "P-M", "dataset_b")
BASE_CAL = os.path.join(DSB, "artifacts", "DATASET_B_SESSION_CALENDAR_v2.json")
BASE_CAL_SHA = "5012be2315dc82ccfd65a2b117e1977753f0a7d3214693821b39077cd18043fa"
EXT_CAL = os.path.join(HERE, "store", "I7_SESSION_CALENDAR_EXTENSION_v1.json")
EXT_CAL_SHA = "a7a4eedf45f3d4b2ced4f9a9f2d90d28e011ef0425b115c127a04fcdda0f189e"
STORE_DIR = os.path.join(HERE, "store")
STORE = os.path.join(STORE_DIR, "I7_V004_ADMISSIBLE_v1.sqlite")
MANIFEST = os.path.join(STORE_DIR, "I7_V004_MANIFEST.json")


def ro(path):
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def verify_base_calendar():
    obj = json.load(open(BASE_CAL))
    if obj["sha256"] != BASE_CAL_SHA:
        raise SystemExit("ABORT: base calendar sha mismatch vs pin")
    body = {k: v for k, v in obj.items()
            if k not in ("sha256", "built_at_utc", "git_commit", "builder",
                         "source_db")}
    canon = json.dumps(body, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode()
    if hashlib.sha256(canon).hexdigest() != obj["sha256"]:
        raise SystemExit("ABORT: base calendar content hash mismatch")
    return obj


def verify_extension_calendar():
    if sha256_file(EXT_CAL) != EXT_CAL_SHA:
        raise SystemExit("ABORT: extension calendar sha mismatch vs pin")
    obj = json.load(open(EXT_CAL))
    if obj["base_calendar"]["sha256"] != BASE_CAL_SHA:
        raise SystemExit("ABORT: extension built on a different base calendar")
    return obj


def calendar_admitted():
    """Admitted sessions = base calendar sessions + extension sessions.
    X3: a session not in this set is excluded."""
    base = verify_base_calendar()
    ext = verify_extension_calendar()
    admitted = set(base["sessions"]) | set(ext["admitted_sessions"])
    return admitted, base, ext


def collect(con, admitted):
    """Candidate cells = every (ticker, session) at/after the contemporaneous
    boundary that has either a daily row or bars. Rule precedence: X3 (session
    level) first, then the E-PIT rules."""
    c = con.cursor()
    first = ADM.CONTEMPORANEOUS_FIRST_SESSION

    prov = {}
    for tk, sd, ua in c.execute(
            "SELECT ticker, trade_date, updated_at FROM stockbit_flow "
            "WHERE trade_date >= ? AND trade_date != ''", (first,)):
        prov[(tk, sd)] = ua

    nbars = {}
    tickers = sorted({tk for (tk, _sd) in prov})
    for tk in tickers:
        for sd, n in c.execute(
                "SELECT trade_date, COUNT(*) FROM stockbit_flow_bars "
                "WHERE ticker = ? AND trade_date >= ? GROUP BY trade_date",
                (tk, first)):
            nbars[(tk, sd)] = n

    rows = []
    for key in sorted(set(prov) | set(nbars)):
        tk, sd = key
        ua = prov.get(key)
        nb = nbars.get(key)
        if sd not in admitted:
            v_rule, v_detail = "X3", ("session not admitted by session_calendar "
                                      "(base v2 + extension v1)")
        else:
            verdict = ADM.admissible(sd, ua, nb)
            v_rule, v_detail = verdict.rule, verdict.detail
        try:
            lag = ADM.write_lag_days(sd, ua) if ua else None
        except Exception:
            lag = None
        rows.append((tk, sd, ua, lag, nb, ADM.expected_bars(sd),
                     1 if v_rule is None else 0, v_rule, v_detail,
                     "stockbit_flow.updated_at (pre-activation proxy)"))
    return rows


def epit1_scale(con):
    c = con.cursor()
    return c.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM stockbit_flow_bars "
        "WHERE trade_date <= ? GROUP BY ticker, trade_date)",
        (ADM.V002_LAST_SESSION,)).fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    admitted, base_cal, ext_cal = calendar_admitted()

    # X1/X2 subsumption assertion (structural, verified not assumed): both
    # exclusion regions end before the contemporaneous window begins.
    assert max("2025-04-14", "2025-09-17") < ADM.CONTEMPORANEOUS_FIRST_SESSION

    con = ro(PROD)
    rows = collect(con, admitted)

    adm = [r for r in rows if r[6] == 1]
    by_rule = Counter(r[7] for r in rows if r[6] == 0)
    sessions_adm = sorted({r[1] for r in adm})
    tickers_adm = {r[0] for r in adm}
    sessions_all = sorted({r[1] for r in rows})
    x3_sessions = sorted({r[1] for r in rows if r[7] == "X3"})

    print("=== I7 v004 ADMISSIBLE-COHORT FREEZE — accounting ===")
    print(f"candidate cells (session >= {ADM.CONTEMPORANEOUS_FIRST_SESSION}): {len(rows):,}")
    print(f"ADMISSIBLE ticker-days : {len(adm):,}")
    print(f"ADMISSIBLE sessions    : {len(sessions_adm)}"
          + (f"  ({sessions_adm[0]} .. {sessions_adm[-1]})" if sessions_adm else ""))
    print(f"ADMISSIBLE tickers     : {len(tickers_adm)}")
    print(f"ADMISSIBLE bar rows    : {sum(r[4] or 0 for r in adm):,}")
    print()
    print("exclusions inside the contemporaneous window:")
    for rule in ("X3", "E-PIT-2", "E-PIT-3", "E-PIT-4"):
        print(f"  {rule:8s} {by_rule.get(rule, 0):>8,}")
    print()
    print(f"X3 sessions ({len(x3_sessions)}): {x3_sessions}")
    base_excluded = {e["date"] for e in base_cal["excluded"]}
    x3_kind = {s: ("calendar-excluded" if s in base_excluded
                   else "absent from calendar (holiday / beyond window)")
               for s in x3_sessions}
    for s in x3_sessions:
        print(f"  X3 {s}  ({x3_kind[s]})")
    print(f"calendar-admitted sessions in window: "
          f"{len([s for s in sessions_all if s in admitted])} of {len(sessions_all)}")
    # X3 evaluability: every session the readiness review listed as
    # unevaluable (2026-08-28..2026-09-11) must now carry an explicit
    # calendar determination (extension artifact admits it).
    review_unevaluable = ["2026-08-28", "2026-08-31", "2026-09-01", "2026-09-02",
                          "2026-09-03", "2026-09-04", "2026-09-07", "2026-09-08",
                          "2026-09-09", "2026-09-10", "2026-09-11"]
    missing = [s for s in review_unevaluable
               if s not in set(ext_cal["admitted_sessions"])]
    print(f"X3 evaluable for all 11 review-listed sessions: {not missing}"
          + (f"  MISSING: {missing}" if missing else ""))
    if missing:
        raise SystemExit("ABORT: X3 still unevaluable for " + repr(missing))
    print()
    print("E-PIT-1 (wholesale historical interval, outside the candidate set):")
    print(f"  ticker-days with bars at session <= {ADM.V002_LAST_SESSION}: "
          f"{epit1_scale(con):,}")
    print()
    per_sess = defaultdict(int)
    for r in adm:
        per_sess[r[1]] += 1
    if per_sess:
        v = sorted(per_sess.values())
        print(f"admissible cells per session: min={v[0]} p50={v[len(v)//2]} max={v[-1]}")
    # hard verification: no admitted cell carries a same-day write before the
    # 16:15 WIB cutoff (lag==0 alone is legitimate when written AFTER cutoff)
    pre_cutoff_admitted = sum(
        1 for r in adm
        if r[3] == 0 and _dt.time.fromisoformat(r[2][11:19]) < ADM.CUTOFF_WIB)
    print(f"same-day pre-cutoff cells admitted: {pre_cutoff_admitted} (must be 0)")
    if pre_cutoff_admitted:
        raise SystemExit("ABORT: pre-cutoff cell admitted — ledger would be invalid")

    if not a.write:
        print("\nDRY RUN — nothing written. Pass --write to materialise.")
        return 0

    os.makedirs(STORE_DIR, exist_ok=True)
    if os.path.exists(STORE):
        print(f"\nREFUSING: {STORE} already exists. A freeze is immutable; "
              f"build a new version rather than overwriting.")
        return 2

    out = sqlite3.connect(STORE)
    out.executescript("""
CREATE TABLE IF NOT EXISTS flow_bars_v004 (
  ticker TEXT NOT NULL, trade_date TEXT NOT NULL, bar_time TEXT NOT NULL,
  buy_lot INTEGER, sell_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
  net_value INTEGER, price REAL, delta INTEGER,
  PRIMARY KEY (ticker, trade_date, bar_time)
) WITHOUT ROWID;

-- EVERY candidate cell, admitted or not, with the rule that excluded it.
CREATE TABLE IF NOT EXISTS admissibility_ledger (
  ticker TEXT NOT NULL, session_date TEXT NOT NULL,
  captured_at_wib TEXT, write_lag_days INTEGER,
  n_bars INTEGER, expected_bars INTEGER,
  admissible INTEGER NOT NULL, exclusion_rule TEXT, detail TEXT,
  provenance_source TEXT NOT NULL,
  PRIMARY KEY (ticker, session_date)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS freeze_manifest (key TEXT PRIMARY KEY, value TEXT);
""")
    out.executemany("INSERT INTO admissibility_ledger VALUES (?,?,?,?,?,?,?,?,?,?)",
                    rows)

    cur = con.cursor()
    copied = 0
    for tk, sd in sorted({(r[0], r[1]) for r in adm}):
        bars = cur.execute(
            "SELECT ticker, trade_date, bar_time, buy_lot, sell_lot, buy_freq, "
            "sell_freq, net_value, price, delta FROM stockbit_flow_bars "
            "WHERE ticker=? AND trade_date=?", (tk, sd)).fetchall()
        out.executemany("INSERT INTO flow_bars_v004 VALUES (?,?,?,?,?,?,?,?,?,?)",
                        bars)
        copied += len(bars)
    out.commit()

    spec_exclusions = {
        "X1": "subsumed by E-PIT-1 (2025-04-14 fixture <= 2026-04-27 boundary; "
              "asserted by the builder)",
        "X2": "subsumed by E-PIT-1 (2025-08-04..2025-09-17 zone <= 2026-04-27 "
              "boundary; asserted by the builder)",
        "X3": "ENFORCED at cohort layer: session not admitted by "
              "session_calendar (base v2 + extension v1); "
              f"excluded sessions in window: {x3_sessions}",
        "X4": "ENFORCED as E-PIT-4 (bars present, n_bars == weekday grid)",
        "X5": "ESTIMATION-LAYER (ohlcv: corporate action t/t+1/t+2, RAJA, "
              "close(t)<100, liquidity floor) — applied and counted by the "
              "estimator; deliberately not applied at accrual",
        "X6": "ESTIMATION-LAYER (t,t+1,t+2 consecutivity) — applied and "
              "counted by the estimator; deliberately not applied at accrual",
    }
    meta = {
        "dataset_version": "I7-admissible-v004",
        "freeze_status": "FROZEN",
        "supersedes": "I7-admissible-v003 (mechanical correction only: X3 "
                      "enforcement + calendar extension; substantive "
                      "specification unchanged; v003 left immutable)",
        "built_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "source_production_db": PROD,
        "admissibility_module_sha256": hashlib.sha256(
            open(os.path.join(HERE, "i7_admissibility.py"), "rb").read()).hexdigest(),
        "builder_sha256": hashlib.sha256(
            open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "rules": ADM.RULES,
        "cutoff_wib": ADM.CUTOFF_WIB.isoformat(),
        "v002_last_session": ADM.V002_LAST_SESSION,
        "session_calendar": {
            "base": {"artifact": "DATASET_B_SESSION_CALENDAR_v2.json",
                     "sha256": BASE_CAL_SHA,
                     "sessions": len(base_cal["sessions"]),
                     "last_session": base_cal["sessions"][-1]},
            "extension": {"artifact": "I7_SESSION_CALENDAR_EXTENSION_v1.json",
                          "sha256": EXT_CAL_SHA,
                          "sessions": len(ext_cal["admitted_sessions"]),
                          "window": ext_cal["extension_window"]},
        },
        "spec_exclusions_x1_to_x6": spec_exclusions,
        "x3_excluded_sessions_in_window": x3_sessions,
        "admissible_ticker_days": len(adm),
        "admissible_sessions": len(sessions_adm),
        "admissible_tickers": len(tickers_adm),
        "admissible_bar_rows": copied,
        "session_range": [sessions_adm[0], sessions_adm[-1]] if sessions_adm else None,
        "candidate_cells": len(rows),
        "exclusions_in_window": {k: by_rule.get(k, 0)
                                 for k in ("X3", "E-PIT-2", "E-PIT-3", "E-PIT-4")},
        "epit1_excluded_ticker_days_with_bars": epit1_scale(con),
        "same_day_pre_cutoff_cells_admitted": pre_cutoff_admitted,
        "outcome_blind": "no close, return, or outcome column is read by the "
                         "builder; admissible() signature unchanged "
                         "(session_date, captured_at_wib, n_bars)",
    }
    out.executemany("INSERT INTO freeze_manifest VALUES (?,?)",
                    [(k, json.dumps(v)) for k, v in meta.items()])
    out.commit()
    out.execute("VACUUM")
    out.close()
    con.close()

    meta["store_sha256"] = sha256_file(STORE)
    meta["store_bytes"] = os.path.getsize(STORE)

    with open(MANIFEST, "w") as f:
        json.dump(meta, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(MANIFEST + ".sha256", "w") as f:
        f.write(hashlib.sha256(open(MANIFEST, "rb").read()).hexdigest() + "\n")

    os.chmod(STORE, 0o444)
    os.chmod(MANIFEST, 0o444)
    print(f"\nFROZEN: {STORE}")
    print(f"  bar rows   : {copied:,}")
    print(f"  store bytes: {meta['store_bytes']:,}")
    print(f"  sha256     : {meta['store_sha256']}")
    print(f"  ledger reconciliation: {len(adm):,} admitted + "
          f"{sum(by_rule.values()):,} excluded = {len(rows):,} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
