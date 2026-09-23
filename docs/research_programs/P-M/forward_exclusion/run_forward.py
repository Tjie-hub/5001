#!/usr/bin/env python3
"""FWD-PM-VOLEX-001 — monthly forward test of the volatility-exclusion rule.

RESEARCH ONLY. Reads production `ohlcv` read-only. Writes nothing but this directory's
append-only ledger. Never imported by production code (research/production boundary).

FROZEN SPEC (see PROTOCOL.md; do not edit without a dated superseding protocol entry):
  universe      liquid set = trailing-60 median traded value >= Rp 1e9 (shift 1), close >= Rp 50,
                traded on the formation day, not within +/-20 sessions of a suspension window;
                then the TOP 200 by that trailing-60 median traded value.
  signal        Parkinson-60 range volatility:  sqrt( mean_60( ln(high/low)^2 ) / (4 ln 2) )
  rule          EXCLUDE the highest-decile (top 10%) by that signal. Hold the rest, equal weight.
  entry         close(t+1) after the formation date t.       horizon 21 sessions.
  benchmark     equal weight of the SAME universe (the 200), same entry and horizon.
  endpoint      incremental = mean(held) - mean(universe), both gross; costs reported separately
                (turnover is ~10.6%/mo on both books and near-cancels).
  cadence       one formation per calendar month, on the last COMPLETE session available.
  session guard a session is COMPLETE only if its priced-ticker count is >= 95% of the trailing
                20-session median. This rejects partial sessions such as 2026-09-15 (824 rows vs
                ~915 normal: the morning fetch wrote is_final=1 rows before the WIB open) and
                2026-09-07 (137 rows). A formation is never taken on an incomplete session.

Usage:
  python run_forward.py                # generate this month's list, score matured entries
  python run_forward.py --as-of DATE   # regenerate for a specific session (idempotent)
  python run_forward.py --json         # dump the full ledger as JSON for publication
"""
from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, sys
from datetime import datetime, timezone
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
DB = os.path.join(ROOT, "data", "walkforward.db")
LEDGER = os.path.join(HERE, "ledger.json")

UNIVERSE_N, EXCLUDE_FRAC, HORIZON = 200, 0.10, 21
SESSION_COMPLETE_FRAC = 0.95
LIQ_FLOOR, MIN_PRICE, SUSP_PAD, PARK_WIN = 1e9, 50.0, 20, 60
SPEC_ID = "FWD-PM-VOLEX-001"


def _ro(path):
    c = sqlite3.connect("file:" + path + "?mode=ro", uri=True)
    c.execute("PRAGMA query_only = ON;")
    return c


