#!/usr/bin/env python3
"""Independent accounting-identity audit — READ-ONLY forensic measurement.

Verifies, from the actual tables, at the exact aggregation levels used by the
affected tests:
  A. FROZEN Dataset B store (limit=150, full population), per (ticker, session):
       SUM(buy value) vs SUM(sell value); SUM(signed lot) == 0.
  B. PRODUCTION broker_flow (top-25 disclosure, Dataset A window), per
       (ticker, trade_date): NV = SUM(value), GV = SUM(|value|)  [BFI-001's
       BFI_broad = NV/GV]; SUM(signed lot)  [HYP-PM-0003's net_flow].
  C. Investor-type decomposition on the frozen store (C2 tautology):
       for_net + loc_net + pem_net == 0 exactness; gate incidences.
"""
import json
import sqlite3

R = "/home/tjiesar/10 Projects/idx-walkforward-5001"
STORE = R + "/docs/research_programs/P-M/dataset_b/store/DATASET_B_BROKER_FLOW_STORE_v1.sqlite"
PROD = R + "/data/walkforward.db"


def pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(p / 100 * (len(vals) - 1)))] if vals else None


def report(name, pairs, signed_lots=None):
    n = len(pairs)
    exact = sum(1 for nv, gv in pairs if nv == 0)
    near = sum(1 for nv, gv in pairs if gv and abs(nv / gv) < 0.001)
    ratios = [abs(nv) / gv for nv, gv in pairs if gv]
    out = {
        "cells": n,
        "exact_zero_net": exact,
        "exact_zero_pct": round(100 * exact / n, 2) if n else None,
        "near_zero_lt_0.1pct": near,
        "near_zero_pct": round(100 * near / n, 2) if n else None,
        "abs_net_over_gross_p50": round(pct(ratios, 50), 6) if ratios else None,
        "abs_net_over_gross_p90": round(pct(ratios, 90), 6) if ratios else None,
        "abs_net_over_gross_p99": round(pct(ratios, 99), 6) if ratios else None,
        "abs_net_over_gross_max": round(max(ratios), 6) if ratios else None,
    }
    if signed_lots is not None:
        nz = sum(1 for v in signed_lots if v == 0)
        out["signed_lot_exact_zero_pct"] = round(100 * nz / len(signed_lots), 2) if signed_lots else None
    print(f"  {name}: {json.dumps(out)}")
    return out


