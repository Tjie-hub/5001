"""Overlap-robust OBSERVABILITY report for FWD-PM-REGIME-002 and FWD-PM-FADE-001 (D-057).

Decides nothing. Each test's frozen PROTOCOL.md section 3 rule stays its only decision. This
script reads the two frozen ledgers (it never writes them) and prints, next to each frozen
statistic, the same mean under three standard errors that allow for overlapping holding windows.
For FADE it also prints the cost-free (gross) contrast.

Why (docs/research_programs/AUDIT_2026-09-24_RESULT_VALIDITY.md, rules R-1/R-2):

  - Both frozen rules use a t clustered on the entry (signal) date. Holds of 20 (FADE) and up to
    60 (T1) sessions overlap, so that t is too large. On a simulated null it rejected 39% at a
    nominal 5%; in-sample it shrank x0.44-0.94 under the estimators below.
  - FADE's endpoint subtracts the 0.60% round trip from the signal leg only, against gross
    benchmarks. A signal with no information therefore scores -0.60%.
  - Calibration read from the in-sample dependence:
      REGIME-002: P(PASS | zero effect) ~ 13-17% (nominal 5%).
      FADE-001:   P(PROMOTE | no information) ~ 3-14% (nominal ~0.1%).

Columns (the same trade-weighted mean in the first four):

  frozen    one-way cluster on entry date (REGIME) / signal date (FADE); the protocol's own t
  month     one-way cluster on the calendar month of entry
  dk_L      Driscoll-Kraay form: residual sums per session, Bartlett to lag L = maximum hold
            (60 for REGIME, 20 for FADE)
  calendar  calendar-time portfolio (Fama 1998; Mitchell & Stafford 2000): each session, the
            equal-weight excess return of every open position, gross; NW(5) t on the daily
            series. Different weighting (per day, not per trade). Needs the DB.

Pre-declared reading (D-057, both deviation logs): a frozen PASS or PROMOTE is reported with these
columns beside it. If calendar-time t does not clear the frozen threshold, the read is recorded as
"<verdict> under the frozen rule; not confirmed under overlap-robust inference". Nothing about
the verdict or the test changes automatically.

    venv/bin/python docs/research_programs/P-M/forward_robust/robust_report.py
    venv/bin/python docs/research_programs/P-M/forward_robust/robust_report.py --no-calendar
"""
import argparse
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PM = os.path.dirname(HERE)
REGIME_LEDGER = os.path.join(PM, "forward_regime", "ledger.json")
FADE_LEDGER = os.path.join(PM, "forward_fade", "ledger.json")
REGIME_L, FADE_H = 60, 20
MIN_N, MIN_CLUSTERS = 30, 10
FROZEN = {
    "REGIME-002": "36 months: PASS iff mean excess >= +0.46%/trade AND one-sided frozen t > 1.65",
    "FADE-001": "12 months: PROMOTE-track iff frozen net t < -2.5 on IHSG AND EW-book; "
                "18 months: PROMOTE iff frozen net t < -3.0 on both",
}


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(PM, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def OA():
    return _load("overlap_audit", os.path.join("overlap_audit", "overlap_audit.py"))


# ------------------------------------------------------------------ ledgers -> frames
def regime_frame(led: dict) -> pd.DataFrame:
    T = pd.DataFrame(led.get("trades", []))
    if T.empty:
        return T
    for c in ("entry_date", "exit_date"):
        T[c] = pd.to_datetime(T[c])
    return T


def fade_frame(led: dict, h: int = FADE_H) -> pd.DataFrame:
    """One row per uncensored signal with a closed h-leg. Censored rows are excluded, exactly as
    the frozen endpoint excludes them."""
    rows = []
    for s in led.get("trades", []):
        if s.get("censored"):
            continue
        leg = (s.get("horizons") or {}).get(str(h))
        if not leg:
            continue
        rows.append({"ticker": s["ticker"], "signal_date": s["signal_date"],
                     "entry_date": s["entry_date"], "exit_date": leg["exit_date"],
                     "gross": leg["gross_return"], "net": leg["net_return"],
                     "ihsg": leg["ihsg_return"], "ewbook": leg["ewbook_return"],
                     "excess_ihsg": leg["excess_ihsg"], "excess_ewbook": leg["excess_ewbook"]})
    F = pd.DataFrame(rows)
    if not F.empty:
        for c in ("signal_date", "entry_date", "exit_date"):
            F[c] = pd.to_datetime(F[c])
    return F


# ------------------------------------------------------------------ estimators
def estimators(x, cluster_dates, cal, L, oa=None):
    """Frozen entry-date t, month t and DK(L) t for the same trade-weighted mean."""
    oa = oa or OA()
    x = np.asarray(x, float)
    d = pd.DatetimeIndex(cluster_dates)
    out = {"N": int(len(x)), "clusters": int(d.nunique()),
           "mean_pct": float(100 * x.mean()) if len(x) else float("nan")}
    if len(x) < MIN_N or d.nunique() < MIN_CLUSTERS:
        out["note"] = f"too few (N < {MIN_N} or clusters < {MIN_CLUSTERS}); t not reported"
        return out
    out["t_frozen"] = float(oa.cluster_t(x, d.values)[1])
    out["t_month"] = float(oa.cluster_t(x, np.asarray(d.to_period("M").astype(str)))[1])
    cal = pd.DatetimeIndex(cal)
    on = cal.get_indexer(d) >= 0
    if not on.all():
        out["dk_note"] = f"{int((~on).sum())} dates off the session calendar were left out of DK"
    out[f"t_dk_L{L}"] = float(oa.dk_t(x[on], d.values[on], cal, L)[1])
    return out


def calendar_t(positions, n_days, oa=None):
    oa = oa or OA()
    if not positions:
        return None
    m, t, nd = oa.calendar_time(None, positions, n_days)
    return {"daily_mean_pct": 100 * m, "t_calendar": t, "days": nd}


# ------------------------------------------------------------------ calendar-time positions
def regime_positions(T, M):
    """Close entry: returns over (entry, exit], stock close-to-close minus IHSG close-to-close."""
    pos = []
    for r in T.itertuples():
        i, j = M["cpos"].get(r.entry_date), M["cpos"].get(r.exit_date)
        c = M["tcol"].get(r.ticker)
        if i is None or j is None or c is None or j <= i:
            continue
        pos.append((i + 1, M["CC"][i + 1:j + 1, c], M["ih_cc"][i + 1:j + 1]))
    return pos


def fade_positions(F, M, bench, h=FADE_H):
    """Next-open entry: entry day open->close, then close->close through the h-th session."""
    bco, bcc = (M["ih_co"], M["ih_cc"]) if bench == "IHSG" else (M["ew_co"], M["ew_cc"])
    pos = []
    for r in F.itertuples():
        e, c = M["cpos"].get(r.entry_date), M["tcol"].get(r.ticker)
        if e is None or c is None:
            continue
        pos.append((e, np.r_[M["CO"][e, c], M["CC"][e + 1:e + h, c]],
                    np.r_[bco[e], bcc[e + 1:e + h]]))
    return pos


# ------------------------------------------------------------------ reports
def report_regime(led, cal, M=None, oa=None):
    oa = oa or OA()
    T = regime_frame(led)
    out = {"test": "FWD-PM-REGIME-002", "frozen_rule": FROZEN["REGIME-002"], "trades": int(len(T))}
    if T.empty:
        return out
    out["excess (net, vs IHSG) - frozen endpoint"] = estimators(T["excess"], T["entry_date"], cal, REGIME_L, oa)
    if M is not None:
        out["excess (net, vs IHSG) - frozen endpoint"]["calendar_gross"] = calendar_t(regime_positions(T, M), len(M["cal"]), oa)
    return out


def report_fade(led, cal, M=None, oa=None):
    oa = oa or OA()
    F = fade_frame(led)
    out = {"test": "FWD-PM-FADE-001", "frozen_rule": FROZEN["FADE-001"], "signals_h20": int(len(F))}
    if F.empty:
        return out
    for bench, col in (("IHSG", "ihsg"), ("EW-book", "ewbook")):
        net = F[f"excess_{col}"]
        gross = F["gross"] - F[col]
        out[f"{bench} net (frozen endpoint)"] = estimators(net, F["signal_date"], cal, FADE_H, oa)
        out[f"{bench} GROSS (no-information null = 0)"] = estimators(gross, F["signal_date"], cal, FADE_H, oa)
        if M is not None:
            out[f"{bench} GROSS (no-information null = 0)"]["calendar_gross"] = calendar_t(
                fade_positions(F, M, bench), len(M["cal"]), oa)
    return out


def _print(rep):
    print(f"\n== {rep['test']} ==  frozen rule: {rep['frozen_rule']}")
    n = rep.get("trades", rep.get("signals_h20", 0))
    if not n:
        print("   0 closed rows in the ledger: nothing to report yet.")
        return
    for k, v in rep.items():
        if not isinstance(v, dict):
            continue
        line = f"   {k:42s} N={v['N']:5d} G={v['clusters']:4d} mean {v['mean_pct']:+.3f}%"
        if "note" in v:
            print(line + "  " + v["note"])
            continue
        dk = [kk for kk in v if kk.startswith("t_dk")][0]
        line += f"  t_frozen {v['t_frozen']:+.2f}  t_month {v['t_month']:+.2f}  {dk} {v[dk]:+.2f}"
        cg = v.get("calendar_gross")
        if cg:
            line += f"  t_calendar(gross) {cg['t_calendar']:+.2f}"
        print(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-calendar", action="store_true", help="skip the calendar-time column")
    ap.add_argument("--cutoff", default="2100-01-01")
    a = ap.parse_args()
    oa = OA()
    regime, fade = json.load(open(REGIME_LEDGER)), json.load(open(FADE_LEDGER))
    va = _load("validity_audit", os.path.join("validity_audit", "validity_audit.py"))
    D, x = va.load_all(a.cutoff)                          # read-only: data.db.connect(read_only=True)
    # session calendar from stock rows, not IHSG (IHSG is missing on a few sessions, e.g. 2026-08-25)
    cal = pd.DatetimeIndex(np.sort(D.loc[D.ticker != "IHSG", "date"].unique()))
    M = None
    if not a.no_calendar and (regime.get("trades") or fade.get("trades")):
        M = va.fade_panel(D, x, oa)
    print("OBSERVABILITY ONLY (D-057). The frozen section 3 rule is the only decision.")
    _print(report_regime(regime, cal, M, oa))
    _print(report_fade(fade, cal, M, oa))


if __name__ == "__main__":
    main()
