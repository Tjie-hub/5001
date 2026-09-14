#!/usr/bin/env python3
"""Build the I7 v003 admissible-cohort freeze.

READ-ONLY against production. Writes only to this package's own store/.
Never touches data/walkforward.db, Dataset B, or the v002 freeze.

  python3 build_v003_freeze.py            # dry run: full exclusion accounting
  python3 build_v003_freeze.py --write    # materialise the immutable freeze

Outcome-blind by construction: the only production columns read are the bar
fields, `stockbit_flow.updated_at` (provenance), and the session calendar. No
close, no return, no outcome column is read anywhere in this file.
"""
from __future__ import annotations

import argparse, datetime as _dt, hashlib, json, os, sqlite3, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import i7_admissibility as ADM  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PROD = os.path.join(REPO, "data", "walkforward.db")
STORE_DIR = os.path.join(HERE, "store")
STORE = os.path.join(STORE_DIR, "I7_V003_ADMISSIBLE_v1.sqlite")

BAR_COLS = ("ticker", "trade_date", "bar_time", "buy_lot", "sell_lot",
            "buy_freq", "sell_freq", "net_value", "price", "delta")

DDL = """
CREATE TABLE IF NOT EXISTS flow_bars_v003 (
  ticker TEXT NOT NULL, trade_date TEXT NOT NULL, bar_time TEXT NOT NULL,
  buy_lot INTEGER, sell_lot INTEGER, buy_freq INTEGER, sell_freq INTEGER,
  net_value INTEGER, price REAL, delta INTEGER,
  PRIMARY KEY (ticker, trade_date, bar_time)
) WITHOUT ROWID;

-- EVERY candidate cell, admitted or not, with the rule that excluded it.
-- This is the audit trail: exclusions are enumerated, never silent.
CREATE TABLE IF NOT EXISTS admissibility_ledger (
  ticker TEXT NOT NULL, session_date TEXT NOT NULL,
  captured_at_wib TEXT, write_lag_days INTEGER,
  n_bars INTEGER, expected_bars INTEGER,
  admissible INTEGER NOT NULL, exclusion_rule TEXT, detail TEXT,
  provenance_source TEXT NOT NULL,
  PRIMARY KEY (ticker, session_date)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS freeze_manifest (key TEXT PRIMARY KEY, value TEXT);
"""


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def collect(con):
    """Candidate cells = every (ticker, session) at/after the contemporaneous
    boundary that has either a daily row or bars. Returns the ledger rows."""
    c = con.cursor()
    first = ADM.CONTEMPORANEOUS_FIRST_SESSION

    prov = {}
    for tk, sd, ua in c.execute(
            "SELECT ticker, trade_date, updated_at FROM stockbit_flow "
            "WHERE trade_date >= ? AND trade_date != ''", (first,)):
        prov[(tk, sd)] = ua

    # Per-TICKER, so each query is a covering range scan on the primary key
    # (ticker, trade_date, bar_time). A per-date query would instead use
    # idx_flow_bars_date, which is not covering, and pay ~26M random row
    # fetches; a single grouped scan would walk all ~98M index entries.
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
        v = ADM.admissible(sd, ua, nb)
        try:
            lag = ADM.write_lag_days(sd, ua) if ua else None
        except Exception:
            lag = None
        rows.append((tk, sd, ua, lag, nb, ADM.expected_bars(sd),
                     1 if v.admissible else 0, v.rule, v.detail,
                     "stockbit_flow.updated_at (pre-activation proxy)"))
    return rows