def main():
    out = {}

    # ---------- A. frozen store, limit=150 ----------
    s = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    s.execute("PRAGMA query_only = ON;")
    rows = s.execute("""
        SELECT ticker, trade_date,
               SUM(CASE WHEN side='BUY'  THEN value ELSE 0 END) AS bv,
               SUM(CASE WHEN side='SELL' THEN -value ELSE 0 END) AS sv
        FROM broker_flow_b GROUP BY ticker, trade_date
    """).fetchall()
    pairs = [(bv - sv, bv + sv) for _, _, bv, sv in rows]
    lots = s.execute("""
        SELECT SUM(lot) FROM (
            SELECT ticker, trade_date, SUM(CASE WHEN side='BUY' THEN lot ELSE -lot END) AS lot
            FROM broker_flow_b GROUP BY ticker, trade_date)
    """).fetchone()[0]
    out["A_frozen_store_limit150"] = report("frozen store", pairs, signed_lots=[lots])
    nv_sum = s.execute("""
        SELECT SUM(CASE WHEN side='BUY' THEN value ELSE -value END) FROM broker_flow_b
    """).fetchone()[0]
    out["A_frozen_store_total_net_value_whole_table"] = nv_sum

    # ---------- B. production broker_flow, top-25, Dataset A window ----------
    p = sqlite3.connect(f"file:{PROD}?mode=ro", uri=True)
    p.execute("PRAGMA query_only = ON;")
    rows = p.execute("""
        SELECT ticker, trade_date, SUM(value), SUM(abs(value)),
               SUM(CASE WHEN side='BUY' THEN lot ELSE -lot END)
        FROM broker_flow
        WHERE trade_date >= '2025-01-02' AND trade_date <= '2026-08-27'
        GROUP BY ticker, trade_date
    """).fetchall()
    pairs = [(nv, gv) for _, _, nv, gv, _ in rows]
    slots = [sl for _, _, _, _, sl in rows]
    out["B_prod_top25_datasetA_window"] = report("production top-25", pairs, signed_lots=slots)
    n_p = len(rows)
    out["B_prod_ge_0.2"] = sum(1 for nv, gv in pairs if gv and abs(nv / gv) >= 0.2)
    lot_rows = p.execute("""
        SELECT SUM(lot), SUM(abs(lot)) FROM (
            SELECT ticker, trade_date, SUM(lot) AS lot, SUM(abs(lot)) AS abs_lot
            FROM broker_flow
            WHERE trade_date >= '2025-01-02' AND trade_date <= '2026-08-27'
            GROUP BY ticker, trade_date)
    """).fetchone()
    # per-day distribution of SUM(lot) (the registered HYP-PM-0003 predictor)
    perday = p.execute("""
        SELECT lot FROM (
            SELECT ticker, trade_date, SUM(lot) AS lot
            FROM broker_flow
            WHERE trade_date >= '2025-01-02' AND trade_date <= '2026-08-27'
            GROUP BY ticker, trade_date)
    """).fetchall()
    perday = [x[0] for x in perday]
    out["B_prod_sum_lot_exact_zero_days"] = sum(1 for v in perday if v == 0)
    out["B_prod_sum_lot_exact_zero_pct"] = round(100 * sum(1 for v in perday if v == 0) / len(perday), 2)
    out["B_prod_sum_lot_days"] = len(perday)
    out["B_prod_total_lot_net_vs_abs_note"] = f"total_net={lot_rows[0]}, total_abs={lot_rows[1]}"
    out["B_prod_0.01_to_0.2"] = sum(1 for nv, gv in pairs
                                    if gv and 0.01 <= abs(nv / gv) < 0.2)
    out["B_prod_lt_0.01"] = sum(1 for nv, gv in pairs if gv and abs(nv / gv) < 0.01)

    # ---------- C. investor-type decomposition on the frozen store (C2) ----------
    # class nets are INTEGER-exact: SUM(value) per (ticker, session, investor_type)
    rows = s.execute("""
        SELECT ticker, trade_date, investor_type, SUM(value)
        FROM broker_flow_b GROUP BY ticker, trade_date, investor_type
    """).fetchall()
    agg = {}
    for tk, d, it, v in rows:
        cls = "F" if (it or "").startswith("Asing") else ("P" if (it or "").startswith("Pemer") else "L")
        agg.setdefault((tk, d), {})[cls] = agg.get((tk, d), {}).get(cls, 0) + v
    ident_exact = 0
    opp = 0
    both_nonzero = 0
    pem_dominant = 0
    for k, a in agg.items():
        f, l, pm = a.get("F", 0), a.get("L", 0), a.get("P", 0)
        if f + l + pm == 0:
            ident_exact += 1
        if f != 0 and l != 0:
            both_nonzero += 1
            if (f > 0) != (l > 0):
                opp += 1
        if abs(pm) > abs(f) and abs(pm) > abs(l):
            pem_dominant += 1
    out["C_investor_decomposition_frozen_store"] = {
        "cells": len(agg),
        "for_plus_loc_plus_pem_exact_zero_cells": ident_exact,
        "exact_identity_pct": round(100 * ident_exact / len(agg), 2) if agg else None,
        "cells_both_class_nets_nonzero": both_nonzero,
        "opposite_sign_cells": opp,
        "opposite_sign_pct": round(100 * opp / max(len(agg), 1), 2),
        "same_sign_cells": both_nonzero - opp,
        "pem_dominant_cells": pem_dominant,
    }

    # gross-participation and net-share C2 gates (execution vs descriptive forms)
    agg2 = {}
    for tk, d, it, side, av in s.execute("""
            SELECT ticker, trade_date, investor_type, side, SUM(abs(value))
            FROM broker_flow_b GROUP BY ticker, trade_date, investor_type, side"""):
        cls = "F" if (it or "").startswith("Asing") else ("P" if (it or "").startswith("Pemer") else "L")
        a = agg2.setdefault((tk, d), {})
        a[cls + side] = a.get(cls + side, 0) + av
    exec_gate = 0
    desc_gate = 0
    cells2 = [k for k in agg2 if k[0] not in
              set() ] # placeholder no-op
    for k, a in agg2.items():
        g = a.get("FBUY", 0) + a.get("FSELL", 0) + a.get("LBUY", 0) + a.get("LSELL", 0) \
            + a.get("PBUY", 0) + a.get("PSELL", 0)
        if g <= 0:
            continue
        f_net = a.get("FBUY", 0) - a.get("FSELL", 0)
        l_net = a.get("LBUY", 0) - a.get("LSELL", 0)
        f_g = (a.get("FBUY", 0) + a.get("FSELL", 0)) / g
        l_g = (a.get("LBUY", 0) + a.get("LSELL", 0)) / g
        if f_g >= 0.15 and l_g >= 0.15 and ((f_net > 0 and l_net < 0) or (f_net < 0 and l_net > 0)):
            exec_gate += 1
        if abs(f_net) / g >= 0.15 and abs(l_net) / g >= 0.15 \
                and ((f_net > 0 and l_net < 0) or (f_net < 0 and l_net > 0)):
            desc_gate += 1
    out["C_exec_gate_gross_participation_cells"] = exec_gate
    out["C_descriptive_net_share_gate_cells"] = desc_gate
    out_json = json.dumps(out, indent=1, sort_keys=True)
    with open("identity_audit_measurements.json", "w") as f:
        f.write(out_json)
    print(out_json)


if __name__ == "__main__":
    main()
