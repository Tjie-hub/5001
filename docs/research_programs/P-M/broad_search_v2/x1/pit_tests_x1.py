"""PIT tests T1-T3 for the X1 signal construction (REVIEW_R2 section 2, mandatory).

Committed with the re-freeze and RUN before any outcome run. These tests read no
outcomes: T1 perturbs open(D)/close(D) precisely to prove they cannot move the
signal; no arm statistic is computed here.

  T1  Invariance: perturb open(D), close(D) (corpus TLKM leg), JKSE_D and FX_D by
      +/-5% for 50 fixed-seed random sessions. Every R_std for session D must be
      bit-identical. A sanity count reports how many LATER sessions DID move
      (proving the perturbation propagated).
  T2  Timestamp assertion: every hedge-leg value is stamped d=cal[j-1] or
      d-1=cal[j-2], both strictly before D=cal[j] (re-derived by explicit-stamp
      recomputation on random sessions), and every US close used lies at/below
      08:45 WIB of D under the DST-aware mapping.
  T3  Sign check: IDR depreciation (FX_d > FX_{d-1}) with a flat index must give a
      NEGATIVE USD return; appreciation must give a positive one (both leg
      variants: JKSE and corpus TLKM).

Output: PIT_TESTS_X1.json next to this file.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("x1drv", HERE / "screen_x1_overnight.py")
drv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drv)          # guard lives in main(); import is inert

out = {"tests": {}}
rng = np.random.default_rng(42)


def main():
    DATA = HERE / "data"
    fx = pd.read_csv(DATA / "usdidr.csv", parse_dates=["date"]).set_index("date")["close"]
    jk = pd.read_csv(DATA / "jkse.csv", parse_dates=["date"]).set_index("date")["close"]
    us = {"EIDO": pd.read_csv(DATA / "eido.csv", parse_dates=["date"]).set_index("date")["close"],
          "TLK": pd.read_csv(DATA / "tlk.csv", parse_dates=["date"]).set_index("date")["close"],
          "SPY": pd.read_csv(DATA / "spy.csv", parse_dates=["date"]).set_index("date")["close"]}

    # ------------------------------------------------------------- T3 (synthetic)
    cal3 = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
    jk_flat = pd.Series([7000.0] * 3, index=cal3)
    fx_dep = pd.Series([15700.0, 16000.0, 16300.0], index=cal3)   # IDR depreciates throughout
    fx_app = pd.Series([15700.0, 15400.0, 15100.0], index=cal3)   # IDR appreciates throughout
    x_dep = drv.fx_idr_usd_leg(cal3, jk_flat, fx_dep)
    x_app = drv.fx_idr_usd_leg(cal3, jk_flat, fx_app)
    t3 = {"depreciation_x": {str(k): v for k, v in x_dep.items()},
          "appreciation_x": {str(k): v for k, v in x_app.items()},
          "depreciation_negative": bool(len(x_dep) > 0 and all(v < 0 for v in x_dep.values())),
          "appreciation_positive": bool(len(x_app) > 0 and all(v > 0 for v in x_app.values()))}
    # TLKM-USD variant: flat corpus close + depreciation -> negative
    flat_close = np.array([4000.0, 4000.0, 4000.0])
    x_tl = drv.fx_idr_usd_leg(cal3, None, fx_dep, alt_close=flat_close)
    t3["tlkm_usd_depreciation_negative"] = bool(len(x_tl) > 0 and all(v < 0 for v in x_tl.values()))
    out["tests"]["T3_sign_check"] = t3
    assert t3["depreciation_negative"] and t3["appreciation_positive"] \
        and t3["tlkm_usd_depreciation_negative"], "T3 FAILED"

    # --------------------------------------------- corpus load (TLKM leg, T1/T2/E4)
    print("loading corpus (TLKM leg) ...", flush=True)
    CP = drv.load_corpus()
    cal = CP["cal"]
    tl = CP["tix"].get("TLKM")
    tlkm_close = CP["C"][:, tl] if tl is not None else None

    def build_all(jk_s, fx_s, tlkm_c):
        sigs = {}
        for nm, s in us.items():
            ymap = drv.us_window_returns(s, cal)
            if nm == "SPY":
                sigs[nm] = drv.build_signal(ymap, {}, cal, residualize=False)["signal"]  # N2
            else:
                xmap = drv.fx_idr_usd_leg(cal, jk_s, fx_s,
                                          alt_close=None if nm != "TLK" else tlkm_c)
                sigs[nm] = drv.build_signal(ymap, xmap, cal)["signal"]
        return sigs

    base = build_all(jk, fx, tlkm_close)

    # --------------------------------------------------------------- T2 (stamps)
    xmaps = {nm: drv.fx_idr_usd_leg(cal, jk, fx,
                                    alt_close=tlkm_close if nm == "TLK" else None)
             for nm in us}
    n_stamp_checks = 0
    for nm, s in us.items():
        ymap = drv.us_window_returns(s, cal)
        wts = drv.us_close_wib_ts(pd.DatetimeIndex(s.index))   # hoisted: DST map is O(1) reuse
        for j, (yv, k) in ymap.items():
            if k == 0 or not np.isfinite(yv):
                continue
            d, dm, D = cal[j - 1], cal[j - 2], cal[j]
            assert d < D and dm < D, f"T2: hedge stamp >= D at {D.date()}"
            fd, fdm = fx.get(d), fx.get(dm)
            jd, jdm = jk.get(d), jk.get(dm)
            if None in (fd, fdm, jd, jdm):
                continue                       # FX-hole or index hole: leg absent
            xj = (jd / jdm) * (fdm / fd) - 1.0
            if nm == "TLK" and tlkm_close is not None:
                xj = (tlkm_close[j - 1] / tlkm_close[j - 2]) * (fdm / fd) - 1.0
            if np.isfinite(xj):
                got = xmaps[nm].get(j)
                assert got is not None and abs(got - xj) < 1e-15, \
                    f"T2: x[{j}] not rebuilt from stamps d,d-1"
                n_stamp_checks += 1
            # US close timestamps: every used close lands <= 08:45 WIB of D
            used = s.index[(s.index >= d) & (s.index < D)]
            for t in used:
                i = s.index.get_loc(t)
                ts = wts[i]
                assert ts.date() <= D.date() and (ts.hour, ts.minute) <= (8, 45), \
                    f"T2: US close {ts} not <= 08:45 WIB {D.date()}"
    out["tests"]["T2_timestamps"] = {
        "sessions_checked": int(n_stamp_checks),
        "hedge_stamps_strictly_before_D": True,
        "us_closes_le_0845_wib": True,
        "note": "assertions raise on violation; x-map values re-derived by explicit stamps"}

    # ------------------------------------------------------------------ T1 (perturb)
    sessions = [j for j in base["EIDO"] if 2012 <= cal[j].year <= 2026]
    pick = sorted(rng.choice(len(sessions), size=50, replace=False))
    perturb_js = [sessions[i] for i in pick]
    identical = {nm: 0 for nm in us}
    moved_later = {nm: 0 for nm in us}
    for jD in perturb_js:
        D = cal[jD]
        jk2 = jk.copy(); fx2 = fx.copy()
        sgn = 1.05 if rng.integers(2) else 0.95
        if D in jk2.index:
            jk2.loc[D] = jk2.loc[D] * sgn
        if D in fx2.index:
            fx2.loc[D] = fx2.loc[D] * sgn
        tlkm2 = None if tlkm_close is None else tlkm_close.copy()
        if tlkm2 is not None and np.isfinite(tlkm2[jD]):
            tlkm2[jD] = tlkm2[jD] * sgn
        pert = build_all(jk2, fx2, tlkm2)
        for nm in us:
            for jj, v in base[nm].items():
                q = pert[nm].get(jj)
                if q is None:
                    continue
                if jj == jD:
                    identical[nm] += int(v["R_std"] == q["R_std"])
                elif jj > jD and v["R_std"] != q["R_std"]:
                    moved_later[nm] += 1
    n_checks = {nm: 50 for nm in us}
    out["tests"]["T1_invariance"] = {
        "sessions_perturbed": 50, "seed": 42,
        "R_std_identical_at_perturbed_session": identical,
        "expected_identical": n_checks,
        "later_sessions_moved_sancount": moved_later,
        "pass": all(identical[nm] == 50 for nm in us),
        "spy_not_residualized": moved_later["SPY"] == 0,
        "note": "N2: SPY's R_std must not move at ALL when hedge-leg inputs (JKSE/FX/TLKM) are perturbed -- zero later-session moves proves the SPY arm is raw, not residualized",
    }
    assert out["tests"]["T1_invariance"]["pass"], "T1 FAILED"
    assert out["tests"]["T1_invariance"]["spy_not_residualized"], "T1-SPY (N2) FAILED: SPY still moves with hedge-leg inputs"

    # ------------------------------------------------------------------ T4 (guard)
    import tempfile
    t4 = {}
    dsha, psha = "a" * 64, "b" * 64
    valid_line = (f"R2-DECISION: X1 GO driver_sha256={dsha} "
                  f"predeclaration_sha256={psha}")
    template_line = "R2-DECISION: X1 GO driver_sha256=<sha> predeclaration_sha256=<sha>"

    def write_reviews(files):
        tmp = tempfile.mkdtemp()
        for name, lines in files.items():
            (Path(tmp) / name).write_text("\n".join(lines) + "\n")
        return tmp

    # (a) template-only file -> refuse
    tmp = write_reviews({"REVIEW_R2_2026-10-05.md": ["## B3 format:", template_line]})
    ok, why = drv.check_guard(directory=tmp, driver_sha=dsha, pre_sha=psha)
    t4["template_only_refused"] = ok is None
    # (b) wrong-sha line -> refuse
    tmp = write_reviews({"REVIEW_R2bis_2026-10-05.md": [
        valid_line.replace("a" * 64, "c" * 64)]})
    ok, why = drv.check_guard(directory=tmp, driver_sha=dsha, pre_sha=psha)
    t4["wrong_sha_refused"] = ok is None
    t4["wrong_sha_reason_lists_candidate"] = bool(why) and "match=False" in why
    # (c) template file plus a valid line in a LATER file -> accept
    tmp = write_reviews({"REVIEW_R2_2026-10-05.md": ["## B3 format:", template_line],
                         "REVIEW_R2bis_2026-10-05.md": ["decision:", valid_line]})
    ok, why = drv.check_guard(directory=tmp, driver_sha=dsha, pre_sha=psha)
    t4["template_plus_valid_later_file_accepted"] = ok is not None
    if ok:
        t4["accepted_from"] = ok
    # (d) no file -> refuse
    tmp = tempfile.mkdtemp()
    ok, why = drv.check_guard(directory=tmp, driver_sha=dsha, pre_sha=psha)
    t4["no_file_refused"] = ok is None
    out["tests"]["T4_guard"] = t4
    assert all(v for k, v in t4.items() if k.startswith(("template", "wrong", "no_"))), "T4 FAILED"

    # ------------------------------------------------- E4 boundary disclosure count
    liquid = (CP["A20"] >= drv.ADV_MIN) & (CP["V"] > 0) & (CP["O"] > 0) & (CP["C"] > 0)
    tickv = np.select([CP["PC"] < 200, CP["PC"] < 500, CP["PC"] < 2000, CP["PC"] < 5000],
                      [1.0, 2.0, 5.0, 10.0], 25.0)
    tf = np.divide(tickv, np.where(CP["PC"] > 0, CP["PC"], np.nan),
                   out=np.full_like(CP["C"], np.nan))
    near = np.isfinite(tf) & (tf > 0.004) & (tf < 0.0065) & liquid
    out["tick_schedule_disclosure"] = {
        "assumed": "current IDX schedule applied to ALL dates (historical unverifiable here)",
        "discovery_liquid_name_days_near_boundary_0.004_0.0065": int(
            sum(int(near[j].sum()) for j in range(len(cal)) if cal[j] < drv.SPLIT_DATE)),
        "confirmation_liquid_name_days_near_boundary_0.004_0.0065": int(
            sum(int(near[j].sum()) for j in range(len(cal)) if drv.SPLIT_DATE <= cal[j])),
    }

    (HERE / "PIT_TESTS_X1.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out["tests"], indent=1, default=str)[:2200])
    print("WROTE", HERE / "PIT_TESTS_X1.json")


if __name__ == "__main__":
    main()