def load_panel(upto: str | None = None):
    """Adjusted panels. Split basis detected per dataset_b/foundation.py convention."""
    con = _ro(DB)
    try:
        q = ("SELECT ticker,date,high,low,close,volume FROM ohlcv "
             "WHERE is_final=1 AND close>0 AND date>='2021-07-01'")
        if upto:
            q += f" AND date<='{upto}'"
        df = pd.read_sql_query(q + " ORDER BY ticker,date", con)
        ca = pd.read_sql_query("SELECT ticker,date,action,value FROM corporate_actions", con)
        susp = pd.read_sql_query(
            "SELECT ticker,last_normal_date,resume_date FROM suspension_events", con)
    finally:
        con.close()

    # split adjustment: if the raw close-to-close move across the ex-date matches 1/factor-1
    # within 25%, the store is UNADJUSTED for that event -> divide pre-ex prices by the factor.
    sp = ca[ca.action == "split"]
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    fix = np.ones(len(df))
    if len(sp):
        by = {t: g[["date", "close"]].reset_index(drop=True) for t, g in df.groupby("ticker")}
        dts, tks = df["date"].values, df["ticker"].values
        for _, row in sp.iterrows():
            t, ex, fac = row["ticker"], row["date"], row["value"]
            g = by.get(t)
            if g is None or not fac or not (0.01 < fac < 1000):
                continue
            prior, cur = g[g.date < ex], g.loc[g.date == ex, "close"]
            if prior.empty or cur.empty:
                continue
            if abs(float(cur.iloc[0]) / float(prior["close"].iloc[-1]) - 1 - (1/fac - 1)) < 0.25:
                idx = np.where(tks == t)[0]
                fix[idx[dts[idx] < ex]] *= 1.0 / fac
    for col in ("high", "low", "close"):
        df[col] = df[col] * fix
    df["traded_value"] = df["close"] * df["volume"]

    P = lambda col: df.pivot_table(index="date", columns="ticker", values=col, aggfunc="last").sort_index()
    cl, hi, lo, vol, tv = P("close"), P("high"), P("low"), P("volume"), P("traded_value")
    tvm = tv.rolling(60, min_periods=20).median().shift(1)
    didx = {d: i for i, d in enumerate(cl.index)}
    cont = pd.DataFrame(False, index=cl.index, columns=cl.columns)
    for _, r in susp.iterrows():
        tk = r["ticker"]
        if tk not in cont.columns:
            continue
        i0 = didx.get(r["last_normal_date"])
        if i0 is None:
            continue
        i1 = didx.get(r["resume_date"], i0)
        cont.iloc[max(0, i0 - SUSP_PAD): min(len(cl.index) - 1, i1 + SUSP_PAD) + 1,
                  cont.columns.get_loc(tk)] = True
    park = np.sqrt((np.log(hi / lo.replace(0, np.nan)) ** 2)
                   .rolling(PARK_WIN, min_periods=PARK_WIN // 2).mean() / (4 * np.log(2)))
    eligible = ((tvm >= LIQ_FLOOR) & (cl >= MIN_PRICE) & (vol > 0) & ~cont).fillna(False)
    # session completeness: a partial fetch must never become a formation date
    cnt = cl.notna().sum(axis=1)
    complete = cnt >= SESSION_COMPLETE_FRAC * cnt.rolling(20, min_periods=5).median()
    return dict(close=cl, vol=vol, tvm=tvm, park=park, eligible=eligible,
                dates=list(cl.index), counts=cnt, complete=complete)


def last_complete_session(panel, upto: str | None = None) -> str:
    comp, cnt = panel["complete"], panel["counts"]
    idx = [d for d in panel["dates"] if (upto is None or d <= upto)]
    for d in reversed(idx):
        if bool(comp.get(d, False)):
            return d
    raise SystemExit("no complete session found")


def generate(panel, as_of: str) -> dict:
    cl, tvm, park, elig = panel["close"], panel["tvm"], panel["park"], panel["eligible"]
    if as_of not in cl.index:
        raise SystemExit(f"{as_of} is not a session in the panel")
    if not bool(panel["complete"].get(as_of, False)):
        raise SystemExit(f"{as_of} is an INCOMPLETE session "
                         f"({int(panel['counts'][as_of])} priced tickers) — refusing to form on it")
    adv = tvm.loc[as_of].where(elig.loc[as_of]).dropna()
    if len(adv) < UNIVERSE_N:
        raise SystemExit(f"only {len(adv)} eligible names on {as_of}")
    uni = adv.nlargest(UNIVERSE_N).index
    sig = park.loc[as_of].reindex(uni).dropna()
    k = max(1, int(round(len(sig) * EXCLUDE_FRAC)))
    drop = sig.nlargest(k)
    held = [t for t in sig.index if t not in set(drop.index)]
    ann = lambda s: float(s) * np.sqrt(252) * 100
    rec = {
        "spec_id": SPEC_ID, "formation_date": as_of,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "universe_n": int(len(sig)), "excluded_n": int(k), "held_n": int(len(held)),
        "adv_floor_rp_b": round(float(adv.nlargest(UNIVERSE_N).min()) / 1e9, 3),
        "cut_point_ann_vol_pct": round(ann(drop.min()), 2),
        "excluded": [{"ticker": t, "park_vol_ann_pct": round(ann(drop[t]), 1),
                      "adv60_rp_b": round(float(tvm.loc[as_of, t]) / 1e9, 2),
                      "close_rp": int(round(float(cl.loc[as_of, t])))}
                     for t in drop.sort_values(ascending=False).index],
        "held": sorted(held),
        "median_ann_vol_excluded_pct": round(ann(drop.median()), 1),
        "median_ann_vol_held_pct": round(ann(park.loc[as_of].reindex(held).dropna().median()), 1),
        "session_priced_tickers": int(panel["counts"][as_of]),
        "outcome": None,
    }
    rec["fingerprint"] = hashlib.sha256(
        json.dumps({k2: rec[k2] for k2 in ("spec_id", "formation_date", "excluded", "held")},
                   sort_keys=True).encode()).hexdigest()[:16]
    return rec


STUCK_AFTER = 10   # DEV-002: complete sessions past an incomplete d0/d1 before flagging for the Owner


def score(panel, rec: dict) -> dict | None:
    """Realised incremental return, entry close(t+1), horizon 21 sessions. None until matured.

    DEV-002 (2026-09-23): an outcome is scored only when BOTH the entry session d0 and the exit
    session d1 pass the same completeness guard that protects formation dates. Before this, an
    exit on a partial fetch (e.g. a session stranded at is_final=0) had every missing name
    silently dropped by basket()'s dropna(), and the degraded outcome was frozen into the ledger,
    never re-scored. d0/d1 are still counted on the raw session list, so the horizon definition
    is unchanged; the scorer simply waits for the data to finalise.
    """
    cl, dates, comp = panel["close"], panel["dates"], panel["complete"]
    i = dates.index(rec["formation_date"])
    if i + 1 + HORIZON >= len(dates):
        return None
    d0, d1 = dates[i + 1], dates[i + 1 + HORIZON]
    bad = [d for d in (d0, d1) if not bool(comp.get(d, False))]
    if bad:
        later = sum(1 for d in dates[i + 2 + HORIZON:] if bool(comp.get(d, False)))
        tag = "[stuck]" if later >= STUCK_AFTER else "[wait]"
        print(f"{tag} {rec['formation_date']}: session(s) {', '.join(bad)} incomplete "
              f"({', '.join(str(int(panel['counts'][d])) for d in bad)} priced tickers) -- not scored"
              + ("; Owner decision required (DEV-002)" if tag == "[stuck]"
                 else "; run scripts/repair_provisional_bars.py --apply if stranded"))
        return None
    def basket(names):
        a, b = cl.loc[d0, names], cl.loc[d1, names]
        r = (b / a - 1).replace([np.inf, -np.inf], np.nan).dropna()
        return (float(r.mean()), int(len(r))) if len(r) else (np.nan, 0)
    held_r, nh = basket([t for t in rec["held"] if t in cl.columns])
    uni = [t for t in rec["held"] + [e["ticker"] for e in rec["excluded"]] if t in cl.columns]
    uni_r, nu = basket(uni)
    exc_r, ne = basket([e["ticker"] for e in rec["excluded"] if e["ticker"] in cl.columns])
    return {"entry_date": d0, "exit_date": d1, "n_held": nh, "n_universe": nu, "n_excluded": ne,
            "held_ret_pct": round(100 * held_r, 3), "universe_ret_pct": round(100 * uni_r, 3),
            "excluded_ret_pct": round(100 * exc_r, 3),
            "incremental_pct": round(100 * (held_r - uni_r), 4),
            "spread_held_minus_excluded_pct": round(100 * (held_r - exc_r), 3)}


def load_ledger():
    return json.load(open(LEDGER)) if os.path.exists(LEDGER) else {"spec_id": SPEC_ID, "entries": []}


def save_ledger(L):
    json.dump(L, open(LEDGER, "w"), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    L = load_ledger()
    if a.json:
        print(json.dumps(L, indent=1)); return
    panel = load_panel()
    as_of = a.as_of or last_complete_session(panel)
    latest = panel["dates"][-1]
    if as_of != latest:
        print(f"[guard] latest session {latest} "
              f"({int(panel['counts'][latest])} priced tickers) is incomplete; "
              f"forming on {as_of} ({int(panel['counts'][as_of])} tickers)")

    by_month = {e["formation_date"][:7]: e for e in L["entries"]}
    m = as_of[:7]
    if m in by_month and by_month[m]["formation_date"] != as_of:
        print(f"[skip] {m} already has a formation on {by_month[m]['formation_date']}")
    elif m not in by_month:
        rec = generate(panel, as_of)
        L["entries"].append(rec)
        L["entries"].sort(key=lambda e: e["formation_date"])
        print(f"[new]  {rec['formation_date']}  universe {rec['universe_n']}  "
              f"exclude {rec['excluded_n']}  hold {rec['held_n']}  fp {rec['fingerprint']}")
        print("       excluded: " + ", ".join(e["ticker"] for e in rec["excluded"]))
    else:
        print(f"[have] {m} formation {by_month[m]['formation_date']} already recorded")

    matured = 0
    for e in L["entries"]:
        if e.get("outcome") is None:
            s = score(panel, e)
            if s:
                e["outcome"] = s; matured += 1
    save_ledger(L)

    done = [e for e in L["entries"] if e.get("outcome")]
    print(f"\n{SPEC_ID}: {len(L['entries'])} formations, {len(done)} matured "
          f"({matured} newly scored), {len(L['entries'])-len(done)} pending")
    if done:
        v = np.array([e["outcome"]["incremental_pct"] for e in done])
        print(f"  incremental: mean {v.mean():+.3f}%/mo  median {np.median(v):+.3f}%  "
              f"P(>0) {100*(v>0).mean():.0f}%  n={len(v)}")
        if len(v) > 2:
            print(f"  t = {v.mean()/(v.std(ddof=1)/np.sqrt(len(v))):+.2f}")
        print(f"  {'formation':12s} {'entry':12s} {'held':>8s} {'univ':>8s} {'excl':>8s} {'INC':>8s}")
        for e in done[-14:]:
            o = e["outcome"]
            print(f"  {e['formation_date']:12s} {o['entry_date']:12s} {o['held_ret_pct']:+7.2f}% "
                  f"{o['universe_ret_pct']:+7.2f}% {o['excluded_ret_pct']:+7.2f}% {o['incremental_pct']:+7.3f}%")


if __name__ == "__main__":
    main()
