"""Broker-flow context screen, NeoBDM-style ("bandarmologi") -- DESCRIPTIVE ONLY.

Owner decision 2026-10-13 (DECISION_LOG D-094): rebuild the ideas behind the paid NeoBDM app from our
own `broker_flow` data, as context next to a chart, never as a signal or a gate. None of these
readings has evidence status: the research record behind that warning is D-091 (daily imbalance
continuation FAILED), D-087/D-092 ({RF} retail flow unpowered), D-093/D-094 (crossing G0 unpowered)
and the Flow Edge Study (null). Do not wire anything here into a scanner, the agent firm or a trade
path without a registered, passed hypothesis.

What is rebuilt (the vendor's code and output are not used; only the ideas, from its public videos):
  * participant groups per broker: retail platforms, foreign-type brokers, zombie (rarely-used
    brokers, often behind arranged volume or share pledges), institution (everyone else);
  * flow lines: cumulative net value of bandar (top-5 buyers' net + top-5 sellers' net, i.e. which
    side is concentrated), non-retail (= -retail), sultan (largest brokers), foreign;
  * "compatibility": which line has tracked the price best over the trailing window -- an in-sample
    fit, shown as such, NOT a forecast;
  * accumulation %: bandar net over a window / traded value over that window (NeoBDM's D1..D4,
    W1..W4 columns);
  * crossing share: the part of non-retail turnover where the same broker sits on both sides of the
    day (NeoBDM's "crossing index"; our own construct, D-093);
  * zombie share of gross.

Data semantics (verified 2026-10-13): per broker-day `value` is the signed net in Rp and
`value_total` the gross of the listed side; the broker's other-side gross is value_total - |value|.
The vendor lists the top 25 net brokers per side, so a broker outside both lists is unobserved;
in practice the lists capture nearly all volume: lots rebuilt this way equal the trade-book
regular volume (median 1.000, 98% of 551 names within +-5% on 2026-10-09), and the bandar sign
agrees with the vendor's own top-5 acc/dist label (100% of 226). Re-check: tools/check_bdm.py.
`investor_type` classifies the BROKER (Asing / Lokal / Pemerintah), not the investor -- "foreign"
here means foreign-type brokers excluding the retail platforms, a proxy for NeoBDM's investor-
citizenship foreign flow.
"""
from __future__ import annotations

import math
import threading
from collections import defaultdict

import numpy as np

from config import DB_PATH
from data.db import connect as db_connect

# --- frozen broker classes (2026-10-13, from broker_flow 2026-04-01 .. 2026-09-30) ------------
# Retail platforms: D-086's ticket-size group (<= Rp 6M per trade, 2025-Q1).
RETAIL = frozenset({"XL", "XC", "YP", "PD", "KK"})
# Zombie: every broker with < 0.10% of market gross value in the freeze window. A code never seen in
# that window is rare by definition and also counts as zombie (see group_of).
ZOMBIE = frozenset("AD AF AH AP AR BF BS DD DU EL ES FO FS GA GI IC ID IH II IT IU JB MI MU OK PF "
                   "PG PI PO PP QA RB RG RO RS SA SF SH TF TS YO ZR".split())
# Mainstream: the remaining brokers seen in the window (>= 0.10% share).
MAINSTREAM = frozenset("AK CC ZP YU BK MG CP SQ NI LG AZ KZ OD RX BB GR HD DR TP BQ XA DX YB EP AI "
                       "AG DH IF KI YJ AO SS HP RF DP BR AT IN CD FZ PC LS".split())
# Sultan: the 10 largest non-retail brokers by gross value in the window.
SULTAN = frozenset({"AK", "CC", "ZP", "YU", "BK", "MG", "CP", "SQ", "NI", "LG"})

METHODS = ("bandar", "nonretail", "sultan", "foreign")
GROUPS = ("foreign", "retail", "institution", "zombie")
LINES = METHODS + ("retail", "institution", "zombie")
BANDAR_TOP = 5
FIT_WINDOW = 60
FIT_MIN = 20
FIT_MIN_CORR = 0.5             # below this no line "fits" (NeoBDM: tidak disarankan)
ACC_WINDOWS = {"d1": 1, "d2": 2, "d3": 3, "d4": 4, "w1": 5, "w2": 10, "w4": 20}
SCREEN_SESSIONS = 20
FLAG_PCTL = 0.90               # crossing / zombie flags = top decile of the day's cross-section
ZOMBIE_FLAG_MIN = 0.10


def sides(side: str, value, value_total) -> tuple[float, float]:
    """(gross buy, gross sell) of one broker-day row."""
    vt, net = float(value_total or 0), abs(float(value or 0))
    other = max(vt - net, 0.0)
    return (vt, other) if side == "BUY" else (other, vt)


def group_of(broker: str, investor_type: str | None) -> str:
    if broker in RETAIL:
        return "retail"
    if broker in ZOMBIE or broker not in MAINSTREAM:
        return "zombie"
    if investor_type == "Asing":
        return "foreign"
    return "institution"


