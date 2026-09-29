"""SCREEN-PM-LC-001 -- {LC} young-listing avoidance screen (brief 2026-09-29, phase 1).

Reads PREDECLARATION_S2_LC_LISTINGS.md (sha256 beside it, frozen and committed before
any outcome is computed). One run; all 6 pre-declared arms reported; the verdict is the
primary cell only (YOUNG, hold 252, confirmation half, gross, |t| >= 2.86 at >= 48 valid
months, negative sign). Listing dates are proxied by first panel bars; coverage-start
artifacts are excluded and counted; a young name's own later issuance ex-dates inside a
hold window are wealth-corrected with the same gap-verified machinery as S1.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

import bs_common as B                                            # noqa: E402
from research.rulecard import engine, events                     # noqa: E402
from research.tracking import track_run                          # noqa: E402

HOLDS = (126, 252)
FIRST_FROM = pd.Timestamp("2015-01-01")


def first_bars(P: pd.DataFrame) -> pd.DataFrame:
    f = P.groupby("ticker")["date"].min().rename("first_bar").reset_index()
    return f


def build_flags(pan: engine.Panel, listed: set[str]):
    """Flag each listed ticker's first own session with n_prior >= 25 (the first row the
    engine can treat as eligible); require trailing adv20 >= Rp 5bn there (pre-declared).
    Counted: tickers with no eligible row, rows below the adv gate."""
    P, F = pan.P, pan.F
    flags = pd.Series(0.0, index=P.index)
    counted = {"listed_tickers": len(listed), "no_eligible_row": 0, "below_adv_gate": 0,
               "flagged": 0}
    first_ok = P[P["ticker"].isin(listed) & (F["n_prior"].values == 25)]
    for row in first_ok.index:
        if np.isfinite(F["adv20"].values[row]) and F["adv20"].values[row] >= B.ADV_MIN_FLAG:
            flags.loc[row] = 1.0
            counted["flagged"] += 1
        else:
            counted["below_adv_gate"] += 1
    got = set(P.loc[flags > 0, "ticker"]) | set()
    counted["no_eligible_row"] = len(listed) - counted["flagged"] - counted["below_adv_gate"]
    return flags, counted, got


def main():
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    pre_sha = (HERE / "PREDECLARATION_S2_LC_LISTINGS.sha256").read_text().split()[0]

    P_raw, load_audit = B.load_panel()
    firsts = first_bars(P_raw)
    # coverage-start artifacts: a first bar exactly on a corpus start date is an old name
    # being onboarded, not a listing (pre-declared defect)
    starts = {pd.Timestamp(P_raw["date"].min()), B.SPLIT_DATE}
    art = firsts[firsts["first_bar"].isin(starts)]
    listed = set(firsts[(firsts["first_bar"] >= FIRST_FROM)
                        & (firsts["first_bar"] <= B.CUT)
                        & (~firsts["first_bar"].isin(starts))]["ticker"])
    defect_counts = {"first_bar_on_coverage_start": int(len(art)),
                     "first_bar_before_2015": int((firsts["first_bar"] < FIRST_FROM).sum())}

    # rule 4: ALL issuance-type ex-dates are wealth-corrected (a mechanical drop in any
    # book member distorts the benchmark just as it distorts a held position)
    ca = B.parse_ca_events(("rightissue", "bonus", "stock_reverse"))
    P_corr, corr_audit = B.wealth_correct(P_raw, ca)
    ih = B.load_ihsg(P_raw)

    panels = {lens: engine.Panel(P) for lens, P in (("corr", P_corr), ("raw", P_raw))}
    results, audits = {}, {"load": load_audit, "correction": corr_audit,
                           "defects": defect_counts}

    with track_run("broad_search_screen_s2_lc_listings",
                   params={"predeclaration_sha256": pre_sha, "script_sha256": sha,
                           "snapshot": B.SNAP_SHA256, "listed": len(listed),
                           "holds": list(HOLDS)}) as run:
        flags_c, counted_c, got_c = build_flags(panels["corr"], listed)
        flags_r, counted_r, got_r = build_flags(panels["raw"], listed)
        audits["flag_counts_corr"] = counted_c
        pre_c, post_c = B.entry_split_flags(panels["corr"], flags_c)
        pre_r, post_r = B.entry_split_flags(panels["raw"], flags_r)

        # volatility-conditioned descriptive cells: realized vol since listing (expanding
        # std of daily returns, min 10 own sessions) above/below the cross-sectional
        # median of the flag date (declared {V}-overlap mitigation; see pre-run amendment)
        Pc, F = panels["corr"].P, panels["corr"].F
        ret1 = Pc.groupby(Pc["ticker"], sort=False)["close"].pct_change()
        vol = ret1.groupby(Pc["ticker"], sort=False).transform(
            lambda x: x.expanding(min_periods=10).std())
        med = vol.groupby(Pc["date"].values).transform("median")
        hi = flags_c * (vol > med).fillna(False).astype(float)
        lo = flags_c * (vol <= med).fillna(False).astype(float)

        for hold in HOLDS:
            results[f"YOUNG|h{hold}|pre2021"] = {
                "corr": B.run_cell(panels["corr"], pre_c, hold),
                "raw": B.run_cell(panels["raw"], pre_r, hold)}
            results[f"YOUNG|h{hold}|post2021"] = {
                "corr": B.run_cell(panels["corr"], post_c, hold, ih=ih),
                "raw": B.run_cell(panels["raw"], post_r, hold, ih=ih)}
        results["YOUNG|h252|post2021|vol_high"] = {"corr": B.run_cell(panels["corr"], hi, 252)}
        results["YOUNG|h252|post2021|vol_low"] = {"corr": B.run_cell(panels["corr"], lo, 252)}

        primary = results["YOUNG|h252|post2021"]["corr"]
        placebo = None
        if primary.get("months_valid", 0) >= 48 and \
                abs(primary.get("primary_t", 0.0)) >= 2.86:   # D-061 precedent
            pl = events.placebo_flags(panels["corr"], post_c)
            pc = B.run_cell(panels["corr"], pl, 252)
            placebo = {"months_valid": pc.get("months_valid"),
                       "primary_t": pc.get("primary_t")}

        stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%SZ")
        result = {"record_type": "exploratory_screen", "canonical_id": "SCREEN-PM-LC-001",
                  "predeclaration_sha256": pre_sha, "script_sha256": sha,
                  "run_utc": stamp, "snapshot_sha256": B.SNAP_SHA256,
                  "panel_rows": int(len(panels["corr"].P)),
                  "panel_last_date": str(pd.Timestamp(panels["corr"].P["date"].max()).date()),
                  "ihsg_last_date": str(ih["date"].max().date()) if len(ih) else None,
                  "listed_tickers": len(listed), "audits": audits, "cells": results,
                  "primary_placebo": placebo}
        run.metrics = {"primary_t": primary.get("primary_t"),
                       "primary_months": primary.get("months_valid")}
        (HERE / f"RESULT_S2_{stamp}.json").write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: {l: {kk: vv for kk, vv in c.items()
                              if kk in ("events", "months_valid", "primary_mean",
                                        "primary_t", "net_mean", "frac_months_pos",
                                        "perdate_mean_daily_excess_pct", "ihsg_excess_mean",
                                        "ihsg_excess_t")}
                          for l, c in v.items()} for k, v in results.items()},
                     indent=1, default=float))
    print("PRIMARY:", json.dumps(primary, default=float)[:800])
    print("AUDITS:", json.dumps({k: v for k, v in audits.items()
                                 if k != "correction"}, default=str)[:600])
    print("CORRECTIONS:", len(corr_audit["applied"]), "applied /",
          corr_audit["already_adjusted"], "already-adjusted /",
          corr_audit["below_band"], "below-band")


if __name__ == "__main__":
    main()
