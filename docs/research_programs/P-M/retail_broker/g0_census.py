"""G0 census for the online-retail broker imbalance study (D-086). COUNTS ONLY.

Never imports outcomes.py. Every quantity is known at or before each formation close, except the
power estimate: weekly random-quintile spreads on the same 98 names over 2023-01-02 .. 2024-12-31,
which is before the formation window and carries no broker signal (hard-asserted).

Writes CENSUS_G0.json, including the frozen stop-rule decision.
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

import flow as FL  # noqa: E402

OW = FL.OW
POWER_FROM, POWER_TO = date(2023, 1, 2), date(2024, 12, 31)
SEED = 20261009


def block_days(wks, i):
    return [d for w in wks[i:i + FL.BLOCK_WEEKS] for d in w]


def power(panel, tickers):
    assert POWER_TO < date(2025, 1, 2)
    wks = [w for w in FL.weeks(panel.sessions) if w[0] >= POWER_FROM and w[-1] <= POWER_TO]
    rng = random.Random(SEED)
    sp = []
    for a, b in zip(wks[:-1], wks[1:]):
        k0, k1 = a[-1], b[-1]
        assert k1 <= POWER_TO
        rs = []
        for t in tickers:
            g = panel.tickers.get(t)
            if g is None or k0 not in g["idx"]:
                continue
            i = g["idx"][k0]
            if not (g["adv"][i] >= FL.ADV_MIN) or g["c"][i] < FL.PRICE_MIN:
                continue
            j, acc, ok = i + 1, 1.0, True
            while j < len(g["d"]) and g["d"][j] <= k1:
                r = (g["c"][j] + panel.divs.get((t, g["d"][j]), 0.0)) / g["c"][j - 1] - 1
                if not np.isfinite(r) or abs(r) > OW.BAD_PRINT:
                    ok = False
                    break
                acc *= 1 + r
                j += 1
            if ok:
                rs.append(acc - 1)
        if len(rs) < 25:
            continue
        rng.shuffle(rs)
        k = len(rs) // 5
        sp.append(float(np.mean(rs[:k]) - np.mean(rs[-k:])))
    return np.asarray(sp)


def main():
    t0 = time.time()
    assert OW.sha256_file(OW.HL_SNAPSHOT) == OW.HL_SHA256
    assert OW.sha256_file(OW.WF_SNAPSHOT) == OW.WF_SHA256
    panel, tickers, daily = FL.load_all()
    wks = FL.formation_weeks(panel)
    secs, per = [], []
    for w in wks:
        cs = FL.cross_section(panel, daily, tickers, w)
        secs.append(cs)
        q1, q5, n = FL.quintiles(cs["rows"])
        per.append({"k": cs["k"].isoformat(), "sessions": len(w), "universe": len(cs["rows"]),
                    "quintile": n // 5, "drop": cs["drop"],
                    "r_present_mean": round(float(np.mean([r["r_present"] for r in cs["rows"]])), 4) if cs["rows"] else None})
    testable = per[:-1]
    # tradeability blocks: every BLOCK_WEEKS-th week from the first, signal over the block's weeks
    blocks = []
    for i in range(0, len(wks) - FL.BLOCK_WEEKS + 1, FL.BLOCK_WEEKS):
        blocks.append(FL.cross_section(panel, daily, tickers, block_days(wks, i)))
    rows = [r for cs in secs for r in cs["rows"]]
    ri = np.asarray([r["ri"] for r in rows])
    rho_fi = float(spearmanr(ri, [r["fi"] for r in rows]).correlation)
    rho_prior = float(spearmanr(ri, [r["prior"] for r in rows]).correlation)
    sp = power(panel, tickers)
    sd = float(sp.std(ddof=1))
    n = len(testable)
    mde = (FL.BAR_FROZEN + 0.8416) * sd / math.sqrt(n)
    pw = float(1 - norm.cdf(FL.BAR_FROZEN - FL.STOP_EFFECT_WEEKLY * math.sqrt(n) / sd))
    stop = pw < FL.STOP_POWER_MIN
    out = {
        "study": "online-retail broker imbalance {RF}, D-086", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "snapshots": {"history_long": OW.HL_SHA256, "walkforward": OW.WF_SHA256, "verified": True},
        "census": {"ledger_before": FL.CENSUS_LEDGER, "arms": FL.N_ARMS, "N": FL.N_FROZEN,
                   "bar_exact": round(FL.BAR_EXACT, 6), "bar_frozen": FL.BAR_FROZEN},
        "panel": {"tickers": len(tickers), "r_group": FL.R_GROUP,
                  "formation_window_excluded": ["2025-01-02", FL.FORMATION_WINDOW_END.isoformat()]},
        "weeks": {"total": len(per), "testable": n, "first_k": per[0]["k"], "last_testable_k": testable[-1]["k"],
                  "h1_le_2025_12_31": sum(1 for p in testable if p["k"] <= "2025-12-31"),
                  "h2": sum(1 for p in testable if p["k"] > "2025-12-31"),
                  "blocks_4w": len(blocks), "block_spreads_testable": max(len(blocks) - 1, 0)},
        "universe": {"median": int(np.median([p["universe"] for p in testable])),
                     "min": min(p["universe"] for p in testable), "max": max(p["universe"] for p in testable),
                     "quintile_median": int(np.median([p["quintile"] for p in testable])),
                     "drop_totals": {k: sum(p["drop"][k] for p in per) for k in per[0]["drop"]}},
        "signal": {"ri_quantiles": {f"p{q}": round(float(np.quantile(ri, q / 100)), 4) for q in (5, 25, 50, 75, 95)},
                   "r_broker_presence_mean": round(float(np.mean([r["r_present"] for r in rows])), 4),
                   "spearman_ri_vs_foreign_imbalance": round(rho_fi, 4),
                   "spearman_ri_vs_formation_week_return": round(rho_prior, 4)},
        "power": {"pre_sample": [POWER_FROM.isoformat(), POWER_TO.isoformat()], "weeks": len(sp),
                  "sd_random_weekly_spread": round(sd, 5), "n_test_weeks": n,
                  "mde_weekly_at_bar_80pct": round(mde, 5),
                  "power_at_0p30pct_week": round(pw, 4)},
        "stop_rule": {"rule": f"power at {FL.STOP_EFFECT_WEEKLY:.2%}/week < {FL.STOP_POWER_MIN:.0%} -> no G1",
                      "fired": bool(stop)},
        "per_week": per,
        "runtime_s": round(time.time() - t0, 1),
    }
    (HERE / "CENSUS_G0.json").write_text(json.dumps(out, indent=1, default=list))
    print(json.dumps({k: out[k] for k in ("census", "panel", "weeks", "universe", "signal", "power", "stop_rule")}, indent=1, default=list))


if __name__ == "__main__":
    main()
