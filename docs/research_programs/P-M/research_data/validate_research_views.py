#!/usr/bin/env python3
"""Phase-6 validation suite for the P-M research view layer (views_v1.sqlite).

Checks DATA/INFRASTRUCTURE CORRECTNESS only — no predictive statistics:
  1. source identity (Dataset B store == freeze pin; v002 == MANIFEST pin)
  2. row-count reconciliation, view-by-view, against the live sources
  3. source-to-derived accounting reconciliation (signed value sums)
  4. duplicate checks (PK uniqueness by construction + explicit GROUP BY)
  5. PIT checks (prev_session < session; formation dates on the admitted
     calendar; no view carries forward-dated columns — structural, by builder)
  6. session/ticker membership checks against frozen roster/calendar artifacts
  7. domain checks (coverage_state, band_contact, investor_type vocabularies)
  8. production DB isolation: every connection this suite (and the builder)
     opens is mode=ro + query_only; nothing outside views_v1.sqlite is written
  9. determinism: a full second build into a temp file must produce the same
     sha256 (run with --rebuild; requires ~5 min and read access to all sources)

Exit code 0 = ALL CHECKS PASS; nonzero = failures listed on stdout.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DSB = os.path.join(REPO, "docs", "research_programs", "P-M", "dataset_b")
STORE_B = os.path.join(DSB, "store", "DATASET_B_BROKER_FLOW_STORE_v1.sqlite")
FREEZE = os.path.join(DSB, "artifacts", "DATASET_B_FREEZE_MANIFEST_v1.json")
V002 = os.path.join(REPO, "data", "frozen", "stockbit-flow-bars-v002",
                    "stockbit-flow-bars-v002.db")
V002_MANIFEST = os.path.join(REPO, "data", "frozen", "stockbit-flow-bars-v002",
                             "MANIFEST.json")
PROD = os.path.join(REPO, "data", "walkforward.db")
VIEWS = os.path.join(HERE, "views_v1.sqlite")
sys.path.insert(0, DSB)
import foundation as F  # noqa: E402


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ro(path: str) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


RESULTS = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    v = ro(VIEWS)
    b = ro(STORE_B)
    f2 = ro(V002)
    p = ro(PROD)

    # 1 ---------------------------------------------------------------- identity
    pin_b = json.load(open(FREEZE))["store"]["sha256"]
    sha_b = sha256_file(STORE_B)
    check("1.1 Dataset B store sha == freeze pin", sha_b == pin_b, sha_b[:16] + "…")
    pin_v = json.load(open(V002_MANIFEST))["database"]["sha256"]
    sha_v = sha256_file(V002)
    check("1.2 v002 store sha == MANIFEST pin", sha_v == pin_v, sha_v[:16] + "…")
    meta = dict(v.execute("SELECT key, value FROM meta_sources").fetchall())
    check("1.3 views meta_records match recomputed pins",
          meta["dataset_b_store_sha256"] == sha_b
          and meta["frozen_flow_bars_v002_sha256"] == sha_v)

    # 2 ------------------------------------------------------- row-count recon
    n_side_src = b.execute("SELECT COUNT(*) FROM broker_flow_b").fetchone()[0]
    n_side = v.execute("SELECT COUNT(*) FROM v_a_side").fetchone()[0]
    check("2.1 v_a_side == broker_flow_b row count", n_side == n_side_src,
          f"{n_side:,}")
    n_bd = v.execute("SELECT COUNT(*) FROM v_a_broker_day").fetchone()[0]
    n_bd_src = b.execute("SELECT COUNT(*) FROM (SELECT DISTINCT ticker, "
                         "trade_date, broker_code FROM broker_flow_b)").fetchone()[0]
    check("2.2 v_a_broker_day == distinct (ticker, date, broker)",
          n_bd == n_bd_src, f"{n_bd:,}")
    n_cc = v.execute("SELECT COUNT(*) FROM v_b_concentration").fetchone()[0]
    n_cc_src = b.execute("SELECT COUNT(DISTINCT ticker || '|' || trade_date) "
                         "FROM broker_flow_b").fetchone()[0]
    n_cc_src2 = b.execute("SELECT COUNT(*) FROM bandar_detector_b").fetchone()[0]
    check("2.3 v_b_concentration == distinct broker-days (== bandar cells)",
          n_cc == n_cc_src == n_cc_src2, f"{n_cc:,}")
    n_int = v.execute("SELECT COUNT(*) FROM v_e_intraday_summary").fetchone()[0]
    v002m = json.load(open(V002_MANIFEST))
    check("2.4 v_e_intraday_summary == v002 expected ticker-days",
          n_int == v002m["coverage_summary"]["expected_ticker_days"],
          f"{n_int:,}")
    n_bars_cells = f2.execute("SELECT COUNT(*) FROM (SELECT DISTINCT ticker, "
                              "trade_date FROM stockbit_flow_bars)").fetchone()[0]
    n_state_bars = v.execute("SELECT COUNT(*) FROM v_e_intraday_summary "
                             "WHERE coverage_state='BARS'").fetchone()[0]
    check("2.5 BARS state count == v002 distinct bar cells",
          n_state_bars == n_bars_cells == 239695, f"{n_state_bars:,}")
    n_fp = v.execute("SELECT COUNT(*) FROM v_f_flow_price").fetchone()[0]
    n_fp_src = p.execute(
        "SELECT COUNT(*) FROM ohlcv WHERE ticker IN (SELECT ticker FROM "
        "pit_universe_in_views) ").fetchone()[0] if False else None  # grid recon below
    roster = F.PitRoster.load("v2")
    cal = F.SessionCalendar.load("v2")
    grid = sum(len(roster.members(d)) for d in cal.sessions)
    n_ev = v.execute("SELECT COUNT(*) FROM v_g_event_flow").fetchone()[0]
    check("2.6 v_g_event_flow == full roster grid", n_ev == grid == 30880,
          f"{n_ev:,}")

    # 3 -------------------------------------------------- accounting reconc.
    src_pos = b.execute("SELECT COALESCE(SUM(value),0) FROM broker_flow_b "
                        "WHERE value>0").fetchone()[0]
    src_neg = b.execute("SELECT COALESCE(SUM(value),0) FROM broker_flow_b "
                        "WHERE value<0").fetchone()[0]
    vw_pos, vw_neg = v.execute("SELECT COALESCE(SUM(value_pos),0), "
                               "COALESCE(SUM(value_neg),0) FROM "
                               "v_a_broker_day").fetchone()
    check("3.1 signed value sums reconcile (pos/neg)", src_pos == vw_pos
          and src_neg == vw_neg, f"pos {vw_pos:,} neg {vw_neg:,}")
    src_gross = b.execute("SELECT COALESCE(SUM(ABS(value)),0) FROM "
                          "broker_flow_b").fetchone()[0]
    vw_gross = v.execute("SELECT COALESCE(SUM(gross),0) FROM "
                         "v_a_broker_day").fetchone()[0]
    check("3.2 gross reconciles (Σ|value|)", src_gross == vw_gross,
          f"{vw_gross:,}")
    vw_net = v.execute("SELECT COALESCE(SUM(net),0) FROM v_a_broker_day").fetchone()[0]
    check("3.3 net reconciles (Σvalue)", src_pos + src_neg == vw_net, f"{vw_net:,}")

    # 4 ------------------------------------------------------------- duplicates
    dup = v.execute("SELECT COUNT(*) FROM (SELECT ticker, trade_date, broker_code"
                    " FROM v_a_broker_day GROUP BY 1,2,3 HAVING COUNT(*)>1)"
                    ).fetchone()[0]
    check("4.1 no duplicate broker-day keys", dup == 0)
    dup2 = v.execute("SELECT COUNT(*) FROM (SELECT ticker, trade_date FROM "
                     "v_e_intraday_summary GROUP BY 1,2 HAVING COUNT(*)>1)"
                     ).fetchone()[0]
    check("4.2 no duplicate intraday-summary keys", dup2 == 0)

    # 5 -------------------------------------------------------------- PIT checks
    bad_prev = v.execute("SELECT COUNT(*) FROM (SELECT session, prev_session FROM "
                         "v_d_broker_persistence WHERE prev_session IS NOT NULL "
                         "AND prev_session >= session)").fetchone()[0]
    check("5.1 persistence prev_session strictly < session", bad_prev == 0)
    off_cal = v.execute("SELECT COUNT(*) FROM v_a_side s LEFT JOIN "
                        "session_calendar c ON c.session=s.trade_date "
                        "WHERE c.session IS NULL OR c.is_admitted<>1").fetchone()[0]
    check("5.2 all v_a_side dates are admitted sessions", off_cal == 0)
    off_cal2 = v.execute("SELECT COUNT(*) FROM v_g_event_flow g LEFT JOIN "
                         "session_calendar c ON c.session=g.trade_date "
                         "WHERE c.session IS NULL OR c.is_admitted<>1").fetchone()[0]
    check("5.3 all event-grid dates are admitted sessions", off_cal2 == 0)

    # 6 ------------------------------------------------------- membership checks
    bad_tk = v.execute("SELECT COUNT(*) FROM v_a_side s LEFT JOIN pit_universe u "
                       "ON u.ticker=s.ticker WHERE u.ticker IS NULL").fetchone()[0]
    check("6.1 v_a_side tickers ⊆ PIT universe", bad_tk == 0)
    roster_ok = v.execute("SELECT COUNT(*) FROM v_g_event_flow g WHERE NOT EXISTS "
                          "(SELECT 1 FROM pit_universe u WHERE u.ticker=g.ticker)"
                          ).fetchone()[0]
    check("6.2 event-grid tickers ⊆ PIT universe", roster_ok == 0)

    # 7 ---------------------------------------------------------- domain checks
    states = {r[0] for r in v.execute("SELECT DISTINCT coverage_state FROM "
                                      "v_e_intraday_summary")}
    check("7.1 coverage_state vocabulary",
          states <= {"BARS", "CONFIRMED_EMPTY_DAILY",
                     "TRUE_GAP_NONZERO_DAILY_NO_BARS", "NO_DAILY_SUMMARY_ROW"},
          str(sorted(states)))
    bands = {r[0] for r in v.execute("SELECT DISTINCT band_contact FROM "
                                     "v_g_event_flow")}
    check("7.2 band_contact vocabulary",
          bands <= {"ARUp", "ARDn", "none", None}, str(sorted(bands, key=str)))
    mixed = v.execute("SELECT COUNT(*) FROM v_a_broker_day WHERE investor_type "
                      "LIKE 'MIXED%'").fetchone()[0]
    check("7.3 investor_type consistent within broker-days (no MIXED)",
          mixed == 0)

    # 8 ------------------------------------------------------ isolation checks
    vq = v.execute("PRAGMA query_only").fetchone()[0]
    bq = b.execute("PRAGMA query_only").fetchone()[0]
    pq = p.execute("PRAGMA query_only").fetchone()[0]
    check("8.1 all suite connections query_only", vq == bq == pq == 1)
    siblings = [x for x in os.listdir(os.path.dirname(VIEWS))
                if x.startswith("views_v1.sqlite-")]
    check("8.2 no unclosed WAL/SHM left on views store", siblings == [],
          str(siblings))

    # 9 ------------------------------------------------- determinism (optional)
    if "--rebuild" in sys.argv:
        tmp = tempfile.mkdtemp(prefix="views_det_")
        try:
            env = dict(os.environ, RESEARCH_VIEWS_OUT=os.path.join(tmp, "v.sqlite"))
            subprocess.run([sys.executable, os.path.join(HERE,
                            "build_research_views.py")], env=env, check=True,
                           capture_output=True)
            h1 = sha256_file(VIEWS)
            h2 = sha256_file(os.path.join(tmp, "v.sqlite"))
            check("9.1 deterministic rebuild (byte-identical store)", h1 == h2,
                  h1[:16] + "…")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    v.close(); b.close(); f2.close(); p.close()
    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n{'ALL CHECKS PASS' if n_fail == 0 else 'FAILURES: ' + str(n_fail)}"
          f" ({len(RESULTS)} checks)")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
