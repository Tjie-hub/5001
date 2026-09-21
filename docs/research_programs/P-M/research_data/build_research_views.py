#!/usr/bin/env python3
"""P-M research-data view layer v1 — DATA VIEWS ONLY (no hypotheses, no signals).

Builds docs/research_programs/P-M/research_data/views_v1.sqlite from read-only
sources: broker-level structure, concentration, pair structure, persistence,
intraday sequence, flow x price co-registration, event-conditioning joins.
NO hypothesis-specific threshold, NO outcome selection, NO tuning is embedded.

Guarantees (enforced):
  * READ-ONLY on every source (mode=ro + query_only).
  * Fail-closed source identity: Dataset B store must match the freeze-manifest
    pin; the frozen flow-bars store must match its MANIFEST sha256.
  * PIT: every materialized field is a function of information dated <= t.
  * Deterministic: same source bytes + same code => identical content hashes.
  * Writes ONLY views_v1.sqlite in this directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DSB = os.path.join(REPO, "docs", "research_programs", "P-M", "dataset_b")
STORE_B = os.path.join(DSB, "store", "DATASET_B_BROKER_FLOW_STORE_v1.sqlite")
FREEZE_MANIFEST = os.path.join(DSB, "artifacts", "DATASET_B_FREEZE_MANIFEST_v1.json")
V002 = os.path.join(REPO, "data", "frozen", "stockbit-flow-bars-v002",
                    "stockbit-flow-bars-v002.db")
V002_MANIFEST = os.path.join(REPO, "data", "frozen", "stockbit-flow-bars-v002",
                             "MANIFEST.json")
PROD = os.path.join(REPO, "data", "walkforward.db")
OUT = os.environ.get("RESEARCH_VIEWS_OUT",
                     os.path.join(HERE, "views_v1.sqlite"))

sys.path.insert(0, DSB)
import foundation as F  # noqa: E402  (read-only loaders + pure band functions)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ro_connect(path: str) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def content_sha(conn: sqlite3.Connection, table: str, order_by: str) -> str:
    """Deterministic content hash: rows streamed in PK order, canonical per-row."""
    h = hashlib.sha256()
    cur = conn.execute(f"SELECT * FROM {table} ORDER BY {order_by}")
    while True:
        batch = cur.fetchmany(50_000)
        if not batch:
            break
        for row in batch:
            h.update(json.dumps(row, sort_keys=True, default=str).encode())
            h.update(b"\n")
    return h.hexdigest()


def main() -> int:
    # ---------------------------------------------------------- source identity
    freeze = json.load(open(FREEZE_MANIFEST))
    store_sha = sha256_file(STORE_B)
    if store_sha != freeze["store"]["sha256"]:
        raise SystemExit(f"ABORT: Dataset B store sha {store_sha[:12]}… != freeze pin")
    v002_manifest = json.load(open(V002_MANIFEST))
    v002_sha = sha256_file(V002)
    if v002_sha != v002_manifest["database"]["sha256"]:
        raise SystemExit(f"ABORT: frozen flow-bars sha {v002_sha[:12]}… != MANIFEST pin")

    b = ro_connect(STORE_B)        # Dataset B broker-flow store (frozen)
    f2 = ro_connect(V002)          # frozen 1-minute flow bars (frozen)
    p = ro_connect(PROD)           # production (read-only; window extracts only)

    roster = F.PitRoster.load("v2")
    cal = F.SessionCalendar.load("v2")
    sessions = cal.sessions
    uni = sorted(roster.universe)
    lo, hi = sessions[0], sessions[-1]

    if os.path.exists(OUT):
        os.remove(OUT)             # rebuild always from scratch (determinism)
    v = sqlite3.connect(f"file:{OUT}", uri=True)  # uri=True => ro ATTACH allowed
    v.executescript("""
    PRAGMA journal_mode = DELETE;
    CREATE TABLE meta_sources (
      key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE meta_view_catalog (
      view_name TEXT PRIMARY KEY, grain TEXT NOT NULL, source TEXT NOT NULL,
      row_count INTEGER, content_sha256 TEXT NOT NULL, notes TEXT);
    CREATE TABLE session_calendar (
      session TEXT PRIMARY KEY, is_admitted INTEGER NOT NULL, exclude_reason TEXT);
    CREATE TABLE pit_universe (
      ticker TEXT PRIMARY KEY);
    CREATE TABLE v_a_side (                       -- exact frozen broker-side rows
      ticker TEXT NOT NULL, trade_date TEXT NOT NULL, broker_code TEXT NOT NULL,
      side TEXT NOT NULL, lot INTEGER, lot_value INTEGER, value INTEGER,
      value_total INTEGER, avg_price REAL, freq INTEGER, investor_type TEXT,
      capture_version TEXT NOT NULL,
      PRIMARY KEY (ticker, trade_date, broker_code, side));
    CREATE TABLE v_a_broker_day (                 -- broker x ticker x date (signed)
      ticker TEXT NOT NULL, trade_date TEXT NOT NULL, broker_code TEXT NOT NULL,
      value_pos INTEGER NOT NULL, value_neg INTEGER NOT NULL,
      gross INTEGER NOT NULL, net INTEGER NOT NULL,
      lot_pos INTEGER, lot_neg INTEGER, freq_sum INTEGER,
      n_rows INTEGER NOT NULL, n_buy_rows INTEGER NOT NULL, n_sell_rows INTEGER NOT NULL,
      investor_type TEXT NOT NULL, vwap_value REAL,
      PRIMARY KEY (ticker, trade_date, broker_code));
    CREATE TABLE v_b_concentration (              -- per ticker-date, no thresholds
      ticker TEXT NOT NULL, trade_date TEXT NOT NULL,
      n_brokers INTEGER, n_buy_brokers INTEGER, n_sell_brokers INTEGER,
      gross INTEGER, net INTEGER,
      top1_gross_share REAL, top3_gross_share REAL, top5_gross_share REAL,
      hhi_gross REAL,
      bandar_total_buyer INTEGER, bandar_total_seller INTEGER,
      bandar_net_broker_count INTEGER,
      bandar_top1_accdist REAL, bandar_top3_accdist REAL,
      bandar_top5_accdist REAL, bandar_top10_accdist REAL,
      PRIMARY KEY (ticker, trade_date));
    CREATE TABLE v_e_intraday_summary (           -- 1-minute coverage, frozen v002
      ticker TEXT NOT NULL, trade_date TEXT NOT NULL,
      n_bars INTEGER, first_bar_time TEXT, last_bar_time TEXT,
      buy_lot_sum INTEGER, sell_lot_sum INTEGER, net_value_sum INTEGER,
      delta_sum REAL,
      daily_flow_present INTEGER, two_sided_lots INTEGER,
      coverage_state TEXT NOT NULL,
      PRIMARY KEY (ticker, trade_date));
    CREATE TABLE v_f_flow_price (                 -- flow x price co-registration
      ticker TEXT NOT NULL, trade_date TEXT NOT NULL,
      close REAL, prev_close REAL, volume REAL, traded_value REAL,
      high REAL, low REAL, day_range REAL, ret1 REAL,
      sb_buy_lot INTEGER, sb_sell_lot INTEGER, sb_two_sided_lot INTEGER,
      sb_net_lot INTEGER, sb_net_value INTEGER,
      broker_gross INTEGER, broker_net INTEGER,
      sb_lot_over_volume REAL, broker_gross_over_traded_value REAL,
      PRIMARY KEY (ticker, trade_date));
    CREATE TABLE v_g_event_flow (                 -- event-conditioning join keys
      ticker TEXT NOT NULL, trade_date TEXT NOT NULL,
      in_suspension_window INTEGER NOT NULL,
      ca_ex_date INTEGER NOT NULL, ca_factor REAL, ca_applied_in_ohlcv INTEGER,
      bandar_imbalance_buyers INTEGER, bandar_imbalance_sellers INTEGER,
      band_contact TEXT, band_regime TEXT, band_exceeds INTEGER,
      PRIMARY KEY (ticker, trade_date));
    """)

    # ------------------------------------------------------------ calendar / universe
    v.executemany("INSERT INTO session_calendar VALUES (?,?,?)",
                  [(d, 1, None) for d in sessions] +
                  [(d, 0, r) for d, r in sorted(cal.excluded.items())])
    v.executemany("INSERT INTO pit_universe VALUES (?)", [(t,) for t in uni])

    # ------------------------------------------------------- A: broker x tx side
    rows = b.execute("SELECT ticker, trade_date, broker_code, side, lot, lot_value,"
                     " value, value_total, avg_price, freq, investor_type,"
                     " capture_version FROM broker_flow_b").fetchall()
    v.executemany("INSERT INTO v_a_side VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    # ------------------------------------------------------- A: broker-day signed
    agg = {}
    for tk, d, bc, side, lot, lotv, val, vtot, ap, freq, itype, capv in rows:
        a = agg.setdefault((tk, d, bc), [0, 0, 0, 0, 0, 0, 0, 0, set(), 0, 0.0])
        val = val or 0
        if val > 0:
            a[0] += val; a[4] += (lot or 0); a[6] += 1
        elif val < 0:
            a[1] += val; a[5] += (lot or 0); a[7] += 1
        a[2] += abs(val); a[3] += val
        a[8].add(itype or "NULL")
        a[9] += (freq or 0)
        if ap:
            a[10] += abs(val) * ap
    broker_day = [(tk, d, bc, a[0], a[1], a[2], a[3], a[4], a[5], a[9],
                   a[6] + a[7], a[6], a[7],
                   ("MIXED:" + "+".join(sorted(a[8]))) if len(a[8]) > 1 else next(iter(a[8])),
                   (a[10] / a[2] if a[2] else None))
                  for (tk, d, bc), a in agg.items()]
    v.executemany("INSERT INTO v_a_broker_day VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  broker_day)

    # ------------------------------------------------------------- B: concentration
    by_day = {}
    for (tk, d, bc), a in agg.items():
        by_day.setdefault((tk, d), []).append((bc, a))
    bandar = {r[:2]: r[2:] for r in b.execute(
        "SELECT ticker, trade_date, total_buyer, total_seller, net_broker_count,"
        " top1_accdist, top3_accdist, top5_accdist, top10_accdist"
        " FROM bandar_detector_b")}
    conc = []
    for (tk, d), lst in by_day.items():
        grosses = sorted((a[2] for _, a in lst), reverse=True)
        g = sum(grosses)
        net = sum(a[3] for _, a in lst)
        n_buy = sum(1 for _, a in lst if a[0] > 0)
        n_sell = sum(1 for _, a in lst if a[1] < 0)
        bd = bandar.get((tk, d), (None,) * 8)
        conc.append((tk, d, len(lst), n_buy, n_sell, g, net,
                     grosses[0] / g if g else None,
                     sum(grosses[:3]) / g if g else None,
                     sum(grosses[:5]) / g if g else None,
                     (sum(x * x for x in grosses) / (g * g)) if g else None,
                     bd[0], bd[1], bd[2], bd[3], bd[4], bd[5], bd[6]))
    v.executemany("INSERT INTO v_b_concentration VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  conc)

    # ------------------------------------------- C/D: pair structure + persistence
    # SQL views only (lossless; limitations documented in the catalog).
    v.executescript("""
    CREATE VIEW v_c_pair_structure AS
      SELECT a.ticker, a.trade_date,
             a.broker_code AS broker_buy, b2.broker_code AS broker_sell,
             a.value_pos AS buy_value, ABS(b2.value_neg) AS sell_value,
             MIN(a.value_pos, ABS(b2.value_neg)) AS crossing_value
      FROM v_a_broker_day a
      JOIN v_a_broker_day b2
        ON a.ticker = b2.ticker AND a.trade_date = b2.trade_date
       AND a.value_pos > 0 AND b2.value_neg < 0;

    CREATE VIEW v_d_broker_persistence AS
      SELECT a.ticker, a.trade_date AS session,
             a.broker_code, a.gross, a.net,
             (SELECT MAX(session) FROM session_calendar
              WHERE is_admitted = 1 AND session < a.trade_date) AS prev_session
      FROM v_a_broker_day a;

    CREATE VIEW v_d_broker_activity AS
      SELECT broker_code, trade_date AS session,
             COUNT(DISTINCT ticker) AS n_tickers, SUM(gross) AS gross_total,
             SUM(net) AS net_total
      FROM v_a_broker_day GROUP BY broker_code, trade_date;
    """)

    # ----------------------------------------------------- E: intraday (frozen v002)
    # Grid = the frozen store's own daily-flow dates (self-consistent with v002).
    daily_flow = {}
    for tk, d, bl, sl in f2.execute(
            "SELECT ticker, trade_date, buy_lot, sell_lot FROM stockbit_flow"):
        daily_flow[(tk, d)] = (bl, sl)
    dates_v002 = sorted({d for (_, d) in daily_flow})
    bar_agg = {}
    for tk, d, n, bt_min, bt_max, sbl, ssl, snv, sdelta in f2.execute(
            "SELECT ticker, trade_date, COUNT(*), MIN(bar_time), MAX(bar_time),"
            " SUM(buy_lot), SUM(sell_lot), SUM(net_value), SUM(delta)"
            " FROM stockbit_flow_bars GROUP BY 1, 2"):
        bar_agg[(tk, d)] = [n, bt_min, bt_max, sbl or 0, ssl or 0, snv or 0,
                            sdelta or 0.0]
    uni_v002 = sorted(r[0] for r in f2.execute(
        "SELECT ticker FROM idx_tickers WHERE status='active'"))
    intraday = []
    for d in dates_v002:
        for tk in uni_v002:
            a = bar_agg.get((tk, d))
            bl, sl = daily_flow.get((tk, d), (None, None))
            tsl = (bl or 0) + (sl or 0) if bl is not None else None
            if a:
                state = "BARS"
            elif tsl is not None and tsl <= 0:
                state = "CONFIRMED_EMPTY_DAILY"
            elif tsl is not None:
                state = "TRUE_GAP_NONZERO_DAILY_NO_BARS"
            else:
                state = "NO_DAILY_SUMMARY_ROW"
            intraday.append((tk, d, a[0] if a else 0, a[1] if a else None,
                             a[2] if a else None, a[3] if a else None,
                             a[4] if a else None, a[5] if a else None,
                             a[6] if a else None,
                             1 if (tk, d) in daily_flow else 0, tsl, state))
    v.executemany("INSERT INTO v_e_intraday_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  intraday)

    # ------------------------------------------------------- F: flow x price
    px = {}
    for tk, d, c, hgh, lw, vlm in p.execute(
            "SELECT ticker, date, close, high, low, volume FROM ohlcv"
            " WHERE ticker IN (%s) AND date >= ? AND date <= ? AND is_final = 1"
            % ",".join("?" * len(uni)), uni + [lo, hi]):
        if d in cal._idx:
            px[(tk, d)] = (c, hgh, lw, vlm)
    sb = {}
    for tk, d, bl, sl, nl, nv in p.execute(
            "SELECT ticker, trade_date, buy_lot, sell_lot, net_lot, net_value"
            " FROM stockbit_flow WHERE ticker IN (%s)"
            " AND trade_date >= ? AND trade_date <= ?" % ",".join("?" * len(uni)),
            uni + [lo, hi]):
        sb[(tk, d)] = (bl, sl, nl, nv)
    flow_price = []
    for i, d in enumerate(sessions):
        prev_d = sessions[i - 1] if i > 0 else None
        for tk in roster.members(d):
            bar = px.get((tk, d))
            if not bar or not bar[0]:
                continue
            pc = px.get((tk, prev_d), (None,) * 4)[0] if prev_d else None
            c, hgh, lw, vlm = bar
            bl, sl, nl, nv = sb.get((tk, d), (None,) * 4)
            lst = by_day.get((tk, d))
            g = sum(a[2] for _, a in lst) if lst else None
            n = sum(a[3] for _, a in lst) if lst else None
            tsl = (bl or 0) + (sl or 0) if bl is not None and sl is not None else None
            rng = ((hgh - lw) / c) if (hgh and lw and c) else None
            flow_price.append((
                tk, d, c, pc, vlm, (c * vlm) if (c and vlm) else None,
                hgh, lw, rng, (c / pc - 1.0) if pc else None,
                bl, sl, tsl, nl, nv, g, n,
                (tsl / (2.0 * vlm)) if (tsl and vlm) else None,
                (g / (c * vlm)) if (g and c and vlm) else None))
    v.executemany("INSERT INTO v_f_flow_price VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  flow_price)

    # ------------------------------------------------------- G: event joins
    susp = set()
    for tk, ln, rd in p.execute(
            "SELECT ticker, last_normal_date, resume_date FROM suspension_events"):
        for d in sessions:
            if ln <= d <= rd:
                susp.add((tk, d))
    actions = F.detect_unapplied_splits(p, F.load_corporate_actions(p, uni, lo, hi))
    ca = {}
    for a in actions:
        ca.setdefault(a["ticker"], {})[a["ex_date"]] = a
    events = []
    for i, d in enumerate(sessions):
        for tk in roster.members(d):
            bar = px.get((tk, d))
            prev_d = sessions[i - 1] if i > 0 else None
            pc = px.get((tk, prev_d), (None,) * 4)[0] if prev_d else None
            c = bar[0] if bar else None
            exceeds = contact = None
            regime = F.band_regime(d)
            if c and pc and regime:
                up, dn = F.ara_arb(pc, d)
                r = c / pc - 1.0
                exceeds = int(r > up + F.BAND_TOLERANCE or r < dn - F.BAND_TOLERANCE)
                contact = ("ARUp" if r >= up - F.BAND_TOLERANCE
                           else "ARDn" if r <= dn + F.BAND_TOLERANCE else "none")
            a = ca.get(tk, {}).get(d)
            bd = bandar.get((tk, d), (None,) * 8)
            events.append((tk, d, int((tk, d) in susp),
                           int(a is not None), a["factor"] if a else None,
                           (int(a["applied_in_ohlcv"]) if a and
                            a.get("applied_in_ohlcv") is not None else None),
                           bd[0], bd[1], contact, regime, exceeds))
    v.executemany("INSERT INTO v_g_event_flow VALUES (?,?,?,?,?,?,?,?,?,?,?)", events)

    # ------------------------------------------------------------- catalog
    v.execute("INSERT INTO meta_sources VALUES ('dataset_b_store_sha256', ?)", (store_sha,))
    v.execute("INSERT INTO meta_sources VALUES ('frozen_flow_bars_v002_sha256', ?)", (v002_sha,))
    v.execute("INSERT INTO meta_sources VALUES ('pit_roster_v2_sha256', ?)", (roster.sha256,))
    v.execute("INSERT INTO meta_sources VALUES ('session_calendar_v2_sha256', ?)", (cal.sha256,))
    v.execute("INSERT INTO meta_sources VALUES ('window', ?)", (json.dumps([lo, hi]),))
    v.execute("INSERT INTO meta_sources VALUES ('v002_window', ?)",
              (json.dumps([v002_manifest["scope"]["date_range_inclusive_start"],
                           v002_manifest["scope"]["date_range_exclusive_end"]]),))

    catalog = [
        ("v_a_side", "ticker x date x broker x side",
         "Dataset B broker_flow_b (frozen store, exact copy)",
         "raw freq column passed through UNCHANGED; freq semantics UNKNOWN — forbidden as a transaction-count denominator (SEMANTIC_REGISTER_v1)"),
        ("v_a_broker_day", "ticker x date x broker (signed aggregate)",
         "derived from broker_flow_b using sign(value) per SEMANTIC_REGISTER_v1 (side column carries a known vendor-rounding defect)",
         "PIT: same-day facts only"),
        ("v_b_concentration", "ticker x date",
         "derived from v_a_broker_day + bandar_detector_b passthrough",
         "shares/HHI are descriptive concentration quantities; no thresholds applied"),
        ("v_c_pair_structure", "ticker x date x (buy broker, sell broker)",
         "SQL view over v_a_broker_day",
         "POTENTIAL-counterparty space: daily data cannot identify which buy broker traded with which sell broker; use intraday sequence (v_e) for finer inference"),
        ("v_d_broker_persistence", "ticker x session x broker (prev-session lookup)",
         "SQL view over v_a_broker_day x session_calendar",
         "prev_session is the immediately prior ADMITTED session; NULL when none"),
        ("v_d_broker_activity", "broker x session",
         "SQL view over v_a_broker_day",
         "cross-ticker broker participation per session"),
        ("v_e_intraday_summary", "ticker x date over the frozen v002 window",
         "v002 stockbit_flow_bars + stockbit_flow",
         "coverage_state: BARS / CONFIRMED_EMPTY_DAILY / TRUE_GAP_NONZERO_DAILY_NO_BARS / NO_DAILY_SUMMARY_ROW; see DATA_GAP_AUDIT_2026-09-14 for the 2025-08-05..2025-09-17 suspect-empty stretch"),
        ("v_e_minute_sequence", "ticker x date x minute",
         "frozen v002 store, consumed by ATTACH — not copied into this store",
         "ATTACH DATABASE 'file:<repo>/data/frozen/stockbit-flow-bars-v002/stockbit-flow-bars-v002.db?mode=ro' AS v002; then SELECT * FROM v002.stockbit_flow_bars; or use research_data/query_intraday.py which verifies the frozen sha256 first; bar_time is WIB session time"),
        ("v_f_flow_price", "ticker x date (Dataset B roster cells)",
         "ohlcv (ro, is_final=1) + stockbit_flow + broker gross",
         "alignment ratios only (lots/2xVolume, broker gross/traded value); no signals"),
        ("v_g_event_flow", "ticker x date (Dataset B roster cells)",
         "suspension windows, corporate_action_events + applied-basis detection, bandar, regime-aware IDX auto-rejection band contact (foundation.ara_arb)",
         "formation-t facts only; band_contact uses exchange band rules, not a strategy threshold"),
    ]
    for name, grain, src, notes in catalog:
        if name == "v_e_minute_sequence":
            n = None  # filled after attach (77.5M-row scan avoided at build time)
            h = "identity delegated to frozen source sha256 (meta_sources.frozen_flow_bars_v002_sha256)"
        else:
            order = {"v_a_side": "ticker, trade_date, broker_code, side",
                     "v_a_broker_day": "ticker, trade_date, broker_code",
                     "v_b_concentration": "ticker, trade_date",
                     "v_e_intraday_summary": "ticker, trade_date",
                     "v_f_flow_price": "ticker, trade_date",
                     "v_g_event_flow": "ticker, trade_date"}.get(name, "1")
            n = v.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            h = content_sha(v, name, order)
        v.execute("INSERT INTO meta_view_catalog VALUES (?,?,?,?,?,?)",
                  (name, grain, src, n, h, notes))

    v.commit()

    # v_e_minute_sequence: SQLite cannot persist a view over an ATTACHed database,
    # and copying 77.5M frozen rows would duplicate an immutable store. The
    # sequence is consumed via the documented attach recipe (see catalog) and the
    # query_intraday.py helper, which verifies the frozen sha256 before opening.
    v.execute("UPDATE meta_view_catalog SET row_count=? WHERE view_name='v_e_minute_sequence'",
              (int(v002_manifest["scope"]["tables_included"]["stockbit_flow_bars"].split()[0]),))
    v.commit()
    v_catalog_rows = [(r[0], f"{r[4]:,}" if isinstance(r[4], int) else str(r[4]), r[3])
                      for r in v.execute(
                          "SELECT view_name, grain, source, content_sha256,"
                          " row_count FROM meta_view_catalog ORDER BY view_name")]
    v.execute("VACUUM")
    v.close(); b.close(); f2.close(); p.close()

    print(f"views_v1.sqlite written: {os.path.getsize(OUT):,} bytes")
    for row in v_catalog_rows:
        print(f"  {row[0]:26s} {row[1]:>12s} rows  sha {row[2][:12]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
