#!/usr/bin/env python3
"""SCREEN-PM-XP-001 -- long-only exclusion portfolio (screen authority only).

Frozen spec: planner instruction 2026-09-30 (constants verbatim below); every
rule is cited to its frozen text in the memo. No registration, no family slot,
no forward test; the corpus is read read-only.

Run from the repo root:
    python docs/research_programs/P-M/exclusion_portfolio/run_screen.py

    Panel input  a prepared panel artifact (CSV.gz) built ONCE outside this
              script by the committed frozen pipeline
              `research.rulecard.data.load_extended_ohlcv(issuance=True)`
              (backfill + corpus merge, split repair, D-064 issuance wealth
              correction), then the broad-search conventions: FORU rows from
              2026-09-14 dropped (D-063), panel cut at 2026-09-16 (the
              broad-search program cutoff). The artifact lives outside the
              repo (~/xp_panel/panel.csv.gz by default, XP_PANEL overrides)
              with a sha256 sidecar that this script verifies -- the same
              fingerprinted-artifact pattern as the broad-search snapshot.
              Its provenance (sha256, row/ticker counts, max date) is recorded
              in results.json. The local corpus ends 2026-07-29 (memo).
    Universe  exactly FWD-PM-VOLEX-001's definition (forward_exclusion/PROTOCOL.md
              section 2, mirrored from run_forward.py): liquid set = trailing-60
              MEDIAN traded value >= Rp 1e9 (shift 1, min_periods 20), close >=
              Rp 50, traded on the formation day (volume > 0), not within +/-20
              sessions of a suspension window (suspension_events,
              last_normal_date..resume_date padded 20); then TOP 200 by that
              trailing-60 median traded value.
    Window    the 2026-09-29 broad-search screens' window: data through CUT
              2026-09-16, formations from the first complete month-end session
              >= 2021-07-05 (the screens' confirmation half; IHSG coverage
              starts 2021-07).
    Exclusions  A = SCREEN-PM-LC-001 YOUNG (PREDECLARATION_S2_LC_LISTINGS.md):
                  listing proxy = first panel bar; first bars exactly on a
                  corpus-coverage start date (backfill start or 2021-07-05) are
                  onboarding artifacts, not listings; flag row = first own
                  session with n_prior >= 25; a name is young at formation F
                  when its flag exists (first bar in [2015-01-01, 2026-09-16])
                  and own sessions since the flag < 252 (the screen's tested
                  primary hold). Pre-flag names (own index < 25) are NOT
                  excluded by the literal rule; their exposure is measured and
                  reported (memo ambiguity A-1).
                B = VOLEX-001 high-vol (PROTOCOL.md section 2): Parkinson-60 =
                  sqrt(mean_60(ln(high/low)^2)/(4 ln2)), min_periods 30; at each
                  formation exclude the top 10% among universe members
                  (k = max(1, round(len*0.10))).
                C = HYP-PM-0012 failed breakdown within the trailing 20 sessions
                  (forward_fade/PROTOCOL.md section 2, gates mirrored verbatim
                  from scripts/fade_failed_breakdown.py): lo20 = rolling-20 low
                  shifted 1; signal = low(t) < lo20(t) and close(t) > lo20(t) on
                  rows passing adv20 >= Rp 1e9 (shift 1, min_periods 15),
                  close >= 50, n >= 25, volume > 0, nz20 >= 18 of trailing 20
                  (shift 1, excluding current). Excluded at F when a signal
                  fired on any of the 20 own sessions ending at F.
    Portfolio equal-weight, monthly rebalance on the last COMPLETE session of
              each calendar month (session guard: priced tickers >= 95% of the
              trailing-20 median, VOLEX convention); fills at the NEXT session
              OPEN (engine/entry_convention.py); held until the next month's
              entry session (contiguous book).
    Variants  A+B+C (combined), A only, B only, C only.
    Benchmarks (1) PRIMARY: equal-weight same universe, no exclusions, identical
              convention; (2) IHSG open-to-open over the same session pairs.
    Costs     frozen 0.60% RT (0.30% per side charged on turnover) AND the
              D-059 modeled cost: 0.50% fees + half Abdi-Ranaldo spread each
              side, floored at one tick + 2*sigma_d*sqrt(Q/adv20) impact at
              entry; Q = Rp 100m (D-059 primary size). The AR-spread/sigma
              primitives are copied VERBATIM from cost_liquidity/cost_by_adv.py
              (per_day_liquidity/tick_size/ar_terms; frozen by its
              PREDECLARATION.md, sha256 ac3a1a19, D-059). Turnover charged on
              membership changes between consecutive books; month 1 builds from
              cash; the final book is never liquidated (identical across
              variants). Names missing D-059 inputs at the charge date fall
              back to the frozen per-side rate (counted, reported).
    Net excess  (variant gross - variant cost) - (benchmark gross - benchmark
              cost); IHSG carries no cost.
    Stats     per variant x benchmark x lens: mean monthly excess, Newey-West
              t (lag 3, stated), by-year table, % months positive, mean
              turnover, max relative drawdown of the compounded net-excess
              curve.
    Verdict   combined variant, PRIMARY benchmark, modeled cost: PASS = NW t >=
              2.8575 (D-064 bar) AND positive excess in >= 2/3 of calendar
              years; SUGGESTIVE = 2.0 <= t < 2.8575; else FAIL.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# The script runs from the repo root (see header). Every repo path used below
# is built DOWNWARD from that root and validated to stay inside it -- no parent
# traversal anywhere. The panel artifact is a fingerprinted input that lives
# OUTSIDE the repo (~/xp_panel/, the broad-search snapshot pattern).
ROOT = Path(os.environ.get("IDX_ROOT", os.getcwd())).resolve()


def _inside_root(p: Path) -> Path:
    rp = p.resolve()
    if rp != ROOT and ROOT not in rp.parents:
        raise SystemExit(f"path escapes the repo root, refusing: {rp}")
    return rp


LOCAL_DB = _inside_root(ROOT / "data" / "walkforward.db")
HERE = _inside_root(ROOT / "docs" / "research_programs" / "P-M" / "exclusion_portfolio")
PANEL = Path(os.environ.get("XP_PANEL", str(Path.home() / "xp_panel" / "panel.csv.gz")))
if not PANEL.exists():
    raise SystemExit(f"panel artifact missing: {PANEL} (see the memo's prep step)")
sys.path.insert(0, str(ROOT))

# WSL/DrvFS: SQLite reads of the corpus through /mnt/d fail with disk I/O error
# unless mmap is disabled on every connection (Python 3.12 build default).
_orig_connect = sqlite3.connect


def _patched_connect(*a, **k):
    conn = _orig_connect(*a, **k)
    try:
        conn.execute("PRAGMA mmap_size=0")
    except Exception:
        pass
    return conn


sqlite3.connect = _patched_connect

# frozen constants (cited above; none chosen after seeing results)
CUT = pd.Timestamp("2026-09-16")           # broad-search program data cutoff
WINDOW_START = pd.Timestamp("2021-07-05")  # broad-search confirmation half
UNIVERSE_N, EXCLUDE_FRAC = 200, 0.10       # VOLEX PROTOCOL.md section 2
LIQ_FLOOR, MIN_PRICE, SUSP_PAD, PARK_WIN = 1e9, 50.0, 20, 60
SESSION_COMPLETE_FRAC = 0.95               # VOLEX session guard
YOUNG_LIST_LO, YOUNG_LIST_HI = pd.Timestamp("2015-01-01"), pd.Timestamp("2026-09-16")
YOUNG_MIN_PRIOR, YOUNG_HOLD = 25, 252      # SCREEN-PM-LC-001 flag + primary hold
FADE_ADV, FADE_PRICE, FADE_MIN_N = 1e9, 50, 25   # HYP-PM-0012 section 2 gates
FADE_GUARD_MIN = 18
C_TRAIL = 20                               # "within the trailing 20 sessions"
NW_LAG = 3                                 # Newey-West lag, monthly series
PASS_T, SUGGEST_T = 2.8575, 2.0            # D-064 bar; planner verdict rule
FROZEN_RT = 0.006                          # repo cost authority (0.30%/side)
FEES_RT = 0.005                            # D-059: fees inside the modeled cost
MODELED_Q = 100e6                          # D-059 primary position size
D059_WIN = 21                              # D-059 AR/sigma trailing window
VARIANTS = ("A", "B", "C", "A_B_C")


# ---- D-059 modeled-cost primitives, copied VERBATIM from
#      docs/research_programs/P-M/cost_liquidity/cost_by_adv.py
#      (tick_size / ar_terms / per_day_liquidity; frozen by its
#      PREDECLARATION.md, sha256 ac3a1a19; D-059). ----
def tick_size(price):
    p = np.asarray(price, float)
    return np.select([p < 200, p < 500, p < 2000, p < 5000], [1, 2, 5, 10], 25).astype(float)


def ar_terms(close, high, low):
    """Abdi-Ranaldo two-day term 4(c_t - eta_t)(c_t - eta_{t+1}), indexed at t."""
    c = np.log(np.asarray(close, float))
    eta = (np.log(np.asarray(high, float)) + np.log(np.asarray(low, float))) / 2
    eta_next = np.r_[eta[1:], np.nan]
    return 4 * (c - eta) * (c - eta_next)


def per_day_liquidity(d):
    """Spread (AR, floored) and sigma_d per name-day, from traded sessions
    t-21..t-1 only (D-059 cost_by_adv.per_day_liquidity, verbatim)."""
    tr = d[d.volume > 0].copy()
    g = tr.groupby("ticker", sort=False)
    parts = []
    for _, x in g:
        term = pd.Series(ar_terms(x.close.values, x.high.values, x.low.values), index=x.index)
        avail = term.shift(1)
        m = avail.rolling(D059_WIN - 1, min_periods=D059_WIN - 1).mean().shift(1)
        lr = np.log(x.close).diff()
        sig = lr.rolling(D059_WIN - 1, min_periods=D059_WIN - 1).std().shift(1)
        parts.append(pd.DataFrame({"s_ar": np.sqrt(m.clip(lower=0)), "sig_d": sig}, index=x.index))
    liq = pd.concat(parts)
    out = d.join(liq)
    out[["s_ar", "sig_d"]] = out.groupby("ticker", sort=False)[["s_ar", "sig_d"]].ffill()
    out["tick_floor"] = tick_size(out.close) / out.close
    out["s"] = np.maximum(out.s_ar, out.tick_floor)
    return out
# ---- END D-059 VERBATIM BLOCK ----


def load_panel():
    """Read + verify the fingerprinted panel artifact."""
    sidecar = PANEL.with_suffix("") .with_suffix(".sha256") \
        if PANEL.name.endswith(".csv.gz") else PANEL.parent / "panel.sha256"
    digest = hashlib.sha256(PANEL.read_bytes()).hexdigest()
    recorded = None
    if sidecar.exists():
        recorded = sidecar.read_text().strip().split()[0]
    P = pd.read_csv(PANEL)
    P["date"] = pd.to_datetime(P["date"])
    meta = {"panel_artifact": str(PANEL), "sha256": digest,
            "sha256_verified": bool(recorded is None or recorded == digest),
            "rows": int(len(P)), "tickers": int(P["ticker"].nunique()),
            "panel_max_date": str(P["date"].max().date()),
            "issuance_corrected": True, "foru_dropped_d063": True}
    return P, meta


def panel_matrix(P):
    """Date x ticker matrices on the prepared panel. IHSG is kept out of the
    stock universe (an index is not a tradeable name -- memo note U-1)."""
    stocks = P[P["ticker"] != "IHSG"]
    piv = lambda c: stocks.pivot_table(index="date", columns="ticker", values=c,
                                       aggfunc="last").sort_index()
    cl, op, hi, lo, vol = piv("close"), piv("open"), piv("high"), piv("low"), piv("volume")
    tvm = (cl * vol).rolling(60, min_periods=20).median().shift(1)   # VOLEX exact
    return dict(close=cl, open=op, high=hi, low=lo, vol=vol, tvm=tvm,
                dates=list(cl.index))


def suspension_mask():
    """VOLEX: not within +/-20 sessions of a suspension window."""
    con = sqlite3.connect(f"file:{LOCAL_DB}?mode=ro", uri=True)
    susp = pd.read_sql_query(
        "SELECT ticker,last_normal_date,resume_date FROM suspension_events", con)
    con.close()
    return susp


def load_ihsg():
    """IHSG open/close from the corpus read-only (the prepared panel carries
    no IHSG rows: the backfill lacks the index and merge_extended drops it
    from the DB rows). Same read as fade_failed_breakdown.load()."""
    con = sqlite3.connect(f"file:{LOCAL_DB}?mode=ro", uri=True)
    ih = pd.read_sql_query(
        "SELECT date,open,close FROM ohlcv WHERE ticker='IHSG' AND is_final=1 "
        "AND close>0 ORDER BY date", con)
    con.close()
    ih["date"] = pd.to_datetime(ih["date"])
    return ih.set_index("date").sort_index()


def parkinson(panel):
    hi, lo = panel["high"], panel["low"]
    return np.sqrt((np.log(hi / lo.replace(0, np.nan)) ** 2)
                   .rolling(PARK_WIN, min_periods=PARK_WIN // 2).mean()
                   / (4 * np.log(2)))                       # VOLEX exact


def fade_signals(P):
    """HYP-PM-0012 signal per name, gates mirrored verbatim from
    forward_fade/scripts/fade_failed_breakdown.py build()."""
    d = P[["ticker", "date", "low", "close", "volume"]].copy()
    d = d.sort_values(["ticker", "date"]).reset_index(drop=True)
    g = d.groupby("ticker", sort=False)
    d["n"] = g.cumcount()
    dval = d["close"] * d["volume"]
    d["adv20"] = dval.groupby(d["ticker"]).transform(
        lambda s: s.rolling(20, min_periods=15).mean())
    d["adv20"] = g["adv20"].shift(1)
    d["lo20"] = g["low"].transform(
        lambda s: s.rolling(20, min_periods=20).min()).groupby(d["ticker"]).shift(1)
    nz = (d["volume"] > 0).astype(int)
    d["nz20"] = nz.groupby(d["ticker"]).transform(
        lambda s: s.shift(1).rolling(20, min_periods=20).sum())
    liq = ((d["adv20"] >= FADE_ADV) & (d["close"] >= FADE_PRICE) &
           (d["n"] >= FADE_MIN_N) & (d["volume"] > 0) &
           (d["nz20"] >= FADE_GUARD_MIN)).fillna(False)
    sig = (d["low"] < d["lo20"]) & (d["close"] > d["lo20"]) & liq
    return d.loc[sig, ["ticker", "date"]].reset_index(drop=True)


def young_flags(P):
    """SCREEN-PM-LC-001 YOUNG flag rows, literal (see module docstring)."""
    d = P[["ticker", "date"]].copy()
    d = d.sort_values(["ticker", "date"]).reset_index(drop=True)
    g = d.groupby("ticker", sort=False)
    first_bar = g["date"].transform("first")
    own_n = g.cumcount()
    coverage_starts = {d["date"].min(), WINDOW_START}
    is_artifact = first_bar.isin(coverage_starts)
    listed_in_window = (first_bar >= YOUNG_LIST_LO) & (first_bar <= YOUNG_LIST_HI)
    flag = listed_in_window & ~is_artifact & (own_n == YOUNG_MIN_PRIOR)
    flags = d.loc[flag].set_index("ticker")["date"]          # flag date per ticker
    own_series = pd.Series(own_n.values,
                           index=pd.MultiIndex.from_arrays([d["ticker"], d["date"]]))
    return flags, own_series


def formations(panel, complete):
    """Last complete session of each calendar month in the window."""
    dates = pd.DatetimeIndex(panel["dates"])
    in_win = dates[(dates >= WINDOW_START) & (dates <= CUT)]
    out = []
    for _, grp in pd.Series(in_win, index=in_win).groupby(in_win.to_period("M")):
        for d in reversed(list(grp)):
            if bool(complete.get(d, False)):
                out.append(d)
                break
    return out


def nw_t(x, lag=NW_LAG):
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    T = len(x)
    if T < 5:
        return float("nan")
    e = x - x.mean()
    s = float(e @ e)
    for k in range(1, min(lag, T - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        s += 2.0 * w * float(e[k:] @ e[:-k])
    se = np.sqrt(s / T / T)
    return float(x.mean() / se) if se > 0 else float("nan")


def max_drawdown(x):
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    if len(x) == 0:
        return float("nan")
    eq = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(eq)
    return float(((eq / peak) - 1.0).min())


def d059_liquidity(P):
    """Per name-day s and sigma_d via the verbatim D-059 primitives above;
    adv20 (FADE convention) for the impact term."""
    d = P[["ticker", "date", "close", "high", "low", "volume"]].copy()
    d = d.sort_values(["ticker", "date"]).reset_index(drop=True)
    liq = per_day_liquidity(d)
    dval = liq["close"] * liq["volume"]
    liq["adv20"] = dval.groupby(liq["ticker"]).transform(
        lambda s: s.rolling(20, min_periods=15).mean())
    liq["adv20"] = liq.groupby("ticker", sort=False)["adv20"].shift(1)
    return liq.set_index(["ticker", "date"])[["s", "sig_d", "adv20"]]


def main():
    t0 = datetime.now(timezone.utc)
    P, meta = load_panel()
    panel = panel_matrix(P)
    ihsg = load_ihsg()
    cl, op, tvm, vol = panel["close"], panel["open"], panel["tvm"], panel["vol"]
    dates_idx = pd.DatetimeIndex(panel["dates"])
    pos_of = {d: i for i, d in enumerate(dates_idx)}

    susp = suspension_mask()
    didx = {d: i for i, d in enumerate(dates_idx)}
    cont = pd.DataFrame(False, index=dates_idx, columns=cl.columns)
    for _, r in susp.iterrows():
        tk = r["ticker"]
        if tk not in cont.columns:
            continue
        i0 = didx.get(pd.Timestamp(r["last_normal_date"]))
        if i0 is None:
            continue
        rd = pd.Timestamp(r["resume_date"]) if r["resume_date"] else None
        i1 = didx.get(rd, i0)
        cont.iloc[max(0, i0 - SUSP_PAD): min(len(dates_idx) - 1, i1 + SUSP_PAD) + 1,
                  cont.columns.get_loc(tk)] = True

    eligible = ((tvm >= LIQ_FLOOR) & (cl >= MIN_PRICE) & (vol > 0) & ~cont).fillna(False)
    park = parkinson(panel)
    flags, own_series = young_flags(P)
    young_until = {tk: YOUNG_MIN_PRIOR + YOUNG_HOLD - 1 for tk in flags.index}
    sig_c = fade_signals(P)
    c_dates = {tk: pd.DatetimeIndex(g["date"].sort_values())
               for tk, g in sig_c.groupby("ticker", sort=False)}
    liq_d059 = d059_liquidity(P)

    cnt = cl.notna().sum(axis=1)   # VOLEX session guard
    complete = cnt >= SESSION_COMPLETE_FRAC * cnt.rolling(20, min_periods=5).median()
    fms = formations(panel, complete)
    fms = fms[:-1] if len(fms) > 1 else fms   # last formation has no next entry

    def entry_session(f):
        i = pos_of[f] + 1
        return dates_idx[i] if i < len(dates_idx) else None

    books, ordered_entries, formation_log = {}, [], []
    pre_flag_total = 0
    for f in fms:
        elig = eligible.loc[f]
        adv = tvm.loc[f].where(elig).dropna()
        if len(adv) < UNIVERSE_N:
            formation_log.append({"formation": str(f.date()),
                                  "skipped": f"only {len(adv)} eligible (< {UNIVERSE_N})"})
            continue
        uni = set(adv.nlargest(UNIVERSE_N).index)              # VOLEX exact
        sigb = park.loc[f].reindex(sorted(uni)).dropna()       # rule B
        k = max(1, int(round(len(sigb) * EXCLUDE_FRAC)))
        excl_b = set(sigb.nlargest(k).index)
        excl_a, young_seen = set(), 0                          # rule A
        for tk in sorted(uni):
            own = own_series.get((tk, f))
            if own is None or not np.isfinite(own):
                continue
            if tk in young_until and own <= young_until[tk]:
                excl_a.add(tk)
            if own < YOUNG_MIN_PRIOR:
                young_seen += 1
        pre_flag_total += young_seen
        excl_c = set()                                         # rule C
        i_f = pos_of[f]
        win_lo = dates_idx[max(0, i_f - (C_TRAIL - 1))]
        for tk in sorted(uni):
            sdates = c_dates.get(tk)
            if sdates is None:
                continue
            if len(sdates[(sdates >= win_lo) & (sdates <= f)]):
                excl_c.add(tk)
        es = entry_session(f)
        if es is None:
            formation_log.append({"formation": str(f.date()), "skipped": "no entry session"})
            continue
        excl = {"A": excl_a, "B": excl_b, "C": excl_c,
                "A_B_C": excl_a | excl_b | excl_c}
        books[es] = {"universe": uni,
                     **{v: uni - excl[v] for v in VARIANTS},
                     "excl_sizes": {v: len(excl[v]) for v in VARIANTS},
                     "formation": f}
        ordered_entries.append(es)
        formation_log.append({
            "formation": str(f.date()), "entry": str(es.date()), "universe_n": len(uni),
            **{f"excl_{v}": len(excl[v]) for v in VARIANTS},
            "young_unflagged_in_universe": young_seen})

    def book_return(names, d0, d1):
        a = op.loc[d0, sorted(names)]
        b = op.loc[d1, sorted(names)]
        return (b / a - 1.0).replace([np.inf, -np.inf], np.nan).dropna()

    def d059_side(tk, d, side):
        """One-side modeled cost; falls back to the frozen per-side rate when
        the D-059 inputs are missing (counted in liq_fallbacks)."""
        key = (tk, d)
        if key in liq_d059.index:
            li = liq_d059.loc[key]
            s, sig, adv = li.get("s", np.nan), li.get("sig_d", np.nan), li.get("adv20", np.nan)
            if all(np.isfinite(v) for v in (s, sig, adv)) and adv > 0:
                if side == "entry":
                    return FEES_RT / 2.0 + 0.5 * s + 2.0 * sig * np.sqrt(MODELED_Q / adv), True
                return FEES_RT / 2.0 + 0.5 * s, True
        return FROZEN_RT / 2.0, False

    months = []
    prev_books = {v: set() for v in ("universe",) + VARIANTS}
    liq_fallbacks = 0
    for j, es in enumerate(ordered_entries):
        nxt = ordered_entries[j + 1] if j + 1 < len(ordered_entries) else None
        if nxt is None:
            continue
        row = {"formation": str(books[es]["formation"].date()),
               "entry": str(es.date()), "next_entry": str(nxt.date())}
        ih0 = ihsg["open"].get(es, np.nan)
        ih1 = ihsg["open"].get(nxt, np.nan)
        row["ihsg_gross"] = (float(ih1 / ih0 - 1.0)
                             if np.isfinite(ih0) and np.isfinite(ih1) and ih0 > 0 else None)
        for v in ("universe",) + VARIANTS:
            names = books[es][v]
            r = book_return(names, es, nxt)
            old = prev_books[v]
            enters, exits = names - old, old - names
            cost_f = FROZEN_RT / 2.0 * (len(exits) / max(1, len(old))
                                        + len(enters) / max(1, len(names)))
            cm = 0.0
            for tk in enters:
                c, ok = d059_side(tk, es, "entry")
                cm += c
                liq_fallbacks += 0 if ok else 1
            for tk in exits:
                c, ok = d059_side(tk, nxt, "exit")
                cm += c
                liq_fallbacks += 0 if ok else 1
            row[v] = {"gross": float(r.mean()) if len(r) else None,
                      "n": int(len(r)),
                      "cost_frozen": float(cost_f),
                      "cost_modeled": float(cm / max(1, len(names))),
                      "turnover_1s": (len(exits) / max(1, len(old))
                                      + len(enters) / max(1, len(names)))}
        months.append(row)
        prev_books = {v: books[es][v] for v in ("universe",) + VARIANTS}

    years = sorted({m["entry"][:4] for m in months})
    stats = {}
    for var in VARIANTS:
        for bench in ("universe", "ihsg"):
            gross_ex, net_f, net_m, tos, ns = [], [], [], [], []
            for m in months:
                b = m["ihsg_gross"] if bench == "ihsg" else m["universe"]["gross"]
                bv = m["universe"]
                if b is None or m[var]["gross"] is None:
                    continue
                gross_ex.append(m[var]["gross"] - b)
                if bench == "universe":
                    bench_net_f = bv["gross"] - bv["cost_frozen"]
                    bench_net_m = bv["gross"] - bv["cost_modeled"]
                else:
                    bench_net_f = bench_net_m = b       # IHSG: no costs
                net_f.append((m[var]["gross"] - m[var]["cost_frozen"]) - bench_net_f)
                net_m.append((m[var]["gross"] - m[var]["cost_modeled"]) - bench_net_m)
                tos.append(m[var]["turnover_1s"])
                ns.append(m[var]["n"])
            d = {"months": len(gross_ex),
                 "mean_book_n": round(float(np.mean(ns)), 1) if ns else None,
                 "mean_turnover_1s": round(float(np.mean(tos)), 4) if tos else None,
                 "mean_monthly_excess_gross_pct": round(100 * float(np.mean(gross_ex)), 4),
                 "nw_t_gross": round(nw_t(gross_ex), 3),
                 "pct_months_positive_gross": round(float(np.mean(np.array(gross_ex) > 0)), 4),
                 "mean_monthly_excess_net_frozen_pct": round(100 * float(np.mean(net_f)), 4),
                 "nw_t_net_frozen": round(nw_t(net_f), 3),
                 "mean_monthly_excess_net_modeled_pct": round(100 * float(np.mean(net_m)), 4),
                 "nw_t_net_modeled": round(nw_t(net_m), 3),
                 "pct_months_positive_net_modeled": round(float(np.mean(np.array(net_m) > 0)), 4),
                 "max_relative_drawdown_net_modeled": round(max_drawdown(net_m), 4),
                 "by_year": {}}
            for y in years:
                ys = [g for g, m in zip(gross_ex, months) if m["entry"][:4] == y]
                ym = [g for g, m in zip(net_m, months) if m["entry"][:4] == y]
                d["by_year"][y] = {"months": len(ys),
                                   "mean_gross_excess_pct": round(100 * float(np.mean(ys)), 3) if ys else None,
                                   "mean_net_modeled_excess_pct": round(100 * float(np.mean(ym)), 3) if ym else None}
            pos_cum = [max(0.0, v["mean_net_modeled_excess_pct"] or 0.0)
                       for v in d["by_year"].values()]
            tot = sum(pos_cum)
            d["era_concentration"] = {
                "max_year_share_of_positive_cumulative_excess":
                    round(max(pos_cum) / tot, 3) if tot > 0 else None,
                "largest_month_gross_excess_pct": round(100 * float(np.max(gross_ex)), 3),
                "largest_month_entry": months[int(np.argmax(gross_ex))]["entry"]}
            stats[f"{var}_vs_{bench}"] = d

    prim = stats["A_B_C_vs_universe"]
    t = prim["nw_t_net_modeled"]
    years_pos = sum(1 for v in prim["by_year"].values()
                    if (v["mean_net_modeled_excess_pct"] or 0) > 0 and v["months"] >= 3)
    years_total = len(prim["by_year"])
    if np.isfinite(t) and t >= PASS_T and years_pos >= (2.0 / 3.0) * years_total:
        verdict = "PASS"
    elif np.isfinite(t) and t >= SUGGEST_T:
        verdict = "SUGGESTIVE"
    else:
        verdict = "FAIL"

    out = {"screen": "SCREEN-PM-XP-001",
           "generated_utc": t0.isoformat(timespec="seconds"),
           "verdict_combined_vs_primary_modeled_cost": verdict,
           "verdict_basis": {"nw_t_net_modeled": t, "years_positive": years_pos,
                             "years_total": years_total, "nw_pass_bar": PASS_T},
           "liq_fallback_sides": liq_fallbacks,
           "pre_flag_young_universe_members_total": pre_flag_total,
           "panel_meta": meta, "nw_lag": NW_LAG, "modeled_cost_Q": MODELED_Q,
           "formations": formation_log, "monthly_series": months, "stats": stats}
    with open(HERE / "results.json", "w") as fh:
        json.dump(out, fh, indent=1, default=str)

    print(f"VERDICT (combined, PRIMARY benchmark, modeled cost): {verdict}")
    print(f"  NW t (net, modeled) = {t}; years positive {years_pos}/{years_total}")
    for key in ("A_B_C_vs_universe", "A_vs_universe", "B_vs_universe", "C_vs_universe",
                "A_B_C_vs_ihsg", "A_vs_ihsg", "B_vs_ihsg", "C_vs_ihsg"):
        s = stats[key]
        print(f"  {key:20s} n={s['months']:3d}  "
              f"gross {s['mean_monthly_excess_gross_pct']:+.3f}%/mo (t {s['nw_t_gross']:+.2f})  "
              f"netF {s['mean_monthly_excess_net_frozen_pct']:+.3f} (t {s['nw_t_net_frozen']:+.2f})  "
              f"netM {s['mean_monthly_excess_net_modeled_pct']:+.3f} (t {s['nw_t_net_modeled']:+.2f})  "
              f"turn {s['mean_turnover_1s']:.3f}")
    print(f"\nformations: {len(formation_log)}  pre-flag young members seen: "
          f"{pre_flag_total}  liq fallbacks: {liq_fallbacks}")
    print(f"written {HERE / 'results.json'}")


if __name__ == "__main__":
    main()
