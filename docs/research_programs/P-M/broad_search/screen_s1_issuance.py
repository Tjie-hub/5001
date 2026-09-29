"""SCREEN-PM-CF-001 -- {CF} issuance-avoidance screen (brief 2026-09-29, phase 1).

Reads PREDECLARATION_S1_CF_ISSUANCE.md (sha256 beside it, frozen and committed before
any outcome is computed). One run; all 8 pre-declared arms reported; the verdict is the
primary cell only (RI, hold 252, confirmation half, corrected panel, gross, |t| >= 2.86
at >= 48 valid months, negative sign). Every cell runs on the wealth-corrected panel
(primary lens); the raw panel is the declared observability lens inside the same arms.
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


def build_flags(pan: engine.Panel, ev: pd.DataFrame, label: str, adv_gate: bool):
    """Announcement stamp -> the ticker's FIRST own session strictly after (known at that
    close). Flagged rows additionally require trailing adv20 >= Rp 5bn (pre-declared
    primary universe). Defects counted."""
    P, F = pan.P, pan.F
    defects = {"stamp_missing": 0, "outside_window": 0, "no_panel_row": 0,
               "below_adv_gate": 0, "not_eligible": 0}
    flags = pd.Series(0.0, index=P.index)
    n_events = 0
    idx = P.groupby("ticker", sort=False).indices
    dts_all = pd.DatetimeIndex(P["date"].values)
    adv = F["adv20"].values
    for t, g in ev.groupby("ticker", sort=False):
        ii = idx.get(t)
        if ii is None:
            defects["no_panel_row"] += len(g)
            continue
        dts = dts_all[ii]
        pos = dts.searchsorted(pd.DatetimeIndex(g["stamp"].values), side="right")
        for p, (_, r) in zip(pos, g.iterrows()):
            n_events += 1
            if pd.isna(r["stamp"]):
                defects["stamp_missing"] += 1
                continue
            if not (pd.Timestamp("2013-01-01") <= r["stamp"] <= B.CUT):
                defects["outside_window"] += 1
                continue
            if p >= len(ii):
                defects["no_panel_row"] += 1
                continue
            row = ii[p]
            if adv_gate and not (np.isfinite(adv[row]) and adv[row] >= B.ADV_MIN_FLAG):
                defects["below_adv_gate"] += 1
                continue
            if not pan.eligible.values[row]:
                defects["not_eligible"] += 1
                continue
            flags.loc[row] = 1.0
    return flags, {"def_" + label: {"events_total": n_events, **defects}}


def main():
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    pre_sha = (HERE / "PREDECLARATION_S1_CF_ISSUANCE.sha256").read_text().split()[0]

    ca = B.parse_ca_events(("rightissue",))          # terms for the wealth correction
    import sqlite3
    con = sqlite3.connect(f"file:{B.SNAP}?mode=ro", uri=True)
    raw = pd.read_sql("SELECT ticker, action_type, raw_json FROM corporate_action_events "
                      "WHERE action_type IN ('rightissue','rups')", con)
    con.close()

    def stamps(ak, key):
        rr = raw[raw["action_type"] == ak]
        out = []
        for _, r in rr.iterrows():
            j = json.loads(r["raw_json"])
            out.append({"ticker": r["ticker"], "type": ak,
                        "stamp": pd.to_datetime(j.get(key), errors="coerce", format="mixed")})
        return pd.DataFrame(out)

    defs = {"RI": stamps("rightissue", "rightissue_created"),
            "RUPS": stamps("rups", "rups_created")}
    # exclude FORU events entirely from 2026-09-14 (D-063; its stamps postdate the cutoff
    # anyway, the panel exclusion covers the price side)
    for k in defs:
        defs[k] = defs[k][defs[k]["ticker"] != "FORU"].reset_index(drop=True)

    P_raw, load_audit = B.load_panel()
    corr_ev = ca[ca["ticker"] != "FORU"].reset_index(drop=True)
    P_corr, corr_audit = B.wealth_correct(P_raw, corr_ev)

    ih = B.load_ihsg(P_raw)
    results, splits = {}, {}
    audits = {"load": load_audit, "correction": corr_audit,
              "corrections_applied": len(corr_audit["applied"])}
    panels = {}
    for lens, P in (("corr", P_corr), ("raw", P_raw)):
        panels[lens] = engine.Panel(P)
    assert len(panels["corr"].P) == len(panels["raw"].P)  # the two lenses share a calendar

    with track_run("broad_search_screen_s1_cf_issuance",
                   params={"predeclaration_sha256": pre_sha, "script_sha256": sha,
                           "snapshot": B.SNAP_SHA256,
                           "defs": list(defs), "holds": list(HOLDS)}) as run:
        for name, evf in defs.items():
            flags_c, audit_c = build_flags(panels["corr"], evf, f"{name}_corr", adv_gate=True)
            flags_r, audit_r = build_flags(panels["raw"], evf, f"{name}_raw", adv_gate=True)
            audits.update(audit_c)
            pre_c, post_c = B.entry_split_flags(panels["corr"], flags_c)
            pre_r, post_r = B.entry_split_flags(panels["raw"], flags_r)
            splits[name] = post_c
            for hold in HOLDS:
                results[f"{name}|h{hold}|pre2021"] = {
                    "corr": B.run_cell(panels["corr"], pre_c, hold),
                    "raw": B.run_cell(panels["raw"], pre_r, hold)}
                results[f"{name}|h{hold}|post2021"] = {
                    "corr": B.run_cell(panels["corr"], post_c, hold, ih=ih),
                    "raw": B.run_cell(panels["raw"], post_r, hold, ih=ih)}

        primary = results["RI|h252|post2021"]["corr"]
        placebo = None
        if primary.get("months_valid", 0) >= 48 and \
                abs(primary.get("primary_t", 0.0)) >= 2.86:   # D-061 precedent
            pl = events.placebo_flags(panels["corr"], splits["RI"])
            pc = B.run_cell(panels["corr"], pl, 252)
            placebo = {"months_valid": pc.get("months_valid"),
                       "primary_t": pc.get("primary_t")}

        stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%SZ")
        result = {"record_type": "exploratory_screen", "canonical_id": "SCREEN-PM-CF-001",
                  "predeclaration_sha256": pre_sha, "script_sha256": sha,
                  "run_utc": stamp, "snapshot_sha256": B.SNAP_SHA256,
                  "panel_rows": int(len(panels["corr"].P)),
                  "panel_last_date": str(pd.Timestamp(panels["corr"].P["date"].max()).date()),
                  "ihsg_last_date": str(ih["date"].max().date()) if len(ih) else None,
                  "audits": audits, "cells": results, "primary_placebo": placebo}
        run.metrics = {"primary_t": primary.get("primary_t"),
                       "primary_months": primary.get("months_valid")}
        (HERE / f"RESULT_S1_{stamp}.json").write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps({k: {l: {kk: vv for kk, vv in c.items()
                              if kk in ("events", "months_valid", "primary_mean",
                                        "primary_t", "net_mean", "frac_months_pos",
                                        "perdate_mean_daily_excess_pct", "ihsg_excess_mean",
                                        "ihsg_excess_t")}
                          for l, c in v.items()} for k, v in results.items()},
                     indent=1, default=float))
    print("PRIMARY:", json.dumps(primary, default=float)[:800])


if __name__ == "__main__":
    main()
