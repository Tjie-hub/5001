"""G1 one-shot runner for daily OIB continuation -- WRITTEN AT G0, NOT RUN.

Runs only with OIB_G1_APPROVED=1 after owner approval, and refuses if the census stop rule fired.
Pass conditions (frozen; ALL must hold):
  1. strength:     mean daily S_cc > 0 and Newey-West t (5 lags) >= BAR_FROZEN (N = 612, 3.2991)
  2. both halves:  mean S_cc > 0 for formations <= 2025-12-31 and for later formations
  3. incremental:  Fama-MacBeth OIB coefficient (controls: same-day return, log ADV, Parkinson-60)
                   mean > 0 and NW t >= 2.0
  4. next-open:    mean S_oc (open t+1 -> close t+1) > 0
  5. tradeable:    5-session blocks, next-open entry, net of cost_realised x turnover: mean net > 0
Report only: block gross and costs, monthly means, counts. Hashes re-verified before any outcome.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import oib as OI  # noqa: E402

OW = OI.OW
DAILY_SHA256 = "73a06abf1feecc1ad3ba098c771666bcd5ee02823e970a9136329999db3e448a"


def main():
    if os.environ.get("OIB_G1_APPROVED") != "1":
        raise SystemExit("G1 not approved: set OIB_G1_APPROVED=1 only after the owner approves the G0")
    census = json.loads((HERE / "CENSUS_G0.json").read_text())
    if census["stop_rule"]["fired"]:
        raise SystemExit("stop rule fired at G0: no G1")
    for p, h in ((OW.HL_SNAPSHOT, OW.HL_SHA256), (OW.WF_SNAPSHOT, OW.WF_SHA256), (OI.DAILY_CACHE, DAILY_SHA256)):
        if OW.sha256_file(p) != h:
            raise SystemExit(f"hash mismatch: {p}")
    import g0_census as GC
    import outcomes as OC  # only after every gate
    panel, daily, opens = OI.load_all()
    tbd = OI.tickers_by_day(daily)
    secs = []
    for d in GC.test_days(panel, daily):
        cs = OI.cross_section(panel, daily, tbd, [d])
        if len(cs["rows"]) >= OI.MIN_UNIVERSE:
            secs.append(cs)
    days, dcnt = OC.run_daily(panel, opens, secs)
    bdays = GC.blocks([cs["k"] for cs in secs])
    bsecs = [OI.cross_section(panel, daily, tbd, b) for b in bdays]
    blocks, bcnt = OC.run_blocks(panel, opens, bsecs)
    m, t, n = OC.newey_west_t([x["s_cc"] for x in days])
    h1 = OC.newey_west_t([x["s_cc"] for x in days if date.fromisoformat(x["k"]) <= OI.H1_LAST])
    h2 = OC.newey_west_t([x["s_cc"] for x in days if date.fromisoformat(x["k"]) > OI.H1_LAST])
    fm = OC.newey_west_t([x["fm"] for x in days])
    oc = OC.newey_west_t([x["s_oc"] for x in days])
    bn = OC.newey_west_t([x["net"] for x in blocks], lags=2)
    bg = OC.newey_west_t([x["gross"] for x in blocks], lags=2)
    v = {"strength": bool(m > 0 and t >= OI.BAR_FROZEN), "both_halves": bool(h1[0] > 0 and h2[0] > 0),
         "incremental": bool(fm[0] > 0 and fm[1] >= 2.0), "next_open": bool(oc[0] > 0),
         "tradeable": bool(bn[0] > 0)}
    v["pass"] = all(v.values())
    mon = {}
    for x in days:
        mon.setdefault(x["k"][:7], []).append(x["s_cc"])
    res = {"generated_utc": datetime.now(timezone.utc).isoformat(), "N": OI.N_FROZEN, "bar": OI.BAR_FROZEN,
           "daily": {"s_cc_mean": m, "s_cc_t": t, "n": n, "h1": h1, "h2": h2, "fm": fm, "s_oc": oc},
           "blocks": {"net": bn, "gross": bg, "mean_c1": sum(b["c1"] for b in blocks) / max(len(blocks), 1),
                      "mean_c5": sum(b["c5"] for b in blocks) / max(len(blocks), 1), "counts": bcnt},
           "verdict": v, "counts": dcnt,
           "by_month_s_cc": {k: round(sum(x) / len(x), 5) for k, x in sorted(mon.items())},
           "days_detail": days, "blocks_detail": blocks}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (HERE / f"RESULT_{stamp}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: res[k] for k in ("daily", "blocks", "verdict")}, indent=1, default=str))


if __name__ == "__main__":
    main()
