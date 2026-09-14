#!/usr/bin/env python3
"""G1 empirical harness — MECHANICAL INFRASTRUCTURE ONLY (P-M program).

Status: DRY-RUN / SYNTHETIC-ONLY. Implements the BFI-002 candidate design
memo (PM_SPECIES_MECHANISM_BFI002_DESIGN_2026-09-10.md, DESIGN ONLY) and the
inherited BFI-001 execution conventions (10_execute_bfi001.py: NW(k) t on the
daily spread series, Holm across the prespecified family, ADV20 = rolling-20
median of traded value shifted 1, price floor 100, breadth floor 40,
|ret1| >= 0.15 exclusion).

The harness refuses to touch real Dataset B data unless the config gates
`dataset_b_frozen` AND `prereg_confirmed` are both true. It never writes
anywhere except its own output directory. It computes nothing on real data
in this task.

Cells (family of 3, Holm alpha=0.05, k in {3,5,10}, primary k=5):
  C1a  ST tercile contrast within signed-NF tercile buckets  [freq-gated]
  C2   foreign/local conduit disagreement by liquidity tercile
  C3   breadth-surprise state contrast                        [freq-free]

Design decisions inherited verbatim (NOT re-derived here):
  - species F-classifier: per-broker median ticket (|value|/freq) over the
    frozen prefix <= 2025-09-30; desk iff median ticket >= Rp 10M.
  - ST = deskBuyShare - deskSellShare on disclosed (limit=150) values.
  - NF control: (buyV - sellV)/gross. At limit=150 broker_flow net is
    identically zero (2026-09-10 trial), so the registered control must come
    from the net-flow source named in config (stockbit_flow family). The
    `net_flow_source_ratified` gate must be true before real runs; the
    synthetic fixture supplies its own net-flow series.
  - Forward returns: Dataset B-owned calendar-indexed close-to-close,
    strict contiguity (foundation.forward_returns on the real path; the
    synthetic path uses the same function via an in-memory DB).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(HERE, "g1_config.json")

# --------------------------------------------------------------- frozen constants
PREFIX_END = "2025-09-30"          # species classifier prefix (memo §1.F)
TICKET_THRESHOLD_IDR = 10_000_000.0  # Rp 10M desk/aggregator line (memo §1.F)
PRICE_FLOOR = 100.0                # BFI-001 §D convention
BREADTH_FLOOR = 40                 # valid names per formation date (memo §8)
RET1_EXCLUSION = 0.15              # |formation-day return| proxy exclusion
ADV20_WINDOW = 20                  # rolling-20 median, shift(1) (BFI-001)
BREADTH_SURPRISE_WINDOW = 60       # C3 trailing-obs median window (memo §7.C3)
BREADTH_SURPRISE_THRESHOLD = 0.30  # C3 state threshold (frozen from incidence)
DISAGREE_MIN_SHARE = 0.15          # C2 both-legs >= 15% of gross (memo §7.C2)
KS = (3, 5, 10)                    # declared horizon set (memo §8)
PRIMARY_K = 5                      # primary read (memo §8)
FAMILY_ALPHA = 0.05
COST_RT_FLOOR = 0.006              # 0.60% round-trip sensitivity floor (memo §8)


# --------------------------------------------------------------- config
def load_config(path: str = DEFAULT_CONFIG) -> dict:
    with open(path) as f:
        cfg = json.load(f)
    cfg["_config_sha256"] = hashlib.sha256(
        json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return cfg


def check_gates(cfg: dict, real_data: bool) -> list[str]:
    """Mechanical stop condition. Returns blocking messages; empty = go."""
    blocks = []
    g = cfg.get("gates", {})
    if real_data:
        if not g.get("dataset_b_frozen", False):
            blocks.append("gate dataset_b_frozen is false — Dataset B not frozen")
        if not g.get("prereg_confirmed", False):
            blocks.append("gate prereg_confirmed is false — H0-H3/P0 not locked")
        if not g.get("freq_semantics_ratified", False):
            blocks.append("gate freq_semantics_ratified is false — freq question "
                          "unresolved: C1a/C1b require either a ratified freq "
                          "semantics or a registered withdrawal (they are not yet "
                          "withdrawn)")
        if not g.get("net_flow_source_ratified", False):
            blocks.append("gate net_flow_source_ratified is false — broker_flow net "
                          "is identically 0 at limit=150; control source unratified")
    return blocks


# --------------------------------------------------------------- data bundle
@dataclass
class DataBundle:
    """Everything the pipeline needs, source-agnostic (real store or synthetic)."""
    sessions: list[str]                    # admitted sessions, ascending
    excluded: dict[str, str]               # session -> reason (strict contiguity)
    roster: dict[str, list[str]]           # session -> PIT member tickers
    ohlcv: dict[tuple[str, str], dict]     # (ticker, session) -> {open, high, low,
                                           #   close, volume, value}
    flow: list[dict]                       # broker rows {ticker, trade_date,
                                           #   broker_code, side, lot, lot_value,
                                           #   value, avg_price, freq, investor_type}
    bandar: dict[tuple[str, str], dict]    # (ticker, session) -> {total_buyer,
                                           #   total_seller, ...}
    suspensions: set[tuple[str, str]]      # (ticker, session)
    corporate_actions: list[dict]          # {ticker, ex_date, factor, applied}
    net_flow: dict[tuple[str, str], float] # (ticker, session) -> control NF in [-1,1]
    quarantined: set[str]                  # tickers excluded entirely (e.g. RAJA)
    provenance: dict = field(default_factory=dict)


# --------------------------------------------------------------- inference
def nw_t(x, lag: int):
    """Newey-West t-stat of the mean of a daily series (BFI-001 convention).
    The daily series IS the date clustering: one observation per date."""
    xs = [v for v in x if v is not None and math.isfinite(v)]
    n = len(xs)
    if n < 10:
        return (float("nan"), n)
    xm = sum(xs) / n
    u = [v - xm for v in xs]
    s = sum(v * v for v in u)
    for L in range(1, min(lag, n - 1) + 1):
        s += 2.0 * (1.0 - L / (lag + 1.0)) * sum(a * b for a, b in zip(u[L:], u[:-L]))
    var = s / n
    if var <= 0:
        return (float("nan"), n)
    return (xm / math.sqrt(var / n), n)


def two_sided_p(t: float) -> float:
    if not math.isfinite(t):
        return float("nan")
    return math.erfc(abs(t) / math.sqrt(2.0))


def holm(pvals) -> list[float]:
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    adj = [float("nan")] * m
    running = 0.0
    for i, j in enumerate(idx):
        p = pvals[j]
        if not math.isfinite(p):
            continue
        running = max(running, (m - i) * p)
        adj[j] = min(1.0, running)
    return adj


# --------------------------------------------------------------- calendar / returns
def k_ahead(sessions: list[str], d: str, k: int) -> Optional[str]:
    try:
        i = sessions.index(d)
    except ValueError:
        return None
    return sessions[i + k] if i + k < len(sessions) else None


def spans_excluded(excluded: dict[str, str], start: str, end: str) -> bool:
    """Strict contiguity: an excluded session strictly inside (start, end]
    invalidates the window (foundation.forward_returns rule)."""
    return any(start < d <= end for d in excluded)


def forward_returns(bundle: DataBundle, k: int) -> list[dict]:
    """Calendar-indexed close-to-close forward returns.

    Mirrors foundation.forward_returns (Dataset B-owned) rule for rule:
    formation and outcome both admitted sessions, exactly k sessions apart,
    PIT membership at formation, no substitution, strict contiguity."""
    out = []
    px = {tk: {d: b["close"] for (t2, d), b in bundle.ohlcv.items() if t2 == tk}
          for tk in {t for (t, _) in bundle.ohlcv}}
    for f_date in bundle.sessions:
        o_date = k_ahead(bundle.sessions, f_date, k)
        for tk in bundle.roster.get(f_date, []):
            if tk in bundle.quarantined:
                continue
            if o_date is None:
                continue
            p0 = px.get(tk, {}).get(f_date)
            if p0 is None:
                continue
            p1 = px.get(tk, {}).get(o_date)
            if p1 is None:
                continue
            if spans_excluded(bundle.excluded, f_date, o_date):
                continue
            out.append({"ticker": tk, "formation": f_date, "outcome": o_date,
                        "k": k, "fwd_ret": p1 / p0 - 1.0})
    return out


# --------------------------------------------------------------- features
def build_species_classifier(flow: list[dict], prefix_end: str = PREFIX_END,
                             threshold: float = TICKET_THRESHOLD_IDR):
    """F-classifier: per-broker median ticket (|value|/freq) over prefix rows.
    Returns ({broker: 'desk'|'agg'}, accounting). Tickets need freq > 0.
    Unclassified brokers (no valid prefix ticket) are excluded downstream."""
    per = {}
    for r in flow:
        if r["trade_date"] > prefix_end:
            continue
        f = r.get("freq")
        v = abs(r.get("value") or 0.0)
        if not f or f <= 0 or v <= 0:
            continue
        per.setdefault(r["broker_code"], []).append(v / f)
    cls, acc = {}, {"brokers_with_prefix_rows": len(per), "classified": 0,
                    "unclassified": 0, "tickets": {}}
    for b, tickets in sorted(per.items()):
        tickets.sort()
        med = tickets[len(tickets) // 2]
        acc["tickets"][b] = med
        if med >= threshold:
            cls[b] = "desk"
        else:
            cls[b] = "agg"
        acc["classified"] += 1
    return cls, acc


def build_panel(bundle: DataBundle, classifier: dict) -> tuple[list[dict], dict]:
    """One row per (ticker, formation session) that survives feature construction.

    Every row carries an accounting trail. Formation t consumes ONLY
    information dated <= t (flow trade_date == t, ADV20 shifted, ret1 at t,
    trailing breadth median). No future field is touched."""
    acc = {"flow_rows_in": len(bundle.flow), "flow_rows_deduped": 0,
           "flow_rows_unclassified_broker": 0, "flow_rows_zero_value": 0,
           "flow_rows_abnormal": 0, "panel_rows_formed": 0,
           "excluded_suspension_at_t": 0, "excluded_price_floor": 0,
           "excluded_ret1": 0, "excluded_no_net_flow": 0,
           "excluded_ca_at_t": 0, "dropped_quarantine": 0}
    # dedup on the natural key; duplicates are counted, first kept
    seen, flow_dedup = set(), []
    for r in bundle.flow:
        key = (r["ticker"], r["trade_date"], r["broker_code"], r["side"])
        if key in seen:
            acc["flow_rows_deduped"] += 1
            continue
        seen.add(key)
        flow_dedup.append(r)
    # aggregate flow to ticker-day
    agg = {}
    for r in flow_dedup:
        if r["ticker"] in bundle.quarantined:
            acc["dropped_quarantine"] += 1
            continue
        b = classifier.get(r["broker_code"])
        if b is None:
            acc["flow_rows_unclassified_broker"] += 1
            continue
        v = r.get("value") or 0.0
        if v == 0:
            acc["flow_rows_zero_value"] += 1
        if abs(v) > 1e14:
            acc["flow_rows_abnormal"] += 1
        side = 1 if r["side"] == "BUY" else -1
        a = agg.setdefault((r["ticker"], r["trade_date"]),
                           {"desk_buy": 0.0, "desk_sell": 0.0, "buy_v": 0.0,
                            "sell_v": 0.0, "n_buy": 0, "n_sell": 0,
                            "for_buy": 0.0, "for_sell": 0.0, "loc_buy": 0.0,
                            "loc_sell": 0.0, "rows": 0})
        av = abs(v)
        a["rows"] += 1
        if side > 0:
            a["buy_v"] += v
            a["n_buy"] += 1
            if b == "desk":
                a["desk_buy"] += v
            if (r.get("investor_type") or "").lower().startswith("asing"):
                a["for_buy"] += v
            else:
                a["loc_buy"] += v
        else:
            a["sell_v"] += v
            a["n_sell"] += 1
            if b == "desk":
                a["desk_sell"] += av
            if (r.get("investor_type") or "").lower().startswith("asing"):
                a["for_sell"] += av
            else:
                a["loc_sell"] += av
    # ADV20: rolling-20 median of traded value, shift(1) — BFI-001 convention
    val = {}
    for (tk, d), b in bundle.ohlcv.items():
        val.setdefault(tk, []).append((d, b.get("value") or b.get("close", 0) * (b.get("volume") or 0)))
    adv20 = {}
    for tk, series in val.items():
        series.sort()
        vals = [v for _, v in series]
        dates = [d for d, _ in series]
        for i, d in enumerate(dates):
            if i >= ADV20_WINDOW:
                w = sorted(vals[i - ADV20_WINDOW:i])  # ends at i-1 -> shift(1)
                adv20[(tk, d)] = w[len(w) // 2]
    panel = []
    for t_i, d in enumerate(bundle.sessions):
        members = [tk for tk in bundle.roster.get(d, []) if tk not in bundle.quarantined]
        for tk in members:
            if (tk, d) in bundle.suspensions:
                acc["excluded_suspension_at_t"] += 1
                continue
            bar = bundle.ohlcv.get((tk, d))
            if bar is None or not bar.get("close"):
                continue
            a = agg.get((tk, d))
            if a is None or a["rows"] == 0:
                continue
            gross = a["buy_v"] + abs(a["sell_v"])  # traded value, NOT net
            if gross <= 0:
                acc["excluded_no_net_flow"] += 1
                continue
            if bar["close"] < PRICE_FLOOR:
                acc["excluded_price_floor"] += 1
                continue
            # ret1: formation-day return vs prior session close (calendar-indexed)
            prev_d = bundle.sessions[t_i - 1] if t_i > 0 else None
            prev_close = bundle.ohlcv.get((tk, prev_d), {}).get("close") if prev_d else None
            ret1 = (bar["close"] / prev_close - 1.0) if prev_close else None
            if ret1 is None or abs(ret1) >= RET1_EXCLUSION:
                acc["excluded_ret1"] += 1
                continue
            nf_ctrl = bundle.net_flow.get((tk, d))
            if nf_ctrl is None:
                acc["excluded_no_net_flow"] += 1
                continue
            desk_buy = a["desk_buy"]
            desk_sell = a["desk_sell"]
            buy_v = a["buy_v"]
            sell_v = a["sell_v"]
            st = (desk_buy / buy_v if buy_v > 0 else 0.0) - \
                 (desk_sell / (abs(sell_v)) if sell_v < 0 else 0.0)
            row = {"ticker": tk, "date": d, "st": st, "gross": gross,
                   "abs_nf": abs(nf_ctrl), "nf": nf_ctrl,
                   "breadth": ((a["n_buy"] - a["n_sell"]) / (a["n_buy"] + a["n_sell"])
                               if (a["n_buy"] + a["n_sell"]) else 0.0),
                   "n_buy": a["n_buy"], "n_sell": a["n_sell"],
                   "adv20": adv20.get((tk, d)),
                   "for_share": (a["for_buy"] - a["for_sell"]) / gross,
                   "loc_share": (a["loc_buy"] - a["loc_sell"]) / gross,
                   "for_gross_share": (a["for_buy"] + a["for_sell"]) / gross,
                   "loc_gross_share": (a["loc_buy"] + a["loc_sell"]) / gross,
                   }
            panel.append(row)
            acc["panel_rows_formed"] += 1
    return panel, acc


def assign_st_terciles(panel: list[dict], cuts: tuple[float, float]):
    """Ex-ante ST terciles from frozen cuts (config-supplied; cuts come from the
    declared prefix distribution at registration, never from returns)."""
    lo, hi = cuts
    for r in panel:
        r["st_bucket"] = 2 if r["st"] >= hi else (0 if r["st"] <= lo else 1)


def assign_nf_terciles_per_date(panel: list[dict]):
    """Signed-NF terciles per formation date (cross-sectional, per memo §3:
    'date x signed-NF-tercile fixed effects'). Ties at zero keep bucket 1."""
    by_date = {}
    for r in panel:
        by_date.setdefault(r["date"], []).append(r)
    for d, rows in by_date.items():
        nfs = sorted(r["nf"] for r in rows)
        def q(p):
            return nfs[min(len(nfs) - 1, int(p * (len(nfs) - 1)))]
        lo, hi = q(1 / 3.0), q(2 / 3.0)
        for r in rows:
            r["nf_bucket"] = 2 if r["nf"] > hi else (0 if r["nf"] <= lo else 1)


def liquidity_terciles_per_date(panel: list[dict]):
    by_date = {}
    for r in panel:
        by_date.setdefault(r["date"], []).append(r)
    for d, rows in by_date.items():
        with_adv = sorted((r for r in rows if r["adv20"]), key=lambda r: r["adv20"])
        n = len(with_adv)
        if n < 3:
            for r in rows:
                r["liq_bucket"] = None
            continue
        for i, r in enumerate(with_adv):
            r["liq_bucket"] = 0 if i < n // 3 else (2 if i >= n - n // 3 else 1)


# --------------------------------------------------------------- cells
def cell_c1a(panel: list[dict], k: int, fwd: dict[tuple[str, str], float]):
    """theta(k): within each signed-NF tercile bucket, equal-weight mean fwd
    return of ST-top cells minus ST-bottom cells; theta_t = unweighted mean
    over buckets present; the daily theta_t series is the date clustering."""
    by_date = {}
    for r in panel:
        fr = fwd.get((r["ticker"], r["date"]))
        if fr is None or r.get("st_bucket") is None or r.get("nf_bucket") is None:
            continue
        by_date.setdefault(r["date"], {}).setdefault(r["nf_bucket"], []).append((r, fr))
    daily = []
    detail = []
    for d in sorted(by_date):
        contrasts = []
        for b in (0, 1, 2):
            rows = by_date[d].get(b)
            if not rows:
                continue
            top = [fr for r, fr in rows if r["st_bucket"] == 2]
            bot = [fr for r, fr in rows if r["st_bucket"] == 0]
            if top and bot:
                contrasts.append(sum(top) / len(top) - sum(bot) / len(bot))
                detail.append({"date": d, "bucket": b,
                               "n_top": len(top), "n_bot": len(bot),
                               "contrast": contrasts[-1]})
        if contrasts:
            daily.append((d, sum(contrasts) / len(contrasts)))
    t, n = nw_t([v for _, v in daily], k)
    mean = sum(v for _, v in daily) / n if n else float("nan")
    return {"cell": "C1a", "k": k, "theta_t": daily, "theta_mean": mean,
            "nw_t": t, "n_days": n, "p": two_sided_p(t),
            "theta_net_cost_floor": mean - COST_RT_FLOOR if n else float("nan"),
            "detail": detail}


def compute_breadth_surprise(panel: list[dict], min_history: int = 30):
    """Per-ticker breadth surprise vs the trailing median of PRIOR panel rows
    (strictly past, all valid feature rows — applied BEFORE the breadth-floor
    formation filter so early formations still have history)."""
    hist = {}
    for r in sorted(panel, key=lambda x: x["date"]):
        h = hist.setdefault(r["ticker"], [])
        r["breadth_surprise"] = (r["breadth"] - sorted(h)[len(h) // 2]
                                 if len(h) >= min_history else None)
        h.append(r["breadth"])


def cell_c3(panel: list[dict], k: int, fwd: dict[tuple[str, str], float]):
    """Breadth surprise states (precomputed per row): surprise >= +thr (broad)
    vs <= -thr (narrow). Spread = broad mean - narrow mean per date."""
    daily = []
    for d in sorted({r["date"] for r in panel}):
        broad, narrow = [], []
        for r in panel:
            if r["date"] != d or r.get("breadth_surprise") is None:
                continue
            fr = fwd.get((r["ticker"], d))
            if fr is None:
                continue
            if r["breadth_surprise"] >= BREADTH_SURPRISE_THRESHOLD:
                broad.append(fr)
            elif r["breadth_surprise"] <= -BREADTH_SURPRISE_THRESHOLD:
                narrow.append(fr)
        if broad and narrow:
            daily.append((d, sum(broad) / len(broad) - sum(narrow) / len(narrow)))
    t, n = nw_t([v for _, v in daily], k)
    mean = sum(v for _, v in daily) / n if n else float("nan")
    return {"cell": "C3", "k": k, "theta_t": daily, "theta_mean": mean,
            "nw_t": t, "n_days": n, "p": two_sided_p(t),
            "theta_net_cost_floor": mean - COST_RT_FLOOR if n else float("nan")}


def cell_c2(panel: list[dict], k: int, fwd: dict[tuple[str, str], float]):
    """Foreign-owned vs locally-owned conduit disagreement: opposite-signed
    net shares, both legs' gross >= DISAGREE_MIN_SHARE of total gross.
    Spread = long-foreign mean - short-foreign mean per date."""
    daily = []
    for d in sorted({r["date"] for r in panel}):
        long_f, short_f = [], []
        for r in panel:
            if r["date"] != d:
                continue
            fr = fwd.get((r["ticker"], d))
            if fr is None:
                continue
            f_ok = r["for_gross_share"] >= DISAGREE_MIN_SHARE
            l_ok = r["loc_gross_share"] >= DISAGREE_MIN_SHARE
            if not (f_ok and l_ok):
                continue
            if r["for_share"] > 0 and r["loc_share"] < 0:
                long_f.append(fr)
            elif r["for_share"] < 0 and r["loc_share"] > 0:
                short_f.append(fr)
        if long_f and short_f:
            daily.append((d, sum(long_f) / len(long_f) - sum(short_f) / len(short_f)))
    t, n = nw_t([v for _, v in daily], k)
    mean = sum(v for _, v in daily) / n if n else float("nan")
    return {"cell": "C2", "k": k, "theta_t": daily, "theta_mean": mean,
            "nw_t": t, "n_days": n, "p": two_sided_p(t),
            "theta_net_cost_floor": mean - COST_RT_FLOOR if n else float("nan")}


# --------------------------------------------------------------- real loader
def load_real_bundle(cfg: dict, required_gates=None) -> DataBundle:
    """Gated Dataset B / production reader. Read-only everywhere; fails loudly
    on any missing table/artifact rather than fabricating a substitute field.
    Fail-closed: re-checks its required gates itself so a direct API call
    cannot bypass them. G1 requires all four gates; C7 requires only the gates
    it actually depends on (dataset_b_frozen) — passed via `required_gates`.

    Sources (interface documented in G1_MECHANICAL_READINESS_2026-09-10.md §4):
      PIT roster + session calendar : dataset_b artifacts (cfg versions)
      broker flow / bandar / manifest: dataset_b/store DATASET_B_BROKER_FLOW_STORE_v1
      ohlcv                          : production walkforward.db (ro), is_final=1
      suspensions                    : production suspension_events, expanded
                                       over the declared calendar
      corporate actions + basis      : foundation.load_corporate_actions +
                                       detect_unapplied_splits
      quarantine                     : foundation.vwap_ratio_report
                                       (BASIS_MISMATCH / BASIS_UNSTABLE)
      net-flow control               : ratified stockbit_flow share-ratio NF
                                       (G1_GOVERNANCE_UNBLOCK_RECORD §3);
                                       consumed by G1 arms only, never by C7.
    """
    req = set(required_gates) if required_gates is not None else {
        "dataset_b_frozen", "prereg_confirmed",
        "freq_semantics_ratified", "net_flow_source_ratified"}
    missing = [g for g in sorted(req)
               if not cfg.get("gates", {}).get(g, False)]
    if missing:
        raise SystemExit("load_real_bundle refused — required gates not "
                         "satisfied:\n  - " + "\n  - ".join(missing))

    import sqlite3
    dataset_b_dir = os.path.join(os.path.dirname(HERE), "dataset_b")
    sys.path.insert(0, dataset_b_dir)
    import foundation

    db = foundation.DB_PATH
    store = foundation.HERE / "store" / "DATASET_B_BROKER_FLOW_STORE_v1.sqlite"
    for p in (db, store):
        if not os.path.exists(p):
            raise SystemExit(f"missing data source: {p}")

    rv = cfg.get("roster_artifact_version", "v2")
    cv = cfg.get("calendar_artifact_version", "v2")
    roster = foundation.PitRoster.load(rv)
    cal = foundation.SessionCalendar.load(cv)
    sessions = cal.sessions

    prod = foundation.ro_connect(db)
    store_conn = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    store_conn.execute("PRAGMA query_only = ON;")

    uni = roster.universe
    ph = ",".join("?" * len(uni))
    lo, hi = sessions[0], sessions[-1]
    ohlcv = {}
    try:
        rows = prod.execute(
            f"SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
            f"WHERE ticker IN ({ph}) AND date >= ? AND date <= ? AND is_final = 1",
            sorted(uni) + [lo, hi]).fetchall()
    except sqlite3.OperationalError as e:
        raise SystemExit(f"ohlcv schema mismatch: {e}")
    for tk, d, o, h_, l_, c, v in rows:
        if d in cal._idx and c:
            ohlcv[(tk, d)] = {"open": o, "high": h_, "low": l_, "close": c,
                              "volume": v, "value": (c * v) if (c and v) else None}

    flow = []
    for tk, d, code, side, lot, lotv, val, ap, freq, itype in store_conn.execute(
            "SELECT ticker, trade_date, broker_code, side, lot, lot_value, value, "
            "avg_price, freq, investor_type FROM broker_flow_b "
            "WHERE trade_date >= ? AND trade_date <= ?", (lo, hi)):
        flow.append({"ticker": tk, "trade_date": d, "broker_code": code,
                     "side": side, "lot": lot, "lot_value": lotv, "value": val,
                     "avg_price": ap, "freq": freq, "investor_type": itype})
    bandar = {}
    for tk, d, tb, ts, nbc in store_conn.execute(
            "SELECT ticker, trade_date, total_buyer, total_seller, "
            "net_broker_count FROM bandar_detector_b "
            "WHERE trade_date >= ? AND trade_date <= ?", (lo, hi)):
        bandar[(tk, d)] = {"total_buyer": tb, "total_seller": ts,
                           "net_broker_count": nbc}
    manifest_ok = store_conn.execute(
        "SELECT COUNT(*) FROM capture_manifest WHERE status <> 'SUCCESS' "
        "AND status <> 'EMPTY' AND session_date >= ? AND session_date <= ?",
        (lo, hi)).fetchone()[0]
    if manifest_ok:
        raise SystemExit(f"{manifest_ok} capture_manifest cells are not in a "
                         "terminal state — Dataset B store incomplete.")

    suspensions = set()
    for tk, ln, rd in prod.execute(
            "SELECT ticker, last_normal_date, resume_date FROM suspension_events"):
        for d in sessions:
            if ln <= d <= rd:
                suspensions.add((tk, d))

    actions = foundation.load_corporate_actions(prod, uni, lo, hi)
    actions = foundation.detect_unapplied_splits(prod, actions)

    basis = foundation.vwap_ratio_report(prod, uni, sessions)
    quarantined = set(basis["flagged"])

    net_flow = {}
    gross_sf = {}
    for tk, d, bl, sl in prod.execute(
            f"SELECT ticker, trade_date, buy_lot, sell_lot FROM stockbit_flow "
            f"WHERE ticker IN ({ph}) AND trade_date >= ? AND trade_date <= ?",
            sorted(uni) + [lo, hi]):
        if bl is not None and sl is not None and (bl + sl) > 0:
            net_flow[(tk, d)] = (bl - sl) / (bl + sl)
            gross_sf[(tk, d)] = (bl + sl)
    prod.close()
    store_conn.close()

    return DataBundle(
        sessions=sessions, excluded=dict(cal.excluded),
        roster={d: roster.members(d) for d in sessions},
        ohlcv=ohlcv, flow=flow, bandar=bandar, suspensions=suspensions,
        corporate_actions=actions, net_flow=net_flow, quarantined=quarantined,
        provenance={
            "pit_roster_version": rv, "pit_roster_sha256": roster.sha256,
            "session_calendar_version": cv, "session_calendar_sha256": cal.sha256,
            "store": str(store), "ohlcv_db": str(db),
            "net_flow_source": "stockbit_flow (PROVISIONAL, unratified)",
            "quarantined_tickers": sorted(quarantined),
            "bandar_rows": len(bandar), "flow_rows": len(flow)})


# ------------------------------------------------- C7 intensity-state (registered)
# Registration: C7_REGISTRATION_v1_2026-09-11 (owner-approved 2026-09-11).
# FREQ-FREE BY CONSTRUCTION: the C7 path below never reads flow `freq`.
C7_HIGH_THRESHOLD = 2.0     # intensity >= 2.0 (family map H; descriptive generator)
C7_ADV_WINDOW = 20          # median traded value over prior 20 sessions, shift(1)


def c7_build_panel(bundle: DataBundle):
    """C7 intensity panel. Returns (rows, accounting).

    Row = one (ticker, formation session) surviving the registered exclusions:
    quarantine, suspension at t, missing bar, missing ADV20 history, gross <= 0,
    price < 100, |ret1| >= 0.15 or undefined prior close. Freq is never read.
    """
    acc = {"flow_rows_in": len(bundle.flow), "dropped_quarantine": 0,
           "panel_rows_formed": 0, "excluded_suspension_at_t": 0,
           "excluded_price_floor": 0, "excluded_ret1": 0,
           "excluded_missing_adv20": 0, "excluded_gross_zero": 0}
    # traded value (close x volume) per (ticker, session)
    tv = {}
    for (tk, d), b in bundle.ohlcv.items():
        if b.get("close") and b.get("volume"):
            tv[(tk, d)] = b["close"] * b["volume"]
    per_t = {}
    for (tk, d), v in tv.items():
        per_t.setdefault(tk, []).append((d, v))
    adv20 = {}
    for tk, s in per_t.items():
        s.sort()
        vals = [v for _, v in s]
        dates = [d for d, _ in s]
        for i in range(C7_ADV_WINDOW, len(dates)):
            w = sorted(vals[i - C7_ADV_WINDOW:i])   # ends at i-1 -> shift(1)
            adv20[(tk, dates[i])] = w[len(w) // 2]
    gross = {}
    for r in bundle.flow:
        if r["ticker"] in bundle.quarantined:
            acc["dropped_quarantine"] += 1
            continue
        key = (r["ticker"], r["trade_date"])
        gross[key] = gross.get(key, 0.0) + abs(r.get("value") or 0.0)
    rows = []
    for t_i, d in enumerate(bundle.sessions):
        for tk in bundle.roster.get(d, []):
            if tk in bundle.quarantined:
                continue
            if (tk, d) in bundle.suspensions:
                acc["excluded_suspension_at_t"] += 1
                continue
            bar = bundle.ohlcv.get((tk, d))
            if bar is None or not bar.get("close"):
                continue
            a = adv20.get((tk, d))
            if not a:
                acc["excluded_missing_adv20"] += 1
                continue
            g = gross.get((tk, d), 0.0)
            if g <= 0:
                acc["excluded_gross_zero"] += 1
                continue
            if bar["close"] < PRICE_FLOOR:
                acc["excluded_price_floor"] += 1
                continue
            prev_d = bundle.sessions[t_i - 1] if t_i > 0 else None
            pc = bundle.ohlcv.get((tk, prev_d), {}).get("close") if prev_d else None
            ret1 = (bar["close"] / pc - 1.0) if pc else None
            if ret1 is None or abs(ret1) >= RET1_EXCLUSION:
                acc["excluded_ret1"] += 1
                continue
            inten = g / a
            rows.append({"ticker": tk, "date": d, "gross": g, "adv20": a,
                         "intensity": inten, "high": inten >= C7_HIGH_THRESHOLD})
            acc["panel_rows_formed"] += 1
    return rows, acc


def cell_c7(panel: list[dict], k: int, fwd: dict[tuple[str, str], float]):
    """Daily contrast: mean fwd return of high-intensity states minus mean fwd
    return of normal/non-high states on the same formation date. The daily
    series is the date clustering."""
    daily = []
    skipped = 0
    for d in sorted({r["date"] for r in panel}):
        hi, lo = [], []
        for r in panel:
            if r["date"] != d:
                continue
            fr = fwd.get((r["ticker"], d))
            if fr is None:
                continue
            (hi if r["high"] else lo).append(fr)
        if hi and lo:
            daily.append((d, sum(hi) / len(hi) - sum(lo) / len(lo)))
        else:
            skipped += 1
    t, n = nw_t([v for _, v in daily], k)
    mean = sum(v for _, v in daily) / n if n else float("nan")
    return {"cell": "C7", "k": k, "theta_t": daily, "theta_mean": mean,
            "nw_t": t, "n_days": n, "p": two_sided_p(t),
            "theta_net_cost_floor": mean - COST_RT_FLOOR if n else float("nan"),
            "dates_skipped_missing_state": skipped}


def run_c7(bundle: DataBundle, cfg: dict) -> dict:
    """Registered C7 run (C7_REGISTRATION_v1_2026-09-11). Fail-closed on the
    c7_registered gate; freq-free by construction; family = {C7} (Holm n=1:
    holm_p equals the raw two-sided p at the primary horizon)."""
    if not cfg.get("c7_registered", False):
        raise SystemExit("C7 NOT LAUNCHED — gate c7_registered is false "
                         "(registration not owner-approved for execution)")
    out = {"run_mode": "C7", "config_sha256": cfg["_config_sha256"],
           "provenance": bundle.provenance}
    panel, acc = c7_build_panel(bundle)
    out["panel_accounting"] = acc
    cells = []
    for k in KS:
        fwd_rows = forward_returns(bundle, k)
        ca_dates = {}
        for a in bundle.corporate_actions:
            ca_dates.setdefault(a["ticker"], []).append(a["ex_date"])
        kept = {}
        ca_dropped = 0
        for o in fwd_rows:
            if any(o["formation"] < x <= o["outcome"]
                   for x in ca_dates.get(o["ticker"], ())):
                ca_dropped += 1
                continue
            kept[(o["ticker"], o["formation"])] = o["fwd_ret"]
        out.setdefault("ca_window_exclusions", {})[str(k)] = ca_dropped
        cells.append(cell_c7(panel, k, kept))
    for c in cells:
        for f in ("theta_mean", "nw_t", "p", "holm_p", "theta_net_cost_floor"):
            if f in c and isinstance(c[f], float) and not math.isfinite(c[f]):
                c[f] = None
    out["cells"] = cells
    fam = [c for c in cells if c["k"] == PRIMARY_K]
    ps = [c["p"] if (c["p"] is not None and math.isfinite(c["p"])) else 1.0
          for c in fam]
    adj = holm(ps)   # single-cell family: holm_p == raw p
    for c, a in zip(fam, adj):
        c["holm_p"] = a
        c["holm_significant"] = a < FAMILY_ALPHA
    out["family_alpha"] = FAMILY_ALPHA
    out["primary_k"] = PRIMARY_K
    out["ks"] = list(KS)
    return out


# --------------------------------------------------------------- orchestration
def run_g1(bundle: DataBundle, cfg: dict) -> dict:
    """Full pipeline on the supplied bundle. Deterministic output ordering."""
    out = {"run_mode": "synthetic-dry-run" if cfg.get("synthetic") else "REAL",
           "config_sha256": cfg["_config_sha256"],
           "provenance": bundle.provenance}
    breadth_floor = int(cfg.get("breadth_floor", BREADTH_FLOOR))
    surprise_min_hist = int(cfg.get("breadth_surprise_min_history", 30))
    classifier, cls_acc = build_species_classifier(
        bundle.flow, prefix_end=cfg.get("prefix_end", PREFIX_END))
    out["species_classifier"] = cls_acc
    panel, panel_acc = build_panel(bundle, classifier)
    out["panel_accounting"] = panel_acc
    # breadth floor on formation dates (BFI-001): count valid names per date
    counts = {}
    for r in panel:
        counts[r["date"]] = counts.get(r["date"], 0) + 1
    form_dates = sorted(d for d, n in counts.items() if n >= breadth_floor)
    out["formation_dates"] = form_dates
    # every declared session is accounted for: below-floor includes 0-row days
    out["formation_dates_dropped_below_floor"] = sorted(
        d for d in bundle.sessions if counts.get(d, 0) < breadth_floor)
    panel_full = panel
    panel = [r for r in panel if r["date"] in set(form_dates)]
    assign_st_terciles(panel, tuple(cfg.get("st_tercile_cuts", (-1.0 / 3, 1.0 / 3))))
    assign_nf_terciles_per_date(panel)
    liquidity_terciles_per_date(panel)
    # breadth surprise over the FULL valid panel (pre-floor), so the trailing
    # median at early formation dates has history
    compute_breadth_surprise(panel_full, min_history=surprise_min_hist)
    # BFI-001 convention: a corporate action strictly inside (t, t+k] invalidates
    # the observation (k-window specific; trailing CAs are not excluded — the
    # adjustment basis itself is owned by Dataset B / quarantine).
    ca_dates = {}
    for a in bundle.corporate_actions:
        ca_dates.setdefault(a["ticker"], []).append(a["ex_date"])
    cells = []
    for k in KS:
        fwd_rows = forward_returns(bundle, k)
        kept = {}
        ca_dropped = 0
        for o in fwd_rows:
            if any(o["formation"] < x <= o["outcome"]
                   for x in ca_dates.get(o["ticker"], ())):
                ca_dropped += 1
                continue
            kept[(o["ticker"], o["formation"])] = o["fwd_ret"]
        out.setdefault("ca_window_exclusions", {})[str(k)] = ca_dropped
        cells.append(cell_c1a(panel, k, kept))
        cells.append(cell_c2(panel, k, kept))
        cells.append(cell_c3(panel, k, kept))
    for c in cells:
        for f in ("theta_mean", "nw_t", "p", "holm_p", "theta_net_cost_floor"):
            if f in c and isinstance(c[f], float) and not math.isfinite(c[f]):
                c[f] = None
        # Freq-dependent arms: the registered resolution (2026-09-11 replacement
        # registration) is WITHDRAWAL — C1a/C1b never execute while the
        # withdrawal is in force, independent of any gate. Before withdrawal
        # they stay blocked on unratified freq semantics.
        if c["cell"] in ("C1a", "C1b"):
            if cfg.get("freq_resolution") == "withdrawn":
                c["status"] = "WITHDRAWN_FREQ_DEPENDENT"
                c["theta_mean"] = None
                c["nw_t"] = None
                c["p"] = None
            elif not cfg.get("gates", {}).get("freq_semantics_ratified", False):
                c["status"] = "BLOCKED_FREQ_SEMANTICS"
                c["theta_mean"] = None
                c["nw_t"] = None
                c["p"] = None
            else:
                c["status"] = "COMPUTED"
        else:
            c["status"] = "COMPUTED"
    out["cells"] = cells
    # Holm across the retained (non-withdrawn) family at the primary horizon
    fam = [c for c in cells
           if c["k"] == PRIMARY_K and c["status"] == "COMPUTED"]
    ps = [c["p"] if (c["p"] is not None and math.isfinite(c["p"])) else 1.0
          for c in fam]
    adj = holm(ps)
    for c, a in zip(fam, adj):
        c["holm_p"] = a
        c["holm_significant"] = a < FAMILY_ALPHA
    out["family_alpha"] = FAMILY_ALPHA
    out["primary_k"] = PRIMARY_K
    out["ks"] = list(KS)
    return out


def main_c7():
    """C7 registered execution path (C7_REGISTRATION_v1_2026-09-11).
    Fail-closed on the c7_registered gate AND the D-048 provenance wrapper.
    Freq is never read on this path."""
    import provenance as prov
    config_path = os.path.abspath(os.environ.get(
        "C7_CONFIG", os.environ.get("G1_CONFIG", DEFAULT_CONFIG)))
    cfg = load_config(config_path)
    if not cfg.get("c7_registered", False):
        print("C7 NOT LAUNCHED — gate c7_registered is false (registration not "
              "owner-approved for execution)")
        return 2
    if cfg.get("synthetic", False):
        print("C7 synthetic mode is exercised by the test suite only; "
              "real dispatch requires synthetic=false.")
        return 3
    # D-048 provenance hard gate: snapshot sources/config/registration/freeze/
    # store BEFORE any data access; refuse on drift or missing receipts.
    registration = os.path.abspath(os.path.join(HERE, "C7_REGISTRATION_v1_2026-09-11.md"))
    freeze_manifest = os.path.abspath(os.path.join(
        os.path.dirname(HERE), "dataset_b", "artifacts", "DATASET_B_FREEZE_MANIFEST_v1.json"))
    store = os.path.abspath(os.path.join(
        os.path.dirname(HERE), "dataset_b", "store", "DATASET_B_BROKER_FLOW_STORE_v1.sqlite"))
    run_id, run_dir, pre = prov.snapshot_run(
        sources=[os.path.abspath(__file__),
                 os.path.abspath(os.path.join(os.path.dirname(HERE),
                                              "dataset_b", "foundation.py"))],
        config_path=config_path,
        registration_paths=[registration],
        freeze_manifest_path=freeze_manifest,
        store_path=store,
        label="C7")
    print(f"C7 provenance: run_id={run_id} preflight_digest={pre['preflight_digest'][:16]}…")
    bundle = load_real_bundle(cfg, required_gates={"dataset_b_frozen"})
    out = run_c7(bundle, cfg)
    out["run_id"] = run_id
    out["run_dir"] = run_dir
    out_path = os.path.join(run_dir, "c7_real_output.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True, allow_nan=False)
    preflight = json.load(open(os.path.join(run_dir, "preflight_manifest.json")))
    sources = [os.path.abspath(__file__),
               os.path.abspath(os.path.join(os.path.dirname(HERE),
                                            "dataset_b", "foundation.py"))]
    seal = prov.seal_run(run_dir, preflight, sources, config_path,
                         [registration], store, output_files=[out_path])
    if not seal["valid_provenance"]:
        print(f"WARNING: provenance seal INVALID — drifted: {seal['drifted_files']}; "
              "output stamped non-reportable.")
    print(f"C7 output written: {out_path}")
    print(f"seal: valid_provenance={seal['valid_provenance']}")
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "c7":
        return main_c7()
    cfg = load_config(os.environ.get("G1_CONFIG", DEFAULT_CONFIG))
    real = not cfg.get("synthetic", False)
    blocks = check_gates(cfg, real_data=real)
    if blocks:
        print("G1 NOT LAUNCHED — mechanical gates:")
        for b in blocks:
            print("  -", b)
        return 2
    if real:
        # D-048 provenance hard gate: snapshot before any data access.
        import provenance as prov
        registration = os.path.abspath(os.path.join(
            os.path.dirname(HERE), "G1_REGISTRATION_v1_2026-09-11.md"))
        freeze_manifest = os.path.abspath(os.path.join(
            os.path.dirname(HERE), "dataset_b", "artifacts", "DATASET_B_FREEZE_MANIFEST_v1.json"))
        store = os.path.abspath(os.path.join(
            os.path.dirname(HERE), "dataset_b", "store", "DATASET_B_BROKER_FLOW_STORE_v1.sqlite"))
        run_id, run_dir, pre = prov.snapshot_run(
            sources=[os.path.abspath(__file__),
                     os.path.abspath(os.path.join(os.path.dirname(HERE),
                                                  "dataset_b", "foundation.py"))],
            config_path=os.path.abspath(os.environ.get("G1_CONFIG", DEFAULT_CONFIG)),
            registration_paths=[registration],
            freeze_manifest_path=freeze_manifest,
            store_path=store,
            label="G1")
        print(f"G1 provenance: run_id={run_id} preflight_digest={pre['preflight_digest'][:16]}…")
        bundle = load_real_bundle(cfg, required_gates={"dataset_b_frozen"})
        out = run_g1(bundle, cfg)
        out["run_id"] = run_id
        out["run_dir"] = run_dir
        out_path = os.path.join(run_dir, "g1_real_output.json")
        with open(out_path, "w") as f:
            json.dump(out, f, indent=1, sort_keys=True, allow_nan=False)
        sources = [os.path.abspath(__file__),
                   os.path.abspath(os.path.join(os.path.dirname(HERE),
                                                "dataset_b", "foundation.py"))]
        seal = prov.seal_run(run_dir, pre, sources, config_path,
                             [registration], store, output_files=[out_path])
        if not seal["valid_provenance"]:
            print(f"WARNING: provenance seal INVALID — drifted: {seal['drifted_files']}")
        print(f"G1 output written: {out_path} (valid_provenance={seal['valid_provenance']})")
        return 0
    from g1_synthetic import make_bundle, synthetic_config
    file_cfg = cfg
    cfg = synthetic_config()          # fixture-scale floors for the dry run
    cfg["gates"] = dict(file_cfg.get("gates", {}))
    cfg["gates"].update(synthetic_config()["gates"])
    cfg["_config_sha256"] = synthetic_config()["_config_sha256"]
    bundle = make_bundle()
    out = run_g1(bundle, cfg)
    path = os.path.join(HERE, "g1_dry_run_output.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, sort_keys=True, default=str)
    print(f"dry-run output written: {path}")
    print(json.dumps({k: out[k] for k in ("panel_accounting", "formation_dates",
                                          "formation_dates_dropped_below_floor")},
                     indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
