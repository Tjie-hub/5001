"""Retail ownership (KSEI) -- {OC} G0-frozen module. PRE-OUTCOME ONLY.

D-083 (mechanism accepted, owner 2026-10-09). Two arms:
  A1 level: individual share of custodied shares, (L_ID + F_ID) / (L_total + F_total).
  A2 flow:  the one-month change of that share.
Prediction: high retail ownership / retail inflow is followed by underperformance, so the spread
S = Q1 (lowest) - Q5 (highest) is > 0.

This module builds, for every formation, the universe, the signals, controls and quintile
membership using ONLY data at or before the formation close. It never computes a return after a
formation date: holding-period returns live in `outcomes.py`, which neither this file nor
`g0_census.py` imports (AST-tested in test_pit_ownership.py).

Panels (frozen, reused from the 2026-10-08 G0s):
- prices: history_long ohlcv_long (pre-2021-07-05 yfinance-derived, split-adjusted; later appended
  from walkforward ohlcv is_final=1). adj_close is a copy of close.
- corporate actions (dividend add-back, split factors) and regular-market minute volume: the
  walkforward snapshot.
- KSEI: ~/idx_external/ksei/ksei_equity_holdings.csv, parsed from 211 public month-end zips
  (manifest + sha256 in ksei_manifest.json).

PIT rule (frozen): KSEI month-end file M is known from the 5th panel session strictly after its
date D_M; the formation is at that session's close (K_M). If the file's zip timestamp is on or after
that session, K_M moves to the first session strictly after the timestamp.

Volume basis (D-081): ohlcv volume is consolidated (incl. negotiated market) from 2026-07-06. For
bars on or after that date the ADV uses regular-market volume, (max buy_lot + max sell_lot) x 100
from stockbit_flow_bars; where no bars exist, the ohlcv volume is kept and the use is counted.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.db import connect as db_connect  # noqa: E402

KSEI_CSV = Path.home() / "idx_external" / "ksei" / "ksei_equity_holdings.csv"
KSEI_CSV_SHA256 = "38c8a90b10546f0602d4568b277d79d154f994e5cafb921bd0d73c3ce55df781"
WF_SNAPSHOT = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db"
HL_SNAPSHOT = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/history_long_snapshot_2026-10-08.db"
WF_SHA256 = "a2d7e675e5c66387446b888287ebbe7cef563b278c48f1518a88c797bc4bbc47"
HL_SHA256 = "7d298068fbc5633277ef0c032ed0257f935c9ef902068b16daa75ac0ba5e5714"

KNOWN_LAG_SESSIONS = 5          # file M usable from the 5th session after its month-end date
ADV_WINDOW = 20
ADV_MIN = 1.0e9                 # true-rupiah ADV20 floor (D-083 / brief)
PRICE_MIN = 50.0                # close at formation (old IDX minimum tick price)
HIST_MIN = 252                  # bars before formation (momentum 12-1 needs them)
PARK_WIN = 60
MOM_SKIP, MOM_LOOK = 21, 252
QUINTILE = 5
BAD_PRINT = 0.35
VOL_BREAK = date(2026, 7, 6)    # D-081
FORU_CUTOFF = date(2026, 9, 14)  # D-063
FIRST_FORMATION_FILE = date(2009, 3, 31)
H1_LAST_FORMATION = date(2017, 12, 31)   # halves by formation date: <= 2017-12-31 / >= 2018-01-01

CENSUS_LEDGER = 609             # after D-080
N_ARMS = 2                      # A1 level, A2 flow
N_FROZEN = CENSUS_LEDGER + N_ARMS   # 611

import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location(
    "bar_v2", REPO_ROOT / "docs" / "research_programs" / "deflation_audit" / "bar_v2.py")
_bar = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_bar)
BAR_EXACT = _bar.e_max_abs_z(N_FROZEN)
BAR_FROZEN = round(BAR_EXACT, 4)

TYPES = ["IS", "CP", "PF", "IB", "ID", "MF", "SC", "FD", "OT"]


def parse_date(v):
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- KSEI

def load_ksei(path=KSEI_CSV) -> dict[date, dict[str, dict]]:
    """{file_date: {ticker: row}}. row: sec_num, tot, ind (L_ID+F_ID), find (F_ID), stamp."""
    out: dict[date, dict[str, dict]] = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            d = parse_date(r["date"])
            tot = float(r["L_total"]) + float(r["F_total"])
            out.setdefault(d, {})[r["ticker"]] = {
                "sec_num": float(r["sec_num"]), "tot": tot,
                "ind": float(r["L_ID"]) + float(r["F_ID"]), "find": float(r["F_ID"]),
                "stamp": parse_date(r["zip_stamp"]),
            }
    return out


# ---------------------------------------------------------------- corporate actions

def load_ca(conn):
    """(split-class share factors per ticker, IDR dividend add-back per (ticker, ex-date)).
    Identical construction to stress_reversal.load_ca (fa78700)."""
    fac: dict[str, list[tuple[date, float]]] = {}
    for at in ("stocksplit", "bonus", "stock_reverse"):
        for t, rj in conn.execute("SELECT ticker, raw_json FROM corporate_action_events "
                                  "WHERE action_type=?", (at,)).fetchall():
            j = json.loads(rj)
            d = parse_date(j.get("stocksplit_exdate"))
            if d is None:
                continue
            try:
                f = (float(j.get("stocksplit_factor")) if at == "bonus"
                     else float(j.get("stocksplit_new")) / float(j.get("stocksplit_old")))
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            if f and f > 0:
                fac.setdefault(t, []).append((d, f))
    for t in fac:
        fac[t].sort()
    divs: dict[tuple[str, date], float] = {}
    seen = set()
    for t, rj in conn.execute("SELECT ticker, raw_json FROM corporate_action_events "
                              "WHERE action_type='dividend'").fetchall():
        j = json.loads(rj)
        did = str(j.get("dividend_id"))
        if did in seen:
            continue
        seen.add(did)
        if j.get("dividend_currency") != "CURRENCY_IDR":
            continue
        try:
            v = float(j.get("dividend_value"))
        except (TypeError, ValueError):
            continue
        ex = parse_date(j.get("dividend_exdate"))
        if v > 0 and ex is not None:
            divs[(t, ex)] = divs.get((t, ex), 0.0) + v
    return fac, divs


def load_regular_volume(conn) -> dict[tuple[str, date], float]:
    """D-081: regular-market shares per (ticker, date) for dates >= VOL_BREAK."""
    out = {}
    for t, d, b, s in conn.execute(
            "SELECT ticker, trade_date, MAX(buy_lot), MAX(sell_lot) FROM stockbit_flow_bars "
            "WHERE trade_date >= ? GROUP BY ticker, trade_date", (VOL_BREAK.isoformat(),)):
        dd = parse_date(d)
        if dd is not None and b is not None and s is not None:
            out[(t, dd)] = (float(b) + float(s)) * 100.0
    return out


# ---------------------------------------------------------------- price panel

class Panel:
    """Per-ticker arrays. Every derived quantity at bar i uses bars <= i only."""

    def __init__(self, hl_conn, fac, divs, regvol, end: date | None = None):
        self.fac, self.divs = fac, divs
        self.tickers: dict[str, dict] = {}
        self.regvol_used = 0
        self.regvol_missing = 0
        sess = set()
        q = "SELECT ticker, date, high, low, close, volume FROM ohlcv_long ORDER BY ticker, date"
        for t, d, h, l, c, v in hl_conn.execute(q):
            dd = parse_date(d)
            if dd is None or (end is not None and dd > end):
                continue
            sess.add(dd)
            g = self.tickers.setdefault(t, {"d": [], "c": [], "v": [], "h": [], "l": []})
            if dd >= VOL_BREAK:
                rv = regvol.get((t, dd))
                if rv is None:
                    self.regvol_missing += 1
                else:
                    v = rv
                    self.regvol_used += 1
            g["d"].append(dd)
            g["c"].append(float(c))
            g["v"].append(float(v or 0.0))
            g["h"].append(float(h))
            g["l"].append(float(l))
        self.sessions = sorted(sess)
        for t, g in self.tickers.items():
            for k in ("c", "v", "h", "l"):
                g[k] = np.asarray(g[k], float)
            n = len(g["d"])
            f = np.asarray([self.f_cum(t, d) for d in g["d"]])
            cv = g["c"] * f * g["v"]
            adv = np.full(n, np.nan)
            if n > ADV_WINDOW:
                cs = np.cumsum(np.concatenate([[0.0], cv]))
                # ADV at bar i = mean of bars i-19..i (the formation bar's own session is known at
                # its close); strictly <= i.
                adv[ADV_WINDOW - 1:] = (cs[ADV_WINDOW:] - cs[:n - ADV_WINDOW + 1]) / ADV_WINDOW
            g["adv"] = adv
            g["idx"] = {d: i for i, d in enumerate(g["d"])}

    def f_cum(self, t: str, d: date) -> float:
        p = 1.0
        for de, f in self.fac.get(t, ()):
            if de > d:
                p *= f
        return p

    def nth_session_after(self, d: date, n: int) -> date | None:
        import bisect
        i = bisect.bisect_right(self.sessions, d)
        j = i + n - 1
        return self.sessions[j] if j < len(self.sessions) else None

    def features(self, t: str, k: date) -> dict | None:
        """Pre-formation facts for ticker t at formation session k (bar must exist at k)."""
        g = self.tickers.get(t)
        if g is None:
            return None
        i = g["idx"].get(k)
        if i is None:
            return None
        hist = i  # bars strictly before k
        c = g["c"]
        out = {"close": float(c[i]), "adv": float(g["adv"][i]) if i >= ADV_WINDOW - 1 else math.nan,
               "hist": hist, "vol_k": float(g["v"][i])}
        if i >= PARK_WIN - 1:
            hh, ll = g["h"][i - PARK_WIN + 1:i + 1], g["l"][i - PARK_WIN + 1:i + 1]
            ok = (hh > 0) & (ll > 0) & (hh >= ll)
            x = np.log(hh[ok] / ll[ok]) ** 2
            out["park60"] = float(math.sqrt(x.mean() / (4 * math.log(2)))) if ok.sum() >= 40 else math.nan
        else:
            out["park60"] = math.nan
        if i >= MOM_LOOK:
            a, b = c[i - MOM_LOOK], c[i - MOM_SKIP]
            out["mom"] = float(b / a - 1.0) if a > 0 else math.nan
        else:
            out["mom"] = math.nan
        # daily-return SD over the 60 sessions up to k (cost impact term), dividend add-back
        if i >= 61:
            w = c[i - 60:i + 1]
            ds = g["d"][i - 60:i + 1]
            div = np.asarray([self.divs.get((t, d), 0.0) for d in ds[1:]])
            r = (w[1:] + div) / w[:-1] - 1.0
            r = r[np.isfinite(r) & (np.abs(r) <= BAD_PRINT)]
            out["sigma60"] = float(np.std(r, ddof=1)) if len(r) >= 40 else math.nan
        else:
            out["sigma60"] = math.nan
        return out


# ---------------------------------------------------------------- formations

def formations(panel: Panel, ksei: dict) -> list[dict]:
    """One row per KSEI file M: file date, known session K_M (formation close)."""
    out = []
    for dm in sorted(ksei):
        if dm < FIRST_FORMATION_FILE:
            continue
        k = panel.nth_session_after(dm, KNOWN_LAG_SESSIONS)
        stamps = [r["stamp"] for r in ksei[dm].values() if r["stamp"]]
        st = max(stamps) if stamps else None
        delayed = False
        # A file whose zip was stamped on or after the planned session may have been (re)published
        # late: form at the first session strictly after the stamp instead (4 of 210 at G0).
        if k is not None and st is not None and st >= k:
            k = panel.nth_session_after(st, 1)
            delayed = True
        if k is None:
            continue
        out.append({"file": dm, "k": k, "stamp": st, "delayed_by_stamp": delayed})
    return out


def build_cross_section(panel: Panel, ksei: dict, form: dict, prev_file: date | None) -> dict:
    """Universe + signals + controls at formation `form` (pre-outcome)."""
    dm, k = form["file"], form["k"]
    rows, drop = [], {"no_bar": 0, "tot0": 0, "adv": 0, "price": 0, "hist": 0, "foru": 0,
                      "ctrl_nan": 0}
    prev = ksei.get(prev_file, {}) if prev_file else {}
    for t, kr in ksei[dm].items():
        if t == "FORU" and k >= FORU_CUTOFF:
            drop["foru"] += 1
            continue
        if kr["tot"] <= 0:
            drop["tot0"] += 1
            continue
        ft = panel.features(t, k)
        if ft is None:
            drop["no_bar"] += 1
            continue
        if not (ft["adv"] >= ADV_MIN):
            drop["adv"] += 1
            continue
        if not (ft["close"] >= PRICE_MIN):
            drop["price"] += 1
            continue
        if ft["hist"] < HIST_MIN:
            drop["hist"] += 1
            continue
        s = kr["ind"] / kr["tot"]
        s_sec = kr["ind"] / kr["sec_num"] if kr["sec_num"] > 0 else math.nan
        pr = prev.get(t)
        ds = (s - pr["ind"] / pr["tot"]) if pr and pr["tot"] > 0 else math.nan
        size = math.log(kr["sec_num"] * ft["close"] * panel.f_cum(t, k)) if kr["sec_num"] > 0 else math.nan
        rows.append({"t": t, "s": s, "s_sec": s_sec, "ds": ds, "adv": ft["adv"], "size": size,
                     "park60": ft["park60"], "mom": ft["mom"], "sigma60": ft["sigma60"],
                     "fshare": kr["find"] / kr["tot"], "custody": kr["tot"] / kr["sec_num"] if kr["sec_num"] > 0 else math.nan})
    # VOLEX flag: top decile of park60 within the formation universe
    pk = sorted(r["park60"] for r in rows if np.isfinite(r["park60"]))
    cut = pk[int(math.floor(0.9 * len(pk)))] if len(pk) >= 10 else math.inf
    for r in rows:
        r["volex"] = 1 if np.isfinite(r["park60"]) and r["park60"] >= cut else 0
    return {"file": dm, "k": k, "rows": rows, "drop": drop}


def quintiles(rows: list[dict], key: str) -> tuple[list[str], list[str], int]:
    """(Q1 lowest, Q5 highest, n ranked); ties by (value, ticker); NaN keys excluded."""
    xs = sorted((r[key], r["t"]) for r in rows if np.isfinite(r[key]))
    n = len(xs)
    kq = n // QUINTILE
    if kq < 1:
        return [], [], n
    return [t for _, t in xs[:kq]], [t for _, t in xs[-kq:]], n


_CACHE = Path.home() / "scratch" / "retail_ownership_regvol_2026-10-08.json"


def load_all(end: date | None = None):
    """Open the pinned snapshots read-only and build everything pre-outcome.
    `end` truncates the price panel (PIT truncation test)."""
    hl = db_connect(path=HL_SNAPSHOT, read_only=True)
    wf = db_connect(path=WF_SNAPSHOT, read_only=True)
    fac, divs = load_ca(wf)
    # the regular-volume scan over stockbit_flow_bars is slow; cache it beside the snapshot
    # (derived only from the pinned snapshot, keyed by its sha256).
    if _CACHE.exists() and json.loads(_CACHE.read_text()).get("wf_sha256") == WF_SHA256:
        raw = json.loads(_CACHE.read_text())["rows"]
        regvol = {(t, parse_date(d)): v for t, d, v in raw}
    else:
        regvol = load_regular_volume(wf)
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE.write_text(json.dumps({"wf_sha256": WF_SHA256,
                                      "rows": [[t, d.isoformat(), v] for (t, d), v in regvol.items()]}))
    panel = Panel(hl, fac, divs, regvol, end=end)
    ksei = load_ksei()
    return panel, ksei