def day_stats(brokers: dict[str, dict]) -> dict:
    """brokers: {code: {"gb": gross buy, "gs": gross sell, "it": investor_type}} for one ticker-day
    (or a window aggregate)."""
    net = {k: 0.0 for k in LINES}
    gross = {g: 0.0 for g in GROUPS}
    nets = []
    cx_num = cx_den = 0.0
    tot = buy = sell = 0.0
    for b, x in brokers.items():
        gb, gs = x["gb"], x["gs"]
        n = gb - gs
        g = group_of(b, x.get("it"))
        net[g] += n
        gross[g] += gb + gs
        if b in SULTAN:
            net["sultan"] += n
        if g != "retail":
            cx_num += 2.0 * min(gb, gs)
            cx_den += gb + gs
        tot += gb + gs
        buy += gb
        sell += gs
        nets.append(n)
    net["nonretail"] = -net["retail"]
    nets.sort()
    net["bandar"] = sum(v for v in nets[::-1][:BANDAR_TOP] if v > 0) + sum(v for v in nets[:BANDAR_TOP] if v < 0)
    return {"net": net, "value": (buy + sell) / 2.0,
            "crossing": cx_num / cx_den if cx_den > 0 else math.nan,
            "zombie_share": gross["zombie"] / tot if tot > 0 else math.nan,
            "group_share": {g: (gross[g] / tot if tot > 0 else math.nan) for g in GROUPS}}


def fit(lines: dict[str, list[float]], closes: list[float]) -> tuple[str | None, dict[str, float]]:
    """Pearson correlation of each cumulative line with the close over the same sessions."""
    c = np.asarray(closes, float)
    scores = {}
    for k, v in lines.items():
        x = np.asarray(v, float)
        ok = np.isfinite(x) & np.isfinite(c)
        if ok.sum() < FIT_MIN or np.std(x[ok]) == 0 or np.std(c[ok]) == 0:
            continue
        scores[k] = float(np.corrcoef(x[ok], c[ok])[0, 1])
    best = max(scores, key=scores.get) if scores else None
    if best is not None and scores[best] < FIT_MIN_CORR:
        best = None
    return best, scores


# --- data access ------------------------------------------------------------------------------

def _sessions(conn, n: int) -> list[str]:
    rows = conn.execute("SELECT DISTINCT trade_date FROM broker_flow ORDER BY trade_date DESC LIMIT ?",
                        (n,)).fetchall()
    return sorted(r[0] for r in rows)


def _load(conn, start: str, end: str, ticker: str | None = None):
    """{(ticker, date): {broker: {gb, gs, it, avg}}}"""
    q = ("SELECT ticker, trade_date, broker_code, side, value, value_total, investor_type, avg_price "
         "FROM broker_flow WHERE trade_date BETWEEN ? AND ?")
    args: tuple = (start, end)
    if ticker:
        q += " AND ticker=?"
        args += (ticker,)
    out: dict = defaultdict(dict)
    for t, d, b, sd, v, vt, it, avg in conn.execute(q, args):
        gb, gs = sides(sd, v, vt)
        x = out[(t, d)].setdefault(b, {"gb": 0.0, "gs": 0.0, "it": it, "avg": None})
        x["gb"] += gb
        x["gs"] += gs
        x["avg"] = avg
    return out


def _closes(conn, ticker: str, start: str, end: str) -> dict[str, float]:
    return {d: c for d, c in conn.execute(
        "SELECT date, close FROM ohlcv WHERE ticker=? AND date BETWEEN ? AND ?", (ticker, start, end))}


def _aggregate(days: list[dict]) -> dict:
    agg: dict = {}
    for brokers in days:
        for b, x in brokers.items():
            a = agg.setdefault(b, {"gb": 0.0, "gs": 0.0, "it": x["it"]})
            a["gb"] += x["gb"]
            a["gs"] += x["gs"]
    return agg


def _acc_pct(per_day: list[dict]) -> dict[str, float | None]:
    out = {}
    for k, w in ACC_WINDOWS.items():
        if len(per_day) < w:
            out[k] = None
            continue
        s = day_stats(_aggregate(per_day[-w:]))
        out[k] = round(100.0 * s["net"]["bandar"] / s["value"], 2) if s["value"] > 0 else None
    return out


def _fit_from(per_day_stats: list[dict], closes: list[float]):
    lines = {m: list(np.cumsum([s["net"][m] for s in per_day_stats])) for m in METHODS}
    best, scores = fit(lines, closes)
    return {"best": best, "scores": {k: round(v, 3) for k, v in scores.items()},
            "window": len(closes), "note": "in-sample fit to the past, not a forecast"}


def _r(x, nd=4):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(x, nd)


