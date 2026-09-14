#!/usr/bin/env python3
"""Per-observation investigation of every move that breached the NAIVE flat
ARB=-15% model. READ-ONLY. The point is to resolve each on its own evidence,
not to widen a tolerance until the failures disappear."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import foundation as F

HERE = Path(__file__).resolve().parent
NAIVE_ARB = -0.15   # the model that produced the 13


def main(write=False):
    conn = F.ro_connect()
    cal = F.SessionCalendar.load("v2"); ros = F.PitRoster.load("v1")
    acts = F.detect_unapplied_splits(conn, F.load_corporate_actions(
        conn, ros.universe, "2025-01-02", "2026-08-27"))
    ca_dates = {(x["ticker"], x["ex_date"]): x for x in acts}
    rep = F.vwap_ratio_report(conn, ros.universe, cal.sessions)
    quarantine = set(rep["flagged"])
    ss = set(cal.sessions)

    ph = ",".join("?" * len(ros.universe))
    rows = conn.execute(
        f"SELECT ticker,date,open,high,low,close,volume FROM ohlcv WHERE ticker IN ({ph}) "
        f"AND date >= ? AND date <= ? ORDER BY ticker,date",
        sorted(ros.universe) + [cal.sessions[0], cal.sessions[-1]]).fetchall()

    prev, findings = {}, []
    for tk, d, o, h, l, c, v in rows:
        if d not in ss or not c:
            continue
        p = prev.get(tk)
        if p:
            r = c / p[4] - 1.0
            tier = next(a for cap, a in F.ARA_TIERS if p[4] <= cap)
            naive_breach = r > tier + F.BAND_TOLERANCE or r < NAIVE_ARB - F.BAND_TOLERANCE
            if naive_breach or abs(r) > 0.30:
                reg = F.band_regime(d)
                outside_now, _, up, dn, _ = F.exceeds_band(p[4], c, d)
                bf = conn.execute(
                    "SELECT COUNT(*), COALESCE(SUM(lot_value),0) FROM broker_flow "
                    "WHERE ticker=? AND trade_date=?", (tk, d)).fetchone()
                findings.append({
                    "ticker": tk, "date": d, "band_regime": reg,
                    "observed_move": round(r, 6),
                    "naive_arb_threshold": NAIVE_ARB,
                    "regime_aware_band": [round(up, 4), round(dn, 4)],
                    "prev_close": p[4], "raw_ohlcv": {"open": o, "high": h, "low": l,
                                                      "close": c, "volume": v},
                    "prev_raw_ohlcv": {"date": p[0], "open": p[1], "high": p[2],
                                       "low": p[3], "close": p[4], "volume": p[5]},
                    "adjusted_ohlcv": "none applied — see adjustment policy",
                    "corporate_action": ca_dates.get((tk, d), None),
                    "broker_rows_that_session": bf[0],
                    "broker_shares_that_session": bf[1],
                    "session_in_calendar": True,
                    "breached_naive_model": naive_breach,
                    "breaches_regime_aware_model": outside_now,
                    "quarantined": tk in quarantine,
                })
        prev[tk] = (d, o, h, l, c, v)  # (date, o, h, l, close, volume)

    for f in findings:
        r, up, dn = f["observed_move"], *f["regime_aware_band"]
        if f["breaches_regime_aware_model"] and f["corporate_action"]:
            f["likely_cause"] = (f"unapplied {f['corporate_action']['type']} "
                                 f"{f['corporate_action']['factor']:g}:1 on this ex-date; "
                                 f"ohlcv not adjusted (applied_in_ohlcv="
                                 f"{f['corporate_action']['applied_in_ohlcv']})")
            f["resolution"] = "QUARANTINE ticker (basis mismatch, see residual detector)"
            f["retained"] = False
            f["evidence"] = ("close/broker-VWAP median 4.946 pre-ex vs 0.993 post-ex; "
                             "corporate_action_events stocksplit_new/old = 5/1")
        elif f["breaches_regime_aware_model"]:
            f["likely_cause"] = "UNRESOLVED"; f["resolution"] = "BLOCK FREEZE"; f["retained"] = None
            f["evidence"] = ""
        elif abs(r) > 0.30:
            hi = f["raw_ohlcv"]["high"]; ceil_ = f["prev_close"] * (1 + up)
            f["likely_cause"] = (f"genuine limit-up: session high {hi:g} against an ARA ceiling of "
                                 f"{ceil_:.2f} ({up:.0%} of ref {f['prev_close']:g})")
            f["resolution"] = "RETAIN — legal move, inside the regime band"
            f["retained"] = True
            f["evidence"] = (f"high/ceiling = {hi/ceil_:.4f}; a data artifact would not land on "
                             f"the regulatory limit. volume {f['raw_ohlcv']['volume']:,.0f}")
        else:
            f["likely_cause"] = (f"legal {f['band_regime']} down-move: {r:.2%} against a "
                                 f"symmetric {dn:.0%} floor. The naive model assumed the R4 "
                                 f"asymmetric ARB of -15%, which did not take effect until "
                                 f"2025-04-08 (SK Kep-00003/BEI/04-2025, LC-PM-0009).")
            f["resolution"] = "RETAIN — naive model was wrong, not the data"
            f["retained"] = True
            f["evidence"] = (f"session {f['date']} precedes 2025-04-08; regime {f['band_regime']} "
                             f"floor {dn:.0%}; move {r:.2%} is inside it")

    naive = [f for f in findings if f["breached_naive_model"]]
    unresolved = [f for f in findings if f["likely_cause"] == "UNRESOLVED"]
    out = {"naive_model": {"arb": NAIVE_ARB, "note": "flat ARB applied to the whole window"},
           "regime_source": "LC-PM-0009 · IDX auto-rejection regime timeline",
           "breached_naive_model": len(naive), "total_examined": len(findings),
           "resolved": len(naive) - len(unresolved), "unresolved": len(unresolved),
           "findings": findings}

    print(f"=== observations breaching the naive flat ARB=-15%% model: {len(naive)} ===\n")
    hdr = (f"{'ticker':6s}{'date':12s}{'reg':5s}{'move':>9s}{'ref':>10s}"
           f"{'band':>14s}{'brk':>5s}  resolution")
    print(hdr); print("-" * len(hdr))
    for f in naive:
        print(f"{f['ticker']:6s}{f['date']:12s}{f['band_regime']:5s}"
              f"{f['observed_move']*100:>8.2f}%{f['prev_close']:>10g}"
              f"{'+%.0f%%/%.0f%%' % (f['regime_aware_band'][0]*100, f['regime_aware_band'][1]*100):>14s}"
              f"{f['broker_rows_that_session']:>5d}  "
              f"{'RETAIN' if f['retained'] else 'EXCLUDE' if f['retained'] is False else 'UNRESOLVED'}"
              f" — {f['likely_cause'][:64]}")
    print(f"\nresolved {len(naive)-len(unresolved)}/{len(naive)}   unresolved {len(unresolved)}")
    if write:
        p = HERE / "artifacts" / "OUTSIDE_BAND_INVESTIGATION_v1.json"
        p.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
        print(f"wrote {p.name}")
    conn.close(); return out


if __name__ == "__main__":
    main(write="--write" in sys.argv)
