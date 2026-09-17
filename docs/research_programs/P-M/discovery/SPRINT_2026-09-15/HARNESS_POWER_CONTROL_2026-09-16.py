#!/usr/bin/env python3
"""DISCOVERY HARNESS POWER CONTROL — false-negative measurement (2026-09-16).

Injects synthetic known effects (+30/50/80/150 bp) into the REAL historical
forward-return panel (hold5, split/dividend-adjusted, production ohlcv) and runs
the UNMODIFIED discovery entry kill rule (the family-program standard):

  G1  net h5 >= +30bp after 60bp RT floor
  G2  pooled per-half h5 mean > 0 in >= 3 of 4 half-years
  G3  FM beta > 0 and |t| >= 2 (controls: ret1, ret5z, volz, ADV tercile, flow z)
  G4  n >= 1000 events AND >= 50 tickers
  G5  pseudo-OOS positive in BOTH 2021-22 and 2023-24 eras

Injection: treated cell forward return y -> y + delta. Treated subsets are
uniform random draws of exact size m from the eligible pool, seeds 0..19,
m in {600, 2500, 10000} (real event frequencies from the discovery record:
veto-cell ~898/1.59y, mid-frequency cells ~6.9k, high-frequency ~17k windows).
Real fat tails, cross-sectional correlation, calendar, exclusions and missingness
are untouched: only treated forward returns are shifted, and the OOS panel
receives the same delta on its own drawn subsets (the effect is a property of
the signal, so it exists in both eras).

No registry change, no production writes, no candidate tuning. Output to stdout
(captured by shell redirection).
"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

SEEDS = list(range(20))
FREQS = (600, 2500, 10000)
DELTAS = (0.003, 0.005, 0.008, 0.015)
HK = (1, 2, 3, 5, 10, 20)


def build_oos():
    c = sl.ro_conn(sl.WF)
    try:
        ohl = pd.read_sql_query("SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
                                "WHERE is_final=1 AND close>0 ORDER BY ticker, date", c)
    finally:
        c.close()
    ohl["traded_value"] = ohl["close"] * ohl["volume"]
    adj = sl.build_adjusted(ohl, sl.load_corporate_actions())
    F = {k: sl.to_panel(adj, k) for k in ("ret", "volume", "traded_value")}
    # ALIGN ALL PANELS TO ONE COMMON INDEX AND COLUMN SET: pivot_table drops
    # all-NaN rows AND columns per field independently, so panels can have
    # different shapes; misalignment would silently shift positions.
    common_idx = F["ret"].index
    common_cols = F["ret"].columns
    for k in F:
        F[k] = F[k].reindex(index=common_idx, columns=common_cols)
    liq = sl.trailing_median_panel(F["traded_value"]) >= sl.LIQ_FLOOR
    trad = liq & (F["volume"].shift(-1) > 0)
    cum = (F["ret"] + 1.0).cumprod()
    F["h5"] = cum.shift(-6) / cum.shift(-1) - 1.0
    F["h10"] = cum.shift(-11) / cum.shift(-1) - 1.0
    F["trad"] = trad & F["h5"].notna()
    return F


def main():
    print("=== DISCOVERY HARNESS POWER CONTROL ===")
    print(f"seeds={SEEDS} freqs={FREQS} deltas_bp={[int(d*1e4) for d in DELTAS]}")
    script_hash = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    harness_hash = hashlib.sha256(open("sprint_lib.py", "rb").read()).hexdigest()
    print(f"control_script_sha256={script_hash}")
    print(f"harness_sprint_lib_sha256={harness_hash}")

    p = sl.SprintPanel()
    mask0 = p.mask_base()
    clean = ~build_contam(p)
    mask = (mask0 & clean)
    r1 = p.ret1
    ret5z = sl.trailing_z(p.ret5)
    volz = sl.trailing_z(p.volume)
    nbz = sl.trailing_z(p.nb)
    adv = p.adv60.where(mask0)
    ter = adv.rank(axis=1, pct=True)

    # eligible pool: cells with valid y and full FM controls
    y = p.hold[5]
    valid = mask & y.notna() & r1.notna() & ret5z.notna() & volz.notna() & ter.notna() & nbz.notna()
    di, ci = np.where(valid.values)
    dates = np.asarray(valid.index)[di]
    tick = np.asarray(valid.columns)[ci]
    yv = y.values[di, ci].astype(float)
    r1v = r1.values[di, ci]; r5v = ret5z.values[di, ci]; vlv = volz.values[di, ci]
    tvl = ter.values[di, ci]; nbv = nbz.values[di, ci]
    half = (pd.Series(dates).str[:4] +
            np.where(pd.Series(dates).str[5:7].astype(int) <= 6, "-H1", "-H2")).values
    year = pd.Series(dates).str[:4].values
    pool_n = len(yv)
    pool_mean = float(yv.mean())
    print(f"eligible pool: {pool_n} cells, pool mean h5={pool_mean:+.5f}, sd={yv.std():.4f}")
    uniq_dates = pd.unique(dates)
    date_pos = {d: i for i, d in enumerate(uniq_dates)}
    dpos = np.array([date_pos[d] for d in dates])
    n_dates = len(uniq_dates)
    # per-date cross-sectional sizes for FM
    date_sizes = np.bincount(dpos, minlength=n_dates)

    # tier assignment (relative within date is implicit in ter values already)
    ter_q = np.digitize(tvl, [1 / 3, 2 / 3])  # 0 bot, 1 mid, 2 top (cross-sec pct per cell)

    results = {"meta": {"script_sha256": script_hash, "harness_sha256": harness_hash,
                        "pool_n": pool_n, "pool_mean": pool_mean,
                        "seeds": SEEDS, "freqs": FREQS,
                        "deltas_bp": [int(d * 1e4) for d in DELTAS],
                        "gate_rule": "G1 net60>=30bp; G2 >=3/4 halves>0; G3 FM beta>0 |t|>=2 "
                                     "(ctrl: ret1,ret5z,volz,ADVterc,flowz); G4 n>=1000 & tickers>=50; "
                                     "G5 OOS both eras mean>0"},
               "runs": []}

    # ---------- OOS panel (built once; per-run random subsets of same size) ----------
    print("\nbuilding 2021-24 pseudo-OOS panels ...")
    F = build_oos()
    oos = {}
    for era, a, b in (("2021H2-2022", "2021-07-01", "2023-01-01"),
                      ("2023-2024", "2023-01-01", "2025-01-01")):
        Fv = F["trad"] & F["h5"].notna()
        Fv = Fv[(Fv.index >= a) & (Fv.index < b)]
        # label-aligned extraction: positions from a SLICED frame must never be
        # used against the full grid — reindex h5 to the sliced rows first
        y = F["h5"].loc[Fv.index].values[Fv.values]
        oos[era] = {"y": y.astype(float),
                    "n_sessions": int(len(np.unique(np.asarray(Fv.index)[np.where(Fv.values)[0]])))}
        print(f"  OOS {era}: {oos[era]['n_sessions']} sessions, {len(oos[era]['y'])} cells, "
              f"base mean={oos[era]['y'].mean():+.5f}")

    # ---------- main loop ----------
    rng_master = np.random.default_rng(20260916)
    summary = {}
    for m in FREQS:
        for delta in DELTAS:
            det = 0
            gate_kill = {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0}
            recs = []
            for seed in SEEDS:
                rng = np.random.default_rng(20260916 * 1000 + hash((m, int(delta * 1e4), seed)) % 10**6)
                idx = rng.choice(pool_n, size=min(m, pool_n), replace=False)
                flag = np.zeros(pool_n)
                flag[idx] = 1.0
                y_syn = yv.copy()
                y_syn[idx] += delta
                ev_mean = float(y_syn[idx].mean())
                # G1
                g1 = (ev_mean - 0.006) >= 0.003
                # G2 halves (event-weighted pooled per half)
                half_means = {}
                for h in sorted(pd.unique(half)):
                    sel = half[idx] == h if False else (half[idx] == h)
                    v = y_syn[idx][sel]
                    half_means[h] = float(v.mean()) if len(v) > 30 else np.nan
                pos_halves = sum(1 for v in half_means.values() if not np.isnan(v) and v > 0)
                g2 = pos_halves >= 3
                # G4
                n_t = len(np.unique(tick[idx]))
                g4 = (len(idx) >= 1000) and (n_t >= 50)
                # G3 FM (only if G1&G2&G4 — same short-circuit the harness used)
                g3_pass, fm_beta, fm_t = False, np.nan, np.nan
                if g1 and g2 and g4:
                    # per-date regression
                    betas = []
                    y_full_syn = yv + delta * flag
                    for dgi in range(n_dates):
                        rows = np.where(dpos == dgi)[0]
                        if rows.size < 30:
                            continue
                        Xd = np.column_stack([np.ones(rows.size), flag[rows], r1v[rows],
                                              r5v[rows], vlv[rows], tvl[rows], nbv[rows]])
                        yd = y_full_syn[rows]
                        if np.abs(flag[rows]).sum() == 0:
                            continue
                        beta, *_ = np.linalg.lstsq(Xd, yd, rcond=None)
                        betas.append(beta[1])
                    betas = np.array(betas)
                    fm_beta = float(betas.mean())
                    se = betas.std(ddof=1) / np.sqrt(len(betas))
                    fm_t = fm_beta / se if se > 0 else np.nan
                    g3_pass = (fm_beta > 0) and (abs(fm_t) >= 2)
                # G5 OOS (same-size subsets, same delta, both eras mean>0)
                oos_ok, oos_means = True, {}
                for era in oos:
                    yy = oos[era]["y"]
                    k = min(m, len(yy))
                    rr = np.random.default_rng(seed * 7919 + int(delta * 1e4))
                    sel = rr.choice(len(yy), size=k, replace=False)
                    mu = float(yy[sel].mean() + delta)
                    oos_means[era] = mu
                    # fail-closed: NaN mean kills the gate (never vacuous pass)
                    oos_ok = oos_ok and (mu > 0)
                # day-weighted vs event-weighted
                dsum = pd.Series(y_syn[idx]).groupby(pd.Series(dates[idx])).mean()
                day_w = float(dsum.mean())
                rec = {"freq_m": m, "delta_bp": int(delta * 1e4), "seed": seed,
                       "n_treated": int(len(idx)), "ev_mean": ev_mean,
                       "net60": ev_mean - 0.006, "pos_halves": pos_halves,
                       "half_means": half_means, "n_tickers": n_t,
                       "g1": bool(g1), "g2": bool(g2), "g3": bool(g3_pass),
                       "g4": bool(g4), "g5": bool(oos_ok),
                       "fm_beta": fm_beta, "fm_t": fm_t,
                       "day_weighted_mean": day_w,
                       "oos_means": oos_means,
                       "tier_mean": {["bot", "mid", "top"][q]: float(y_syn[idx][ter_q[idx] == q].mean())
                                     for q in (0, 1, 2) if (ter_q[idx] == q).sum() > 30}}
                detected = g1 and g2 and g3_pass and g4 and oos_ok
                rec["detected"] = bool(detected)
                if not detected:
                    for g, v in (("G1", g1), ("G2", g2), ("G3", g3_pass), ("G4", g4), ("G5", oos_ok)):
                        if not v:
                            gate_kill[g] += 1
                            break
                det += int(detected)
                recs.append(rec)
            rate = det / len(SEEDS)
            summary[f"m{m}_d{int(delta*1e4)}bp"] = {
                "detection_rate": rate, "false_negative_rate": 1 - rate,
                "gate_kill_first": dict(gate_kill), "runs": recs}
            print(f"m={m:5d} delta={int(delta*1e4):+4d}bp: detection={det}/{len(SEEDS)} "
                  f"({rate:.0%})  first-gate kills={gate_kill}")

    # ---------- minimum reliably detectable effect ----------
    print("\n=== MINIMUM RELIABLY DETECTABLE EFFECT (>=80% detection) ===")
    mde = {}
    for m in FREQS:
        prev = None
        for delta in DELTAS:
            r = summary[f"m{m}_d{int(delta*1e4)}bp"]["detection_rate"]
            if r >= 0.8:
                mde[m] = f"{int(delta*1e4)}bp (or between {int(prev*1e4) if prev else 0} and {int(delta*1e4)}bp)"
                break
            prev = delta
        else:
            mde[m] = ">150bp"
        print(f"  freq {m:5d}: MDE = {mde[m]}")
    OUT = {"meta": results["meta"], "summary": summary, "mde": mde,
           "oos_base": {e: {"base_mean": None} for e in oos}}
    print("===JSON_BEGIN===")
    print(json.dumps(OUT, indent=1, default=str))
    print("===JSON_END===")
    print("(results printed to stdout; captured by shell redirection)")


if __name__ == "__main__":
    main()