def ticker_detail(ticker: str, sessions: int = 120, db_path: str | None = None) -> dict | None:
    ticker = ticker.upper()
    conn = db_connect(db_path or DB_PATH, read_only=True)
    try:
        # the market-wide session calendar, as in screener(): a day the vendor returned nothing for
        # this ticker is a gap, not a reason to reach further back
        ds = _sessions(conn, sessions)
        if not ds:
            return None
        raw = _load(conn, ds[0], ds[-1], ticker)
        if not raw:
            return None
        closes = _closes(conn, ticker, ds[0], ds[-1])
    finally:
        conn.close()
    per_day = [raw.get((ticker, d), {}) for d in ds]
    stats = [day_stats(b) for b in per_day]
    cum = {k: 0.0 for k in LINES}
    series = []
    for d, s in zip(ds, stats):
        for k in LINES:
            cum[k] += s["net"][k]
        series.append({"date": d, "close": closes.get(d), "value": round(s["value"]),
                       "net": {k: round(v) for k, v in s["net"].items()},
                       "cum": {k: round(v) for k, v in cum.items()},
                       "crossing": _r(s["crossing"]), "zombie_share": _r(s["zombie_share"]),
                       "group_share": {g: _r(v) for g, v in s["group_share"].items()}})
    fw = [(s, closes.get(d)) for d, s in zip(ds, stats)][-FIT_WINDOW:]
    fit_out = _fit_from([s for s, _ in fw], [c if c is not None else math.nan for _, c in fw])
    # top brokers over the last 20 sessions: net and average price of the net side
    agg: dict = {}
    for brokers in per_day[-20:]:
        for b, x in brokers.items():
            a = agg.setdefault(b, {"gb": 0.0, "gs": 0.0, "it": x["it"]})
            a["gb"] += x["gb"]
            a["gs"] += x["gs"]
    nets = sorted(((x["gb"] - x["gs"], b, x) for b, x in agg.items()), key=lambda r: r[0])

    def _bk(n, b, x):
        return {"broker": b, "group": group_of(b, x["it"]), "sultan": b in SULTAN, "net": round(n)}
    return {
        "ticker": ticker, "as_of": ds[-1], "sessions": len(ds), "series": series,
        "fit": fit_out, "acc_pct": _acc_pct(per_day),
        "top_brokers": {"window": min(20, len(ds)),
                        "buyers": [_bk(*r) for r in nets[::-1][:8] if r[0] > 0],
                        "sellers": [_bk(*r) for r in nets[:8] if r[0] < 0]},
        "descriptive_only": True,
    }


_SCREEN_CACHE: dict[tuple[str, str], dict] = {}
_SCREEN_LOCK = threading.Lock()


def screener(db_path: str | None = None) -> dict:
    """Market-wide table on the latest broker_flow date; cached per (db, date)."""
    path = db_path or DB_PATH
    conn = db_connect(path, read_only=True)
    try:
        ds = _sessions(conn, FIT_WINDOW)
        if not ds:
            return {"as_of": None, "rows": [], "descriptive_only": True}
        key = (path, ds[-1])
        with _SCREEN_LOCK:
            if key in _SCREEN_CACHE:
                return _SCREEN_CACHE[key]
        raw = _load(conn, ds[0], ds[-1])
        closes: dict = defaultdict(dict)
        for t, d, c in conn.execute("SELECT ticker, date, close FROM ohlcv WHERE date BETWEEN ? AND ?",
                                    (ds[0], ds[-1])):
            closes[t][d] = c
    finally:
        conn.close()
    tickers = sorted({t for (t, d) in raw if d >= ds[-SCREEN_SESSIONS:][0]})
    rows = []
    for t in tickers:
        per_day = [raw.get((t, d), {}) for d in ds]
        if not per_day[-1]:
            continue
        stats = [day_stats(b) for b in per_day]
        cl = [closes[t].get(d, math.nan) for d in ds]
        last5 = day_stats(_aggregate(per_day[-5:]))
        last20 = [s for s in stats[-SCREEN_SESSIONS:]]
        c_now = cl[-1]
        c_5 = cl[-6] if len(cl) >= 6 else math.nan
        rows.append({
            "ticker": t, "close": _r(c_now, 2),
            "ret_5d": _r(100.0 * (c_now / c_5 - 1.0), 2) if (c_5 and math.isfinite(c_5) and math.isfinite(c_now)) else None,
            "value_20d": round(sum(s["value"] for s in last20) / len(last20)),
            "acc_pct": _acc_pct(per_day),
            "net_5d": {k: round(last5["net"][k]) for k in ("foreign", "nonretail", "sultan", "bandar")},
            "crossing": _r(stats[-1]["crossing"]), "crossing_5d": _r(last5["crossing"]),
            "zombie_share": _r(last5["zombie_share"]),
            "fit": _fit_from(stats, cl),
            "flags": [],
        })
    for k, flag, floor in (("crossing", "high_crossing", 0.0), ("zombie_share", "zombie_heavy", ZOMBIE_FLAG_MIN)):
        vals = sorted(r[k] for r in rows if r[k] is not None)
        if len(vals) >= 10:
            cut = vals[int(FLAG_PCTL * (len(vals) - 1))]
            for r in rows:
                if r[k] is not None and r[k] >= cut and r[k] >= floor:
                    r["flags"].append(flag)
    for r in rows:
        if r["fit"]["best"] is None:
            r["flags"].append("no_fit")
    out = {"as_of": ds[-1], "rows": rows, "descriptive_only": True,
           "note": "context only -- no reading here has evidence status (D-094)"}
    with _SCREEN_LOCK:
        _SCREEN_CACHE.clear()
        _SCREEN_CACHE[key] = out
    return out
