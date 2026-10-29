#!/usr/bin/env python3
"""G1 for HYP-PM-0024 ({PY} dividend-yield level): the one pre-registered test. Runs ONCE, after registration.

Implements HYP-PM-0024_REGISTERED.md §3-§4 on the panel g0_dy_breadth.py builds, with the frozen {FQ} G1 return,
Newey-West and E/P code imported (not re-derived). It refuses to run -- and prints nothing but the refusal --
unless the registration sha256, the imported code, the freeze inputs and the FM daily inputs all match their pins.

    cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
    venv/bin/python3 docs/research_programs/P-M/dy/g1_dy.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
P_M = HERE.parent
ROOT = HERE.parents[3]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g0dy = _load("g0_dy_breadth", HERE / "g0_dy_breadth.py")   # puts dy/ and fq/ on sys.path, imports ex + fq
ex, fq = g0dy.ex, g0dy.fq
g1fq = _load("g1_fq_ep", P_M / "fq" / "g1_fq_ep.py")

REG = HERE / "HYP-PM-0024_REGISTERED.md"
REG_SHA256: str | None = None

# ---- registered parameters (HYP-PM-0024_REGISTERED.md §3) ----
BAR = 3.300529                   # e_max_abs_z(615), deflation_audit/bar_v2.py
NW_LAGS = 6                      # the {FQ} G1's rule (g1_fq_ep.newey_west default)
COST_RT = 0.006                  # 0.60% round trip, D-082 basis
FIRST_TO = 1.0                   # first formation's turnover (initial build), as registered
FLOOR = 0.008                    # hypothesised effect, reported only
MIN_VALID = 30                   # valid-yield names to form
FM_MIN = 30                      # names per FM month
FM_T_MIN = 2.0
VOLEX_Q = 0.90
PARK_N, PARK_MAX_GAP = 60, 10
ERA_SPLIT = date(2021, 7, 1)
DAILY_SWITCH, DAILY_END = date(2021, 7, 5), date(2026, 9, 30)

PICKLE = P_M / "forward_volex" / "remeasure" / "work" / "hist_pre2021.pkl"
PICKLE_SHA256 = "ea827fa632d09c5b8ed85163c4e3a141ebfc853adca12678e6a549350bd221f8"
OHLCV_FP_SHA256 = "3978ec8f395b180c65f041cc1aa3e9a7ea934daeffdda5d0dd3cbea37817b941"
CODE_PINS = {
    HERE / "g0_dy_breadth.py": "497f32b9c28eea2bd288881114d00c1919d38709b05df5bf9b8b540d0e6f6899",
    HERE / "extract_dividends.py": "a73a2df2c60fc210b1a7c5436f9f43e9358438bb1fb55e3e907d91ae3026e366",
    P_M / "fq" / "g1_fq_ep.py": "f5d35449caaf6e584d11d258bce7014aefefd21ccda5c50e26f4a83a8f6a437b",
    P_M / "fq" / "g0_fq_ep_breadth.py": "d741e9b50a3d6547f683f0d94e6bd237734187c9ad370752f4e2c4392e7ef1b1",
}


# ---------------------------------------------------------------- pure pieces (synthetic-tested)

def book_weights(valid, mcap=None):
    """valid: [(ticker, yield)]. Top quintile = last floor(n/5) by (yield, ticker); EW, or mcap-weighted if mcap
    is given (sensitivity). None if fewer than MIN_VALID valid names."""
    if len(valid) < MIN_VALID:
        return None
    top = [t for _, t in sorted((y, t) for t, y in valid)[-(len(valid) // 5):]]
    if mcap is None:
        return {t: 1 / len(top) for t in top}
    tot = sum(mcap[t] for t in top)
    return {t: mcap[t] / tot for t in top}


def park60_index(bars):
    """bars: [(date, high, low)] -> (date ordinals, ln(h/l)^2) of the valid bars, date-sorted
    (bars with high <= 0, low <= 0, high < low or a missing value are skipped)."""
    ok = sorted((d.toordinal(), math.log(h / l) ** 2) for d, h, l in bars
                if h is not None and l is not None and h > 0 and l > 0 and h >= l)
    return np.array([d for d, _ in ok], dtype=np.int64), np.array([v for _, v in ok], dtype=float)


def park60_at(index, D):
    """Parkinson-60 at D from the last PARK_N valid bars dated <= D; None without 60 bars or if the newest is
    more than PARK_MAX_GAP calendar days before D."""
    dates, lr2 = index
    i = int(np.searchsorted(dates, D.toordinal(), side="right"))
    if i < PARK_N or D.toordinal() - int(dates[i - 1]) > PARK_MAX_GAP:
        return None
    return math.sqrt(float(lr2[i - PARK_N:i].sum()) / PARK_N / (4 * math.log(2)))


def pct_ranks(x):
    x = np.asarray(x, dtype=float)
    return rankdata(x, method="average") / len(x)


def fm_coef(rows, with_volex=True):
    """rows: [(ret, yield, ep, log_mcap, park, volex)]. OLS of ret on ranked yield/ep/size/park (+ VOLEX dummy).
    Returns the yield-rank coefficient, or None if too few names or the design is not identified: a constant
    column (e.g. no VOLEX name this month) is dropped first; a still rank-deficient design gives no coefficient
    (least squares would otherwise split a collinear yield/E-P effect between them and fake an increment)."""
    if len(rows) < FM_MIN:
        return None
    a = np.asarray(rows, dtype=float)
    cols = [np.ones(len(a)), pct_ranks(a[:, 1]), pct_ranks(a[:, 2]), pct_ranks(a[:, 3]), pct_ranks(a[:, 4])]
    if with_volex:
        cols.append(a[:, 5])
    X = np.column_stack([cols[0]] + [c for c in cols[1:] if np.ptp(c) > 0])
    if np.ptp(cols[1]) == 0 or np.linalg.matrix_rank(X) < X.shape[1]:
        return None
    beta = np.linalg.lstsq(X, a[:, 0], rcond=None)[0]
    return float(beta[1])


def evaluate(net, fm):
    """Primary verdict from the per-month net spreads and FM yield coefficients (both in date order)."""
    out = {"n_months": len(net)}
    if len(net) < 3:
        return {**out, "passed": False, "reason": "too few months"}
    m, se, t = g1fq.newey_west(net, NW_LAGS)
    h = len(net) // 2
    h1, h2 = float(np.mean(net[:h])), float(np.mean(net[h:]))
    fm_ok = [c for c in fm if c is not None]
    fm_m, fm_se, fm_t = g1fq.newey_west(fm_ok, NW_LAGS) if len(fm_ok) >= 3 else (None, None, None)
    passed = bool(t >= BAR and h1 > 0 and h2 > 0 and fm_t is not None and fm_t >= FM_T_MIN)
    reasons = [r for r, bad in (("t < bar", not t >= BAR), ("half <= 0", not (h1 > 0 and h2 > 0)),
                                ("FM t < 2", fm_t is None or not fm_t >= FM_T_MIN)) if bad]
    return {**out, "mean_net_monthly": m, "nw_se": se, "t": t, "bar": BAR, "half1_mean": h1, "half2_mean": h2,
            "fm_months": len(fm_ok), "fm_mean_coef": fm_m, "fm_t": fm_t, "floor_met": bool(m >= FLOOR),
            "passed": passed, "kill_reasons": reasons}


def run(panel, ksei, series, ep_of, park_of, delist_minus100=False, vw=False, cost=COST_RT):
    """One pass of the registered test. panel: D -> {t: (sec, px)}; ksei: D -> {t: (sec, px)} (all months);
    series: t -> dividend TTM series; ep_of(t, D, mcap) -> E/P or None; park_of(t, D) -> Parkinson-60 or None.
    Returns per-month records (date order) with the net spread and both FM coefficients."""
    months = sorted(ksei)
    nxt = {d: n for d, n in zip(months, months[1:])}
    recs, prev = [], None
    for D in sorted(panel):
        if D not in nxt:
            continue
        uni = panel[D]
        mcap = {t: s * p for t, (s, p) in uni.items()}
        yld = {}
        for t in uni:
            ttm = ex.ttm_at(series.get(t, []), D)
            if ttm is not None:
                yld[t] = ttm / mcap[t]
        bw = book_weights(list(yld.items()), mcap if vw else None)
        if bw is None:
            continue
        uw = {t: 1 / len(uni) for t in uni}
        rd, rn = ksei[D], ksei[nxt[D]]
        splits: list = []
        rb, db = g1fq.leg_return(bw, rd, rn, delist_minus100, splits)
        ru, du = g1fq.leg_return(uw, rd, rn, delist_minus100, splits)
        if rb is None or ru is None:
            continue
        to = FIRST_TO if prev is None else g1fq.turnover(prev, bw)
        prev = bw
        parks = {t: park_of(t, D) for t in uni}
        pv = [v for v in parks.values() if v is not None]
        q90 = float(np.quantile(pv, VOLEX_Q)) if pv else None
        rows = []
        for t, y in yld.items():
            ep, pk = ep_of(t, D, mcap[t]), parks[t]
            if ep is None or pk is None:
                continue
            s0, p0 = rd[t]
            if t in rn:
                s1, p1 = rn[t]
                r = g1fq.split_adjusted_return(p0, s0, p1, s1)
            else:
                r = -1.0 if delist_minus100 else 0.0
            if r is None or r < g1fq.MECH_DROP:
                continue
            rows.append((r, y, ep, math.log(mcap[t]), pk, 1.0 if pk > q90 else 0.0))
        uy = sum(yld.values()) / len(uni)                      # universe non-payers at yield 0
        recs.append({"D": D.isoformat(), "n_uni": len(uni), "n_valid": len(yld), "n_book": len(bw),
                     "spread": rb - ru, "turnover": to, "net": rb - ru - cost * to,
                     "fm": fm_coef(rows), "fm_novolex": fm_coef(rows, with_volex=False), "fm_n": len(rows),
                     "carry_gap_monthly": (sum(yld[t] for t in bw) / len(bw) - uy) / 12,
                     "dropped_mech": db + du, "split_adjusted": sorted(set(splits))})
    return recs


def summarise(recs, keep=lambda D: True, fm_keep=lambda D: True, fm_key="fm"):
    sel = [r for r in recs if keep(date.fromisoformat(r["D"]))]
    fm = [r[fm_key] for r in sel if fm_keep(date.fromisoformat(r["D"]))]
    return evaluate([r["net"] for r in sel], fm)


# ---------------------------------------------------------------- pins and real inputs

def _sha(path):
    return g0dy.sha256_file(path)


def verify(con) -> list[str]:
    bad = [f"{p.name}: code sha256 mismatch" for p, want in CODE_PINS.items() if not p.exists() or _sha(p) != want]
    bad += g0dy.verify_inputs()
    if not PICKLE.exists() or _sha(PICKLE) != PICKLE_SHA256:
        bad.append("hist_pre2021.pkl: sha256 mismatch")
    h = hashlib.sha256()
    for t, d, hi, lo in _ohlcv_rows(con):
        h.update(f"{t},{d},{hi!r},{lo!r}\n".encode())
    if h.hexdigest() != OHLCV_FP_SHA256:
        bad.append("production ohlcv: fingerprint mismatch")
    return bad


def _ohlcv_rows(con):
    return con.execute("SELECT ticker, date, high, low FROM ohlcv WHERE is_final = 1 AND date >= ? AND date <= ? "
                       "ORDER BY ticker, date", (DAILY_SWITCH.isoformat(), DAILY_END.isoformat()))


def load_daily(con):
    """Ticker -> (date ordinals, ln(h/l)^2), built vectorised (2.5M bars; the XPS is the production box).
    Same validity rule as park60_index."""
    import pandas as pd

    h = pd.read_pickle(PICKLE)[["ticker", "date", "high", "low"]]
    h = h[h["date"] < pd.Timestamp(DAILY_SWITCH)].copy()
    h["date"] = h["date"].map(lambda x: x.toordinal())
    o = pd.DataFrame(list(_ohlcv_rows(con)), columns=["ticker", "date", "high", "low"])
    o["date"] = o["date"].map(lambda x: date.fromisoformat(x).toordinal())
    d = pd.concat([h, o], ignore_index=True)
    d = d[(d["high"] > 0) & (d["low"] > 0) & (d["high"] >= d["low"])]
    d = d.assign(lr2=np.log(d["high"] / d["low"]) ** 2).sort_values(["ticker", "date"])
    return {t: (g["date"].to_numpy(np.int64), g["lr2"].to_numpy(float)) for t, g in d.groupby("ticker", sort=False)}


def main(argv=None) -> int:
    if REG_SHA256 is None or not REG.exists() or hashlib.sha256(REG.read_bytes()).hexdigest() != REG_SHA256:
        print("Registration not pinned or changed; refusing to run (no return is computed before registration).")
        return 2
    sys.path.insert(0, str(ROOT))
    from data.db import connect

    con = connect(read_only=True)
    try:
        problems = verify(con)
        if problems:
            print("Pinned inputs do not match; refusing to run:\n  " + "\n  ".join(problems))
            return 3
        daily = load_daily(con)
    finally:
        con.close()

    panel = g0dy.monthly_panel()
    ksei = fq.load_ksei()
    withheld, fyx = fq.load_withheld(), fq.load_fyx()
    fcon = connect(path=str(fq.FIN_DB), read_only=True)
    try:
        payouts = ex.sum_paid_rows(fcon, ex.row_labels(fcon))
    finally:
        fcon.close()
    series = ex.build_ttm(ex.dividends_with_meta(payouts, withheld, fyx))

    G0 = g1fq.G0
    fin = G0.load_fin(withheld=G0.load_withheld(), fyx=G0.load_fyx(), yahoo=G0.load_yahoo())
    kdate = {(d.year, d.month): d for d in sorted(G0.load_ksei())}
    for qs in fin.values():                       # deadlines qualified exactly as g1_fq_ep.run_variant does
        for q in qs.values():
            q["qual"] = G0.first_qualifying(q["deadline"], kdate) if q["deadline"] else None

    def ep_of(t, D, mcap):
        qs = fin.get(t)
        return g1fq.signal("ep", D, qs, mcap) if qs else None

    def park_of(t, D):
        return park60_at(daily[t], D) if t in daily else None

    recs = run(panel, ksei, series, ep_of, park_of)
    primary = summarise(recs)
    post = lambda D: D >= ERA_SPLIT
    sens = {
        "gross": evaluate([r["spread"] for r in recs], [r["fm"] for r in recs]),
        "delist_minus100": summarise(run(panel, ksei, series, ep_of, park_of, delist_minus100=True)),
        "pre_2021_07": summarise(recs, keep=lambda D: D < ERA_SPLIT),
        "post_2021_07": summarise(recs, keep=post),
        "fm_2021_07_on": summarise(recs, fm_keep=post),
        "fm_without_volex": summarise(recs, fm_key="fm_novolex"),
        "vw_top_quintile": summarise(run(panel, ksei, series, ep_of, park_of, vw=True)),
    }
    report = {"carry_gap_mean_monthly": float(np.mean([r["carry_gap_monthly"] for r in recs])) if recs else None,
              "fm_months_used": primary.get("fm_months"), "median_n_valid": float(np.median([r["n_valid"] for r in recs])),
              "median_n_book": float(np.median([r["n_book"] for r in recs])),
              "mech_drops": sum(len(r["dropped_mech"]) for r in recs)}
    res = {"hypothesis": "HYP-PM-0024", "registration_sha256": REG_SHA256, "bar": BAR, "census": 615,
           "primary": primary, "passed": primary["passed"],
           "sensitivities": {k: {kk: v.get(kk) for kk in ("n_months", "mean_net_monthly", "t", "half1_mean",
                                                           "half2_mean", "fm_t", "fm_months")} for k, v in sens.items()},
           "report": report, "months": recs}
    stamp = datetime.now(timezone(timedelta(hours=7))).strftime("%Y%m%dT%H%M%S")
    out = HERE / f"G1_RESULT_{stamp}.json"
    out.write_text(json.dumps(res, indent=1, default=str))
    line = (f"G1 HYP-PM-0024: {primary['n_months']} months, mean net {primary.get('mean_net_monthly', float('nan')):.4%}/mo, "
            f"NW t {primary.get('t', float('nan')):.3f} vs bar {BAR}; halves {primary.get('half1_mean', float('nan')):.4%} / "
            f"{primary.get('half2_mean', float('nan')):.4%}; FM t {primary.get('fm_t')} ({primary.get('fm_months')} months) -> "
            f"{'PASS' if primary['passed'] else 'FAIL ' + ', '.join(primary.get('kill_reasons', []))}; {out.name}")
    (HERE / f"g1_run_{stamp}.log").write_text(line + "\n")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
