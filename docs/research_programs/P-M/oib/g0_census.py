"""G0 census for daily OIB continuation (D-088). COUNTS ONLY -- never imports outcomes.py.

Power uses daily random-quintile close-to-close spreads over 2023-01-02 .. 2024-12-31 (history_long;
before any OIB data exists, no signal), hard-asserted pre-sample.
"""
from __future__ import annotations

import json
import math
import random
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import norm, spearmanr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import oib as OI  # noqa: E402

OW = OI.OW
P_FROM, P_TO = date(2023, 1, 2), date(2024, 12, 31)
SEED = 20261009


def test_days(panel, daily):
    have = {d for (_, d) in daily}
    return [d for d in panel.sessions if d in have]


def blocks(days):
    return [days[i:i + OI.BLOCK] for i in range(0, len(days) - OI.BLOCK + 1, OI.BLOCK)]


def pre_sample_power(panel):
    assert P_TO < date(2025, 1, 2)
    sess = [d for d in panel.sessions if P_FROM <= d <= P_TO]
    rng = random.Random(SEED)
    sp, ks = [], []
    for a, b in zip(sess[:-1], sess[1:]):
        assert b <= P_TO
        rs = []
        for t, g in panel.tickers.items():
            i = g["idx"].get(a)
            j = g["idx"].get(b)
            if i is None or j is None or j != i + 1 or i < 61:
                continue
            if not (g["adv"][i] >= OI.ADV_MIN) or g["c"][i] < OI.PRICE_MIN:
                continue
            r = (g["c"][j] + panel.divs.get((t, b), 0.0)) / g["c"][i] - 1
            if np.isfinite(r) and abs(r) <= OW.BAD_PRINT:
                rs.append(r)
        if len(rs) < 50:
            continue
        rng.shuffle(rs)
        k = len(rs) // 5
        ks.append(k)
        sp.append(float(np.mean(rs[:k]) - np.mean(rs[-k:])))
    return np.asarray(sp), int(np.median(ks))


def main():
    t0 = time.time()
    assert OW.sha256_file(OW.HL_SNAPSHOT) == OW.HL_SHA256
    assert OW.sha256_file(OW.WF_SNAPSHOT) == OW.WF_SHA256
    panel, daily, _ = OI.load_all()
    tbd = OI.tickers_by_day(daily)
    days = test_days(panel, daily)
    per, secs = [], []
    for d in days:
        cs = OI.cross_section(panel, daily, tbd, [d])
        n = len(cs["rows"])
        per.append({"k": d.isoformat(), "universe": n, "quintile": n // 5, "test_day": n >= OI.MIN_UNIVERSE,
                    "drop": cs["drop"]})
        if n >= OI.MIN_UNIVERSE:
            secs.append(cs)
    test = [p for p in per if p["test_day"]][:-1]   # the last test day has no t+1 inside the snapshot
    rows = [r for cs in secs for r in cs["rows"]]
    rho = float(spearmanr([r["oib"] for r in rows], [r["r_t"] for r in rows]).correlation)
    bl = blocks([date.fromisoformat(p["k"]) for p in per if p["test_day"]])
    sp, k_pre = pre_sample_power(panel)
    sd_pre = float(sp.std(ddof=1))
    k_test = int(np.median([p["quintile"] for p in test]))
    sd = sd_pre * math.sqrt(k_pre / k_test)
    n = len(test)
    pw = float(1 - norm.cdf(OI.BAR_FROZEN - OI.STOP_EFFECT_DAILY * math.sqrt(n) / sd))
    pw_unscaled = float(1 - norm.cdf(OI.BAR_FROZEN - OI.STOP_EFFECT_DAILY * math.sqrt(n) / sd_pre))
    mde = (OI.BAR_FROZEN + 0.8416) * sd / math.sqrt(n)
    out = {
        "study": "daily OIB continuation, D-088", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "snapshots": {"history_long": OW.HL_SHA256, "walkforward": OW.WF_SHA256, "verified": True},
        "census": {"ledger_before": OI.CENSUS_LEDGER, "arms": OI.N_ARMS, "N": OI.N_FROZEN,
                   "bar_exact": round(OI.BAR_EXACT, 6), "bar_frozen": OI.BAR_FROZEN},
        "days": {"sessions_with_flow": len(per), "test_days": len(per) - sum(not p["test_day"] for p in per),
                 "testable": n, "first": test[0]["k"], "last_testable": test[-1]["k"],
                 "thin_days_excluded": [p["k"] for p in per if not p["test_day"]][:40],
                 "h1_le_2025_12_31": sum(1 for p in test if p["k"] <= "2025-12-31"),
                 "h2": sum(1 for p in test if p["k"] > "2025-12-31"),
                 "blocks_5d": len(bl), "block_spreads_testable": max(len(bl) - 1, 0)},
        "universe": {"median": int(np.median([p["universe"] for p in test])),
                     "min": min(p["universe"] for p in test), "max": max(p["universe"] for p in test),
                     "quintile_median": k_test,
                     "drop_totals": {kk: sum(p["drop"][kk] for p in per) for kk in per[0]["drop"]}},
        "signal": {"oib_quantiles": {f"p{q}": round(float(np.quantile([r['oib'] for r in rows], q / 100)), 4)
                                     for q in (5, 25, 50, 75, 95)},
                   "spearman_oib_vs_same_day_return": round(rho, 4)},
        "power": {"pre_sample": [P_FROM.isoformat(), P_TO.isoformat()], "days": len(sp),
                  "sd_pre": round(sd_pre, 5), "k_pre": k_pre, "k_test": k_test, "sd_test_scaled": round(sd, 5),
                  "n_test_days": n, "mde_daily_at_bar_80pct": round(mde, 5),
                  "power_at_0p10pct_day": round(pw, 4), "power_unscaled_sd": round(pw_unscaled, 4)},
        "stop_rule": {"rule": f"power at {OI.STOP_EFFECT_DAILY:.2%}/day < {OI.STOP_POWER_MIN:.0%} -> no G1",
                      "fired": bool(pw < OI.STOP_POWER_MIN)},
        "per_day": per,
        "runtime_s": round(time.time() - t0, 1),
    }
    (HERE / "CENSUS_G0.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("census", "days", "universe", "signal", "power", "stop_rule")}, indent=1))


if __name__ == "__main__":
    main()