def epit1_scale(con):
    """Size of the wholesale E-PIT-1 exclusion, for the report."""
    c = con.cursor()
    cells = c.execute("SELECT COUNT(*) FROM (SELECT 1 FROM stockbit_flow_bars "
                      "WHERE trade_date <= ? GROUP BY ticker, trade_date)",
                      (ADM.V002_LAST_SESSION,)).fetchone()[0]
    return cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    con = ro(PROD)
    rows = collect(con)

    adm = [r for r in rows if r[6] == 1]
    by_rule = Counter(r[7] for r in rows if r[6] == 0)
    sessions_adm = sorted({r[1] for r in adm})
    tickers_adm = {r[0] for r in adm}

    print("=== I7 v003 ADMISSIBLE-COHORT FREEZE — accounting ===")
    print(f"candidate cells (session >= {ADM.CONTEMPORANEOUS_FIRST_SESSION}): {len(rows):,}")
    print(f"ADMISSIBLE ticker-days : {len(adm):,}")
    print(f"ADMISSIBLE sessions    : {len(sessions_adm)}"
          + (f"  ({sessions_adm[0]} .. {sessions_adm[-1]})" if sessions_adm else ""))
    print(f"ADMISSIBLE tickers     : {len(tickers_adm)}")
    print(f"ADMISSIBLE bar rows    : {sum(r[4] or 0 for r in adm):,}")
    print()
    print("exclusions inside the contemporaneous window:")
    for rule in ("E-PIT-2", "E-PIT-3", "E-PIT-4"):
        print(f"  {rule}  {ADM.RULES[rule]:<58s} {by_rule.get(rule,0):>8,}")
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

    if not a.write:
        print("\nDRY RUN — nothing written. Pass --write to materialise.")
        return 0

    os.makedirs(STORE_DIR, exist_ok=True)
    if os.path.exists(STORE):
        print(f"\nREFUSING: {STORE} already exists. A freeze is immutable; "
              f"build a new version rather than overwriting.")
        return 2

    out = sqlite3.connect(STORE)
    out.executescript(DDL)
    out.executemany("INSERT INTO admissibility_ledger VALUES (?,?,?,?,?,?,?,?,?,?)", rows)

    cur = con.cursor()
    copied = 0
    for tk, sd in sorted({(r[0], r[1]) for r in adm}):
        bars = cur.execute(
            f"SELECT {','.join(BAR_COLS)} FROM stockbit_flow_bars "
            "WHERE ticker=? AND trade_date=?", (tk, sd)).fetchall()
        out.executemany("INSERT INTO flow_bars_v003 VALUES (?,?,?,?,?,?,?,?,?,?)", bars)
        copied += len(bars)
    out.commit()

    meta = {
        "dataset_version": "I7-admissible-v003",
        "freeze_status": "FROZEN",
        "built_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "source_production_db": PROD,
        "admissibility_module_sha256": hashlib.sha256(
            open(os.path.join(HERE, "i7_admissibility.py"), "rb").read()).hexdigest(),
        "builder_sha256": hashlib.sha256(
            open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "rules": ADM.RULES,
        "cutoff_wib": ADM.CUTOFF_WIB.isoformat(),
        "v002_last_session": ADM.V002_LAST_SESSION,
        "admissible_ticker_days": len(adm),
        "admissible_sessions": len(sessions_adm),
        "admissible_tickers": len(tickers_adm),
        "admissible_bar_rows": copied,
        "session_range": [sessions_adm[0], sessions_adm[-1]] if sessions_adm else None,
        "exclusions_in_window": {k: by_rule.get(k, 0) for k in ("E-PIT-2", "E-PIT-3", "E-PIT-4")},
        "epit1_excluded_ticker_days_with_bars": epit1_scale(con),
        "outcome_blind": "no close, return, or outcome column is read by the builder",
    }
    out.executemany("INSERT INTO freeze_manifest VALUES (?,?)",
                    [(k, json.dumps(v)) for k, v in meta.items()])
    out.commit()
    out.execute("VACUUM")
    out.close()
    con.close()

    h = hashlib.sha256()
    with open(STORE, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    meta["store_sha256"] = h.hexdigest()
    meta["store_bytes"] = os.path.getsize(STORE)

    mpath = os.path.join(STORE_DIR, "I7_V003_MANIFEST.json")
    with open(mpath, "w") as f:
        json.dump(meta, f, indent=1, sort_keys=True)
        f.write("\n")
    with open(mpath + ".sha256", "w") as f:
        f.write(hashlib.sha256(open(mpath, "rb").read()).hexdigest() + "\n")

    os.chmod(STORE, 0o444)
    os.chmod(mpath, 0o444)
    print(f"\nFROZEN: {STORE}")
    print(f"  bar rows   : {copied:,}")
    print(f"  store bytes: {meta['store_bytes']:,}")
    print(f"  sha256     : {meta['store_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
